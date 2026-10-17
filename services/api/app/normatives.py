from pathlib import Path


def _val(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1]
    return s


def load_catalog(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    types: dict[str, dict] = {}
    current: dict | None = None
    in_source = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip(" "))
        if stripped == "types:":
            current = None
            in_source = False
            continue
        if stripped.startswith("- id:"):
            current = {"id": _val(stripped[5:]), "source": {}}
            types[current["id"]] = current
            in_source = False
            continue
        if current is None:
            continue
        if stripped == "source:":
            in_source = True
            continue
        if in_source and indent >= 6:
            k, _, v = stripped.partition(":")
            current["source"][k.strip()] = _val(v)
            continue
        in_source = False
        k, _, v = stripped.partition(":")
        key = k.strip()
        if key == "verified":
            current["verified"] = _val(v).lower() == "true"
    return {t: d for t, d in types.items() if d.get("verified")}


def enrich(violations: list[dict], catalog: dict[str, dict]) -> None:
    for v in violations:
        if v.get("normative"):
            continue
        entry = catalog.get(v.get("type", ""))
        if entry is None:
            continue
        src = entry.get("source", {})
        if src.get("document") or src.get("clause") or src.get("url"):
            v["normative"] = {
                "document": src.get("document") or "",
                "clause": src.get("clause") or "",
                "url": src.get("url") or "",
            }
