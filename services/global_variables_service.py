"""
Global Variables service for managing webhook.site global variables.

Handles CRUD operations on global variables that persist across
all webhooks and schedules for the authenticated user.
"""

from __future__ import annotations

from typing import Any

from models.schemas import ToolResult
from utils.http_client import WebhookHttpClient


class GlobalVariablesService:
    """Service for Global Variables operations.

    Provides business logic for:
    - Listing all global variables
    - Creating new variables
    - Updating existing variables
    - Deleting variables
    """

    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.

        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client

    async def list_variables(self) -> ToolResult:
        """List all global variables for the authenticated user.

        Returns:
            ToolResult with array of variable objects
        """
        data = await self._client.get("/global-variables")

        variables = data.get("data", []) if isinstance(data, dict) else data
        formatted = [self._format_variable(v) for v in variables]

        return ToolResult(
            success=True,
            message=f"Found {len(formatted)} global variable(s)",
            data={"total": len(formatted), "variables": formatted},
        )

    async def create_variable(
        self,
        name: str,
        value: str,
    ) -> ToolResult:
        """Create a new global variable.

        Args:
            name: Variable name
            value: Variable value

        Returns:
            ToolResult with the created variable object
        """
        response = await self._client.post(
            "/global-variables",
            json_data={"name": name, "value": value},
        )
        response.raise_for_status()
        data = response.json()

        return ToolResult(
            success=True,
            message=f"Global variable '{name}' created",
            data={"variable": self._format_variable(data)},
        )

    async def update_variable(
        self,
        variable_id: str,
        name: str | None = None,
        value: str | None = None,
    ) -> ToolResult:
        """Update an existing global variable.

        Args:
            variable_id: UUID of the variable to update
            name: New variable name
            value: New variable value

        Returns:
            ToolResult with the updated variable object
        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if value is not None:
            payload["value"] = value

        data = await self._client.put(
            f"/global-variables/{variable_id}",
            json_data=payload,
        )

        return ToolResult(
            success=True,
            message=f"Global variable {variable_id} updated",
            data={"variable": self._format_variable(data)},
        )

    async def delete_variable(self, variable_id: str) -> ToolResult:
        """Delete a global variable.

        Args:
            variable_id: UUID of the variable to delete

        Returns:
            ToolResult indicating success/failure
        """
        status_code = await self._client.delete(
            f"/global-variables/{variable_id}"
        )
        success = status_code in [200, 204]

        return ToolResult(
            success=success,
            message=(
                f"Global variable {variable_id} deleted"
                if success
                else f"Failed to delete variable (HTTP {status_code})"
            ),
            data={"variable_id": variable_id, "status_code": status_code},
        )

    @staticmethod
    def _format_variable(var: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API variable into clean output.

        Args:
            var: Raw variable data from API

        Returns:
            Formatted variable dictionary
        """
        return {
            "uuid": var.get("uuid"),
            "name": var.get("name"),
            "value": var.get("value"),
            "created_at": var.get("created_at"),
            "updated_at": var.get("updated_at"),
        }
