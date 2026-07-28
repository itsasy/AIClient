import logging
import tempfile
import hmac

from functools import wraps
from pathlib import Path

from flask import Flask, request, jsonify, abort

from core.config import Config
from core.document_ingestor import DocumentIngestor
from core.engram_memory import EngramMemory
from core.orchestrator import Orchestrator
from core.spec_manager import SpecManager
from core.standards_learner import StandardsLearner

logger = logging.getLogger(__name__)

app = Flask(__name__)
orchestrator = Orchestrator()
learner = StandardsLearner()
engram_memory = EngramMemory()
spec_manager = SpecManager()
ingestor = DocumentIngestor()


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or not hmac.compare_digest(api_key, Config.DASHBOARD_API_KEY):
            logger.warning(
                "Intento de acceso no autorizado desde %s", request.remote_addr
            )
            abort(401, description="API Key inválida o no proporcionada.")
        return f(*args, **kwargs)

    return decorated


@app.route("/api/health", methods=["GET"])
def health():
    """Endpoint público para verificar que el servidor está vivo."""
    return jsonify({"status": "ok", "provider": Config.DEFAULT_PROVIDER})


@app.route("/api/ask", methods=["POST"])
@require_api_key
def ask():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    if not query:
        return jsonify({"error": "El campo 'query' es obligatorio."}), 400

    try:
        response = orchestrator.process(query)
        return jsonify({"response": response})
    except Exception as e:
        logger.exception("Error procesando consulta: %s", query[:50])
        return jsonify({"error": str(e)}), 500


@app.route("/api/learn", methods=["POST"])
@require_api_key
def learn():
    data = request.get_json(silent=True) or {}
    key = data.get("key")
    value = data.get("value")
    if not key or not value:
        return jsonify({"error": "Faltan 'key' o 'value'."}), 400

    try:
        learner.learn(key, value)
        return jsonify({"status": "learned", "key": key})
    except Exception as e:
        logger.exception("Error aprendiendo estándar: %s", key)
        return jsonify({"error": str(e)}), 500


@app.route("/api/memory/search", methods=["GET"])
@require_api_key
def memory_search():
    """Busca memorias en Engram."""
    query = request.args.get("q", "")
    limit = int(request.args.get("limit", 5))
    if not query:
        return jsonify({"error": "Falta el parámetro 'q'"}), 400

    results = engram_memory.recall(query, limit=limit)
    return jsonify({"results": results})


@app.route("/api/specs/list", methods=["GET"])
@require_api_key
def specs_list():
    """Lista todas las especificaciones."""
    specs = spec_manager.list_specs()
    return jsonify({"specs": specs})


@app.route("/api/specs/load", methods=["GET"])
@require_api_key
def specs_load():
    """Carga una especificación por nombre."""
    name = request.args.get("name")
    if not name:
        return jsonify({"error": "Falta el parámetro 'name'"}), 400
    spec = spec_manager.load_spec_by_name(name)
    if not spec:
        return jsonify({"error": f"Spec '{name}' no encontrada"}), 404
    return jsonify(spec)


@app.route("/api/stats", methods=["GET"])
@require_api_key
def stats():
    """Devuelve estadísticas del sistema."""
    stats_data = engram_memory.stats()
    if not stats_data:
        return jsonify({"error": "No se pudieron obtener estadísticas"}), 500
    stats_data["providers"] = {
        "code": Config.CODE_PROVIDER,
        "architecture": Config.ARCHITECTURE_PROVIDER,
        "fast": getattr(Config, "FAST_PROVIDER", "None"),
    }
    return jsonify(stats_data)


@app.route("/api/ingest", methods=["POST"])
@require_api_key
def ingest_file():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ningún archivo"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
        ) as tmp:
            file.save(tmp.name)
            tmp_path = Path(tmp.name)

        success = ingestor.ingest_file(tmp_path, tags=["uploaded_via_api"])
        if success:
            return jsonify(
                {
                    "status": "ok",
                    "message": f"Documento '{file.filename}' ingerido correctamente",
                }
            )
        else:
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"No se pudo ingerir '{file.filename}'",
                    }
                ),
                500,
            )
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


if __name__ == "__main__":
    Config.validate()

    logger.info(
        "🚀 Dashboard iniciado en http://%s:%s",
        Config.DASHBOARD_HOST,
        Config.DASHBOARD_PORT,
    )
    logger.info("🔑 API Key requerida en header: X-API-Key")
    app.run(
        host=Config.DASHBOARD_HOST,
        port=Config.DASHBOARD_PORT,
        debug=Config.DASHBOARD_DEBUG,
    )
