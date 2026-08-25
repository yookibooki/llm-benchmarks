import csv
import html
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.csv_utils import merge_provider_csvs
from shared.provider import PROVIDERS

PROVIDER_NAMES = list(PROVIDERS)
MERGED_PATH = str(REPO_ROOT / "data" / "tps.csv")
HTML_PATH = REPO_ROOT / "index.html"


def _int_or_float(v):
    """Parse a CSV cell that may be '-' or a number (int or float)."""
    if v in ("", "-", None):
        return None
    return float(v)


def _has_intelligence(r):
    v = r.get("Intelligence", "")
    return v not in ("", "-", None)


def _has_measurements(r):
    lat = r.get("Latency", "")
    tps = r.get("TPS", "")
    return lat not in ("", "-") and tps not in ("", "-")


def _fmt_number(v):
    """Format a numeric cell: one decimal for small latency, integer for TPS."""
    if v in ("", "-", None):
        return "-"
    try:
        f = float(v)
    except (ValueError, TypeError):
        return html.escape(str(v))
    if f < 10:
        return f"{f:.1f}"
    return str(round(f))


def reconcile_with_catalogs(all_rows):
    """Ensure the page mirrors the providers' endpoint catalogs exactly.

    Adds models in the endpoint catalog but missing from merged data, and
    removes rows whose model is no longer in its provider's catalog (model
    deleted from the endpoint). Benchmark failures are NOT a removal
    criterion — rows for catalogued models are preserved even when the
    latest benchmark attempt failed.
    Writes the reconciled data back to MERGED_PATH.
    """
    catalogs: dict[str, set[str]] = {}
    for prov in PROVIDER_NAMES:
        models_path = REPO_ROOT / prov / "data" / "models.txt"
        if not models_path.exists():
            continue
        with open(models_path) as f:
            catalogs[prov] = {line.strip() for line in f if line.strip()}

    for prov, endpoint_models in catalogs.items():
        csv_models = {r["Model"] for r in all_rows if r["Provider"] == prov}

        for model in sorted(endpoint_models - csv_models):
            all_rows.append({
                "Model": model,
                "Provider": prov,
                "Intelligence": "-",
                "Latency": "-",
                "TPS": "-",
            })

        stale = csv_models - endpoint_models
        if stale:
            print(f"  Removed {len(stale)} {prov} models absent from the endpoint catalog")
            for model in sorted(stale)[:10]:
                print(f"    - {model}")

    all_rows[:] = [
        r for r in all_rows
        if r["Provider"] not in catalogs or r["Model"] in catalogs[r["Provider"]]
    ]

    fieldnames = ["Model", "Provider", "Intelligence", "Latency", "TPS"]
    with open(MERGED_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    return all_rows


def validate_consistency(all_rows):
    """Warn when endpoint catalog models are missing from benchmark data."""
    for prov in PROVIDER_NAMES:
        models_path = REPO_ROOT / prov / "data" / "models.txt"
        if not models_path.exists():
            continue
        with open(models_path) as f:
            endpoint_models = {line.strip() for line in f if line.strip()}
        csv_models = {r["Model"] for r in all_rows if r["Provider"] == prov}
        missing = endpoint_models - csv_models
        if missing:
            print(
                f"[WARN] {prov}: {len(missing)} models in endpoint catalog but "
                f"missing from benchmark data: {sorted(missing)}",
                file=sys.stderr,
            )


def build_sort_key(r):
    """Sort: measured models with intelligence first, then the rest."""
    return (
        0 if _has_intelligence(r) else 1,
        0 if _has_measurements(r) else 1,
        -_int_or_float(r["Intelligence"]) if _has_intelligence(r) else 0,
        r.get("Provider", ""),
        r.get("Model", ""),
    )


def generate_rows_html(rows):
    parts = []
    for r in rows:
        model = html.escape(r.get("Model", ""))
        provider = html.escape(r.get("Provider", ""))
        intelligence = html.escape(r.get("Intelligence", "") or "-")
        latency = _fmt_number(r.get("Latency", ""))
        tps = _fmt_number(r.get("TPS", ""))
        badge = f' class="provider-{provider}"' if provider else ""
        parts.append(
            f"<tr><td>{model}</td><td{badge}>{provider}</td>"
            f"<td>{intelligence}</td><td>{latency}</td><td>{tps}</td></tr>\n"
        )
    return "".join(parts)


def generate_html(rows_html, timestamp):
    return f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>LLM Benchmarks Leaderboard</title>
<style>
body {{ background: #1a1a1a; color: #e0e0e0; font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }}
h1 {{ text-align: center; }}
.updated {{ text-align: center; color: #888; font-size: .9rem; margin-top: -.5rem; }}
table {{ border-collapse: collapse; margin: 1rem auto; }}
th, td {{ padding: .4rem .6rem; border-bottom: 1px solid #333; }}
th:first-child, td:first-child {{ text-align: right; }}
th:not(:first-child), td:not(:first-child) {{ white-space: nowrap; text-align: center; }}
th {{ background: #2a2a2a; cursor: pointer; }}
.provider {{ font-size: .75rem; padding: .1rem .3rem; border-radius: 3px; }}
.provider-nvidia {{ background: #76b900; color: #000; }}
.provider-openrouter {{ background: #ff6b35; color: #000; }}
.provider-google {{ background: #4285f4; color: #fff; }}
.provider-mistral {{ background: #ff7000; color: #000; }}
.provider-nous {{ background: #e74c3c; color: #fff; }}
</style>
</head>
<body>
<h1>LLM Benchmarks Leaderboard</h1>
<p class="updated" data-iso="{timestamp}"></p>
<table>
<tr><th>Model</th><th>Provider</th><th>Intelligence</th><th>Latency</th><th>TPS</th></tr>
{rows_html}</table>
<script>
function fmtAgo(secs) {{
  const m = Math.floor(secs / 60);
  if (m < 60) return m + ' minute' + (m === 1 ? '' : 's') + ' ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h + ' hour' + (h === 1 ? '' : 's') + ' ago';
  const d = Math.floor(h / 24);
  return d + ' day' + (d === 1 ? '' : 's') + ' ago';
}}
const el = document.querySelector('.updated');
const then = new Date(el.dataset.iso);
function tick() {{
  const secs = (Date.now() - then.getTime()) / 1000;
  el.textContent = 'Updated ' + fmtAgo(secs);
}}
tick();
setInterval(tick, 60000);
document.querySelectorAll('th').forEach((th, col) => {{
  th.addEventListener('click', () => {{
    const rows = [...document.querySelectorAll('tr')].slice(1);
    const asc = th.dataset.asc = th.dataset.asc === '1' ? '0' : '1';
    document.querySelectorAll('th').forEach(h => h.classList.remove('asc', 'desc'));
    th.classList.add(asc == 1 ? 'asc' : 'desc');
    rows.sort((a, b) => {{
      const va = a.children[col].textContent.trim();
      const vb = b.children[col].textContent.trim();
      const na = parseFloat(va), nb = parseFloat(vb);
      const cmp = (isNaN(na) || isNaN(nb)) ? va.localeCompare(vb) : na - nb;
      return asc == 1 ? cmp : -cmp;
    }});
    rows.forEach(r => r.parentNode.appendChild(r));
  }});
}});
</script>
</body>
</html>
"""


def main():
    provider_dirs = [str(REPO_ROOT / name) for name in PROVIDER_NAMES]
    merge_provider_csvs(provider_dirs, MERGED_PATH)

    if not Path(MERGED_PATH).exists():
        print(f"[error] {MERGED_PATH} not found, skipping HTML generation", file=sys.stderr)
        sys.exit(1)

    with open(MERGED_PATH) as f:
        all_rows = list(csv.DictReader(f))

    if not all_rows:
        print(f"[error] {MERGED_PATH} is empty, skipping HTML generation", file=sys.stderr)
        sys.exit(1)

    all_rows = reconcile_with_catalogs(all_rows)
    validate_consistency(all_rows)

    rows = sorted(all_rows, key=build_sort_key)

    rows_html = generate_rows_html(rows)
    timestamp = datetime.now(timezone.utc).isoformat()
    HTML_PATH.write_text(generate_html(rows_html, timestamp))
    print(f"Generated {HTML_PATH} with {len(rows)} models")


if __name__ == "__main__":
    main()
