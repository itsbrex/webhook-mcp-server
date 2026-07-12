"""
Custom Actions service for managing webhook.site automation rules.

Handles creation, retrieval, update, deletion, testing, and execution
of Custom Actions on webhook tokens.
"""

from __future__ import annotations

from typing import Any

from models.schemas import ToolResult
from utils.http_client import WebhookHttpClient


class CustomActionsService:
    """Service for Custom Actions operations.

    Provides business logic for:
    - Listing actions on a token
    - Creating new actions (conditions, scripts, HTTP forwarding, etc.)
    - Updating existing action settings
    - Deleting actions
    - Testing actions with sample request data
    - Executing all actions against a captured request
    """

    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.

        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client

    async def list_actions(self, webhook_token: str) -> ToolResult:
        """List all custom actions configured on a webhook token.

        Args:
            webhook_token: The webhook UUID

        Returns:
            ToolResult with array of action objects
        """
        data = await self._client.get(f"/token/{webhook_token}/actions")

        actions = data.get("data", []) if isinstance(data, dict) else data
        formatted = []
        for action in actions:
            formatted.append(self._format_action(action))

        return ToolResult(
            success=True,
            message=f"Found {len(formatted)} custom action(s)",
            data={"total": len(formatted), "actions": formatted},
        )

    async def create_action(
        self,
        webhook_token: str,
        action_type: str,
        order: int = 0,
        parameters: dict[str, Any] | None = None,
        disabled: bool = False,
        queue: bool = False,
        delay: int | None = None,
        condition: str | None = None,
    ) -> ToolResult:
        """Create a new custom action on a webhook token.

        Args:
            webhook_token: The webhook UUID
            action_type: Action type name (e.g. 'condition', 'script',
                'http_request', 'slack', 'email', etc.)
            order: Execution order (lower runs first)
            parameters: Type-specific configuration object
            disabled: If True, action is skipped during execution
            queue: If True, action runs asynchronously
            delay: Seconds to wait before running (requires queue=True)
            condition: UUID of a Condition action that gates this action

        Returns:
            ToolResult with the created action object
        """
        payload: dict[str, Any] = {
            "type": action_type,
            "order": order,
            "disabled": disabled,
        }
        if parameters is not None:
            payload["parameters"] = parameters
        if queue:
            payload["queue"] = queue
        if delay is not None:
            payload["delay"] = delay
        if condition is not None:
            payload["condition"] = condition

        response = await self._client.post(
            f"/token/{webhook_token}/actions",
            json_data=payload,
        )
        response.raise_for_status()
        data = response.json()

        return ToolResult(
            success=True,
            message=f"Custom action created (type: {action_type}, order: {order})",
            data={"action": self._format_action(data)},
        )

    async def update_action(
        self,
        webhook_token: str,
        action_id: str,
        action_type: str | None = None,
        order: int | None = None,
        parameters: dict[str, Any] | None = None,
        disabled: bool | None = None,
        queue: bool | None = None,
        delay: int | None = None,
        condition: str | None = None,
    ) -> ToolResult:
        """Update an existing custom action's settings.

        Args:
            webhook_token: The webhook UUID
            action_id: UUID of the action to update
            action_type: New action type name
            order: New execution order
            parameters: New type-specific configuration
            disabled: New disabled state
            queue: New async execution flag
            delay: New delay in seconds
            condition: New condition action UUID

        Returns:
            ToolResult with the updated action object
        """
        payload: dict[str, Any] = {}
        if action_type is not None:
            payload["type"] = action_type
        if order is not None:
            payload["order"] = order
        if parameters is not None:
            payload["parameters"] = parameters
        if disabled is not None:
            payload["disabled"] = disabled
        if queue is not None:
            payload["queue"] = queue
        if delay is not None:
            payload["delay"] = delay
        if condition is not None:
            payload["condition"] = condition

        data = await self._client.put(
            f"/token/{webhook_token}/actions/{action_id}",
            json_data=payload,
        )

        return ToolResult(
            success=True,
            message=f"Custom action {action_id} updated",
            data={"action": self._format_action(data)},
        )

    async def delete_action(
        self,
        webhook_token: str,
        action_id: str,
    ) -> ToolResult:
        """Delete a custom action from a webhook token.

        Args:
            webhook_token: The webhook UUID
            action_id: UUID of the action to delete

        Returns:
            ToolResult indicating success/failure
        """
        status_code = await self._client.delete(
            f"/token/{webhook_token}/actions/{action_id}"
        )
        success = status_code in [200, 204]

        return ToolResult(
            success=success,
            message=(
                f"Custom action {action_id} deleted"
                if success
                else f"Failed to delete action (HTTP {status_code})"
            ),
            data={"action_id": action_id, "status_code": status_code},
        )

    async def test_action(
        self,
        webhook_token: str,
        action_type: str,
        order: int = 0,
        parameters: dict[str, Any] | None = None,
        request_id: str | None = None,
        action_id: str | None = None,
    ) -> ToolResult:
        """Test a custom action with sample request data without saving it.

        Args:
            webhook_token: The webhook UUID
            action_type: Action type to test
            order: Execution order
            parameters: Type-specific configuration
            request_id: Optional request UUID to base the test on
            action_id: Optional existing action UUID to overwrite params for

        Returns:
            ToolResult with test execution output, response, and variables
        """
        payload: dict[str, Any] = {
            "type": action_type,
            "order": order,
        }
        if parameters is not None:
            payload["parameters"] = parameters

        query_params: dict[str, str] = {}
        if request_id is not None:
            query_params["request_id"] = request_id
        if action_id is not None:
            query_params["action_id"] = action_id

        # Build URL with query params
        path = f"/token/{webhook_token}/test-action"
        if query_params:
            qs = "&".join(f"{k}={v}" for k, v in query_params.items())
            path = f"{path}?{qs}"

        response = await self._client.post(path, json_data=payload)
        response.raise_for_status()
        data = response.json()

        result_data = data.get("result", {})

        return ToolResult(
            success=data.get("success", True),
            message=f"Action test completed (type: {action_type})",
            data={
                "test_success": data.get("success", True),
                "output": result_data.get("output", {}),
                "response": result_data.get("response", {}),
                "variables": result_data.get("variables", {}),
            },
        )

    async def execute_actions(
        self,
        webhook_token: str,
        request_id: str,
        error_notifications: bool = False,
    ) -> ToolResult:
        """Execute all custom actions against a specific captured request.

        Args:
            webhook_token: The webhook UUID
            request_id: UUID of the captured request to execute actions on
            error_notifications: Send email if an error occurs

        Returns:
            ToolResult with execution output, response, and variables
        """
        path = f"/token/{webhook_token}/request/{request_id}/execute"
        if error_notifications:
            path = f"{path}?error_notifications=true"

        response = await self._client.post(path)
        response.raise_for_status()
        data = response.json()

        result_data = data.get("result", {})

        return ToolResult(
            success=data.get("success", True),
            message=f"Custom actions executed on request {request_id}",
            data={
                "request_id": request_id,
                "execution_success": data.get("success", True),
                "output": result_data.get("output", {}),
                "response": result_data.get("response", {}),
                "variables": result_data.get("variables", {}),
            },
        )

    @staticmethod
    def _format_action(action: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API action into clean output.

        Args:
            action: Raw action data from API

        Returns:
            Formatted action dictionary
        """
        return {
            "uuid": action.get("uuid"),
            "token_id": action.get("token_id"),
            "type": action.get("type"),
            "order": action.get("order"),
            "disabled": action.get("disabled"),
            "queue": action.get("queue"),
            "delay": action.get("delay"),
            "condition": action.get("condition"),
            "parameters": action.get("parameters", {}),
        }
