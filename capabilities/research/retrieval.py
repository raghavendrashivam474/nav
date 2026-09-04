"""Retrieval layer — S7 + S9.

Handles bounded retrieval, HTTP error states, timeouts, content size limits,
deterministic URL normalization, and PDF document text extraction.

S9 additions:
  - PDF document retrieval and text extraction via pypdf
  - Bounded binary streaming for documents (max download byte limits)
  - Resilient handling of malformed or password-protected PDFs
"""

from __future__ import annotations

import io
import urllib.parse

import httpx

from core.contracts.research import (
    ResearchSource,
    RetrievedContent,
    SourceRetriever,
)
from core.log import get_logger

logger = get_logger(__name__)

# Hard cap on raw binary downloads (10 MB) to prevent DOS / memory exhaustion
MAX_PDF_DOWNLOAD_BYTES = 10 * 1024 * 1024


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    1. Lowercase scheme and host.
    2. Strip common default ports (80, 443).
    3. Strip trailing slashes.
    4. Strip common analytics query parameters (utm_*).
    5. Strip fragments.
    """
    try:
        parsed = urllib.parse.urlparse(url.strip())
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()

        # Remove default ports
        if scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]

        path = parsed.path
        if path.endswith("/"):
            path = path[:-1]

        # Strip query params except important ones
        query_params = urllib.parse.parse_qsl(parsed.query)
        filtered_params = [
            (k, v)
            for k, v in query_params
            if not k.lower().startswith("utm_") and k.lower() != "ref"
        ]

        query = ""
        if filtered_params:
            query = "?" + urllib.parse.urlencode(filtered_params)

        return f"{scheme}://{netloc}{path}{query}"
    except Exception:
        return url.strip().lower().rstrip("/")


def extract_text_from_pdf_bytes(pdf_bytes: bytes, max_chars: int) -> tuple[str, bool]:
    """Extract plain text from raw PDF bytes using pypdf.

    Returns:
        (extracted_text, truncated)
    """
    try:
        import pypdf
    except ImportError:
        logger.error("pypdf package not installed. Run: pip install pypdf")
        raise RuntimeError("pypdf is required for PDF extraction")

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        logger.warning("Failed to parse PDF binary: %s", exc)
        raise ValueError(f"Malformed or unreadable PDF document: {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            logger.warning("PDF is password-protected/encrypted: %s", exc)
            raise ValueError("PDF is encrypted and password-protected") from exc

    extracted_pages: list[str] = []
    char_count = 0
    truncated = False

    for page_idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
        except Exception as page_exc:
            logger.debug("Failed extracting page %d: %s", page_idx, page_exc)
            continue

        if not page_text.strip():
            continue

        extracted_pages.append(page_text)
        char_count += len(page_text)

        if char_count >= max_chars:
            truncated = True
            logger.debug(
                "PDF text truncated at %d characters across %d pages",
                max_chars,
                page_idx + 1,
            )
            break

    full_text = "\n\n".join(extracted_pages)[:max_chars]
    if not full_text.strip():
        raise ValueError("PDF document contains no extractable text (may be scanned image)")

    return full_text, truncated


class HttpxRetriever(SourceRetriever):
    """Production HTTP retriever using httpx supporting HTML, Text, and PDF documents.

    Enforces hard bounds on content size, requests timeout, and logs all metrics.
    """

    def __init__(self, name: str = "httpx-retriever") -> None:
        self.name = name

    def retrieve(self, source: ResearchSource, max_chars: int, timeout: float) -> RetrievedContent:
        logger.info("Retrieving content for %s (timeout=%.1fs)", source.url, timeout)

        limits = httpx.Limits(max_keepalive_connections=2, max_connections=5)
        headers = {"User-Agent": "NAV-Research-Bot/0.9 (+https://github.com/anti-grav/nav)"}

        with httpx.Client(limits=limits, headers=headers, follow_redirects=True) as client:
            try:
                with client.stream("GET", source.url, timeout=timeout) as response:
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "").lower()
                    url_lower = source.url.lower()
                    is_pdf = "application/pdf" in content_type or url_lower.endswith(".pdf")

                    if is_pdf:
                        byte_chunks: list[bytes] = []
                        byte_count = 0
                        for chunk in response.iter_bytes(chunk_size=8192):
                            byte_chunks.append(chunk)
                            byte_count += len(chunk)
                            if byte_count >= MAX_PDF_DOWNLOAD_BYTES:
                                logger.warning(
                                    "PDF download exceeded cap of %d bytes for %s",
                                    MAX_PDF_DOWNLOAD_BYTES,
                                    source.url,
                                )
                                break

                        raw_pdf = b"".join(byte_chunks)
                        pdf_text, truncated = extract_text_from_pdf_bytes(raw_pdf, max_chars)

                        return RetrievedContent(
                            source_id=source.source_id,
                            text=pdf_text,
                            content_type="application/pdf",
                            truncated=truncated,
                        )

                    if not any(t in content_type for t in ("text/", "json", "xml")):
                        raise ValueError(f"Unsupported content type: {content_type}")

                    text_chunks: list[str] = []
                    char_count = 0
                    truncated = False

                    for chunk_str in response.iter_text(chunk_size=4096):
                        text_chunks.append(chunk_str)
                        char_count += len(chunk_str)
                        if char_count >= max_chars:
                            truncated = True
                            logger.warning("Content truncated at limit of %d characters", max_chars)
                            break

                    full_text = "".join(text_chunks)[:max_chars]
                    return RetrievedContent(
                        source_id=source.source_id,
                        text=full_text,
                        content_type=content_type,
                        truncated=truncated,
                    )

            except httpx.TimeoutException as exc:
                logger.error("Timeout retrieving %s: %s", source.url, exc)
                raise TimeoutError(f"HTTP request timed out after {timeout} seconds") from exc
            except Exception as exc:
                logger.error("Failed to retrieve %s: %s", source.url, exc)
                raise exc


class MockRetriever(SourceRetriever):
    """Offline-friendly retriever. Matches URLs against canned responses
    or generates representative technical text dynamically."""

    def __init__(self, name: str = "mock-retriever") -> None:
        self.name = name
        self._preset_responses: dict[str, str] = {}

    def add_response(self, url: str, content: str) -> None:
        normalized = normalize_url(url)
        self._preset_responses[normalized] = content

    def retrieve(self, source: ResearchSource, max_chars: int, timeout: float) -> RetrievedContent:
        normalized = normalize_url(source.url)
        if normalized in self._preset_responses:
            text = self._preset_responses[normalized][:max_chars]
            return RetrievedContent(
                source_id=source.source_id,
                text=text,
                content_type="text/plain",
                truncated=len(text) >= max_chars,
            )

        # Dynamic technical article content generator
        if "solid-state-intro" in normalized:
            content = (
                "Solid-state battery interfaces are plagued by high contact resistance. "
                "Because solid materials do not wet electrode surfaces like liquid "
                "electrolytes do, microscopic gaps form at the interface. This limits ion "
                "transport and causes local current concentration. Recent studies confirm "
                "that high manufacturing pressure can lower this resistance, but it "
                "introduces significant mechanical stress, leading to cathode fracture."
            )
        elif "sulfide-vs-oxide" in normalized:
            content = (
                "Sulfide solid electrolytes offer exceptional ionic conductivity "
                "(exceeding 10-2 S/cm), approaching liquid organic electrolytes. "
                "However, they are highly reactive with ambient moisture, releasing toxic "
                "hydrogen sulfide (H2S) gas. In contrast, oxide electrolytes (LLZO) "
                "are chemically stable in air, but exhibit lower bulk conductivity and "
                "are brittle, making mechanical roll-to-roll processing difficult."
            )
        elif "manufacturing-scale" in normalized:
            content = (
                "Scaling solid-state battery assembly requires re-purposing existing "
                "roll-to-roll lithium-ion equipment. However, sulfide electrolytes "
                "must be processed in ultra-dry environments with a dew point below -50°C. "
                "Furthermore, continuous high-pressure calendering is required to ensure "
                "contact, which frequently tears thin solid electrolyte separator films."
            )
        elif "dendrite-prevention" in normalized:
            content = (
                "US Patent 1102934 details a composite polymer-ceramic interlayer that "
                "suppresses lithium dendrites. Despite early theories that solid "
                "electrolytes would block dendrites, experiments prove lithium dendrites "
                "propagate through solid electrolyte grain boundaries. This invention "
                "utilizes a self-healing polymer matrix with dispersed LLZO nanoparticles."
            )
        else:
            content = (
                f"Mock technical corpus content for {source.url}. "
                "Investigating relevant parameters and unresolved structural challenges."
            )

        text = content[:max_chars]
        return RetrievedContent(
            source_id=source.source_id,
            text=text,
            content_type="text/plain",
            truncated=len(text) >= max_chars,
        )
