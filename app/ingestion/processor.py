import importlib
import json
import os
import sys
import uuid
from collections.abc import Callable
from pinecone import Pinecone, ServerlessSpec
from app.config import settings
from app.ingestion.chunking.splitter import chunk_text
from app.logger import log, setup_logging
from app.services.retrieval.embedding import embed_texts, get_embedding_dim

setup_logging()

# Local folder where parsed + chunked JSON is saved
PROCESSED_DATA_DIR = "processed_data"
UPSERT_BATCH_SIZE = 100

pc = Pinecone(api_key=settings.pinecone_api_key)


# ---------------------------------------------------------------------------
# Loader registry
# extension -> (module path, function name)
#
# Modules are imported lazily on first use, so a missing optional dependency
# (e.g. openpyxl) only affects that file type instead of crashing ingestion.
# Module names match the files in app/ingestion/loaders/ exactly
# (including upper-case names such as CSV.py, JSON.py, XLXS.py, XML.py).
# ---------------------------------------------------------------------------

LOADERS: dict[str, tuple[str, str]] = {
    # PDF
    "pdf": ("app.ingestion.loaders.pdf", "parse_pdf"),

    # HTML
    "html": ("app.ingestion.loaders.html", "parse_html"),
    "htm": ("app.ingestion.loaders.html", "parse_html"),
    "xhtml": ("app.ingestion.loaders.html", "parse_html"),

    # Plain text
    "txt": ("app.ingestion.loaders.text", "parse_text"),

    # Office documents
    "docx": ("app.ingestion.loaders.office", "parse_office"),
    "pptx": ("app.ingestion.loaders.office", "parse_office"),

    # JSON
    "json": ("app.ingestion.loaders.json", "parse_json"),
    "jsonl": ("app.ingestion.loaders.json", "parse_json"),

    # Markdown
    "md": ("app.ingestion.loaders.markdown", "parse_markdown"),
    "markdown": ("app.ingestion.loaders.markdown", "parse_markdown"),

    # CSV / TSV
    "csv": ("app.ingestion.loaders.csv", "parse_csv"),
    "tsv": ("app.ingestion.loaders.csv", "parse_csv"),

    # Excel
    "xlsx": ("app.ingestion.loaders.xlsx", "parse_xlsx"),
    "xlsm": ("app.ingestion.loaders.xlsx", "parse_xlsx"),

    # XML
    "xml": ("app.ingestion.loaders.xml", "parse_xml"),
}



def get_loader(ext: str) -> Callable[[str], str] | None:
    """Return the parser function for an extension, or None if unsupported."""
    entry = LOADERS.get(ext)
    if entry is None:
        return None
    module_path, func_name = entry
    module = importlib.import_module(module_path)  # raises ImportError if dep missing
    return getattr(module, func_name)


def save_processed_locally(data: dict, source_type: str, filename: str) -> str:
    """Save parsed chunk metadata as JSON in processed_data/<source_type>/."""
    folder = os.path.join(PROCESSED_DATA_DIR, source_type)
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, f"{filename}.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return dest


def ensure_index(wipe: bool = False):
    """Create the Pinecone index if needed (optionally deleting it first) and return it."""
    name = settings.pinecone_index_name

    if wipe and pc.has_index(name):
        with log.span("Wiping Index"):
            pc.delete_index(name)
            log.info("Index '{name}' deleted.", name=name)

    if not pc.has_index(name):
        dim = get_embedding_dim()  # resolved at runtime from the embedding model
        pc.create_index(
            name=name,
            dimension=dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=settings.pinecone_region),
        )
        log.info("Created index '{name}' ({dim}-dim, cosine).", name=name, dim=dim)

    return pc.Index(name)


def upsert_in_batches(index, vectors: list[dict]) -> None:
    for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
        index.upsert(vectors=vectors[i : i + UPSERT_BATCH_SIZE])

MAX_CHUNK_CHARS = 6000
CHUNK_OVERLAP_CHARS = 200


