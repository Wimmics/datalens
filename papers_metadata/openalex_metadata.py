"""Utilities to retrieve OpenAlex paper metadata from a DOI."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen
import json

OPENALEX_API_URL = "https://api.openalex.org/works"


def fetch_openalex_metadata_by_doi(doi: str, timeout: int = 15) -> dict[str, Any]:
    """Return metadata for a paper indexed by OpenAlex using a DOI.

    Args:
        doi: DOI of the paper.
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        A dictionary with the paper metadata.

    Raises:
        ValueError: If DOI is empty or no work was found.
        RuntimeError: If OpenAlex API cannot be reached.
    """
    normalized_doi = doi.strip().lower()
    if not normalized_doi:
        raise ValueError("DOI cannot be empty.")

    filter_value = quote(f"doi:https://doi.org/{normalized_doi}", safe=":/")
    url = f"{OPENALEX_API_URL}?filter={filter_value}&per-page=1"

    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Failed to query OpenAlex API: {exc}") from exc

    results = payload.get("results", [])
    if not results:
        raise ValueError(f"No OpenAlex work found for DOI: {normalized_doi}")

    return _work_to_metadata(results[0])


def _work_to_metadata(work: dict[str, Any]) -> dict[str, Any]:
    authorships = work.get("authorships", [])
    authors = [
        auth.get("author", {}).get("display_name", "")
        for auth in authorships
        if auth.get("author", {}).get("display_name")
    ]

    concepts = work.get("concepts", [])
    concept_names = [c.get("display_name", "") for c in concepts if c.get("display_name")]

    primary_location = work.get("primary_location", {})
    source = primary_location.get("source", {})
    ids = work.get("ids", {})

    return {
        "openalex_id": work.get("id", ""),
        "doi": (ids.get("doi", "") or "").replace("https://doi.org/", ""),
        "title": work.get("title", ""),
        "publication_year": work.get("publication_year", None),
        "publication_date": work.get("publication_date", ""),
        "type": work.get("type", ""),
        "cited_by_count": work.get("cited_by_count", 0),
        "authors": authors,
        "concepts": concept_names,
        "abstract_inverted_index": work.get("abstract_inverted_index", {}),
        "open_access": work.get("open_access", {}),
        "host_venue": source.get("display_name", ""),
        "landing_page_url": primary_location.get("landing_page_url", ""),
        "pdf_url": primary_location.get("pdf_url", ""),
    }


if __name__ == "__main__":
    sample_doi = "10.48550/arXiv.1706.03762"
    print(fetch_openalex_metadata_by_doi(sample_doi))
