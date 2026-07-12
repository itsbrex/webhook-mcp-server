"""
Schedules service for managing webhook.site scheduled tasks.

Handles creation, retrieval, execution, and log access
for cron-based HTTP request schedules.
"""

from __future__ import annotations

from typing import Any

from models.schemas import ToolResult
from utils.http_client import WebhookHttpClient


class SchedulesService:
    """Service for Schedules operations.

    Provides business logic for:
    - Listing all scheduled tasks
    - Creating new schedules (cron-based HTTP requests)
    - Triggering immediate execution
    - Retrieving execution logs
    """

    def __init__(self, client: WebhookHttpClient) -> None:
        """Initialize service with HTTP client.

        Args:
            client: Configured WebhookHttpClient instance
        """
        self._client = client

    async def list_schedules(self) -> ToolResult:
        """List all scheduled tasks for the authenticated user.

        Returns:
            ToolResult with array of schedule objects
        """
        data = await self._client.get("/schedules")

        schedules = data.get("data", []) if isinstance(data, dict) else data
        formatted = [self._format_schedule(s) for s in schedules]

        return ToolResult(
            success=True,
            message=f"Found {len(formatted)} schedule(s)",
            data={"total": len(formatted), "schedules": formatted},
        )

    async def create_schedule(
        self,
        name: str,
        request_url: str,
        interval: str | None = None,
        cron: str | None = None,
        request_method: str = "GET",
        request_body: str | None = None,
        request_headers: str | None = None,
        timeout: int = 10,
    ) -> ToolResult:
        """Create a new scheduled task.

        Args:
            name: Human-readable schedule name
            request_url: Target URL for the scheduled request
            interval: Preset interval or 'cron' for custom
            cron: Custom cron expression (when interval='cron')
            request_method: HTTP method (default: GET)
            request_body: Request body for POST/PUT/PATCH
            request_headers: Newline-separated 'Key: Value' headers
            timeout: Request timeout in seconds (1-30)

        Returns:
            ToolResult with the created schedule object
        """
        payload: dict[str, Any] = {
            "name": name,
            "request_url": request_url,
            "request_method": request_method,
            "timeout": timeout,
        }
        if interval is not None:
            payload["interval"] = interval
        if cron is not None:
            payload["cron"] = cron
        if request_body is not None:
            payload["request_body"] = request_body
        if request_headers is not None:
            payload["request_headers"] = request_headers

        response = await self._client.post(
            "/schedules",
            json_data=payload,
        )
        response.raise_for_status()
        data = response.json()

        return ToolResult(
            success=True,
            message=f"Schedule '{name}' created (interval: {interval or cron or 'default'})",
            data={"schedule": self._format_schedule(data)},
        )

    async def run_now(self, schedule_id: str) -> ToolResult:
        """Trigger immediate execution of a schedule.

        Args:
            schedule_id: UUID of the schedule to run

        Returns:
            ToolResult with execution result
        """
        response = await self._client.post(
            f"/schedules/{schedule_id}/run-now",
        )
        response.raise_for_status()

        # Response may have JSON body or may be empty
        try:
            data = response.json()
        except Exception:
            data = {}

        return ToolResult(
            success=True,
            message=f"Schedule {schedule_id} triggered for immediate execution",
            data={
                "schedule_id": schedule_id,
                "result": data,
            },
        )

    async def get_logs(
        self,
        schedule_id: str,
        sorting: str = "newest",
    ) -> ToolResult:
        """Get execution logs for a schedule.

        Args:
            schedule_id: UUID of the schedule
            sorting: Sort order ('newest' or 'oldest')

        Returns:
            ToolResult with array of log entries
        """
        data = await self._client.get(
            f"/schedules/{schedule_id}/logs",
            params={"sorting": sorting},
        )

        logs = data.get("data", []) if isinstance(data, dict) else data
        formatted = [self._format_log(log) for log in logs]

        return ToolResult(
            success=True,
            message=f"Retrieved {len(formatted)} log entries for schedule {schedule_id}",
            data={
                "schedule_id": schedule_id,
                "total": len(formatted),
                "logs": formatted,
            },
        )

    @staticmethod
    def _format_schedule(schedule: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API schedule into clean output.

        Args:
            schedule: Raw schedule data from API

        Returns:
            Formatted schedule dictionary
        """
        return {
            "uuid": schedule.get("uuid"),
            "name": schedule.get("name"),
            "interval": schedule.get("interval"),
            "cron": schedule.get("cron"),
            "request_url": schedule.get("request_url"),
            "request_method": schedule.get("request_method"),
            "request_body": schedule.get("request_body"),
            "request_headers": schedule.get("request_headers"),
            "timeout": schedule.get("timeout"),
            "enabled": schedule.get("enabled"),
            "last_run_at": schedule.get("last_run_at"),
            "next_run_at": schedule.get("next_run_at"),
            "created_at": schedule.get("created_at"),
            "updated_at": schedule.get("updated_at"),
        }

    @staticmethod
    def _format_log(log: dict[str, Any]) -> dict[str, Any]:
        """Format a raw API log entry into clean output.

        Args:
            log: Raw log data from API

        Returns:
            Formatted log dictionary
        """
        return {
            "uuid": log.get("uuid"),
            "schedule_id": log.get("schedule_id"),
            "status_code": log.get("status_code"),
            "response_body": log.get("response_body"),
            "success": log.get("success"),
            "error": log.get("error"),
            "runtime_ms": log.get("runtime_ms"),
            "created_at": log.get("created_at"),
        }