def enforce_chunk_size(chunks: list[str]) -> list[str]:
    """Split oversized chunks before embedding and Pinecone indexing."""
    safe_chunks = []

    for chunk in chunks:
        if len(chunk.encode("utf-8")) <= 30 * 1024:
            safe_chunks.append(chunk)
            continue

        start = 0

        while start < len(chunk):
            end = min(start + MAX_CHUNK_CHARS, len(chunk))

            # Prefer breaking at a word boundary.
            if end < len(chunk):
                boundary = chunk.rfind(" ", start, end)
                if boundary > start:
                    end = boundary

            piece = chunk[start:end].strip()

            if piece:
                # Verify the actual UTF-8 metadata size.
                if len(piece.encode("utf-8")) > 30 * 1024:
                    raise ValueError("Chunk exceeds the safe metadata limit.")

                safe_chunks.append(piece)

            if end >= len(chunk):
                break

            start = max(end - CHUNK_OVERLAP_CHARS, start + 1)

    return safe_chunks
def process_file(index, file_path: str, filename: str, source_type: str):
    """Parse → chunk → save locally → embed → index in Pinecone."""
    with log.span("Processing File", file=filename, source=source_type):
        try:
            # 1. Extract text based on file extension
            ext = os.path.splitext(filename)[1].lstrip(".").lower()
            loader = get_loader(ext)
            if loader is None:
                log.warn("Skipping unsupported file type: {file}", file=filename)
                return

            full_text = loader(file_path)

            if not full_text or not full_text.strip():
                log.warn("No text extracted from {file}, skipping.", file=filename)
                return

            # 2. Chunk text
            # 2. Chunk text and enforce Pinecone metadata limits
            chunks = chunk_text(full_text)

            if not chunks:
                log.warn("No chunks generated for {file}.", file=filename)
                return

            original_count = len(chunks)
            chunks = enforce_chunk_size(chunks)

            log.info(
                "Chunked {file}: {original} original chunks → {final} safe chunks.",
                file=filename,
                original=original_count,
                final=len(chunks),
                )

            # 3. Save processed data locally
            processed_data = {
                "filename": filename,
                "source_type": source_type,
                "chunks": chunks,
            }
            local_path = save_processed_locally(processed_data, source_type, filename)
            log.info("Saved processed data → {path}", path=local_path)

            # 4. Embed and index in Pinecone
            with log.span("Vectorizing & Indexing"):
                embeddings = embed_texts(chunks)
                vectors = [
                    {
                        # same file + chunk number always gives the same ID,
                        # so re-running ingestion overwrites instead of duplicating
                        "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_type}/{filename}/{i}")),
                        "values": vector,
                        "metadata": {
                            "text": chunk,
                            "source": filename,
                            "source_type": source_type,
                        },
                    }
                    for i, (chunk, vector) in enumerate(zip(chunks, embeddings))
                ]
                upsert_in_batches(index, vectors)
                log.info(
                    "Indexed {n} vectors to Pinecone from {file}.",
                    n=len(vectors),
                    file=filename,
                )

        except Exception:
            # Also catches ImportError from a missing loader dependency,
            # so one bad file type never stops the rest of the run.
            log.exception("Failed to process {file}", file=filename)


def process_directory(index, dir_path: str, source_type: str):
    """Process every file in a directory."""
    with log.span("Scanning Directory", path=dir_path, source=source_type):
        files = [
            f for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))
        ]
        log.info("Found {n} files in {path}.", n=len(files), path=dir_path)
        for filename in files:
            process_file(index, os.path.join(dir_path, filename), filename, source_type)


def run_universal_ingestion(
    base_dir: str, explicit_source_type: str = None, wipe: bool = False
):
    """
    Scan base_dir, map sub-folders to source types, and ingest all documents.
    Pass --wipe to delete and recreate the Pinecone index before ingestion.
    """
    with log.span("Universal Ingestion Started", base_directory=base_dir):
        index = ensure_index(wipe=wipe)
        log.info(
            "Processing directory '{path}' as '{source}'.",
            path=base_dir,
            source=explicit_source_type,
        )
        process_directory(index, base_dir, explicit_source_type)
        

if __name__ == "__main__":
    wipe_requested = "--wipe" in sys.argv
    clean_args = [a for a in sys.argv if a != "--wipe"]

    target_dir = clean_args[1] if len(clean_args) > 1 else "app/data"
    explicit_type = clean_args[2] if len(clean_args) > 2 else "general"

    if not os.path.isdir(target_dir):
        print(f"Error: directory '{target_dir}' does not exist.")
        sys.exit(1)

    run_universal_ingestion(
        target_dir,
        explicit_source_type=explicit_type,
        wipe=wipe_requested,
    )

    log.info("Ingestion job completed.")