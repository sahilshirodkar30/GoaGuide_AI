
import pytest

from app.ingestion.chunking.splitter import chunk_text


@pytest.mark.unit
def test_chunk_text_returns_empty_list_for_empty_input():
    assert chunk_text("") == []


@pytest.mark.unit
def test_chunk_text_returns_empty_list_for_whitespace():
    assert chunk_text("   \n\n   ") == []


@pytest.mark.unit
def test_chunk_text_returns_single_chunk_for_short_text():
    text = "North Goa has beautiful beaches."

    result = chunk_text(text)

    assert len(result) == 1
    assert result[0] == text


@pytest.mark.unit
def test_chunk_text_preserves_paragraph_content():
    text = "Baga Beach is popular.\n\nFort Aguada is historic."

    result = chunk_text(text)

    combined = "\n\n".join(result)

    assert "Baga Beach is popular." in combined
    assert "Fort Aguada is historic." in combined


@pytest.mark.unit
def test_chunk_text_splits_long_paragraphs():
    text = "A" * 60 + "\n\n" + "B" * 60

    result = chunk_text(text, chunk_size=100)

    assert len(result) == 2
    assert result[0] == "A" * 60
    assert result[1] == "B" * 60


@pytest.mark.unit
def test_chunk_text_strips_whitespace_from_chunks():
    text = "   North Goa beaches   \n\n   South Goa beaches   "

    result = chunk_text(text)

    assert all(chunk == chunk.strip() for chunk in result)


@pytest.mark.unit
def test_chunk_text_handles_single_oversized_paragraph():
    text = "Goa " * 100

    result = chunk_text(text, chunk_size=20)

    # Documents the current implementation's behavior:
    # an individual oversized paragraph is not subdivided.
    assert len(result) == 1
    assert result[0] == text.strip()


@pytest.mark.unit
def test_chunk_text_rejects_no_valid_content():
    result = chunk_text("\n\n\n")

    assert result == []
