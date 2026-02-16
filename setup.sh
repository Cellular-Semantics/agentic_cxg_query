#!/usr/bin/env bash
set -euo pipefail

MIN_PYTHON="3.10"

# ---- Helpers ----------------------------------------------------------------

info()  { printf '\033[1;34m[INFO]\033[0m  %s\n' "$*"; }
ok()    { printf '\033[1;32m[OK]\033[0m    %s\n' "$*"; }
warn()  { printf '\033[1;33m[WARN]\033[0m  %s\n' "$*"; }
fail()  { printf '\033[1;31m[FAIL]\033[0m  %s\n' "$*"; exit 1; }

# ---- Check Python -----------------------------------------------------------

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
[ -n "$PYTHON" ] || fail "Python not found. Install Python >=$MIN_PYTHON."

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Found $PYTHON $PY_VERSION"

if "$PYTHON" -c "
import sys
min_parts = [int(x) for x in '$MIN_PYTHON'.split('.')]
if (sys.version_info.major, sys.version_info.minor) < tuple(min_parts):
    sys.exit(1)
" 2>/dev/null; then
    ok "Python version OK (>=$MIN_PYTHON)"
else
    fail "Python >=$MIN_PYTHON required, found $PY_VERSION"
fi

# ---- Create venv ------------------------------------------------------------

if [ ! -d .venv ]; then
    info "Creating virtual environment..."
    "$PYTHON" -m venv .venv
    ok "Virtual environment created"
else
    info "Virtual environment already exists"
fi

# ---- Install ----------------------------------------------------------------

info "Installing dependencies (editable)..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -e ".[dev]" -q
ok "Dependencies installed"

# ---- Verify imports ----------------------------------------------------------

info "Verifying imports..."
.venv/bin/python -c "
from cxg_query_enhancer import enhance
from gene_resolver import resolve_genes, build_var_value_filter
print('  cxg_query_enhancer.enhance ......... OK')
print('  gene_resolver.resolve_genes ........ OK')
print('  gene_resolver.build_var_value_filter OK')
"
ok "All imports verified"

# ---- Check OLS4 MCP ---------------------------------------------------------

info "Checking OLS4 MCP connectivity..."
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://www.ebi.ac.uk/ols4/api/mcp" --max-time 10 2>/dev/null || echo "000")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "405" ]; then
        ok "OLS4 MCP reachable (HTTP $HTTP_CODE)"
    else
        warn "OLS4 MCP returned HTTP $HTTP_CODE (may still work via MCP protocol)"
    fi
else
    warn "curl not found, skipping OLS4 connectivity check"
fi

# ---- Sync shared config (.claude → .codex) -----------------------------------

info "Syncing shared configs from .claude to .codex..."

# Agents
mkdir -p .codex/agents
for src in .claude/agents/*.md; do
    [ -f "$src" ] || continue
    dest=".codex/agents/$(basename "$src")"
    if [ -f "$dest" ] && diff -q "$src" "$dest" &>/dev/null; then
        continue
    fi
    cp "$src" "$dest"
    ok "  Synced agents/$(basename "$src")"
done

# Skills (mirror entire skill directories)
if [ -d .claude/skills ]; then
    for skill_dir in .claude/skills/*/; do
        [ -d "$skill_dir" ] || continue
        skill_name="$(basename "$skill_dir")"
        dest_dir=".codex/skills/$skill_name"
        mkdir -p "$dest_dir"
        # Sync all files recursively
        rsync -a --delete "$skill_dir" "$dest_dir/"
        ok "  Synced skills/$skill_name/"
    done
fi

# AGENTS.md ← CLAUDE.md
if [ -f CLAUDE.md ]; then
    if ! [ -f AGENTS.md ] || ! diff -q CLAUDE.md AGENTS.md &>/dev/null; then
        cp CLAUDE.md AGENTS.md
        ok "  Synced AGENTS.md"
    fi
fi

# ---- Done --------------------------------------------------------------------

echo ""
ok "Setup complete!"
echo ""
info "Activate the environment:"
echo "  source .venv/bin/activate"
echo ""
info "Usage with Claude Code:"
echo "  claude"
echo "  /cxg-query female T cells in lung tissue"
echo ""
info "Run tests:"
echo "  make test"
