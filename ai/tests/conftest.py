import os

import pytest

pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "e2e: marks tests as end-to-end (require real database)",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip e2e tests unless a real database URL is available."""
    has_db = bool(os.environ.get("PGVECTOR_DSN"))
    if not has_db:
        for item in items:
            if item.get_closest_marker("e2e"):
                item.add_marker(
                    pytest.mark.skip(reason="e2e tests require a real database (set DATABASE_URL)")
                )
