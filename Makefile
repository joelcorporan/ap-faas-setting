##@ Formatting

format-black: ## black (code formatter)
	@black .

format-isort: ## isort (import formatter)
	@isort .

format: format-black format-isort ## run all formatters

##@ Linting

lint-black: ## black in linting mode
	@black . --check

lint-isort: ## isort in linting mode
	@isort . --check

lint-flake8: ## flake8 (linter)
	@flake8 .

lint-mypy: ## mypy (static-type checker)
	@mypy --config-file pyproject.toml . --install-types

lint-mypy-report: ## run mypy & create report
	@mypy --config-file pyproject.toml . --html-report ./mypy_html

lint: lint-black lint-isort lint-flake8 lint-mypy ## run all linters