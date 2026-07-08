import csv
from pathlib import Path

csv_path = Path("data/tps.csv")
html_path = Path("index.html")

with open(csv_path) as f:
    rows = sorted(
        [r for r in csv.DictReader(f) if r["Intelligence"] not in ("-", "")],
        key=lambda r: float(r["Intelligence"]),
        reverse=True,
    )

def fmt(v):
    if v == "-":
        return "-"
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:g}"

rows_html = ""
for r in rows:
    latency = r["Latency"]
    if latency != "-":
        latency = f"{float(latency):.0f}"
    rows_html += f'<tr><td>{r["Model"]}</td><td>{r["Intelligence"]}</td><td>{latency}</td><td>{fmt(r["TPS"])}</td></tr>\n'

html_path.write_text(f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>NVIDIA NIM Models Benchmarks</title>
<style>
body {{ background: #1a1a1a; color: #e0e0e0; font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }}
h1 {{ text-align: center; }}
table {{ border-collapse: collapse; margin: 1rem auto; }}
th, td {{ padding: .4rem .6rem; border-bottom: 1px solid #333; }}
th:first-child, td:first-child {{ text-align: right; }}
th:not(:first-child), td:not(:first-child) {{ white-space: nowrap; text-align: center; }}
th {{ background: #2a2a2a; cursor: pointer; }}
</style>
</head>
<body>
<h1>integrate.api.nvidia.com/v1/models</h1>
<table>
<tr><th>Model</th><th>Intelligence</th><th>Latency</th><th>TPS</th></tr>
{rows_html}</table>
<script>
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
""")
