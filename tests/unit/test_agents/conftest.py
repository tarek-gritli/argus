"""
Shared fixtures for security-agent unit tests.

OSV API calls and cache reads are stubbed out so tests are deterministic and
network-free. The static dependency_cves.json database is always the sole
source of truth during unit tests.
"""

import pytest
from specialized.security import osv_client


@pytest.fixture(autouse=True)
def stub_osv_api(monkeypatch):
    """Replace the entire OSV query function with a no-op returning empty results.

    Patching query() (not just _batch_api_call) is necessary because the real
    query() reads a disk cache that may have been populated by earlier runs with
    live network access. Bypassing the whole function guarantees isolation.
    """
    monkeypatch.setattr(
        osv_client,
        "query",
        lambda deps, cache_file: {},
    )
