"""
Generates index.html from tps.csv data.
Only includes models actually benchmarked on NVIDIA NIM.
Outputs a self-contained HTML file with dark mode and sortable columns.
"""

import csv

TPS_PATH = "_data/tps.csv"
INTELLIGENCE_PATH = "_data/intelligence.csv"
OUTPUT_PATH = "index.html"


def main():
    # Read intelligence.csv for lookup
    intelligence = {}
    with open(INTELLIGENCE_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            intelligence[row["name"]] = row["intelligence"]

    # Read tps.csv - these are the only NIM-hosted models
    models = []
    with open(TPS_PATH) as f:
        reader = csv.DictReader(f)
        for row in reader:
            models.append(row)

    # Sort by intelligence index descending (highest first)
    def sort_key(row):
        val = intelligence.get(row["name"], "0")
        try:
            return -float(val)
        except (ValueError, TypeError):
            return 0

    models.sort(key=sort_key)

    # Build table rows
    rows_html = []
    for row in models:
        name = row["name"]
        intel = intelligence.get(name, "-")
        ttft_raw = row["ttft"]
        tps_raw = row["tps"]

        # Format intelligence
        try:
            intel_fmt = f"{float(intel):.2f}"
        except (ValueError, TypeError):
            intel_fmt = "-"

        # Convert TTFT from ms to seconds
        if ttft_raw == "-":
            ttft_fmt = "-"
        else:
            try:
                ttft_fmt = f"{float(ttft_raw) / 1000:.2f}"
            except (ValueError, TypeError):
                ttft_fmt = "-"

        # Format TPS
        if tps_raw == "-":
            tps_fmt = "-"
        else:
            try:
                tps_fmt = f"{float(tps_raw):.2f}"
            except (ValueError, TypeError):
                tps_fmt = "-"

        rows_html.append(
            f"<tr><td>{name}</td><td>{intel_fmt}</td><td>{ttft_fmt}</td><td>{tps_fmt}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NVIDIA NIM Models Benchmarks</title>
<style>
body {{ background: #1a1a1a; color: #e0e0e0; font-family: system-ui, sans-serif; margin: 0; padding: 2rem; overflow-x: hidden; }}
h1 {{ text-align: center; margin-bottom: 1.5rem; }}
table {{ border-collapse: collapse; width: auto; margin: 0 auto; }}
th, td {{ padding: 0.4rem 0.6rem; text-align: left; border-bottom: 1px solid #333; }}
th:first-child, td:first-child {{ white-space: normal; min-width: 200px; text-align: right; }}
th:not(:first-child), td:not(:first-child) {{ white-space: nowrap; text-align: center; }}
th {{ background: #2a2a2a; }}
tr:hover {{ background: #252525; }}
a {{ color: #4fc3f7; }}
th {{ cursor: pointer; user-select: none; }}
th .arrow {{ display: inline-block; margin-left: 0.3rem; font-size: 0.5rem; opacity: 0.4; transition: opacity 0.2s; vertical-align: middle; line-height: 1; }}
th:hover .arrow, th.active .arrow {{ opacity: 1; }}
th .arrow::before {{ content: '\\25B2'; }}
th .arrow::after {{ content: '\\25BC'; }}
th.asc .arrow::before, th.desc .arrow::after {{ opacity: 1; }}
th.asc .arrow::after, th.desc .arrow::before {{ opacity: 0.2; }}
</style>
</head>
<body>
<h1>NVIDIA NIM Models Benchmarks</h1>
<table>
<thead>
<tr><th>Model <span class="arrow"></span></th><th>Index <span class="arrow"></span></th><th>TTFT (s) <span class="arrow"></span></th><th>TPS <span class="arrow"></span></th></tr>
</thead>
<tbody>
{chr(10).join(rows_html)}
</tbody>
</table>
<p style="text-align:center;margin-top:1rem;"><a href="https://yookibooki.github.io/nvidia-nim-benchmarks">Results published at yookibooki.github.io/nvidia-nim-benchmarks</a></p>
<script>
document.querySelectorAll('th').forEach((th, col) => {{
  th.addEventListener('click', () => {{
    const tbody = document.querySelector('tbody');
    const rows = [...tbody.querySelectorAll('tr')];
    const asc = th.dataset.asc = th.dataset.asc === '1' ? '0' : '1';
    document.querySelectorAll('th').forEach(h => {{ h.classList.remove('asc', 'desc'); }});
    th.classList.add(asc == 1 ? 'asc' : 'desc');
    rows.sort((a, b) => {{
      const va = a.children[col].textContent.trim();
      const vb = b.children[col].textContent.trim();
      const na = parseFloat(va), nb = parseFloat(vb);
      const cmp = (isNaN(na) || isNaN(nb)) ? va.localeCompare(vb) : na - nb;
      return asc == 1 ? cmp : -cmp;
    }});
    rows.forEach(r => tbody.appendChild(r));
  }});
}});
</script>
</body>
</html>"""

    with open(OUTPUT_PATH, "w") as f:
        f.write(html)

    print(f"Wrote {len(models)} NIM-hosted models to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
