#!/usr/bin/env python3
"""
Webhook.site MCP Server

A Model Context Protocol (MCP) server for interacting with webhook.site.
Provides tools for creating, managing, and monitoring webhooks.

Usage:
    python server.py

Architecture:
    server.py          - MCP entry point (this file)
    handlers/          - Tool call routing
    services/          - Business logic
    models/            - Data models and schemas
    utils/             - HTTP client utilities
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from project root
load_dotenv(PROJECT_ROOT / ".env")

from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
)

from models.schemas import TOOL_DEFINITIONS
from handlers.tool_handlers import ToolHandler
from utils.http_client import WebhookHttpClient


# =============================================================================
# SERVER INITIALIZATION
# =============================================================================

async def list_tools(
    ctx: ServerRequestContext, params: PaginatedRequestParams | None
) -> ListToolsResult:
    """Return all available webhook.site tools.

    Returns:
        Tool definitions from models/schemas.py
    """
    return ListToolsResult(tools=TOOL_DEFINITIONS)


async def call_tool(
    ctx: ServerRequestContext, params: CallToolRequestParams
) -> CallToolResult:
    """Handle MCP tool calls.

    Routes tool calls through the handler layer which delegates
    to appropriate services.

    Args:
        ctx: Request context
        params: Tool name and arguments
    """
    api_key = os.environ.get("WEBHOOK_SITE_API_KEY")
    async with WebhookHttpClient(api_key=api_key) as client:
        handler = ToolHandler(client)
        content = await handler.handle(params.name, params.arguments or {})
    return CallToolResult(content=content)


server = Server(
    "webhook-site-mcp",
    version="3.0.0",
    on_list_tools=list_tools,
    on_call_tool=call_tool,
)


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main() -> None:
    """Run the MCP server.
    
    Starts the stdio transport and runs the server
    until interrupted.
    """
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_server() -> None:
    """Synchronous entry point for console script."""
    asyncio.run(main())


if __name__ == "__main__":
    run_server()
