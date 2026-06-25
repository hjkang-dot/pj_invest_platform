import sys
import os

# Add backend root to sys.path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.db import init_db

def main():
    print("[System] Initializing database...")
    init_db()
    print("[System] Database initialization verification finished.")

if __name__ == "__main__":
    main()
