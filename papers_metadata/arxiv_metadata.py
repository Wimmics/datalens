"""Utilities to retrieve arXiv paper metadata from a DOI."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import re
import xml.etree.ElementTree as ET

ARXIV_API_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def fetch_arxiv_metadata_by_doi(doi: str, timeout: int = 15) -> dict[str, Any]:
    """Return metadata for an arXiv paper identified by DOI.

    The function supports:
    - arXiv DOI format: ``10.48550/arXiv.<arxiv_id>``
    - generic DOI values indexed in arXiv metadata

    Args:
        doi: DOI of the paper.
        timeout: Timeout in seconds for the HTTP requests.

    Returns:
        A dictionary with the paper metadata.

    Raises:
        ValueError: If DOI is empty or no arXiv paper was found.
        RuntimeError: If arXiv API cannot be reached.
    """
    normalized_doi = doi.strip()
    if not normalized_doi:
        raise ValueError("DOI cannot be empty.")

    match = re.match(r"^10\.48550/arxiv\.(?P<id>[^\s]+)$", normalized_doi, flags=re.IGNORECASE)
    arxiv_id = match.group("id") if match else None
    queries: list[dict[str, str]] = []

    if arxiv_id:
        queries.append({"id_list": arxiv_id})

    queries.append({"search_query": f"doi:{normalized_doi}", "max_results": "1"})

    entry = None
    for params in queries:
        url = f"{ARXIV_API_URL}?{urlencode(params)}"

        try:
            with urlopen(url, timeout=timeout) as response:
                data = response.read()
        except (HTTPError, URLError) as exc:
            raise RuntimeError(f"Failed to query arXiv API: {exc}") from exc

        root = ET.fromstring(data)
        entry = root.find(f"{ATOM_NS}entry")
        if entry is not None:
            break

    if entry is None:
        raise ValueError(f"No arXiv paper found for DOI: {normalized_doi}")

    return _entry_to_metadata(entry)


def _entry_to_metadata(entry: ET.Element) -> dict[str, Any]:
    def text(path: str) -> str:
        node = entry.find(path)
        if node is None or node.text is None:
            return ""
        return node.text.strip()

    title = text(f"{ATOM_NS}title")
    summary = text(f"{ATOM_NS}summary")
    published = text(f"{ATOM_NS}published")
    updated = text(f"{ATOM_NS}updated")
    doi = text(f"{ARXIV_NS}doi")

    authors: list[str] = []
    for author in entry.findall(f"{ATOM_NS}author"):
        name_node = author.find(f"{ATOM_NS}name")
        name = name_node.text.strip() if name_node is not None and name_node.text else ""
        if name:
            authors.append(name)

    categories = [
        cat.attrib.get("term", "")
        for cat in entry.findall(f"{ATOM_NS}category")
        if cat.attrib.get("term")
    ]

    primary_category_node = entry.find(f"{ARXIV_NS}primary_category")
    primary_category = (
        primary_category_node.attrib.get("term", "") if primary_category_node is not None else ""
    )

    entry_id = text(f"{ATOM_NS}id")
    arxiv_id = entry_id.rsplit("/abs/", maxsplit=1)[-1] if "/abs/" in entry_id else ""

    abs_url = ""
    pdf_url = ""
    for link in entry.findall(f"{ATOM_NS}link"):
        href = link.attrib.get("href", "")
        if not abs_url and link.attrib.get("rel") == "alternate" and link.attrib.get("type") == "text/html":
            abs_url = href
        if not pdf_url and link.attrib.get("title") == "pdf":
            pdf_url = href

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "summary": summary,
        "authors": authors,
        "published": published,
        "updated": updated,
        "doi": doi,
        "primary_category": primary_category,
        "categories": categories,
        "abs_url": abs_url,
        "pdf_url": pdf_url,
    }


if __name__ == "__main__":
    sample_doi = "10.48550/arXiv.1706.03762"
    print(fetch_arxiv_metadata_by_doi(sample_doi))
