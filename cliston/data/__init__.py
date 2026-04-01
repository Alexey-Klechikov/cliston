import os
from pathlib import Path

DATA_DIR_PATH = Path(os.path.dirname(os.path.abspath(__file__)))

DB_DIR_PATH = DATA_DIR_PATH / "tables"
DB_DIR_PATH.mkdir(parents=True, exist_ok=True)
DB_PATH_GARM_INTELLIGENCE = DB_DIR_PATH / "garm_intelligence.db"

BOOKS_DIR_PATH = DATA_DIR_PATH / "books"
BOOKS_DIR_PATH.mkdir(parents=True, exist_ok=True)

VECTORSTORE_DIR_PATH = DATA_DIR_PATH / "vectorstore"
VECTORSTORE_DIR_PATH.mkdir(parents=True, exist_ok=True)
