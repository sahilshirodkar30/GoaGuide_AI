from app.logger import log
from unstructured.partition.auto import partition

def parse_office(file_path: str):
    """
    Parses Office documents (.docx, .pptx) using the Unstructured library.
    Unlike PDFs, these formats are structured and lightweight, so they are processed locally.
    """
    with log.span(f"📄 Office Document Parsing {file_path}"):
        try:
            # Unstructured automatically detects if it's docx or pptx
            elements = partition(filename=file_path)
            full_text = "\n".join([str(el) for el in elements])
            
            if not full_text.strip():
                log.warning(f"⚠️ Unstructured returned empty text for {file_path}")
            else:
                log.info(f"✅ Successfully parsed {len(full_text)} characters")

            return full_text
        except Exception as e:
            log.exception(f"❌ Office Parse Failed: {e}")
            raise e
