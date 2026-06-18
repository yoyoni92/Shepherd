"""T2 - DB-blindness: assistant.py must not import Fleet API / RAG / DB clients."""
import ast
from pathlib import Path


ASSISTANT_SRC = Path(__file__).parent.parent / "app" / "assistant.py"
FORBIDDEN = {"fleet", "rag", "sqlalchemy", "psycopg", "shepherd_db", "database"}


def _imports(src: str) -> set[str]:
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def test_no_forbidden_imports():
    imports = _imports(ASSISTANT_SRC.read_text())
    hits = imports & FORBIDDEN
    assert not hits, f"assistant.py imports DB/Fleet/RAG modules: {hits}"
