"""Retrieval layer — S7.

Handles bounded retrieval, HTTP error states, timeouts, content size limits,
and deterministic URL normalization.
"""

from __future__ import annotations

import urllib.parse

import httpx

from core.contracts.research import (
    ResearchSource,
    RetrievedContent,
    SourceRetriever,
)
from core.log import get_logger

logger = get_logger(__name__)


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
        # If parsing fails, fall back to basic cleanup
        return url.strip().lower().rstrip("/")


class HttpxRetriever(SourceRetriever):
    """Production HTTP retriever using httpx.

    Enforces hard bounds on content size, requests timeout, and logs all metrics."""

    def __init__(self, name: str = "httpx-retriever") -> None:
        self.name = name

    def retrieve(self, source: ResearchSource, max_chars: int, timeout: float) -> RetrievedContent:
        logger.info("Retrieving content for %s (timeout=%.1fs)", source.url, timeout)

        # Enforce conservative client limits
        limits = httpx.Limits(max_keepalive_connections=2, max_connections=5)

        with httpx.Client(limits=limits, follow_redirects=True) as client:
            try:
                # Use stream to enforce size limits early and avoid giant downloads
                with client.stream("GET", source.url, timeout=timeout) as response:
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "").lower()
                    if not any(t in content_type for t in ("text/", "json", "xml")):
                        raise ValueError(f"Unsupported content type: {content_type}")

                    chunks = []
                    char_count = 0
                    truncated = False

                    for chunk in response.iter_text(chunk_size=4096):
                        chunks.append(chunk)
                        char_count += len(chunk)
                        if char_count >= max_chars:
                            truncated = True
                            logger.warning("Content truncated at limit of %d characters", max_chars)
                            break

                    full_text = "".join(chunks)[:max_chars]
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
