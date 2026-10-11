import time

from pinecone import Pinecone

from app.config import settings
from app.logger import log

BATCH_SIZE = 96   # Pinecone inference limit per embed request
MAX_RETRIES = 4

_pc: Pinecone | None = None


# ── Client initialisation ──────────────────────────────────────────────────────

def _get_client() -> Pinecone:
    """Create the Pinecone client once per process, on first use."""
    global _pc
    if _pc is None:
        _pc = Pinecone(api_key=settings.pinecone_api_key)
        log.info("Pinecone embeddings ready ({model}, {dim}-dim).",
                 model=settings.embedding_model, dim=settings.embedding_dim)
    return _pc


# ── Public helpers ─────────────────────────────────────────────────────────────

def get_embedding_dim() -> int:
    """Vector dimension used when creating the Pinecone index."""
    return settings.embedding_dim


# ── Batch embedding with retry ─────────────────────────────────────────────────

def _embed_batch(batch: list[str], input_type: str) -> list[list[float]]:
    pc = _get_client()

    # Exponential backoff: 1 s → 2 s → 4 s (4 attempts total)
    for attempt in range(MAX_RETRIES):
        try:
            res = pc.inference.embed(
                model=settings.embedding_model,
                inputs=batch,
                parameters={"input_type": input_type, "truncate": "END"},
            )
            return [item["values"] for item in res]
        except Exception as e:
            err = str(e).lower()
            is_rate_limit = any(x in err for x in ("429", "rate", "quota", "too many"))
            if is_rate_limit and attempt < MAX_RETRIES - 1:
                wait = 2 ** attempt
                log.warn(
                    "Pinecone rate limit hit, retrying in {wait}s (attempt {n}/{total}).",
                    wait=wait, n=attempt + 1, total=MAX_RETRIES,
                )
                time.sleep(wait)
            else:
                log.exception("Pinecone embedding failed")
                raise

    raise RuntimeError(f"Pinecone rate limit persisted after {MAX_RETRIES} attempts.")


def _check_dim(vectors: list[list[float]]) -> None:
    # Catch a model/index mismatch early instead of failing at upsert time
    if vectors and len(vectors[0]) != settings.embedding_dim:
        raise ValueError(
            f"Embedding model returned {len(vectors[0])}-dim vectors but "
            f"settings.embedding_dim is {settings.embedding_dim}. "
            f"Fix embedding_dim in config to match '{settings.embedding_model}'."
        )


# ── Public API ─────────────────────────────────────────────────────────────────

def embed_query(query: str) -> list[float]:
    """Embed a single search query."""
    vectors = _embed_batch([query], input_type="query")
    _check_dim(vectors)
    return vectors[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed documents/chunks for indexing."""
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        with log.span("Embed batch", model=settings.embedding_model, start=i, size=len(batch)):
            all_embeddings.extend(_embed_batch(batch, input_type="passage"))
    _check_dim(all_embeddings)
    return all_embeddings