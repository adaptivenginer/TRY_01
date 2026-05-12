"""
SQL Server Database Connection Module

Provides a reusable class for connecting to a Microsoft SQL Server database
using pyodbc. Supports both Windows Authentication and SQL Server Authentication.

Requirements:
    pip install pyodbc

Usage:
    from db_connection import SQLServerConnection

    with SQLServerConnection(server="localhost", database="mydb",
                             username="sa", password="secret") as conn:
        rows = conn.execute_query("SELECT * FROM my_table")
        for row in rows:
            print(row)
"""

import logging
from typing import Any, Optional

import pyodbc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class SQLServerConnection:
    """Manages a connection to a Microsoft SQL Server database.

    Can be used as a context manager (``with`` statement) to ensure the
    connection is always properly closed.

    Args:
        server:   Hostname or IP address of the SQL Server instance.
                  Append the port with a comma, e.g. ``"myhost,1433"``.
        database: Name of the target database.
        username: SQL Server login username.
                  Leave ``None`` to use Windows Authentication (Trusted Connection).
        password: Password for the SQL Server login.
                  Ignored when ``username`` is ``None``.
        driver:   ODBC driver name. Defaults to ``"ODBC Driver 17 for SQL Server"``.
        timeout:  Connection timeout in seconds. Defaults to 30.
    """

    DEFAULT_DRIVER = "ODBC Driver 17 for SQL Server"

    def __init__(
        self,
        server: str,
        database: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        driver: str = DEFAULT_DRIVER,
        timeout: int = 30,
    ) -> None:
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.timeout = timeout
        self._connection: Optional[pyodbc.Connection] = None

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _build_connection_string(self) -> str:
        """Build the ODBC connection string."""
        if self.username:
            # SQL Server Authentication
            return (
                f"DRIVER={{{self.driver}}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"Connection Timeout={self.timeout};"
            )
        # Windows / Trusted Authentication
        return (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"Trusted_Connection=yes;"
            f"Connection Timeout={self.timeout};"
        )

    def connect(self) -> None:
        """Open the database connection.

        Raises:
            pyodbc.Error: If the connection attempt fails.
        """
        connection_string = self._build_connection_string()
        logger.info("Connecting to SQL Server: server=%s, database=%s", self.server, self.database)
        self._connection = pyodbc.connect(connection_string)
        logger.info("Connection established successfully.")

    def disconnect(self) -> None:
        """Close the database connection if it is open."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Connection closed.")

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> "SQLServerConnection":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.disconnect()

    # ------------------------------------------------------------------
    # Query execution helpers
    # ------------------------------------------------------------------

    def execute_query(self, query: str, params: Optional[tuple] = None) -> list[pyodbc.Row]:
        """Execute a SELECT query and return all rows.

        Args:
            query:  SQL query string. Use ``?`` as a placeholder for parameters.
            params: Optional tuple of parameter values.

        Returns:
            A list of :class:`pyodbc.Row` objects.

        Raises:
            RuntimeError:  If called before :meth:`connect`.
            pyodbc.Error:  If the query fails.

        Example::

            rows = conn.execute_query(
                "SELECT id, name FROM users WHERE active = ?", (1,)
            )
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")
        cursor = self._connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()

    def execute_non_query(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute an INSERT, UPDATE, or DELETE statement.

        Changes are committed automatically on success and rolled back on error.

        Args:
            query:  SQL statement string. Use ``?`` as a placeholder for parameters.
            params: Optional tuple of parameter values.

        Returns:
            The number of rows affected.

        Raises:
            RuntimeError:  If called before :meth:`connect`.
            pyodbc.Error:  If the statement fails (transaction is rolled back).

        Example::

            affected = conn.execute_non_query(
                "UPDATE users SET active = ? WHERE id = ?", (0, 42)
            )
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")
        cursor = self._connection.cursor()
        try:
            cursor.execute(query, params or ())
            self._connection.commit()
            return cursor.rowcount
        except pyodbc.Error:
            self._connection.rollback()
            logger.exception("Query failed; transaction rolled back.")
            raise
        finally:
            cursor.close()

    def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """Execute a parameterised statement for multiple rows in a single batch.

        Args:
            query:       SQL statement string with ``?`` placeholders.
            params_list: List of parameter tuples, one per row.

        Returns:
            The number of rows affected.

        Raises:
            RuntimeError:  If called before :meth:`connect`.
            pyodbc.Error:  If the statement fails (transaction is rolled back).

        Example::

            conn.execute_many(
                "INSERT INTO users (name, email) VALUES (?, ?)",
                [("Alice", "alice@example.com"), ("Bob", "bob@example.com")],
            )
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")
        cursor = self._connection.cursor()
        try:
            cursor.fast_executemany = True
            cursor.executemany(query, params_list)
            self._connection.commit()
            return cursor.rowcount
        except pyodbc.Error:
            self._connection.rollback()
            logger.exception("Batch query failed; transaction rolled back.")
            raise
        finally:
            cursor.close()


# ---------------------------------------------------------------------------
# Quick-start example (run this file directly to test your connection)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    # Values can also be set via environment variables before running:
    #   export DB_SERVER=localhost DB_NAME=master DB_USER=sa DB_PASSWORD=secret
    SERVER = os.environ.get("DB_SERVER", "localhost")      # e.g. "myserver.database.windows.net"
    DATABASE = os.environ.get("DB_NAME", "master")
    USERNAME = os.environ.get("DB_USER") or None           # None → Windows Authentication
    PASSWORD = os.environ.get("DB_PASSWORD") or None       # ignored when USERNAME is None

    try:
        with SQLServerConnection(
            server=SERVER,
            database=DATABASE,
            username=USERNAME,
            password=PASSWORD,
        ) as db:
            rows = db.execute_query("SELECT @@VERSION AS version")
            for row in rows:
                print("SQL Server version:", row.version)
    except pyodbc.Error as exc:
        logger.error("Failed to connect or query: %s", exc)
