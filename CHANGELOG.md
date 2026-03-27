# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [1.0.0] – Initial Release

### Added
- `src/lumber_compare.py` – SerpApi Home Depot fetch + ProductPrice dataclass
- `src/chart.py` – dual-panel dark-theme price comparison chart
- `main.py` – CLI with `--key`, `--out`, `--no-chart`, `--queries`, `--dpi` flags
- `tests/` – unit tests for core logic and CLI
- `.gitlab-ci.yml` – lint → test → build → release pipeline
- GitLab MR and issue templates
