import os
import sys
from pathlib import Path

import pytest

VENDOR_ROOT = Path(__file__).resolve().parents[1] / "vendor"
for stub in ["coverage_stub", "pytest_cov_stub", "requests_mock_stub"]:
    stub_path = VENDOR_ROOT / stub
    if stub_path.exists():
        sys.path.insert(0, str(stub_path))

pytest_plugins = ["pytest_cov.plugin"]

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SECRET_KEY", "testkey")
os.environ.setdefault("RATE_LIMIT", "1000/minute")
os.environ.setdefault("LOG_LEVEL", "INFO")

import api.api as api_module  # noqa: E402
from api.vysalytica.db import Base, engine  # noqa: E402
from api.vysalytica.db.migrations import run_migrations  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.drop_all(bind=engine)
    run_migrations()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    run_migrations()
    yield


@pytest.fixture()
def client():
    with api_module.app.test_client() as client:
        yield client
