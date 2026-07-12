"""
Templates service for managing webhook.site templates.

Handles CRUD operations on templates — reusable sets of Custom Actions
and variables that can be applied to webhook tokens.
"""

from __future__ import annotations

from typing import Any

from models.schemas import ToolResult
from utils.http_client import WebhookHttpClient


class TemplatesService:
    """Service for Templates operations.

    Provides business logic for:
    - Listing all templates
    - Creating new templates
    - Updating existing templates
    - Deleting templates
    """

    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.

        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client

    async def list_templates(self) -> ToolResult:
        """List all templates for the authenticated user.

        Returns:
            ToolResult with array of template objects
        """
        data = await self._client.get("/templates")

        templates = data.get("data", []) if isinstance(data, dict) else data
        formatted = [self._format_template(t) for t in templates]

        return ToolResult(
            success=True,
            message=f"Found {len(formatted)} template(s)",
            data={"total": len(formatted), "templates": formatted},
        )

    async def create_template(
        self,
        name: str,
        actions: list[dict[str, Any]] | None = None,
        variables: list[dict[str, Any]] | None = None,
    ) -> ToolResult:
        """Create a new template.

        Args:
            name: Template name
            actions: Array of action definitions
            variables: Array of variable definitions ({name, value})

        Returns:
            ToolResult with the created template object
        """
        payload: dict[str, Any] = {"name": name}
        if actions is not None:
            payload["actions"] = actions
        if variables is not None:
            payload["variables"] = variables

        response = await self._client.post(
            "/templates",
            json_data=payload,
        )
        response.raise_for_status()
        data = response.json()

        return ToolResult(
            success=True,
            message=f"Template '{name}' created",
            data={"template": self._format_template(data)},
        )

    async def update_template(
        self,
        template_id: str,
        name: str | None = None,
        actions: list[dict[str, Any]] | None = None,
        variables: list[dict[str, Any]] | None = None,
    ) -> ToolResult:
        """Update a template.

        Args:
            template_id: UUID of the template to update
            name: New template name
            actions: New array of action definitions
            variables: New array of variable definitions

        Returns:
            ToolResult with the updated template object
        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if actions is not None:
            payload["actions"] = actions
        if variables is not None:
            payload["variables"] = variables

        data = await self._client.put(
            f"/templates/{template_id}",
            json_data=payload,
        )

        return ToolResult(
            success=True,
            message=f"Template {template_id} updated",
            data={"template": self._format_template(data)},
        )

    async def delete_template(self, template_id: str) -> ToolResult:
        """Delete a template.

        Args:
            template_id: UUID of the template to delete

        Returns:
            ToolResult indicating success/failure
        """
        status_code = await self._client.delete(
            f"/templates/{template_id}"
        )
        success = status_code in [200, 204]

        return ToolResult(
            success=success,
            message=(
                f"Template {template_id} deleted"
                if success
                else f"Failed to delete template (HTTP {status_code})"
            ),
            data={"template_id": template_id, "status_code": status_code},
        )

    @staticmethod
    def _format_template(template: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API template into clean output.

        Args:
            template: Raw template data from API

        Returns:
            Formatted template dictionary
        """
        return {
            "uuid": template.get("uuid"),
            "name": template.get("name"),
            "actions": template.get("actions"),
            "variables": template.get("variables"),
            "created_at": template.get("created_at"),
            "updated_at": template.get("updated_at"),
        }
