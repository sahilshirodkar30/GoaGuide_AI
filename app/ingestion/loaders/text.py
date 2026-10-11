from app.logger import log

def parse_text(file_path: str):
    """
    Parses plain text files.
    """
    with log.span(f"📄 Text Parsing {file_path}"):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            log.error(f"❌ Text Parse Failed: {e}")
            raise e
