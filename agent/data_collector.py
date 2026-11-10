"""
data_collector.py: Fetches cancer statistics from three confirmed-working sources:
  1. WHO GHO  — 11 cancer/NCD indicators (~32,000 rows)
  2. World Bank — 5 NCD/cancer mortality indicators (~32,000 rows)
  3. Wikipedia — 15 cancer-type profiles (full text).
"""

import os, time, sqlite3, json
import urllib.request, urllib.parse
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from config import (
    WHO_GHO_API, WHO_INDICATORS,
    SQLITE_DB, DATA_DIR,
    CANCER_TYPES_TO_SCRAPE,
)

console    = Console()
WIKI_DELAY = 1.5

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    )
}


# HTTP helper

def _get_json(url: str, retries: int = 4):
    """
    Fetch JSON via urllib with exponential-backoff retry on 429.
    Uses urllib directly.
    """
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            if "429" in str(exc) and attempt < retries - 1:
                wait = 2 ** (attempt + 2)
                console.print(f"  [dim]rate-limited, retrying in {wait}s...[/dim]")
                time.sleep(wait)
            else:
                console.print(f"  [yellow]WARNING {url[:80]}: {exc}[/yellow]")
                return None
    return None


# Database setup

def init_database(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS who_statistics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator    TEXT NOT NULL,
            label        TEXT,
            country_code TEXT,
            year         INTEGER,
            sex          TEXT,
            value        REAL,
            source       TEXT DEFAULT 'WHO GHO',
            fetched_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS worldbank_statistics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator    TEXT NOT NULL,
            label        TEXT,
            country_code TEXT,
            country_name TEXT,
            year         INTEGER,
            value        REAL,
            source       TEXT DEFAULT 'World Bank',
            fetched_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS cancer_profiles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cancer_type     TEXT NOT NULL,
            description     TEXT,
            incidence_notes TEXT,
            mortality_notes TEXT,
            survival_notes  TEXT,
            risk_factors    TEXT,
            source_url      TEXT,
            fetched_at      TEXT
        );
        CREATE TABLE IF NOT EXISTS cancer_statistics (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            cancer_type  TEXT NOT NULL,
            metric       TEXT,
            gender       TEXT,
            year         INTEGER,
            region       TEXT,
            value        REAL,
            unit         TEXT,
            source       TEXT,
            fetched_at   TEXT
        );
        CREATE TABLE IF NOT EXISTS raw_documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT,
            content     TEXT,
            source_url  TEXT,
            cancer_type TEXT,
            fetched_at  TEXT
        );
    """)
    conn.commit()


# 1. WHO GHO

def _fetch_who_indicator(code: str, label: str, conn: sqlite3.Connection) -> int:
    url  = f"{WHO_GHO_API}/{code}"
    data = _get_json(url)
    if not data or not isinstance(data, dict):
        return 0

    now, rows = datetime.utcnow().isoformat(), []
    for item in data.get("value", []):
        val = item.get("NumericValue")
        if val is None:
            continue
        rows.append((
            code, label,
            item.get("SpatialDim"),
            item.get("TimeDim"),
            item.get("Dim1") or "BTSX",
            float(val),
            "WHO GHO",
            now,
        ))
    if rows:
        conn.executemany(
            "INSERT INTO who_statistics "
            "(indicator,label,country_code,year,sex,value,source,fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
    return len(rows)


def fetch_all_who(conn, progress, task) -> int:
    total = 0
    for code, label in WHO_INDICATORS.items():
        total += _fetch_who_indicator(code, label, conn)
        progress.advance(task)
    return total


# 2. World Bank

WB_BASE = "https://api.worldbank.org/v2"

WB_INDICATORS = {
    "SH.DYN.NCOM.ZS":    "NCD mortality probability age 30-70, both sexes (%)",
    "SH.DYN.NCOM.FE.ZS": "NCD mortality probability age 30-70, female (%)",
    "SH.DYN.NCOM.MA.ZS": "NCD mortality probability age 30-70, male (%)",
    "SP.DYN.CDRT.IN":    "Death rate, crude (per 1,000 people)",
    "SH.XPD.CHEX.PC.CD": "Current health expenditure per capita (USD)",
}


def _fetch_wb_indicator(code: str, label: str, conn: sqlite3.Connection) -> int:
    now, total, page = datetime.utcnow().isoformat(), 0, 1
    while True:
        url  = (
            f"{WB_BASE}/country/all/indicator/{code}"
            f"?format=json&per_page=1000&page={page}&mrv=30"
        )
        resp = _get_json(url)
        if not resp or not isinstance(resp, list) or len(resp) < 2:
            break

        meta, items = resp[0], resp[1] or []
        rows = []
        for item in items:
            val = item.get("value")
            if val is None:
                continue
            country = item.get("country") or {}
            rows.append((
                code, label,
                item.get("countryiso3code") or country.get("id"),
                country.get("value", ""),
                item.get("date"),
                float(val),
                "World Bank",
                now,
            ))
        if rows:
            conn.executemany(
                "INSERT INTO worldbank_statistics "
                "(indicator,label,country_code,country_name,year,value,source,fetched_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
            conn.commit()
            total += len(rows)

        if page >= int(meta.get("pages", 1)):
            break
        page += 1
        time.sleep(0.15)
    return total


def fetch_all_worldbank(conn, progress, task) -> int:
    total = 0
    for code, label in WB_INDICATORS.items():
        total += _fetch_wb_indicator(code, label, conn)
        progress.advance(task)
    return total


# 3. Wikipedia

def _wikipedia_text(cancer_type: str) -> dict:
    title = cancer_type.replace(" ", "_").title()
    url   = (
        "https://en.wikipedia.org/w/api.php"
        "?action=query&prop=extracts&exintro=false&explaintext=true"
        f"&titles={urllib.parse.quote(title)}&format=json&redirects=1"
    )
    data = _get_json(url, retries=4)
    if not data:
        return {"text": "", "url": "", "title": cancer_type}
    pages = data.get("query", {}).get("pages", {})
    page  = next(iter(pages.values()), {})
    return {
        "text":  page.get("extract", ""),
        "url":   f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
        "title": page.get("title", cancer_type),
    }


def _extract_section(text: str, *keywords) -> str:
    lines, capture, buf = text.split("\n"), False, []
    for line in lines:
        low = line.lower()
        if line.startswith("==") and any(k in low for k in keywords):
            capture = True
            continue
        if capture and line.startswith("=="):
            break
        if capture:
            buf.append(line)
    return "\n".join(buf).strip()[:2000]


def fetch_all_wikipedia(conn, progress, task) -> int:
    now, count = datetime.utcnow().isoformat(), 0
    for cancer in CANCER_TYPES_TO_SCRAPE:
        wiki = _wikipedia_text(cancer)
        text = wiki.get("text", "")
        if text:
            conn.execute(
                "INSERT INTO cancer_profiles "
                "(cancer_type,description,incidence_notes,mortality_notes,"
                " survival_notes,risk_factors,source_url,fetched_at) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (
                    cancer, text[:1500],
                    _extract_section(text, "incidence", "epidemiol"),
                    _extract_section(text, "mortalit", "death"),
                    _extract_section(text, "survival", "prognosis"),
                    _extract_section(text, "risk factor", "cause"),
                    wiki["url"], now,
                ),
            )
            conn.execute(
                "INSERT INTO raw_documents "
                "(title,content,source_url,cancer_type,fetched_at) "
                "VALUES (?,?,?,?,?)",
                (wiki["title"], text[:50000], wiki["url"], cancer, now),
            )
            conn.commit()
            count += 1
        progress.advance(task)
        time.sleep(WIKI_DELAY)
    return count


# Orchestration

def run_data_collection() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)

    conn = sqlite3.connect(SQLITE_DB)
    init_database(conn)
    summary = {}

    console.print("\n[bold cyan]Cancer Data Collector Starting[/bold cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        t1 = progress.add_task(
            "[green]Fetching WHO GHO indicators...",
            total=len(WHO_INDICATORS),
        )
        summary["who_rows"] = fetch_all_who(conn, progress, t1)

        t2 = progress.add_task(
            "[green]Fetching World Bank statistics...",
            total=len(WB_INDICATORS),
        )
        summary["wb_rows"] = fetch_all_worldbank(conn, progress, t2)

        t3 = progress.add_task(
            "[green]Scraping Wikipedia profiles...",
            total=len(CANCER_TYPES_TO_SCRAPE),
        )
        summary["profiles"] = fetch_all_wikipedia(conn, progress, t3)

    conn.close()

    console.print("\n[bold green]Data collection complete![/bold green]")
    console.print(f"  WHO GHO rows:       {summary['who_rows']:,}")
    console.print(f"  World Bank rows:    {summary['wb_rows']:,}")
    console.print(f"  Wikipedia profiles: {summary['profiles']}")
    return summary


if __name__ == "__main__":
    run_data_collection()
