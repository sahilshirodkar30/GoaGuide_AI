import xml.etree.ElementTree as ET
from app.logger import log


def _walk(elem, path: str, lines: list[str]):
    tag = elem.tag.split("}")[-1]  # strip namespace
    current = f"{path}.{tag}" if path else tag

    for attr, val in elem.attrib.items():
        lines.append(f"{current}@{attr}: {val}")

    text = (elem.text or "").strip()
    if text:
        lines.append(f"{current}: {text}")

    for child in elem:
        _walk(child, current, lines)


def parse_xml(file_path: str) -> str:
    """Flattens XML into 'root.child.tag: value' lines."""
    with log.span(f"📄 XML Parsing {file_path}"):
        try:
            root = ET.parse(file_path).getroot()
            lines: list[str] = []
            _walk(root, "", lines)
            text = "\n".join(lines)
            log.info(f"✅ Extracted {len(text)} characters")
            return text
        except Exception as e:
            log.error(f"❌ XML Parse Failed: {e}")
            raise e