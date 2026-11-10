"""
tools.py: LangChain tools for the Cancer AI Agent
"""
import sqlite3
from typing import Optional
from langchain_core.tools import tool
from config import SQLITE_DB


def _conn():
    return sqlite3.connect(SQLITE_DB)


@tool
def query_cancer_profiles(cancer_type: str) -> str:
    """
    Return the stored profile for a cancer type: overview, incidence,
    mortality, survival/prognosis, and risk factors (sourced from Wikipedia).

    Args:
        cancer_type: e.g. 'lung cancer', 'breast cancer', 'leukemia'
    """
    conn = _conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT cancer_type, description, incidence_notes,
               mortality_notes, survival_notes, risk_factors, source_url
        FROM   cancer_profiles
        WHERE  LOWER(cancer_type) LIKE ?
        LIMIT 3
    """, (f"%{cancer_type.lower()}%",))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return f"No profile found for '{cancer_type}'."
    out = []
    for r in rows:
        out.append(
            f"=== {r[0].title()} ===\n"
            f"Overview:\n{r[1][:600]}\n\n"
            f"Incidence/Epidemiology:\n{r[2][:500] or 'N/A'}\n\n"
            f"Mortality:\n{r[3][:500] or 'N/A'}\n\n"
            f"Survival/Prognosis:\n{r[4][:500] or 'N/A'}\n\n"
            f"Risk Factors:\n{r[5][:400] or 'N/A'}\n\n"
            f"Source: {r[6]}"
        )
    return "\n\n---\n\n".join(out)


@tool
def query_who_statistics(
    indicator: Optional[str] = None,
    country_code: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    sex: Optional[str] = None,
) -> str:
    """
    Query WHO GHO cancer death rates and NCD mortality by country/year/sex.

    Indicators (partial match on code or label keyword):
      SA_0000001807  all cancers age-standardised death rate
      SA_0000001438  breast cancer death rate
      SA_0000001439  cervical cancer death rate
      SA_0000001445  colorectal cancer death rate
      SA_0000001448  lung cancer death rate
      SA_0000001449  liver cancer death rate
      SA_0000001426  prostate cancer death rate
      SA_0000001419  cancer incidence, female
      SA_0000001420  cancer incidence, male
      NCDMORT3070    probability dying age 30-70 from cancer/NCD
      NCD_DTH_TOT    total NCD deaths

    Args:
        indicator:    partial code or label keyword (e.g. 'breast', 'lung')
        country_code: ISO 3-letter code e.g. 'USA', 'DEU', 'JPN'
        year_from:    start year
        year_to:      end year
        sex:          'SEX_MLE' | 'SEX_FMLE' | 'SEX_BTSX'
    """
    conn = _conn()
    cur  = conn.cursor()
    wheres, params = [], []
    if indicator:
        wheres.append("(indicator LIKE ? OR LOWER(label) LIKE ?)")
        params += [f"%{indicator}%", f"%{indicator.lower()}%"]
    if country_code:
        wheres.append("UPPER(country_code) = ?")
        params.append(country_code.upper())
    if year_from:
        wheres.append("CAST(year AS INTEGER) >= ?")
        params.append(year_from)
    if year_to:
        wheres.append("CAST(year AS INTEGER) <= ?")
        params.append(year_to)
    if sex:
        wheres.append("UPPER(sex) LIKE ?")
        params.append(f"%{sex.upper()}%")
    where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    cur.execute(f"""
        SELECT indicator, label, country_code, year, sex, value, source
        FROM   who_statistics
        {where}
        ORDER BY year DESC, country_code
        LIMIT 80
    """, params)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "No WHO statistics found. Try list_available_countries first."
    lines = ["indicator | label | country | year | sex | value | source", "-" * 80]
    for r in rows:
        lines.append(" | ".join(str(x) for x in r))
    return "\n".join(lines)


@tool
def query_worldbank_statistics(
    country_code: Optional[str] = None,
    country_name: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    indicator: Optional[str] = None,
) -> str:
    """
    Query World Bank NCD/cancer mortality data, with male/female split.

    Indicators:
      SH.DYN.NCOM.ZS    NCD/cancer mortality age 30-70, both sexes (%)
      SH.DYN.NCOM.FE.ZS NCD/cancer mortality age 30-70, female (%)
      SH.DYN.NCOM.MA.ZS NCD/cancer mortality age 30-70, male (%)
      SP.DYN.CDRT.IN    Crude death rate per 1,000
      SH.XPD.CHEX.PC.CD Health expenditure per capita (USD)

    Args:
        country_code: ISO 3-letter code e.g. 'USA', 'DEU', 'JPN', 'GBR'
        country_name: partial name e.g. 'Germany', 'United States'
        year_from:    start year
        year_to:      end year
        indicator:    keyword e.g. 'female', 'male', 'NCOM'
    """
    conn = _conn()
    cur  = conn.cursor()
    wheres, params = [], []
    if indicator:
        wheres.append("(indicator LIKE ? OR LOWER(label) LIKE ?)")
        params += [f"%{indicator}%", f"%{indicator.lower()}%"]
    if country_code:
        wheres.append("UPPER(country_code) = ?")
        params.append(country_code.upper())
    if country_name:
        wheres.append("LOWER(country_name) LIKE ?")
        params.append(f"%{country_name.lower()}%")
    if year_from:
        wheres.append("CAST(year AS INTEGER) >= ?")
        params.append(year_from)
    if year_to:
        wheres.append("CAST(year AS INTEGER) <= ?")
        params.append(year_to)
    where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
    cur.execute(f"""
        SELECT indicator, label, country_code, country_name, year, value, source
        FROM   worldbank_statistics
        {where}
        ORDER BY year DESC, country_name
        LIMIT 80
    """, params)
    rows = cur.fetchall()
    conn.close()
    if not rows:
        return "No World Bank statistics found for those filters."
    lines = ["indicator | label | code | country | year | value | source", "-" * 90]
    for r in rows:
        lines.append(" | ".join(str(x) for x in r))
    return "\n".join(lines)


@tool
def list_available_cancer_types() -> str:
    """List all cancer types stored in the database."""
    conn = _conn()
    cur  = conn.cursor()
    cur.execute("SELECT DISTINCT cancer_type FROM cancer_profiles ORDER BY cancer_type")
    profiles = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT cancer_type FROM cancer_statistics ORDER BY cancer_type")
    stats = [r[0] for r in cur.fetchall()]
    conn.close()
    return (
        "Wikipedia profiles:\n  " + "\n  ".join(profiles or ["none"]) +
        "\n\nAdditional stats:\n  " + "\n  ".join(stats or ["none"])
    )


@tool
def list_available_countries() -> str:
    """List countries available in the WHO and World Bank tables."""
    conn = _conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT country_code, COUNT(*) n FROM who_statistics
        WHERE country_code IS NOT NULL
        GROUP BY country_code ORDER BY n DESC LIMIT 40
    """)
    who = cur.fetchall()
    cur.execute("""
        SELECT country_code, country_name, COUNT(*) n
        FROM worldbank_statistics
        WHERE country_code IS NOT NULL AND LENGTH(country_code) = 3
        GROUP BY country_code ORDER BY country_name LIMIT 60
    """)
    wb = cur.fetchall()
    conn.close()
    out  = "WHO GHO countries (top 40):\n"
    out += "  " + ", ".join(f"{r[0]}({r[1]})" for r in who)
    out += "\n\nWorld Bank countries:\n"
    out += "\n".join(f"  {r[0]}  {r[1]}  ({r[2]} rows)" for r in wb)
    return out


