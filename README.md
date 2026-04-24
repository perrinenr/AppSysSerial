# AppSysSerial Python GUI

Small Python Tkinter application that activates a serial number from SQL Server.

## What it does

1. User enters an SN of exactly 13 digits.
2. The app checks `dbo.AppSysSerial` in SQL Server.
3. If the SN exists and has no `ExpiryDate`, it reads `ValidityDays`.
4. It calculates `ExpiryDate = current date + ValidityDays`.
5. It saves the expiry date into the same SQL record.
6. It shows success or failure in the GUI.

If the serial already has an `ExpiryDate`, the app refuses it because it was already used.

## Files

- `main.py` = GUI screen.
- `db.py` = config reader and SQL Server logic.
- `config.txt` = database connection settings.
- `DatabaseScript.sql` = table and sample data.
- `requirements.txt` = Python dependency list.

## Setup

Install the ODBC Driver for SQL Server, then install Python packages:

Edit `config.txt`:

```txt
SERVER=.\SQLEXPRESS
DATABASE=master
DRIVER=ODBC Driver 17 for SQL Server
TRUSTED_CONNECTION=yes
TRUST_SERVER_CERTIFICATE=yes
```

Run:

```bash
python main.py
```

## SQL Authentication

If your SQL Server uses username/password, edit `config.txt` like this:

```txt
SERVER=YOUR_SERVER
DATABASE=YOUR_DATABASE
DRIVER=ODBC Driver 17 for SQL Server
TRUST_SERVER_CERTIFICATE=yes
SQL_USERNAME=your_username
SQL_PASSWORD=your_password
```

The app will use SQL Authentication when `SQL_USERNAME` and `SQL_PASSWORD` are present.
