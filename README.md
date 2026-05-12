# TRY_01

This is trial repo

## SQL Server Connection (`db_connection.py`)

A reusable Python module for connecting to Microsoft SQL Server using **pyodbc**.

### Requirements

```bash
pip install pyodbc
```

You also need the appropriate ODBC driver installed on your system:
- **Windows / Linux / macOS** – [Microsoft ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

### Quick Start

```python
from db_connection import SQLServerConnection

# SQL Server Authentication
with SQLServerConnection(
    server="localhost",
    database="mydb",
    username="sa",
    password="YourPassword123",
) as db:
    rows = db.execute_query("SELECT * FROM users WHERE active = ?", (1,))
    for row in rows:
        print(row)

# Windows / Trusted Authentication (omit username/password)
with SQLServerConnection(server="localhost", database="mydb") as db:
    affected = db.execute_non_query(
        "UPDATE users SET active = ? WHERE id = ?", (0, 42)
    )
    print(f"{affected} row(s) updated")
```

### API

| Method | Description |
|---|---|
| `connect()` | Open the connection (called automatically in `with` block) |
| `disconnect()` | Close the connection (called automatically in `with` block) |
| `execute_query(query, params)` | Run a `SELECT` and return all rows |
| `execute_non_query(query, params)` | Run `INSERT` / `UPDATE` / `DELETE`; auto-commit |
| `execute_many(query, params_list)` | Batch insert/update for a list of rows |

### Running the built-in example

Edit the connection details at the bottom of `db_connection.py` and run:

```bash
python db_connection.py
```
