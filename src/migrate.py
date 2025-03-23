import os

from dotenv import load_dotenv

load_dotenv(override=True)
import psycopg2

DB_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

DATABASE_URL = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"


def execute_sql_file(filename):
    with open(filename, 'r') as file:
        sql = file.read()

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        print(f"✅ Successfully executed: {filename}")
    except Exception as e:
        print(f"❌ Error executing {filename}: {e}")
    finally:
        if conn:
            conn.close()


def migrate():
    sql_dir = "scripts"
    if not os.path.exists(sql_dir):
        print(f"❌ Error: Directory '{sql_dir}' does not exist!")
        return

    sql_files = sorted([f for f in os.listdir(sql_dir) if f.endswith(".sql")])

    if not sql_files:
        print("⚠️ No SQL files found in 'src/scripts'.")
        return

    for sql_file in sql_files:
        print(f"🚀 Executing {sql_file}...")
        execute_sql_file(os.path.join(sql_dir, sql_file))


if __name__ == "__main__":
    migrate()
