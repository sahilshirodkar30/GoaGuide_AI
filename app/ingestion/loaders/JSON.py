import json
from app.logger import log


def _flatten(obj, prefix: str = "") -> list[str]:
    """Recursively turn nested JSON into 'path.to.key: value' lines."""
    lines: list[str] = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            new_prefix = f"{prefix}.{key}" if prefix else str(key)
            lines.extend(_flatten(value, new_prefix))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            lines.extend(_flatten(item, f"{prefix}[{i}]"))
    else:
        if obj is not None and str(obj).strip():
            lines.append(f"{prefix}: {obj}" if prefix else str(obj))

    return lines


def parse_json(file_path: str) -> str:
    """
    Parses JSON / JSONL files into readable 'key: value' text for RAG.
    Nested structures are flattened so each line keeps its full key path.
    """
    with log.span(f"📄 JSON Parsing {file_path}"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw = f.read()

            try:
                data = json.loads(raw)
                lines = _flatten(data)
            except json.JSONDecodeError:
                # Fallback: JSON Lines (one JSON object per line)
                log.info("Not a single JSON document, trying JSONL.")
                lines = []
                for n, line in enumerate(raw.splitlines(), start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        lines.append(f"--- record {n} ---")
                        lines.extend(_flatten(json.loads(line)))
                    except json.JSONDecodeError:
                        log.warning(f"⚠️ Skipping invalid JSON on line {n}")

            text = "\n".join(lines)

            if not text.strip():
                log.warning(f"⚠️ No content extracted from {file_path}")
            else:
                log.info(f"✅ Extracted {len(text)} characters")

            return text
        except Exception as e:
            log.error(f"❌ JSON Parse Failed: {e}")
            raise e