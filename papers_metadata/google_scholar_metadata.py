"""Utilities to retrieve Google Scholar paper metadata from a DOI.

Google Scholar does not provide an official public API for this use case.
This module uses the public lookup page and parses citation meta tags.
"""

from __future__ import annotations

from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

GOOGLE_SCHOLAR_LOOKUP_URL = "https://scholar.google.com/scholar_lookup"


class _CitationMetaParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, list[str]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "meta":
            return

        attrs_dict = {k.lower(): v for k, v in attrs if v is not None}
        name = attrs_dict.get("name", "")
        content = attrs_dict.get("content", "")

        if name.startswith("citation_") and content:
            self.meta.setdefault(name, []).append(content)


def fetch_google_scholar_metadata_by_doi(doi: str, timeout: int = 15) -> dict[str, Any]:
    """Return metadata from Google Scholar lookup page for a DOI.

    Args:
        doi: DOI of the paper.
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        A dictionary with extracted citation metadata.

    Raises:
        ValueError: If DOI is empty or no Scholar metadata was found.
        RuntimeError: If Google Scholar cannot be reached.
    """
    normalized_doi = doi.strip()
    if not normalized_doi:
        raise ValueError("DOI cannot be empty.")

    url = f"{GOOGLE_SCHOLAR_LOOKUP_URL}?doi={quote_plus(normalized_doi)}"
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        },
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to query Google Scholar: {exc}") from exc

    parser = _CitationMetaParser()
    parser.feed(html)

    if "citation_title" not in parser.meta:
        raise ValueError(
            "No Google Scholar metadata found for DOI. "
            "The page may be blocked by rate limits or anti-bot checks."
        )

    meta = parser.meta

    def first(key: str) -> str:
        values = meta.get(key, [])
        return values[0] if values else ""

    return {
        "doi": normalized_doi,
        "title": first("citation_title"),
        "authors": meta.get("citation_author", []),
        "journal": first("citation_journal_title"),
        "conference": first("citation_conference_title"),
        "publication_date": first("citation_publication_date"),
        "volume": first("citation_volume"),
        "issue": first("citation_issue"),
        "firstpage": first("citation_firstpage"),
        "lastpage": first("citation_lastpage"),
        "publisher": first("citation_publisher"),
        "language": first("citation_language"),
        "abstract_url": first("citation_abstract_html_url"),
        "pdf_url": first("citation_pdf_url"),
        "source_url": first("citation_public_url"),
    }


if __name__ == "__main__":
    sample_doi = "10.48550/arXiv.1706.03762"
    try:
        print(fetch_google_scholar_metadata_by_doi(sample_doi))
    except ValueError as exc:
        print(f"Google Scholar lookup: {exc}")
