import csv
import sys
from app.logger import log


def parse_csv(file_path: str) -> str:
    """
    Parses CSV files into row-wise text for RAG.
    Each row becomes: 'col1: value | col2: value | ...' so every chunk
    keeps its column context.
    """
    with log.span(f"📄 CSV Parsing {file_path}"):
        try:
            csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

            # utf-8-sig strips the BOM that Excel adds to CSV exports
            with open(file_path, "r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                sample = f.read(4096)
                f.seek(0)

                # Auto-detect delimiter (comma, semicolon, tab, pipe)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                except csv.Error:
                    dialect = csv.excel

                reader = csv.DictReader(f, dialect=dialect)
                rows: list[str] = []

                for row in reader:
                    parts = [
                        f"{key.strip()}: {value.strip()}"
                        for key, value in row.items()
                        if key and value and value.strip()
                    ]
                    if parts:
                        rows.append(" | ".join(parts))

            text = "\n".join(rows)

            if not text.strip():
                log.warning(f"⚠️ No rows extracted from {file_path}")
            else:
                log.info(f"✅ Parsed {len(rows)} rows, {len(text)} characters")

            return text
        except Exception as e:
            log.error(f"❌ CSV Parse Failed: {e}")
            raise e