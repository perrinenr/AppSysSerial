import os
import sys
import re
from datetime import date, timedelta

import pyodbc


def app_path() -> str:
    """Return folder path for normal Python run or PyInstaller exe."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def config_path() -> str:
    return os.path.join(app_path(), "config.txt")


def get_available_sql_driver() -> str:
    """
    Try several SQL Server ODBC drivers and return the first installed one.
    """

    installed = pyodbc.drivers()

    possible = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13.1 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "ODBC Driver 11 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server Native Client 10.0",
        "SQL Server",
    ]

    for driver in possible:
        if driver in installed:
            return driver

    raise Exception(
        "No SQL Server ODBC driver found. "
        "Please install ODBC Driver 17 or 18 for SQL Server."
    )


def read_config() -> dict:
    """Read KEY=VALUE pairs from config.txt."""
    path = config_path()

    if not os.path.exists(path):
        raise FileNotFoundError(f"config.txt not found at: {path}")

    config = {}

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            config[key.strip().upper()] = value.strip()

    required = ["SERVER", "DATABASE"]
    missing = [key for key in required if not config.get(key)]

    if missing:
        raise ValueError(
            f"Missing required setting(s) in config.txt: {', '.join(missing)}"
        )

    config.setdefault("TRUST_SERVER_CERTIFICATE", "yes")
    config.setdefault("TRUSTED_CONNECTION", "yes")

    return config


def get_db_name() -> str:
    return read_config()["DATABASE"]


def get_server_name() -> str:
    return read_config()["SERVER"]


def get_driver_name() -> str:
    """
    If DRIVER is written in config.txt, use it.
    If DRIVER is missing or DRIVER=AUTO, detect automatically.
    """

    cfg = read_config()
    driver_from_config = cfg.get("DRIVER", "AUTO").strip()

    installed = pyodbc.drivers()

    if driver_from_config and driver_from_config.upper() != "AUTO":
        if driver_from_config in installed:
            return driver_from_config

        raise Exception(
            f"The driver '{driver_from_config}' is not installed on this PC. "
            f"Installed drivers are: {installed}"
        )

    return get_available_sql_driver()


def build_connection_string() -> str:
    cfg = read_config()

    driver_name = get_driver_name()

    parts = [
        f"DRIVER={{{driver_name}}}",
        f"SERVER={cfg['SERVER']}",
        f"DATABASE={cfg['DATABASE']}",
        f"Trusted_Connection=yes",
        f"TrustServerCertificate={cfg.get('TRUST_SERVER_CERTIFICATE', 'yes')}",
    ]

    encrypt = cfg.get("ENCRYPT")
    if encrypt:
        parts.append(f"Encrypt={encrypt}")

    return ";".join(parts) + ";"


def get_connection():
    return pyodbc.connect(build_connection_string(), timeout=10)


def get_serial_count() -> int:
    """Used by the GUI to show that DB is reachable."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dbo.AppSysSerial")
        return int(cur.fetchone()[0])


