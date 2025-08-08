#!/usr/bin/env python3
"""Tests for PDF number-based matching strategy."""

import re
import pytest


@pytest.mark.parametrize(
    "pdf_name, article_idx, should_match",
    [
        ("12_Graphs where Search Methods are Indistinguishable.pdf", 11, True),
        ("1_Search for Neutral MSSM Higgs Bosons at LEP.pdf", 0, True),
        ("99_Some Article.pdf", 98, True),
        ("67_Construction of Hierarchical Neural Architecture.pdf", 66, True),
        ("no_number_article.pdf", 5, False),
    ],
)
def test_pdf_number_matching(pdf_name: str, article_idx: int, should_match: bool) -> None:
    """Verify that leading numbers in PDF filenames map to article indices.

    For matching cases, the extracted number should equal ``article_idx + 1``.
    Files without a leading number should not match.
    """
    match = re.match(r"^(\d+)_", pdf_name)

    if should_match:
        assert match is not None, "Expected a leading number in the PDF filename"
        pdf_number = int(match.group(1))
        assert pdf_number == article_idx + 1
    else:
        # Files lacking a leading number should not match
        assert match is None
