#!/bin/bash
# Script to rebuild git history into clean conventional commits.
#
# This is a DOCUMENTATION SCRIPT — it does not execute automatically.
# Follow the instructions below to manually restructure the git history.
#
# ============================================================================
# PREREQUISITES
# ============================================================================
#
# 1. All changes are committed (clean working tree)
# 2. All tests pass:          pytest -v
# 3. Linting is clean:        ruff check . && ruff format --check .
# 4. Type checking passes:    mypy app cli
# 5. You have a backup or can force-push:
#        git branch backup-before-rebase
#
# ============================================================================
# INSTRUCTIONS
# ============================================================================
#
# Run an interactive rebase from the root commit:
#
#     git rebase -i --root
#
# In the editor, restructure ALL changes into the 14 commits listed below.
# Use 'edit' to stop at a commit and amend its contents, or 'squash'/'fixup'
# to fold commits together. Between stops, use:
#
#     git reset HEAD~1                    # unstage the current commit
#     git add <files>                     # stage files for this logical commit
#     git commit -m "type: description"   # create the clean commit
#     git rebase --continue               # move to the next stop
#
# ============================================================================
# TARGET COMMIT HISTORY (oldest → newest)
# ============================================================================
#
# 1.  chore: scaffold project structure with pyproject.toml
#
#     Files: pyproject.toml, requirements.txt, requirements-dev.txt,
#            .gitignore, .env.example, Makefile, Dockerfile,
#            docker-compose.yml, app/__init__.py, cli/__init__.py,
#            tests/__init__.py
#
# 2.  feat: add Redis client with health check and dependency injection
#
#     Files: app/core/config.py, app/db/redis_client.py,
#            app/api/dependencies.py
#
# 3.  feat: add URL shortening service with idempotent hashing
#
#     Files: app/core/exceptions.py, app/models/schemas.py (ShortenRequest,
#            ShortenResponse, HealthResponse), app/services/url_service.py
#            (create_short_url, resolve_short_url, update_short_url,
#            delete_short_url)
#
# 4.  feat: add FastAPI routes — shorten, redirect, preview
#
#     Files: app/api/routes.py (health, shorten, redirect endpoints),
#            app/main.py
#
# 5.  feat: add Click CLI — add, update, delete commands
#
#     Files: cli/main.py
#
# 6.  test: add comprehensive test suite
#
#     Files: tests/conftest.py (FakeRedis, FakePipeline, fixtures),
#            tests/test_api.py, tests/test_service.py, tests/test_cli.py
#
# 7.  fix: escape HTML in preview endpoint to prevent XSS
#
#     Files: app/api/routes.py (html.escape on all user-controlled values),
#            tests/test_api.py (test_preview_escapes_html_to_prevent_xss)
#
# 8.  feat: add request-id and rate-limiting middleware
#
#     Files: app/api/middleware.py (RequestIDMiddleware, RateLimitMiddleware),
#            app/main.py (middleware registration),
#            app/core/config.py (rate_limit_* settings),
#            tests/test_api.py (rate limit and request-id tests)
#
# 9.  feat: add structured JSON logging with request correlation
#
#     Files: app/core/logging.py (JSONFormatter, setup_logging),
#            app/core/config.py (log_format, log_level settings),
#            app/main.py (setup_logging call)
#
# 10. feat: add click analytics with /stats endpoint and referrer tracking
#
#     Files: app/services/url_service.py (get_url_stats, click recording
#            in resolve_short_url), app/models/schemas.py (StatsResponse,
#            ReferrerInfo), app/api/routes.py (stats endpoint),
#            tests/test_api.py (stats and referrer tests)
#
# 11. feat: add TTL/expiration support for short URLs
#
#     Files: app/services/url_service.py (ttl_seconds param, meta:{code}
#            hash), app/models/schemas.py (expires_at, ttl_remaining fields),
#            tests/test_api.py (TTL and expiration tests)
#
# 12. feat: add OpenGraph preview cards with Redis caching
#
#     Files: app/services/og_service.py, app/api/routes.py (preview
#            endpoint with OG card HTML), tests/test_api.py (OG preview,
#            fallback, and cache tests)
#
# 13. ci: add GitHub Actions CI, ruff, mypy, pre-commit
#
#     Files: .github/workflows/ci.yml, .pre-commit-config.yaml
#
# 14. docs: add ADRs, architecture diagram, update HOWTO.md
#
#     Files: HOWTO.md, docs/adr/001-redis-over-mongodb.md,
#            docs/adr/002-idempotent-url-shortening.md,
#            docs/adr/003-og-preview-with-cache.md,
#            docs/adr/004-rate-limiting-strategy.md
#
# ============================================================================
# AFTER REBASE
# ============================================================================
#
# Verify everything still works:
#
#     ruff check . && ruff format --check .
#     mypy app cli
#     pytest -v
#
# Then force-push (use --force-with-lease for safety):
#
#     git push --force-with-lease origin main
#
# If anything goes wrong, restore from backup:
#
#     git checkout backup-before-rebase
#     git branch -D main
#     git checkout -b main
#
# ============================================================================
