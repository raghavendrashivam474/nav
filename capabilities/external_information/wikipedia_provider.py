"""
NAV v2 — S23.1: Real Wikipedia Information Provider.

Implements the ExternalInformationProvider Protocol.
Fetches real-time, genuine external context using Wikipedia's search API.
Uses only standard library components to avoid dependency bloat.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from core.contracts.external_information import (
    ExternalInformationItem,
    ExternalInformationRequest,
    ExternalInformationResult,
    RetrievalStatus,
    SourceMetadata,
)


class WikipediaProvider:
    """
    A live external provider utilizing the Wikipedia search API.
    """

    @property
    def provider_id(self) -> str:
        return "wikipedia-api-provider"

    def retrieve(
        self,
        request: ExternalInformationRequest,
    ) -> ExternalInformationResult:
        encoded_query = urllib.parse.quote_plus(request.query)
        url = (
            "https://en.wikipedia.org/w/api.php"
            f"?action=query&list=search&srsearch={encoded_query}"
            "&utf8=&format=json"
        )

        try:
            # Set a defensive user-agent to ensure Wikipedia does not throttle us
            req = urllib.request.Request(
                url, headers={"User-Agent": "NAV-v2-S23-InformationBridge/1.0"}
            )

            # Execute live request with a strict 8-second timeout
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status != 200:
                    return ExternalInformationResult(
                        status=RetrievalStatus.PROVIDER_ERROR,
                        provider_id=self.provider_id,
                        request_id=request.request_id,
                        error_message=f"HTTP Error: {response.status}",
                    )

                raw_data = response.read().decode("utf-8")
                data = json.loads(raw_data)

            # Parse results
            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                return ExternalInformationResult(
                    status=RetrievalStatus.NO_RESULTS,
                    provider_id=self.provider_id,
                    request_id=request.request_id,
                )

            items = []
            # Take only up to the requested result limit
            for result in search_results[: request.result_limit]:
                title = result.get("title")
                snippet = result.get("snippet", "")
                # Strip raw HTML tags Wikipedia returns in snippets
                clean_snippet = (
                    snippet.replace('<span class="searchmatch">', "").replace("</span>", "").strip()
                )
                page_id = result.get("pageid")
                page_url = f"https://en.wikipedia.org/?curid={page_id}" if page_id else None

                metadata = SourceMetadata(
                    source_name=f"Wikipedia: {title}",
                    source_url=page_url,
                    provider_id=self.provider_id,
                    retrieved_at=datetime.now(timezone.utc),
                    query_echo=request.query,
                )

                items.append(
                    ExternalInformationItem(
                        content=clean_snippet,
                        source=metadata,
                        relevance_hint=1.0,
                    )
                )

            return ExternalInformationResult(
                status=RetrievalStatus.SUCCESS,
                items=items,
                provider_id=self.provider_id,
                request_id=request.request_id,
            )

        except urllib.error.URLError as exc:
            return ExternalInformationResult(
                status=RetrievalStatus.UNAVAILABLE,
                provider_id=self.provider_id,
                request_id=request.request_id,
                error_message=f"Network unreachable: {exc}",
            )
        except TimeoutError:
            return ExternalInformationResult(
                status=RetrievalStatus.TIMEOUT,
                provider_id=self.provider_id,
                request_id=request.request_id,
                error_message="Wikipedia connection timed out.",
            )
        except Exception as exc:
            return ExternalInformationResult(
                status=RetrievalStatus.PROVIDER_ERROR,
                provider_id=self.provider_id,
                request_id=request.request_id,
                error_message=f"Unexpected failure: {type(exc).__name__}: {exc}",
            )

    def is_available(self) -> bool:
        # Check standard internet status / ping Wikipedia endpoint quickly
        try:
            req = urllib.request.Request(
                "https://en.wikipedia.org",
                method="HEAD",
                headers={"User-Agent": "NAV-v2-S23-InformationBridge/1.0"},
            )
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False
