# 🪵 Lumber Price Differential

Compare Home Depot lumber prices between two U.S. ZIP codes using the
[SerpApi Home Depot engine](https://serpapi.com/home-depot-search-api).
Outputs a formatted terminal summary and a dual-panel price comparison chart.

---

## Features

- Queries 6 standard lumber SKUs (customizable) per ZIP code
- Prints a side-by-side price table with per-item and average deltas
- Generates a dark-theme PNG chart (bar + delta panels)
- Fully CLI-driven with environment-variable key support
- GitLab CI/CD pipeline included (lint → test → build → release)

---

## Requirements

| Dependency | Version |
|---|---|
| Python | ≥ 3.11 |
| matplotlib | ≥ 3.7 |
| numpy | ≥ 1.24 |
| SerpApi account | [serpapi.com](https://serpapi.com) |

---

## Installation

```bash
git clone https://gitlab.com/<your-namespace>/lumber-price-diff.git
cd lumber-price-diff
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

Set your SerpApi key as an environment variable (recommended):

```bash
export SERPAPI_KEY="your_serpapi_key_here"
```

Or pass it directly via `--key` (see Usage below).

> ⚠️ **Never commit your API key.** `.env` and `secrets.yml` are in `.gitignore`.

---

## Usage

```
python main.py <ZIP1> <ZIP2> [OPTIONS]
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--key`, `-k` | `$SERPAPI_KEY` | SerpApi API key |
| `--out`, `-o` | `charts/lumber_<Z1>_vs_<Z2>.png` | Chart output path |
| `--no-chart` | off | Print summary only, skip chart |
| `--dpi` | 150 | Chart image resolution |
| `--queries` | (6 defaults) | Override product search terms |
| `--verbose`, `-v` | off | Enable debug logging |

### Examples

```bash
# Basic comparison
python main.py 90210 10001

# Custom output path
python main.py 30301 77001 --out results/atlanta_vs_houston.png

# Override products
python main.py 60601 02101 --queries "pressure treated 4x4x10" "cedar fence picket 6ft"

# Summary only (no chart)
python main.py 90210 10001 --no-chart
```

### Sample output

```
──────────────────────────────────────────────────────────────
  LUMBER PRICE DIFFERENTIAL  |  90210  →  10001
──────────────────────────────────────────────────────────────
Product                        90210     10001    Delta
──────────────────────────────────────────────────────────────
2x4x8 framing lumber           $8.97    $10.47    +$1.50
2x6x8 lumber                  $12.34    $13.98    +$1.64
4x4x8 post                    $15.22    $15.22    +$0.00
2x4x96 stud                    $9.18    $10.75    +$1.57
OSB sheathing 4x8             $22.47    $24.98    +$2.51
plywood 4x8 sheet             $34.97    $37.50    +$2.53
──────────────────────────────────────────────────────────────
  Average delta: +$1.63/item  (ZIP 10001 is pricier)
──────────────────────────────────────────────────────────────

✓ Chart saved → charts/lumber_90210_vs_10001.png
```

---

## Project Structure

```
lumber-price-diff/
├── .gitlab/
│   ├── issue_templates/
│   │   └── bug.md
│   └── merge_request_templates/
│       └── Default.md
├── src/
│   ├── lumber_compare.py   # SerpApi fetch + ProductPrice dataclass
│   └── chart.py            # Matplotlib chart renderer
├── tests/
│   ├── test_lumber_compare.py
│   └── test_main.py
├── charts/                 # Generated chart output (git-ignored)
├── .gitignore
├── .gitlab-ci.yml
├── CHANGELOG.md
├── main.py                 # CLI entry point
├── pyproject.toml          # pytest config
├── requirements.txt
└── requirements-dev.txt
```

---

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest                          # run all tests
pytest --cov=src                # with coverage report
```

---

## CI/CD Pipeline

The `.gitlab-ci.yml` defines four stages:

| Stage | Job | Trigger |
|---|---|---|
| lint | `ruff check` | MR + main branch |
| test | pytest + coverage | MR + main branch |
| test | smoke test (`--help` + import) | MR + main branch |
| build | tarball artifact | main branch |
| release | GitLab Release entry | semver tags (`v*.*.*`) |

### Creating a release

```bash
git tag v1.0.0
git push origin v1.0.0
```

The pipeline will automatically create a GitLab Release with the source tarball attached.

---

## Customizing Lumber Products

Edit `DEFAULT_QUERIES` in `src/lumber_compare.py`, or pass `--queries` at runtime:

```python
DEFAULT_QUERIES = [
    "2x4x8 framing lumber",
    "2x6x8 lumber",
    "4x4x8 post",
    "2x4x96 stud",
    "OSB sheathing 4x8",
    "plywood 4x8 sheet",
]
```

---

## License

MIT
