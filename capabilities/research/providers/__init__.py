"""Pluggable search providers for NAV Research — S9.

Each provider implements the SearchProvider Protocol from
core.contracts.research. The research layer remains agnostic
to which search engine is active.
"""

from capabilities.research.providers.duckduckgo import DuckDuckGoSearchProvider

__all__ = ["DuckDuckGoSearchProvider"]
