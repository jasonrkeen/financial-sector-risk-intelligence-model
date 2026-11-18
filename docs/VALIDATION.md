# Reproduction and validation scope

Evidence date: November 18, 2026.

## Verified locally

Python 3.14.4 on Windows, with the exact dependencies committed in `requirements.txt` and `requirements-dev.txt`: 28 pytest cases pass. Two independent offline processes produce matching artifact hashes and manifests. Tests block outbound socket connections. The default sample uses 1,000 draws with seed 42 and noise standard deviation 7.5.

The suite checks hand-calculated weighted scores and scenario changes; risk-band boundaries; clipping; ranking; seeded repeatability; changed-seed sensitivity; zero-noise identity; finite bounded simulation outputs; simulation band-share bounds; input preservation; refusal to overwrite output directories; and configuration constraints. Repeated CSV, PNG, and PDF files match byte for byte within a recorded environment. Cross-platform byte identity is not claimed.

## Automated evidence

The [workflow](../.github/workflows/tests.yml) installs the pinned environment on Windows and Ubuntu, runs `pip check` and all tests, generates the default sample, and verifies tracked files are unchanged. Each successful job uploads the sample files and `run_manifest.json`. Consult [actual run results](https://github.com/jasonrkeen/financial-sector-risk-intelligence-model/actions/workflows/tests.yml) rather than treating the existence of a workflow as proof of success.

The manifest records the fictional input hash, sample settings, Python/platform and principal numerical/rendering package versions, requirements-file hash, scoring/scenario/simulation/sample source hashes, and generated artifact hashes. It deliberately excludes timestamps and absolute paths. Exact dependency pins provide an installation baseline, not an archive of package distributions or operating-system libraries.

## Preservation boundary

[Source hashes](../tests/preserved_source_hashes.json) freeze `main.py` and every pre-existing `src/` module at commit `7e4c45256cbf6c1b49c567c46d296746b58f20fb`; the test normalizes line endings only. No scoring formula, threshold, weight, scenario, or Monte Carlo implementation was changed. Sample configuration and rendering are separate additions. Published screenshots and release history are outside the sample output path and remain unchanged.

## Not established

These checks do not validate live connectors, credential handling, fallback-data quality, dashboard behavior, or the full live report pipeline. They do not reproduce historical published outputs under their original environment. No live sources were fetched for this sample. Predictive accuracy, calibrated real-world probabilities, independent replication, and empirical validity of analyst-defined weights remain unestablished. Simulation shares describe model sensitivity only.
