#!/usr/bin/env bash
# Wrapper used by the Codex VS Code extension to give each workspace an isolated
# Codex home directory and app-server port so that multiple workspaces can run
# concurrently without clobbering each other's state.

set -euo pipefail

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${THIS_DIR}/.." && pwd)"

# Allow manual overrides when needed.
if [[ -n "${CODEX_HOME:-}" ]]; then
  WORKSPACE_CODEX_HOME="${CODEX_HOME}"
else
  WORKSPACE_CODEX_HOME="${WORKSPACE_ROOT}/.codex-vscode"
  export CODEX_HOME="${WORKSPACE_CODEX_HOME}"
fi

mkdir -p "${WORKSPACE_CODEX_HOME}"

PORT_FILE="${WORKSPACE_CODEX_HOME}/app-port"
if [[ -f "${PORT_FILE}" ]]; then
  WORKSPACE_PORT="$(<"${PORT_FILE}")"
else
  # Derive a deterministic, non-privileged port from the workspace path.
  WORKSPACE_PORT="$(
    python3 - <<'PY' "${WORKSPACE_ROOT}"
import hashlib
import sys

path = sys.argv[1]
digest = hashlib.sha256(path.encode("utf-8")).digest()
# Map to the dynamic/private port range and stay clear of the very high end.
base = 20000
span = 10000
value = int.from_bytes(digest[:8], "big") % span
print(base + value)
PY
  )"
  echo "${WORKSPACE_PORT}" > "${PORT_FILE}"
fi

# Keep the CLI path in sync with the bundled extension version.
CLI_DIR="$(ls -d "${HOME}"/.vscode/extensions/openai.chatgpt-*-linux-x64/bin/linux-x86_64 2>/dev/null | sort | tail -n 1)"
if [[ -z "${CLI_DIR}" ]]; then
  echo "Unable to locate the Codex CLI bundled with the VS Code extension." >&2
  exit 1
fi

CLI_BIN="${CLI_DIR}/codex"

exec "${CLI_BIN}" -c "app_server.port=${WORKSPACE_PORT}" "$@"
