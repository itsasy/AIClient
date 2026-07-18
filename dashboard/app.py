import logging
from functools import wraps

from flask import Flask, request, jsonify, abort

from core.config import Config
from core.orchestrator import Orchestrator
from core.standards_learner import StandardsLearner

logger = logging.getLogger(__name__)

app = Flask(__name__)
orchestrator = Orchestrator()
learner = StandardsLearner()


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != Config.DASHBOARD_API_KEY:
            logger.warning(
                "Intento de acceso no autorizado desde %s", request.remote_addr
            )
            abort(401, description="API Key inválida o no proporcionada.")
        return f(*args, **kwargs)

    return decorated


@app.route("/api/ask", methods=["POST"])
@require_api_key
def ask():
    data = request.json or {}
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
    data = request.json or {}
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


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "provider": Config.DEFAULT_PROVIDER})


if __name__ == "__main__":
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
