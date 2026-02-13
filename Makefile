.PHONY: setup test check-mcp clean help

VENV := .venv/bin

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Create venv and install dependencies
	./setup.sh

test: ## Run unit tests
	$(VENV)/python -m pytest tests/ -v

check-mcp: ## Verify OLS4 MCP is reachable
	@curl -s -o /dev/null -w "OLS4 MCP: HTTP %{http_code}\n" \
		"http://www.ebi.ac.uk/ols4/api/mcp" --max-time 10

clean: ## Remove generated files
	rm -rf .cache/ .venv/ *.egg-info/ build/ dist/ outputs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
