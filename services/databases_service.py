"""
Databases service for managing webhook.site built-in PostgreSQL databases.

Handles querying, creation, listing, updating, and deletion
of webhook.site databases for the authenticated user.
"""

from __future__ import annotations

from typing import Any

from models.schemas import ToolResult
from utils.http_client import WebhookHttpClient


class DatabasesService:
    """Service for Databases operations.

    Provides business logic for:
    - Running SQL queries against databases
    - Creating new databases
    - Listing all databases
    - Updating database metadata
    - Deleting databases
    """

    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.

        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client

    async def query_database(
        self,
        database_id: str,
        query: str,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> ToolResult:
        """Run a SQL query against a webhook.site database.

        Args:
            database_id: UUID of the database to query
            query: SQL query string
            params: Optional positional (array) or named (object) parameters

        Returns:
            ToolResult with query results, error info, and execution time
        """
        payload: dict[str, Any] = {"query": query}
        if params is not None:
            payload["params"] = params

        response = await self._client.post(
            f"/databases/{database_id}/query",
            json_data=payload,
        )
        response.raise_for_status()
        data = response.json()

        error = data.get("error")
        if error:
            return ToolResult(
                success=False,
                message=f"Query error: {error}",
                data={
                    "database_id": database_id,
                    "error": error,
                    "time_ms": data.get("time"),
                },
            )

        result = data.get("result", [])
        return ToolResult(
            success=True,
            message=f"Query returned {len(result)} row(s)",
            data={
                "database_id": database_id,
                "rows": len(result),
                "result": result,
                "time_ms": data.get("time"),
            },
        )

    async def create_database(
        self,
        name: str,
        plan: str = "db-s",
        group_id: int | None = None,
    ) -> ToolResult:
        """Create a new webhook.site database.

        Args:
            name: Database name
            plan: Database plan (db-s, db-m, db-l)
            group_id: Optional group ID to assign to

        Returns:
            ToolResult with the created database object
        """
        payload: dict[str, Any] = {"name": name, "plan": plan}
        if group_id is not None:
            payload["group_id"] = group_id

        response = await self._client.post(
            "/databases",
            json_data=payload,
        )
        response.raise_for_status()
        data = response.json()

        return ToolResult(
            success=True,
            message=f"Database '{name}' created (plan: {plan})",
            data={"database": self._format_database(data)},
        )

    async def list_databases(self) -> ToolResult:
        """List all databases for the authenticated user.

        Returns:
            ToolResult with array of database objects
        """
        data = await self._client.get("/database")

        databases = data.get("data", []) if isinstance(data, dict) else data
        formatted = [self._format_database(db) for db in databases]

        return ToolResult(
            success=True,
            message=f"Found {len(formatted)} database(s)",
            data={"total": len(formatted), "databases": formatted},
        )

    async def update_database(
        self,
        database_id: str,
        name: str | None = None,
        group_id: int | None = None,
    ) -> ToolResult:
        """Update database metadata.

        Args:
            database_id: UUID of the database to update
            name: New database name
            group_id: New group ID

        Returns:
            ToolResult with the updated database object
        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if group_id is not None:
            payload["group_id"] = group_id

        data = await self._client.put(
            f"/databases/{database_id}",
            json_data=payload,
        )

        return ToolResult(
            success=True,
            message=f"Database {database_id} updated",
            data={"database": self._format_database(data)},
        )

    async def delete_database(self, database_id: str) -> ToolResult:
        """Delete a database.

        Args:
            database_id: UUID of the database to delete

        Returns:
            ToolResult indicating success/failure
        """
        status_code = await self._client.delete(
            f"/databases/{database_id}"
        )
        success = status_code in [200, 204]

        return ToolResult(
            success=success,
            message=(
                f"Database {database_id} deleted"
                if success
                else f"Failed to delete database (HTTP {status_code})"
            ),
            data={"database_id": database_id, "status_code": status_code},
        )

    @staticmethod
    def _format_database(db: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API database into clean output.

        Args:
            db: Raw database data from API

        Returns:
            Formatted database dictionary
        """
        return {
            "uuid": db.get("uuid"),
            "name": db.get("name"),
            "plan": db.get("plan"),
            "group_id": db.get("group_id"),
            "bytes_used": db.get("bytes_used"),
            "tables_used": db.get("tables_used"),
            "created_at": db.get("created_at"),
            "updated_at": db.get("updated_at"),
        }
