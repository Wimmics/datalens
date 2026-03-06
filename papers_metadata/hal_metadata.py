"""Utilities to retrieve HAL paper metadata from a DOI."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import urlopen
import json
import re

HAL_API_URL = "https://api.archives-ouvertes.fr/search/"
HAL_FIELDS = (
    "docid,title_s,authFullName_s,abstract_s,publicationDateY_i,"
    "producedDate_tdate,uri_s,journalTitle_s,doiId_s,halId_s,docType_s,arxivId_s"
)


def fetch_hal_metadata_by_doi(doi: str, timeout: int = 15) -> dict[str, Any]:
    """Return metadata for a HAL paper identified by DOI.

    Args:
        doi: DOI of the paper.
        timeout: Timeout in seconds for the HTTP request.

    Returns:
        A dictionary with the paper metadata.

    Raises:
        ValueError: If DOI is empty or no HAL record was found.
        RuntimeError: If HAL API cannot be reached.
    """
    normalized_doi = doi.strip()
    normalized_doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", normalized_doi, flags=re.IGNORECASE)
    if not normalized_doi:
        raise ValueError("DOI cannot be empty.")

    queries = [f'doiId_s:"{normalized_doi}"']

    # HAL indexes DOI values inconsistently in some records (case and URL form).
    lowered = normalized_doi.lower()
    if lowered != normalized_doi:
        queries.append(f'doiId_s:"{lowered}"')

    match = re.match(r"^10\.48550/arxiv\.(?P<id>[^\s]+)$", normalized_doi, flags=re.IGNORECASE)
    arxiv_id = match.group("id") if match else None
    if arxiv_id:
        queries.append(f'arxivId_s:"{arxiv_id}"')

    docs: list[dict[str, Any]] = []
    for hal_query in queries:
        encoded_query = quote_plus(hal_query)
        url = f"{HAL_API_URL}?q={encoded_query}&rows=1&wt=json&fl={HAL_FIELDS}"

        try:
            with urlopen(url, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Failed to query HAL API: {exc}") from exc

        docs = payload.get("response", {}).get("docs", [])
        if docs:
            break

    if not docs:
        raise ValueError(f"No HAL paper found for DOI: {normalized_doi}")

    return _doc_to_metadata(docs[0])


def _doc_to_metadata(doc: dict[str, Any]) -> dict[str, Any]:
    title_list = doc.get("title_s", [])
    title = title_list[0] if title_list else ""

    abstract_list = doc.get("abstract_s", [])
    abstract = abstract_list[0] if abstract_list else ""

    return {
        "hal_id": doc.get("halId_s", ""),
        "docid": doc.get("docid", ""),
        "doi": doc.get("doiId_s", ""),
        "arxiv_id": doc.get("arxivId_s", ""),
        "title": title,
        "authors": doc.get("authFullName_s", []),
        "abstract": abstract,
        "doc_type": doc.get("docType_s", ""),
        "journal": doc.get("journalTitle_s", ""),
        "publication_year": doc.get("publicationDateY_i", None),
        "produced_date": doc.get("producedDate_tdate", ""),
        "uri": doc.get("uri_s", ""),
    }


if __name__ == "__main__":
    sample_doi = "hal-01161054"
    try:
        print(fetch_hal_metadata_by_doi(sample_doi))
    except ValueError as exc:
        print(f"HAL lookup: {exc}")
