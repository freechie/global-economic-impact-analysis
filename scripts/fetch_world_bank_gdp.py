from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "open" / "world-bank" / "gdp.csv"
INDICATOR = "NY.GDP.MKTP.CD"
API = (
    "https://api.worldbank.org/v2/country/all/indicator/"
    f"{INDICATOR}?format=json&per_page=20000&date=1960:2026"
)


def fetch_rows(url: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    page = 1
    pages = 1
    while page <= pages:
        request = Request(
            f"{url}&page={page}",
            headers={"User-Agent": "global-economic-impact-analysis/0.1"},
        )
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        meta, records = payload
        pages = int(meta["pages"])
        rows.extend(records)
        page += 1
    return rows


def write_long_csv(records: list[dict[str, object]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for record in records:
        value = record.get("value")
        name = str((record.get("country") or {}).get("value") or "").strip()
        code = str(record.get("countryiso3code") or "").strip()
        year = record.get("date")
        if value is None or not name or not code or year is None:
            continue
        written.append((name, code, INDICATOR, int(year), float(value)))
    written.sort(key=lambda row: (row[1], row[3]))
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["Country Name", "Country Code", "Series Code", "Year", "GDP"])
        writer.writerows(written)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    write_long_csv(fetch_rows(API), args.output)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
