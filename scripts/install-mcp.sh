#!/usr/bin/env bash
#
# install-mcp.sh — add webhook-mcp-server to your AI coding clients via `mcp-add`.
#
# Interactive by default: pick a source (published release or your local dev
# checkout), pick a scope + clients, and paste an optional webhook.site API key
# (paid accounts only — just press Enter to skip). Everything can also be driven
# non-interactively with flags/env vars for CI or scripted setups.
#
# Requires: node/npx (for `mcp-add`) and, for the local-dev source, `uv`.
#
# Usage:
#   ./scripts/install-mcp.sh                 # fully interactive
#   ./scripts/install-mcp.sh --local         # use this checkout as the server
#   ./scripts/install-mcp.sh --published      # use the released uvx package
#   ./scripts/install-mcp.sh --yes            # accept defaults, no prompts
#   MCP_API_KEY=... ./scripts/install-mcp.sh --local --yes
#
# Flags:
#   --local | --published   Server source (default: ask, else published)
#   --name <name>           MCP server name           (default: webhook)
#   --scope <global|project>                          (default: global)
#   --clients "<list>"      Comma-separated client list (default: "claude code")
#   --api-key <key>         webhook.site API key (or set MCP_API_KEY)
#   --no-sync               Skip `uv sync` in local mode
#   --yes, -y               Non-interactive; accept defaults
#   --help, -h              Show this help
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- defaults (overridable by env) -----------------------------------------
NAME="${MCP_NAME:-webhook}"
SCOPE="${MCP_SCOPE:-global}"
CLIENTS="${MCP_CLIENTS:-claude code}"
API_KEY="${MCP_API_KEY:-${WEBHOOK_SITE_API_KEY:-}}"
SOURCE="${MCP_SOURCE:-}"        # "local" | "published" | "" (ask)
ASSUME_YES=0
DO_SYNC=1

# --- pretty output ----------------------------------------------------------
if [ -t 1 ]; then B=$'\033[1m'; DIM=$'\033[2m'; GRN=$'\033[32m'; YEL=$'\033[33m'; RST=$'\033[0m'; else B=; DIM=; GRN=; YEL=; RST=; fi
info() { printf '%s\n' "$*"; }
step() { printf '%s==>%s %s\n' "$GRN" "$RST" "$*"; }
warn() { printf '%s!  %s%s\n' "$YEL" "$*" "$RST" >&2; }
die()  { printf 'Error: %s\n' "$*" >&2; exit 1; }

usage() { awk 'NR>=3 && /^#/{sub(/^# ?/,""); print; next} NR>=3{exit}' "${BASH_SOURCE[0]}"; exit 0; }

# --- arg parsing ------------------------------------------------------------
while [ $# -gt 0 ]; do
  case "$1" in
    --local)      SOURCE="local" ;;
    --published)  SOURCE="published" ;;
    --name)       NAME="$2"; shift ;;
    --scope)      SCOPE="$2"; shift ;;
    --clients)    CLIENTS="$2"; shift ;;
    --api-key)    API_KEY="$2"; shift ;;
    --no-sync)    DO_SYNC=0 ;;
    -y|--yes)     ASSUME_YES=1 ;;
    -h|--help)    usage ;;
    *) die "unknown argument: $1 (try --help)" ;;
  esac
  shift
done

command -v npx >/dev/null 2>&1 || die "npx not found. Install Node.js (https://nodejs.org) to use mcp-add."

info "${B}webhook-mcp-server installer${RST}"
info "${DIM}Configures your AI clients to run this MCP server via mcp-add.${RST}"
info ""

# --- 1. source --------------------------------------------------------------
if [ -z "$SOURCE" ] && [ "$ASSUME_YES" -eq 0 ]; then
  info "Which server should your clients run?"
  info "  ${B}1${RST}) Published release  ${DIM}(uvx webhook-mcp-server — stable)${RST}"
  info "  ${B}2${RST}) Local dev checkout ${DIM}(this repo — your live edits)${RST}"
  printf 'Choose [1/2] (default 1): '
  read -r _src || true
  case "${_src:-1}" in
    2) SOURCE="local" ;;
    *) SOURCE="published" ;;
  esac
fi
SOURCE="${SOURCE:-published}"

# --- 2. build the launch command -------------------------------------------
if [ "$SOURCE" = "local" ]; then
  command -v uv >/dev/null 2>&1 || die "uv not found. Install it (https://docs.astral.sh/uv/) for local-dev mode."
  if [ "$DO_SYNC" -eq 1 ]; then
    step "Syncing local dependencies (uv sync)"
    uv sync --directory "$REPO_ROOT"
  fi
  # `uv run --directory` runs THIS checkout's source on every launch, so your
  # in-progress edits are what the client actually executes.
  COMMAND="uv run --directory $REPO_ROOT python server.py"
  info "Source: ${B}local dev${RST} ${DIM}($REPO_ROOT)${RST}"
else
  command -v uvx >/dev/null 2>&1 || warn "uvx not found on PATH; clients will need it at runtime (comes with uv)."
  COMMAND="uvx webhook-mcp-server"
  info "Source: ${B}published${RST} ${DIM}(uvx webhook-mcp-server)${RST}"
fi

# --- 3. scope + clients -----------------------------------------------------
if [ "$ASSUME_YES" -eq 0 ]; then
  printf 'Config scope [global/project] (default %s): ' "$SCOPE"
  read -r _scope || true
  SCOPE="${_scope:-$SCOPE}"

  info "Clients: comma-separated. e.g. ${DIM}claude code, cursor, vscode, windsurf, claude${RST}"
  printf 'Clients (default "%s"): ' "$CLIENTS"
  read -r _clients || true
  CLIENTS="${_clients:-$CLIENTS}"
fi

# --- 4. optional API key ----------------------------------------------------
if [ -z "$API_KEY" ] && [ "$ASSUME_YES" -eq 0 ]; then
  info ""
  info "${B}webhook.site API key${RST} ${DIM}(optional — paid accounts only)${RST}"
  info "${DIM}Enables custom domains, higher rate limits & private tokens. Free? Just press Enter.${RST}"
  printf 'API key (hidden, Enter to skip): '
  read -rs API_KEY || true
  echo
fi

# --- 5. assemble and run mcp-add -------------------------------------------
set -- --name "$NAME" --type stdio --command "$COMMAND" --scope "$SCOPE" --clients "$CLIENTS"
if [ -n "$API_KEY" ]; then
  set -- "$@" --env "WEBHOOK_SITE_API_KEY=$API_KEY"
  KEY_NOTE="set (${#API_KEY} chars)"
else
  KEY_NOTE="skipped (free tier)"
fi

info ""
step "Running mcp-add"
info "  name:    $NAME"
info "  command: $COMMAND"
info "  scope:   $SCOPE"
info "  clients: $CLIENTS"
info "  api key: $KEY_NOTE"
info ""

npx -y mcp-add "$@"

info ""
step "Done. Restart your AI client(s) to load ${B}$NAME${RST}."
