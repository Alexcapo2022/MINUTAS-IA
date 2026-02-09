from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import engine


def test_db_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[DB] ✅ Conexión OK")
        return True
    except SQLAlchemyError as e:
        print(f"[DB] ❌ Error conectando a la BD: {str(e)}")
        return False
