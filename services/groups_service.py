"""
Groups service for managing webhook.site groups.

Handles CRUD operations on groups that organize webhook tokens
into containers for the authenticated user.
"""

from __future__ import annotations

from typing import Any

from models.schemas import ToolResult
from utils.http_client import WebhookHttpClient


class GroupsService:
    """Service for Groups operations.

    Provides business logic for:
    - Listing all groups
    - Creating new groups
    - Updating existing groups
    - Deleting groups
    """

    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.

        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client

    async def list_groups(self) -> ToolResult:
        """List all groups for the authenticated user.

        Returns:
            ToolResult with array of group objects
        """
        data = await self._client.get("/groups")

        groups = data.get("data", []) if isinstance(data, dict) else data
        formatted = [self._format_group(g) for g in groups]

        return ToolResult(
            success=True,
            message=f"Found {len(formatted)} group(s)",
            data={"total": len(formatted), "groups": formatted},
        )

    async def create_group(self, name: str) -> ToolResult:
        """Create a new group.

        Args:
            name: Group name

        Returns:
            ToolResult with the created group object
        """
        response = await self._client.post(
            "/groups",
            json_data={"name": name},
        )
        response.raise_for_status()
        data = response.json()

        return ToolResult(
            success=True,
            message=f"Group '{name}' created",
            data={"group": self._format_group(data)},
        )

    async def update_group(
        self,
        group_id: str,
        name: str,
    ) -> ToolResult:
        """Update a group's name.

        Args:
            group_id: UUID of the group to update
            name: New group name

        Returns:
            ToolResult with the updated group object
        """
        data = await self._client.put(
            f"/groups/{group_id}",
            json_data={"name": name},
        )

        return ToolResult(
            success=True,
            message=f"Group {group_id} updated to '{name}'",
            data={"group": self._format_group(data)},
        )

    async def delete_group(self, group_id: str) -> ToolResult:
        """Delete a group.

        Args:
            group_id: UUID of the group to delete

        Returns:
            ToolResult indicating success/failure
        """
        status_code = await self._client.delete(
            f"/groups/{group_id}"
        )
        success = status_code in [200, 204]

        return ToolResult(
            success=success,
            message=(
                f"Group {group_id} deleted"
                if success
                else f"Failed to delete group (HTTP {status_code})"
            ),
            data={"group_id": group_id, "status_code": status_code},
        )

    @staticmethod
    def _format_group(group: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API group into clean output.

        Args:
            group: Raw group data from API

        Returns:
            Formatted group dictionary
        """
        return {
            "uuid": group.get("uuid"),
            "name": group.get("name"),
            "created_at": group.get("created_at"),
            "updated_at": group.get("updated_at"),
        }
