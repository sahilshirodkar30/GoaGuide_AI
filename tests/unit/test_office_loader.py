
from unittest.mock import patch

import pytest

from app.ingestion.loaders.office import parse_office


@pytest.mark.unit
@patch("app.ingestion.loaders.office.partition")
def test_parse_office_returns_extracted_text(mock_partition):
    mock_partition.return_value = [
        "Goa is a popular tourist destination.",
        "Fort Aguada is a historic landmark.",
    ]

    result = parse_office("sample.docx")

    assert result == (
        "Goa is a popular tourist destination.\n"
        "Fort Aguada is a historic landmark."
    )
    mock_partition.assert_called_once_with(filename="sample.docx")


@pytest.mark.unit
@patch("app.ingestion.loaders.office.partition")
def test_parse_office_returns_empty_string_for_no_elements(
    mock_partition,
):
    mock_partition.return_value = []

    result = parse_office("empty.docx")

    assert result == ""
    mock_partition.assert_called_once_with(filename="empty.docx")



@pytest.mark.unit
@patch("app.ingestion.loaders.office.partition")
def test_parse_office_handles_empty_text(mock_partition):
    mock_partition.return_value = ["", "   "]

    result = parse_office("blank.docx")

    assert result == "\n   "
    assert result.strip() == ""
    mock_partition.assert_called_once_with(filename="blank.docx")



@pytest.mark.unit
@patch("app.ingestion.loaders.office.partition")
def test_parse_office_reraises_partition_error(mock_partition):
    mock_partition.side_effect = RuntimeError("Document parsing failed")

    with pytest.raises(RuntimeError, match="Document parsing failed"):
        parse_office("broken.docx")


@pytest.mark.unit
@patch("app.ingestion.loaders.office.partition")
def test_parse_office_supports_pptx_path(mock_partition):
    mock_partition.return_value = ["Goa travel presentation"]

    result = parse_office("travel.pptx")

    assert result == "Goa travel presentation"
    mock_partition.assert_called_once_with(filename="travel.pptx")