@tool
def semantic_search(query: str, n_results: int = 5) -> str:
    """
    Search the cancer knowledge base by meaning.
    Required for open-ended questions about biology, treatment, risk factors, prognosis.

    Args:
        query:     natural language e.g. 'What causes lung cancer?'
        n_results: results to return (default 5, max 10)
    """
    try:
        from vector_store import get_vector_store
        vstore = get_vector_store()
        docs   = vstore.similarity_search(query, k=min(n_results, 10))
        if not docs:
            return "No semantic results found."
        parts = []
        for i, d in enumerate(docs, 1):
            meta = d.metadata
            parts.append(
                f"[{i}] {meta.get('title', '?')} "
                f"| cancer: {meta.get('cancer_type', '?')}\n"
                f"{d.page_content[:600]}"
            )
        return "\n\n---\n\n".join(parts)
    except Exception as e:
        return f"Semantic search unavailable: {e}"


@tool
def run_custom_sql(sql_query: str) -> str:
    """
    Execute a read-only SQL SELECT against the local cancer database.

    Tables:
      who_statistics       — indicator, country_code, year, sex, value
      worldbank_statistics — indicator, country_code, country_name, year, value
      cancer_profiles      — cancer_type, description, mortality_notes, ...
      cancer_statistics    — supplemental stats
      raw_documents        — full-text Wikipedia articles

    Args:
        sql_query: a valid SQLite SELECT statement
    """
    if not sql_query.strip().upper().startswith("SELECT"):
        return "Error: only SELECT queries are permitted."
    try:
        conn = _conn()
        cur  = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchmany(100)
        cols = [d[0] for d in (cur.description or [])]
        conn.close()
        if not rows:
            return "Query returned no rows."
        lines = [" | ".join(cols), "-" * 60]
        for r in rows:
            lines.append(" | ".join(str(x) for x in r))
        return "\n".join(lines)
    except Exception as e:
        return f"SQL error: {e}"


ALL_TOOLS = [
    query_cancer_profiles,
    query_who_statistics,
    query_worldbank_statistics,
    list_available_cancer_types,
    list_available_countries,
    semantic_search,
    run_custom_sql,
]
