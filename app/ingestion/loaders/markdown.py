import re
from app.logger import log


def parse_markdown(file_path: str) -> str:
    """
    Parses Markdown files.
    Keeps headings/structure (useful for chunking), removes YAML front matter
    and HTML comments, and collapses extra blank lines.
    """
    with log.span(f"📄 Markdown Parsing {file_path}"):
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # 1. Remove YAML front matter (--- ... --- at top of file)
            content = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

            # 2. Remove HTML comments
            content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)

            # 3. Collapse 3+ newlines into 2 and strip trailing spaces
            content = re.sub(r"[ \t]+\n", "\n", content)
            content = re.sub(r"\n{3,}", "\n\n", content).strip()

            if not content:
                log.warning(f"⚠️ Markdown file is empty: {file_path}")
            else:
                log.info(f"✅ Extracted {len(content)} characters")

            return content
        except Exception as e:
            log.error(f"❌ Markdown Parse Failed: {e}")
            raise e