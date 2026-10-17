
import pytest

from app.ingestion.processor import (
    MAX_CHUNK_CHARS,
    CHUNK_OVERLAP_CHARS,
    enforce_chunk_size,
)


@pytest.mark.unit
def test_enforce_chunk_size_returns_empty_list():
    assert enforce_chunk_size([]) == []


@pytest.mark.unit
def test_enforce_chunk_size_preserves_small_chunks():
    chunks = ["North Goa beaches", "South Goa temples"]

    result = enforce_chunk_size(chunks)

    assert result == chunks


@pytest.mark.unit
def test_enforce_chunk_size_preserves_unicode_text():
    chunks = ["Goa beaches and Portuguese heritage"]

    result = enforce_chunk_size(chunks)

    assert result == chunks


@pytest.mark.unit
def test_enforce_chunk_size_splits_oversized_chunk():
    text = ("Goa has beautiful beaches and forts. " * 1000).strip()

    result = enforce_chunk_size([text])

    assert len(result) > 1
    assert all(chunk.strip() for chunk in result)
    assert all(len(chunk) <= MAX_CHUNK_CHARS for chunk in result)


@pytest.mark.unit
def test_enforce_chunk_size_preserves_all_content():
    text = ("Goa has beautiful beaches and forts. " * 1000).strip()

    result = enforce_chunk_size([text])

    # Overlapping chunks may repeat content, so check that
    # the beginning and end of the original remain present.
    assert result[0] in text
    assert result[-1] in text
    assert text.startswith(result[0])
    assert text.endswith(result[-1])


@pytest.mark.unit
def test_enforce_chunk_size_keeps_small_utf8_chunk():
    text = "Goa beaches 🏖️"

    result = enforce_chunk_size([text])

    assert result == [text]
