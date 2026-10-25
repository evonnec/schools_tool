from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def in_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """The modules read ./input/*.csv relative to the working directory."""
    monkeypatch.chdir(REPO_ROOT)
