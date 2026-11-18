import hashlib
import json
from pathlib import Path
import sys
import os
import subprocess

import pytest

from src.sample_config import ROOT, SampleConfig
from src.sample_run import run_sample, output_path


def test_offline_run_repeatability_and_manifest(tmp_path):
    a, b = tmp_path / "first", tmp_path / "second"
    first = run_sample(a, SampleConfig(simulations=12))
    second = run_sample(b, SampleConfig(simulations=12))
    assert first == second
    assert len(first["artifact_sha256"]) == 8
    for name, expected_hash in first["artifact_sha256"].items():
        assert hashlib.sha256((a/name).read_bytes()).hexdigest() == expected_hash
        assert (a/name).read_bytes() == (b/name).read_bytes()
    assert (a/"synthetic_brief.pdf").read_bytes().startswith(b"%PDF-")
    assert (a/"synthetic_scores.png").read_bytes().startswith(b"\x89PNG")
    assert json.loads((a/"run_manifest.json").read_text())["status"].startswith("SYNTHETIC")
    assert "src.data_sources" not in sys.modules
    assert "src.acled_live" not in sys.modules


def test_existing_directory_is_untouched(tmp_path):
    sentinel = tmp_path / "existing.txt"
    sentinel.write_text("preserve")
    with pytest.raises(FileExistsError):
        run_sample(tmp_path, SampleConfig(simulations=2))
    assert sentinel.read_text() == "preserve"
    assert list(tmp_path.iterdir()) == [sentinel]


@pytest.mark.parametrize("path", [ROOT, ROOT.parent, ROOT / "outputs/reports/new", ROOT / "data/raw/new"])
def test_protected_output_paths(path):
    with pytest.raises(ValueError):
        output_path(path)


@pytest.mark.parametrize("kwargs", [{"seed":-1},{"simulations":0},{"simulations":1},
    {"noise_std":-1},{"noise_std":float("nan")},{"noise_std":float("inf")}])
def test_invalid_configuration(kwargs):
    with pytest.raises(ValueError):
        SampleConfig(**kwargs)


def test_preserved_production_sources():
    baseline = json.loads((ROOT / "tests/preserved_source_hashes.json").read_text())
    for path, expected in baseline["sha256_lf"].items():
        content = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == expected, path


def test_cli_repeats_in_separate_offline_processes(tmp_path):
    # sitecustomize blocks sockets before imports in each child interpreter.
    (tmp_path / "sitecustomize.py").write_text(
        "import socket\ndef blocked(*a, **k):\n raise RuntimeError('Network forbidden')\n"
        "socket.socket.connect = blocked\nsocket.socket.connect_ex = blocked\n"
        "socket.create_connection = blocked\n")
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(tmp_path), str(ROOT)]))
    for name in ("cli_a", "cli_b"):
        result = subprocess.run([sys.executable, "-m", "src.sample_run", "--simulations", "5",
                                 "--output-dir", str(tmp_path/name)], cwd=tmp_path,
                                env=env, capture_output=True, text=True, check=True)
        assert "SYNTHETIC DEMO complete" in result.stdout
    assert (tmp_path/"cli_a/run_manifest.json").read_bytes() == (tmp_path/"cli_b/run_manifest.json").read_bytes()
