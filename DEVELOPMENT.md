# Development Guide

## Prerequisites

- Python 3.11+
- Redis 7+ (or use Docker: `docker run -d -p 6379:6379 redis:7-alpine`)
- Docker & Docker Compose (for containerized development)

## Local Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Copy environment config
cp .env.example .env

# Start the dev server
uvicorn app.main:app --reload --port 9000
```

## Project Structure

```
app/
├── api/
│   ├── routes.py           # API endpoint handlers
│   ├── middleware.py        # Request ID & rate limiting middleware
│   └── dependencies.py     # FastAPI dependency injection
├── core/
│   ├── config.py           # Settings (pydantic-settings)
│   ├── exceptions.py       # Custom exception classes
│   └── logging.py          # Structured logging setup
├── db/
│   └── redis_client.py     # Redis connection pool management
├── models/
│   └── schemas.py          # Pydantic request/response models
├── services/
│   ├── url_service.py      # Core URL shortening logic
│   └── og_service.py       # OpenGraph metadata fetching & caching
└── main.py                 # FastAPI application factory

cli/
└── main.py                 # Click CLI for URL management

tests/
├── conftest.py             # FakeRedis implementation & fixtures
├── test_api.py             # API endpoint tests
├── test_service.py         # Service layer unit tests
└── test_cli.py             # CLI command tests

docs/adr/                   # Architecture Decision Records
```

## Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Install all dependencies |
| `make lint` | Run ruff linter |
| `make format` | Format code with ruff |
| `make typecheck` | Run mypy (strict mode) |
| `make test` | Run tests with verbose output |
| `make test-cov` | Run tests with coverage report |
| `make run` | Start uvicorn dev server (port 9000, auto-reload) |
| `make docker-up` | Build and start containers |
| `make docker-down` | Stop containers and remove volumes |
| `make clean` | Remove build and cache artifacts |

## Running Tests

```bash
pytest -v                                       # all tests
pytest --cov --cov-report=term-missing          # with coverage
```

Tests use a `FakeRedis` implementation (see `tests/conftest.py`) so no running Redis instance is needed.

## Linting & Type Checking

```bash
ruff check .          # lint
ruff format .         # format
mypy app cli          # type check (strict)
```

## Pre-commit Hooks

Pre-commit hooks are configured for automated checks on each commit:

```bash
pre-commit install    # set up hooks
pre-commit run --all  # run on all files
```

## CI/CD

GitHub Actions runs three jobs on every push and PR:

1. **Lint** — ruff check, ruff format, mypy
2. **Test** — pytest with coverage against a Redis service
3. **Docker** — build, start, and health-check the containerized stack

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes and ensure all checks pass (`make lint && make typecheck && make test`)
4. Commit with a descriptive message
5. Open a pull request
