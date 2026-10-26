"""Publish one coherent, completed dashboard snapshot; never mix pipeline runs."""

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from collections.abc import Iterator
from typing import Any
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED, BadZipFile


class SnapshotUnavailable(RuntimeError):
    """No verified, completed run is available for display."""


def write_state(tables: Path, state: dict[str, Any]) -> None:
    path = tables / "run_status.json"
    temporary = tables / f".{uuid4().hex}.json"
    try:
        temporary.write_text(json.dumps(state), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass
class Publication:
    tables: Path
    run_id: str
    mode: str

    def complete(self, report: Path) -> None:
        """Build a ZIP then atomically publish it; loose files are working artifacts."""
        temporary = self.tables / f".{self.run_id}.zip"
        try:
            with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
                archive.writestr("run.json", json.dumps({"run_id": self.run_id, "mode": self.mode}))
                for path in sorted(self.tables.glob("*.csv")):
                    archive.write(path, f"tables/{path.name}")
                archive.write(report, f"reports/{report.name}")
            digest = sha256(temporary.read_bytes()).hexdigest()
            temporary.replace(self.tables / "run_snapshot.zip")
            write_state(self.tables, dict(status="complete", run_id=self.run_id,
                                          mode=self.mode, sha256=digest))
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def publishing_run(tables: Path, mode: str) -> Iterator[Publication]:
    """A failed/interrupted run cannot expose mixed old and new files as current."""
    tables.mkdir(parents=True, exist_ok=True)
    # One writer owns the ordinary output paths. A hard-killed process leaves this
    # lock behind; remove it manually only after confirming the writer is stopped.
    lock = tables / ".pipeline.lock"
    with lock.open("x", encoding="utf-8") as handle:
        run_id = uuid4().hex
        handle.write(run_id)
    try:
        write_state(tables, dict(status="running", run_id=run_id, mode=mode))
        try:
            yield Publication(tables, run_id, mode)
        except BaseException:
            write_state(tables, dict(status="failed", run_id=run_id, mode=mode))
            raise
    finally:
        lock.unlink(missing_ok=True)


def read_snapshot(tables: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
    """Read one immutable byte snapshot, rejecting stale, damaged, or changing runs."""
    try:
        state_bytes = (tables / "run_status.json").read_bytes()
        state = json.loads(state_bytes)
        if state.get("status") != "complete":
            raise SnapshotUnavailable("The latest pipeline run is incomplete or failed. Run the pipeline successfully before viewing results.")
        data = (tables / "run_snapshot.zip").read_bytes()
        if sha256(data).hexdigest() != state.get("sha256"):
            raise SnapshotUnavailable("The completed output snapshot failed its integrity check.")
        with ZipFile(BytesIO(data)) as archive:
            metadata = json.loads(archive.read("run.json"))
            if metadata.get("run_id") != state.get("run_id"):
                raise SnapshotUnavailable("Output snapshot and run status do not match.")
            files = {name: archive.read(name) for name in archive.namelist() if name != "run.json"}
        if (tables / "run_status.json").read_bytes() != state_bytes:
            raise SnapshotUnavailable("A new run started while loading results. Refresh after it completes.")
        return metadata, files
    except SnapshotUnavailable:
        raise
    except (OSError, ValueError, KeyError, BadZipFile, AttributeError) as exc:
        raise SnapshotUnavailable("No readable completed output snapshot. Run python main.py or python main.py --demo.") from exc
