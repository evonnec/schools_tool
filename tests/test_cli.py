import io
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from schools_tool.cli import main

SRC = Path(__file__).resolve().parents[1] / "src"

# The write_school_csv fixture: rows of (ID, name, city, state, locale)
WriteCsv = Callable[[list[tuple[str, str, str, str, str]]], Path]


def test_counts(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["counts"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Total Schools: 34779\n")


def test_counts_writes_csv_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["counts", "--output-dir", str(tmp_path / "output")]) == 0
    assert sorted(path.name for path in (tmp_path / "output").iterdir()) == [
        "schools_by_city.csv",
        "schools_by_metro_locale.csv",
        "schools_by_state.csv",
        "summary.csv",
    ]
    assert "Wrote " in capsys.readouterr().err


def test_search_joins_query_words(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["search", "foley", "high", "alabama"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith('Results for "foley high alabama"')
    assert lines[1:3] == ["1. FOLEY HIGH SCHOOL", "FOLEY, AL"]


def test_search_limit(capsys: pytest.CaptureFixture[str]) -> None:
    main(["search", "--limit", "1", "foley"])
    assert len(capsys.readouterr().out.splitlines()) == 3


def test_search_reads_queries_from_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        sys, "stdin", io.StringIO("kuskokwim\n\n  \nfoley high alabama\n")
    )
    assert main(["search"]) == 0
    headers = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("Results")
    ]
    assert [header.split('"')[1] for header in headers] == [
        "kuskokwim",
        "foley high alabama",
    ]


def test_alternate_data_file(
    write_school_csv: WriteCsv, capsys: pytest.CaptureFixture[str]
) -> None:
    path = write_school_csv([("1", "PINE SCHOOL", "DENVER", "CO", "1")])
    assert main(["--data", str(path), "search", "pine"]) == 0
    assert "1. PINE SCHOOL" in capsys.readouterr().out
    assert main(["--data", str(path), "counts"]) == 0
    assert capsys.readouterr().out.startswith("Total Schools: 1\n")


@pytest.mark.parametrize("limit", ["0", "-1", "two"])
def test_invalid_limit(limit: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["search", "--limit", limit, "foley"])
    assert exit_info.value.code == 2
    assert "--limit" in capsys.readouterr().err


def test_missing_data_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--data", str(tmp_path / "nope.csv"), "counts"])
    assert exit_info.value.code == 2
    assert "No such file" in capsys.readouterr().err


def test_malformed_data_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("NCESSCH,SCHNAM05\n1,PINE SCHOOL\n")
    with pytest.raises(SystemExit) as exit_info:
        main(["--data", str(path), "counts"])
    assert exit_info.value.code == 2
    assert "missing columns" in capsys.readouterr().err


def test_no_command_is_an_error() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main([])
    assert exit_info.value.code == 2


def test_python_dash_m(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "schools_tool", "search", "kuskokwim"],
        capture_output=True,
        text=True,
        check=True,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(SRC)},
    )
    assert "1. TOP OF THE KUSKOKWIM SCHOOL" in result.stdout
