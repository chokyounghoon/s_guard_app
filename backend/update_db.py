from sqlalchemy import create_engine, text
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://sguard_user:sguard_password@localhost:5433/sguard_db")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS code VARCHAR(50) UNIQUE;"))
        conn.commit()
    print("Column 'code' added successfully.")
except Exception as e:
    print(f"Error: {e}")
