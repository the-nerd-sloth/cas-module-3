"""
setup_check.py: verify prerequisites before running the agent.
"""
import sys
import urllib.request
import json

REQUIRED = [
    ("langchain",               "langchain==1.3.4"),
    ("langchain_core",          "langchain-core==1.4.2"),
    ("langchain_community",     "langchain-community==0.4.2"),
    ("langchain_text_splitters","langchain-text-splitters==1.1.2"),
    ("langchain_ollama",        "langchain-ollama==1.1.0"),
    ("langchain_chroma",        "langchain-chroma==1.1.0"),
    ("chromadb",                "chromadb==1.5.9"),
    ("langgraph",               "langgraph==1.2.4"),
    ("rich",                    "rich==15.0.0"),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    )
}

RECOMMENDED_MODELS = {
    "llm":   ["llama3.1:8b", "qwen2.5:7b-instruct", "qwen3:8b"],
    "embed": ["nomic-embed-text"],
}


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def check_python():
    ok = sys.version_info >= (3, 12)
    v  = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  [{'OK  ' if ok else 'FAIL'}] Python {v}  (need >= 3.12)")
    return ok


def check_packages():
    all_ok = True
    for mod, pkg in REQUIRED:
        try:
            __import__(mod)
            print(f"  [OK  ] {pkg}")
        except ImportError:
            print(f"  [FAIL] {pkg}  <-- pip install {pkg}")
            all_ok = False
    return all_ok


def check_ollama():
    try:
        data   = _get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in data.get("models", [])]
        model_str = ", ".join(models) if models else "none"
        print(f"  [OK  ] Ollama running -- models: {model_str}")

        has_llm = any(
            any(rec in m for rec in RECOMMENDED_MODELS["llm"])
            for m in models
        )
        has_embed = any(
            any(rec in m for rec in RECOMMENDED_MODELS["embed"])
            for m in models
        )

        if not has_llm:
            print("  [WARN] No recommended LLM found.")
            print("         Run:  ollama pull llama3.1:8b")
            print("         Note: llama3.1:8b is required for reliable tool-calling.")
        if not has_embed:
            print("  [WARN] Embedding model missing.")
            print("         Run:  ollama pull nomic-embed-text")
        return True
    except Exception as e:
        print(f"  [FAIL] Ollama not reachable: {e}")
        print("         Install from https://ollama.com  then run: ollama serve")
        return False


def check_who_api():
    try:
        d = _get("https://ghoapi.azureedge.net/api/SA_0000001807", timeout=15)
        n = len(d.get("value", []))
        print(f"  [OK  ] WHO GHO API reachable -- {n} rows for test indicator")
        return True
    except Exception as e:
        print(f"  [FAIL] WHO GHO API: {e}")
        return False


def check_worldbank_api():
    try:
        d = _get(
            "https://api.worldbank.org/v2/country/all/indicator/"
            "SH.DYN.NCOM.ZS?format=json&per_page=1&mrv=1",
            timeout=15,
        )
        print(f"  [OK  ] World Bank API reachable -- {d[0]['total']} total rows")
        return True
    except Exception as e:
        print(f"  [FAIL] World Bank API: {e}")
        return False


def main():
    print()
    print("=== Cancer AI Agent -- Setup Check ===")

    print()
    print("Python:")
    py_ok = check_python()

    print()
    print("Python packages:")
    pkg_ok = check_packages()

    print()
    print("Ollama (LLM server):")
    ol_ok = check_ollama()

    print()
    print("External APIs:")
    who_ok = check_who_api()
    wb_ok  = check_worldbank_api()

    print()
    if all([py_ok, pkg_ok, ol_ok, who_ok, wb_ok]):
        print("All checks passed.")
        print()
        print("Next steps:")
        print("  1.  ollama pull llama3.1:8b        (if not already pulled)")
        print("  2.  ollama pull nomic-embed-text   (if not already pulled)")
        print("  3.  python main.py collect")
        print("  4.  python main.py chat")
    else:
        print("Some checks failed -- fix the issues above before running.")


if __name__ == "__main__":
    main()
