import pyodbc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Try both common driver versions automatically ─────────────────────────────
DRIVERS = [
    "ODBC Driver 17 for SQL Server",
    "ODBC Driver 18 for SQL Server",
    "SQL Server",                      # fallback: built-in Windows driver
]

SERVER   = r"DESKTOP-JGD7VJ0\SQLEXPRESS01"   # raw string — backslash safe
DATABASE = "DigitalActivityFlowSystem"


def get_connection() -> pyodbc.Connection:
    last_error = None

    for driver in DRIVERS:
        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={SERVER};"
            f"DATABASE={DATABASE};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
            f"Connection Timeout=10;"
        )
        try:
            conn = pyodbc.connect(conn_str, autocommit=False)
            logger.info(f"✅ Connected using: {driver}")
            return conn
        except pyodbc.Error as e:
            logger.warning(f"❌ Driver '{driver}' failed: {e}")
            last_error = e

    raise RuntimeError(
        f"\n\n🔴 Could not connect to SQL Server.\n"
        f"Last error: {last_error}\n\n"
        f"Checklist:\n"
        f"  1. Open Services (services.msc) → is 'SQL Server (SQLEXPRESS01)' Running?\n"
        f"  2. Run in terminal: odbcad32  → check ODBC drivers installed\n"
        f"  3. Server name correct? → {SERVER}\n"
        f"  4. Database exists?    → {DATABASE}\n"
    )


def list_installed_drivers() -> list:
    return [d for d in pyodbc.drivers() if "SQL Server" in d]


# ── Quick test: run this file directly to verify connection ───────────────────
if __name__ == "__main__":
    print("Installed SQL Server drivers:", list_installed_drivers())
    print("Attempting connection…")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DB_NAME(), GETDATE()")
        db, dt = cursor.fetchone()
        print(f"✅ Connected!  Database: {db}  |  Server time: {dt}")
        conn.close()
    except RuntimeError as e:
        print(e)