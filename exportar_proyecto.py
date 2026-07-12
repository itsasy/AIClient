import os
from pathlib import Path

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

# Carpeta raíz del proyecto (la carpeta donde se encuentra este script)
PROJECT_ROOT = Path(__file__).parent.resolve()

# Archivo de salida
OUTPUT_FILE = PROJECT_ROOT / "codigo_proyecto.txt"

# Extensiones de archivos que se incluirán
INCLUDED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".sql",
    ".md",
    ".txt",
    ".ini",
    ".cfg",
    ".toml",
    ".java",
    ".kt",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".php",
    ".swift",
    ".dart",
    ".vue",
    ".sh",
    ".bat",
    ".ps1",
}

# Carpetas que no se recorrerán
EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".idea",
    ".vscode",
    ".vs",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".cache",
    ".next",
    ".nuxt",
    ".terraform",
    "bin",
    "obj",
}

# Archivos que nunca se incluirán
EXCLUDED_FILES = {
    OUTPUT_FILE.name,
    "exportar_proyecto.py",

    # Variables de entorno
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.test",

    # Locks
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",

    # Otros
    ".DS_Store",
    "Thumbs.db",
}


# ==============================================================================
# FUNCIONES
# ==============================================================================

def debe_incluir(path: Path) -> bool:
    """Indica si un archivo debe exportarse."""

    if path.name in EXCLUDED_FILES:
        return False

    return path.suffix.lower() in INCLUDED_EXTENSIONS


def escribir_separador(f, titulo):
    f.write("\n")
    f.write("=" * 100 + "\n")
    f.write(titulo + "\n")
    f.write("=" * 100 + "\n\n")


# ==============================================================================
# EXPORTACIÓN
# ==============================================================================

cantidad = 0

with open(OUTPUT_FILE, "w", encoding="utf-8") as salida:

    escribir_separador(
        salida,
        f"PROYECTO: {PROJECT_ROOT}"
    )

    for root, dirs, files in os.walk(PROJECT_ROOT):

        # Excluir carpetas
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED_DIRS)

        for archivo in sorted(files):

            ruta = Path(root) / archivo

            if not debe_incluir(ruta):
                continue

            relativa = ruta.relative_to(PROJECT_ROOT)

            escribir_separador(
                salida,
                f"ARCHIVO: {relativa}"
            )

            try:
                with open(ruta, "r", encoding="utf-8") as f:
                    salida.write(f.read())
                    salida.write("\n\n")
                    cantidad += 1

            except UnicodeDecodeError:
                salida.write("[No se pudo leer el archivo: codificación no compatible]\n\n")

            except Exception as e:
                salida.write(f"[ERROR] {e}\n\n")

print("=" * 60)
print("EXPORTACIÓN FINALIZADA")
print("=" * 60)
print(f"Archivos exportados : {cantidad}")
print(f"Salida              : {OUTPUT_FILE}")
print("=" * 60)