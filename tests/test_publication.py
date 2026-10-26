from hashlib import sha256
import json

import pandas as pd
import pytest

import main
from src.publication import publishing_run, read_snapshot, SnapshotUnavailable


def complete_fixture(tables, value=1):
    with publishing_run(tables, "demonstration") as publication:
        pd.DataFrame({"value": [value]}).to_csv(tables / "example.csv", index=False)
        report = tables.parent / "financial_sector_risk_report.pdf"
        report.write_bytes(f"synthetic report {value}".encode())
        publication.complete(report)
    return read_snapshot(tables)


def test_snapshot_is_coherent_when_working_files_change(tmp_path):
    metadata, files = complete_fixture(tmp_path / "tables")
    (tmp_path / "tables" / "example.csv").write_text("value\n999\n")
    (tmp_path / "financial_sector_risk_report.pdf").write_bytes(b"changed report")
    assert read_snapshot(tmp_path / "tables") == (metadata, files)
    assert files["reports/financial_sector_risk_report.pdf"] == b"synthetic report 1"


def test_completed_rerun_replaces_all_snapshot_bytes(tmp_path):
    first, files1 = complete_fixture(tmp_path)
    second, files2 = complete_fixture(tmp_path, 2)
    assert first["run_id"] != second["run_id"]
    assert files1 != files2
    assert files2["reports/financial_sector_risk_report.pdf"] == b"synthetic report 2"


@pytest.mark.parametrize("phase", ["fetch", "export", "report"])
def test_pipeline_failure_blocks_old_snapshot_and_mixed_outputs(monkeypatch, tmp_path, phase):
    tables = tmp_path / "tables"
    complete_fixture(tables)
    monkeypatch.setattr(main, "TABLES_DIR", tables)
    monkeypatch.setattr(main, "ensure_directories", lambda: None)
    def fail_run(*args):
        if phase != "fetch":
            (tables / "example.csv").write_text("value\n999\n")
        if phase == "report":
            (tmp_path / "financial_sector_risk_report.pdf").write_bytes(b"partial PDF")
        raise RuntimeError("fixture failure")
    monkeypatch.setattr(main, "_run_pipeline", fail_run)
    with pytest.raises(RuntimeError, match="fixture failure"):
        main.run_pipeline(False)
    assert json.loads((tables / "run_status.json").read_text())["status"] == "failed"
    with pytest.raises(SnapshotUnavailable):
        read_snapshot(tables)
    assert not (tables / ".pipeline.lock").exists()
    # A clean rerun recovers publication, rather than retaining the failed status.
    complete_fixture(tables, 2)


def test_running_or_interrupted_run_is_not_displayable(tmp_path):
    complete_fixture(tmp_path)
    with publishing_run(tmp_path, "live"):
        with pytest.raises(SnapshotUnavailable):
            read_snapshot(tmp_path)
    # Returning without completing, like a missing publish step, is not success.
    with pytest.raises(SnapshotUnavailable):
        read_snapshot(tmp_path)


def test_snapshot_write_failure_cannot_publish_old_report(tmp_path):
    complete_fixture(tmp_path)
    with pytest.raises(FileNotFoundError):
        with publishing_run(tmp_path, "live") as publication:
            publication.complete(tmp_path / "missing-new-report.pdf")
    with pytest.raises(SnapshotUnavailable):
        read_snapshot(tmp_path)
    assert not list(tmp_path.glob(".*.zip"))


def test_concurrent_writer_cannot_modify_current_run(tmp_path):
    with publishing_run(tmp_path, "live"):
        state = (tmp_path / "run_status.json").read_bytes()
        with pytest.raises(FileExistsError):
            with publishing_run(tmp_path, "live"):
                pytest.fail("Second writer acquired ownership")
        assert (tmp_path / "run_status.json").read_bytes() == state


@pytest.mark.parametrize("damage", ["zip", "state", "mismatch", "unreadable_zip"])
def test_corrupt_or_mismatched_snapshot_is_rejected(tmp_path, damage):
    complete_fixture(tmp_path)
    state_path = tmp_path / "run_status.json"
    if damage == "state":
        state_path.write_text("not json")
    elif damage == "mismatch":
        state = json.loads(state_path.read_text())
        state["run_id"] = "wrong-run"
        state_path.write_text(json.dumps(state))
    else:
        (tmp_path / "run_snapshot.zip").write_bytes(b"not a zip")
        if damage == "unreadable_zip":
            state = json.loads(state_path.read_text())
            state["sha256"] = sha256(b"not a zip").hexdigest()
            state_path.write_text(json.dumps(state))
    with pytest.raises(SnapshotUnavailable):
        read_snapshot(tmp_path)


def test_no_snapshot_is_not_a_legacy_success(tmp_path):
    (tmp_path / "example.csv").write_text("value\n1\n")
    with pytest.raises(SnapshotUnavailable):
        read_snapshot(tmp_path)


def test_run_change_during_read_is_rejected(monkeypatch, tmp_path):
    complete_fixture(tmp_path)
    path_type = type(tmp_path)
    original = path_type.read_bytes
    reads = 0
    def changing_read(path):
        nonlocal reads
        data = original(path)
        if path.name == "run_status.json":
            reads += 1
            if reads == 2:
                return b'{"status": "running"}'
        return data
    monkeypatch.setattr(path_type, "read_bytes", changing_read)
    with pytest.raises(SnapshotUnavailable, match="new run started"):
        read_snapshot(tmp_path)