def preview_serial(sn: str) -> dict:
    """
    Preview serial information without changing the database.

    This function:
    - Checks if SN exists.
    - Reads ValidityDays from database.
    - Calculates current date.
    - Calculates expiry date.
    - Does NOT update ExpiryDate in SQL Server.
    """

    sn = (sn or "").strip()

    if not re.fullmatch(r"\d{13}", sn):
        return {
            "success": False,
            "message": "Serial number must be exactly 13 digits.",
            "sn": sn,
        }

    try:
        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT SN, ValidityDays, ExpiryDate
                FROM dbo.AppSysSerial
                WHERE SN = ?
                """,
                sn,
            )

            row = cur.fetchone()

            if not row:
                return {
                    "success": False,
                    "message": "Serial number not found.",
                    "sn": sn,
                }

            validity_days = row.ValidityDays
            old_expiry_date = row.ExpiryDate

            if validity_days is None:
                return {
                    "success": False,
                    "message": "ValidityDays is missing for this serial.",
                    "sn": sn,
                }

            try:
                validity_days = int(validity_days)
            except Exception:
                return {
                    "success": False,
                    "message": "ValidityDays is invalid.",
                    "sn": sn,
                }

            if validity_days <= 0:
                return {
                    "success": False,
                    "message": "ValidityDays must be greater than 0.",
                    "sn": sn,
                    "validity_days": validity_days,
                }

            current_date = date.today()
            calculated_expiry_date = current_date + timedelta(days=validity_days)

            current_text = current_date.strftime("%Y-%m-%d")
            calculated_expiry_text = calculated_expiry_date.strftime("%Y-%m-%d")

            already_used = old_expiry_date is not None and str(old_expiry_date).strip() != ""

            if already_used:
                return {
                    "success": True,
                    "message": "Serial found, but it is already activated.",
                    "sn": sn,
                    "validity_days": validity_days,
                    "current_date": current_text,
                    "expiry_date": str(old_expiry_date).strip(),
                    "calculated_expiry_date": calculated_expiry_text,
                    "already_used": True,
                    "can_activate": False,
                    "preview_only": True,
                }

            return {
                "success": True,
                "message": "Preview only. Database was not changed.",
                "sn": sn,
                "validity_days": validity_days,
                "current_date": current_text,
                "expiry_date": calculated_expiry_text,
                "calculated_expiry_date": calculated_expiry_text,
                "already_used": False,
                "can_activate": True,
                "preview_only": True,
            }

    except Exception as exc:
        return {
            "success": False,
            "message": f"Database error: {exc}",
            "sn": sn,
        }


def activate_serial(sn: str) -> dict:
    """
    Activate a serial number.

    Rules:
    - SN must be exactly 13 digits.
    - SN must exist in dbo.AppSysSerial.
    - ExpiryDate must be NULL or empty.
    - ValidityDays must exist and be > 0.
    - ExpiryDate is saved as YYYY-MM-DD because SQL column is nvarchar(10).
    """

    sn = (sn or "").strip()

    if not re.fullmatch(r"\d{13}", sn):
        return {
            "success": False,
            "message": "Serial number must be exactly 13 digits.",
            "sn": sn,
        }

    conn = get_connection()

    try:
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute(
            """
            SELECT SN, ValidityDays, ExpiryDate
            FROM dbo.AppSysSerial WITH (UPDLOCK, HOLDLOCK)
            WHERE SN = ?
            """,
            sn,
        )

        row = cur.fetchone()

        if not row:
            conn.rollback()
            return {
                "success": False,
                "message": "Serial number not found.",
                "sn": sn,
            }

        validity_days = row.ValidityDays
        old_expiry_date = row.ExpiryDate

        if old_expiry_date is not None and str(old_expiry_date).strip() != "":
            conn.rollback()
            return {
                "success": False,
                "message": "Serial number already used. It already has an expiry date.",
                "sn": sn,
                "validity_days": validity_days,
                "expiry_date": str(old_expiry_date).strip(),
            }

        if validity_days is None:
            conn.rollback()
            return {
                "success": False,
                "message": "ValidityDays is missing for this serial.",
                "sn": sn,
            }

        try:
            validity_days = int(validity_days)
        except Exception:
            conn.rollback()
            return {
                "success": False,
                "message": "ValidityDays is invalid.",
                "sn": sn,
            }

        if validity_days <= 0:
            conn.rollback()
            return {
                "success": False,
                "message": "ValidityDays must be greater than 0.",
                "sn": sn,
                "validity_days": validity_days,
            }

        current_date = date.today()
        expiry_date = current_date + timedelta(days=validity_days)

        current_text = current_date.strftime("%Y-%m-%d")
        expiry_text = expiry_date.strftime("%Y-%m-%d")

        cur.execute(
            """
            UPDATE dbo.AppSysSerial
            SET ExpiryDate = ?
            WHERE SN = ?
              AND (ExpiryDate IS NULL OR LTRIM(RTRIM(ExpiryDate)) = '')
            """,
            expiry_text,
            sn,
        )

        if cur.rowcount != 1:
            conn.rollback()
            return {
                "success": False,
                "message": "Activation failed. The serial may have been used by another user.",
                "sn": sn,
            }

        conn.commit()

        return {
            "success": True,
            "message": "Operation succeeded. Serial activated successfully.",
            "sn": sn,
            "validity_days": validity_days,
            "current_date": current_text,
            "expiry_date": expiry_text,
            "already_used": False,
            "can_activate": False,
            "preview_only": False,
        }

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass

        return {
            "success": False,
            "message": f"Database error: {exc}",
            "sn": sn,
        }

    finally:
        try:
            conn.close()
        except Exception:
            pass