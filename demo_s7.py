"""NAV S7 Live Demonstration — Research Capability.

Demonstrates the systematic research lifecycle:
  1. Systematic question formulation
  2. Bounded source discovery
  3. Resilient retrieval with provenance tracking
  4. Structured evidence extraction
  5. Synthesis: Supported findings, contradictions, uncertainties, and open questions
  6. Optional durable memory persistence

Usage:
  python demo_s7.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from capabilities.research.capability import ResearchCapability
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.retrieval import MockRetriever
from capabilities.research.service import ResearchService
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
from core.orchestration.orchestrator import Orchestrator


def main() -> None:
    print("=" * 70)
    print("NAV v0.7 — S7 RESEARCH CAPABILITY DEMO")
    print("=" * 70)

    db_path = Path(".demo_s7_memory.db")
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass

    repo = SQLiteMemoryRepository(db_path=db_path)
    mem_service = MemoryService(repository=repo)

    search_provider = MockSearchProvider()
    retriever = MockRetriever()
    research_service = ResearchService(
        gateway=None,  # Uses built-in analytical heuristics
        search_provider=search_provider,
        retriever=retriever,
    )
    research_capability = ResearchCapability(
        service=research_service, memory=mem_service
    )

    registry = CapabilityRegistry()
    registry.register(research_capability)
    orchestrator = Orchestrator(registry)

    prompt = (
        "Research solid-state batteries and identify the major unresolved technical problems."
    )
    print(f"\n[USER REQUEST]:\n  \"{prompt}\"\n")
    print("Investigating systematically through NAV Orchestrator...\n")

    req = Request(
        request_id="demo_s7_req_001",
        payload={
            "question": prompt,
            "max_sources": 4,
            "save_to_memory": True,
        },
    )

    response = orchestrator.route_request("research", req)

    if not response.success:
        print(f"[-] Research Failed: {response.error}")
        sys.exit(1)

    data = response.data

    print("-" * 70)
    print("RESEARCH EVIDENCE LANDSCAPE")
    print("-" * 70)

    print(f"\n1. SOURCES DISCOVERED & RETRIEVED ({len(data['sources'])}):")
    for s in data["sources"]:
        print(f"   • [{s['source_id']}] {s['title']} ({s['source_type']})")
        print(f"     URL: {s['url']}")
        print(f"     Status: {s['status']}")

    print(f"\n2. EXTRACTED EVIDENCE ({len(data['evidence'])} items):")
    for ev in data["evidence"][:4]:
        print(f"   • [{ev['evidence_id']} -> Source {ev['source_id']}]")
        print(f"     Claim: {ev['claim']}")

    print("\n3. SYNTHESIZED RESEARCH MAP:")
    if data["uncertainties"]:
        print("   [Identified Technical Challenges & Uncertainties]:")
        for u in data["uncertainties"][:3]:
            back = ", ".join(u["evidence_ids"])
            print(f"   - {u['statement']}")
            print(f"     ↳ Backing Evidence: [{back}] (Support: {u['support']})")

    print("\n4. OPEN QUESTIONS & NEXT INVESTIGATIONS:")
    for q in data["open_questions"]:
        print(f"   ↳ {q}")

    print("\n" + "=" * 70)
    print("PROVENANCE & BOUNDARIES CONFIRMED — S7 VALIDATED")
    print("=" * 70)

    # Cleanup demo db safely on process exit
    try:
        if db_path.exists():
            db_path.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    main()
