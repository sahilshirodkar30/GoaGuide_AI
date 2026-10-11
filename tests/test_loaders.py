import sys
from pathlib import Path

from app.ingestion.loaders.html import parse_html
from app.ingestion.loaders.office import parse_office
from app.ingestion.loaders.pdf import parse_pdf
from app.ingestion.loaders.text import parse_text
from app.ingestion.loaders.JSON import parse_json
from app.ingestion.loaders.CSV import parse_csv
from app.ingestion.loaders.markdown import parse_markdown

DATA_DIR = Path("app/data")

# file extension -> loader function (same routing as processor.py)
LOADERS = {
    "txt": parse_text,
    "html": parse_html,
    "htm": parse_html,
    "pdf": parse_pdf,
    "docx": parse_office,
    "pptx": parse_office,
    "csv":parse_csv,
    "json":parse_json,
    "md":parse_markdown

}


def find_files(folder: Path) -> list[Path]:
    """All supported files under folder, including sub-folders."""
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lstrip(".").lower() in LOADERS
    )


def test_one(path: Path) -> bool:
    loader = LOADERS[path.suffix.lstrip(".").lower()]
    label = str(path.relative_to(DATA_DIR)) if path.is_relative_to(DATA_DIR) else path.name

    try:
        text = loader(str(path))
    except Exception as e:
        print(f"FAIL  {label}: {type(e).__name__}: {e}")
        return False

    if not isinstance(text, str):
        print(f"FAIL  {label}: loader returned {type(text).__name__}, expected str")
        return False
    if not text.strip():
        print(f"FAIL  {label}: no text extracted")
        return False

    preview = text.strip()[:120].replace("\n", " ")
    print(f"OK    {label}: {len(text)} chars | {preview}")
    return True


def main() -> int:
    if len(sys.argv) > 1:
        paths = [Path(p) for p in sys.argv[1:]]   # specific files
    else:
        if not DATA_DIR.exists():
            print(f"Error: '{DATA_DIR}' does not exist.")
            return 1
        paths = find_files(DATA_DIR)              # everything under app/data

    if not paths:
        print(f"No supported files found (looking for: {', '.join(LOADERS)}).")
        return 1

    results = [test_one(p) for p in paths]
    passed = sum(results)
    print(f"\n{passed}/{len(results)} passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())