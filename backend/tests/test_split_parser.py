import pytest

from app.services.pdf_errors import PdfProcessingError
from app.services.split import parse_ranges


def test_single_pages_and_ranges():
    assert parse_ranges("1-3,5", 10) == [0, 1, 2, 4]


def test_open_ended_range_runs_to_last_page():
    assert parse_ranges("8-", 10) == [7, 8, 9]


def test_whitespace_is_ignored_and_order_is_kept():
    assert parse_ranges(" 5 , 1-2 ", 10) == [4, 0, 1]


def test_duplicates_are_removed_keeping_first_occurrence():
    assert parse_ranges("1-3,2-4", 10) == [0, 1, 2, 3]


def test_single_page_document():
    assert parse_ranges("1", 1) == [0]


@pytest.mark.parametrize(
    "spec",
    ["", "   ", "abc", "0", "0-2", "5-3", "11", "1-11", "1,,2", "1--2", "-3", "1-2-3", "1.5"],
)
def test_invalid_specs_are_rejected(spec):
    with pytest.raises(PdfProcessingError):
        parse_ranges(spec, 10)


def test_error_message_mentions_document_size():
    with pytest.raises(PdfProcessingError, match="10 page"):
        parse_ranges("12", 10)
