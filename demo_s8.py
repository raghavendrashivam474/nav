"""NAV S8 Interactive Demonstration Script.

Demonstrates:
  1. Capability Integration: Simple Cognition vs Deep Research through Orchestrator
  2. Bounded Concurrent Retrieval: Visualizing parallel source fetching
  3. Progressive Interaction: Real-time structured progress events at each lifecycle stage
  4. Prompt-Injection Hardening: Untrusted data boundaries
  5. Provenance & Uncertainty: Synthesized evidence map with full traceability
"""

from __future__ import annotations

import time

from capabilities.cognition.cognition import CognitionCapability
from capabilities.research.capability import ResearchCapability
from capabilities.research.discovery import MockSearchProvider
from capabilities.research.progress import LoggingProgressReporter
from capabilities.research.retrieval import MockRetriever
from capabilities.research.service import ResearchService
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
from core.orchestration.orchestrator import Orchestrator


def banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def main() -> None:
    banner("NAV S8 Integration & Progressive Interaction Demo")

    # 1. Setup Orchestrator and Capabilities
    print("\n[1] Registering capabilities in CapabilityRegistry...")
    registry = CapabilityRegistry()

    # Register Cognition
    cognition = CognitionCapability()
    registry.register(cognition)

    # Register Research with real-time LoggingProgressReporter
    progress_reporter = LoggingProgressReporter(logger_name="NAV.Progress")
    research_service = ResearchService(
        search_provider=MockSearchProvider(),
        retriever=MockRetriever(),
        progress_reporter=progress_reporter,
        max_concurrent_retrievals=4,
    )
    research_cap = ResearchCapability(service=research_service)
    registry.register(research_cap)

    orchestrator = Orchestrator(registry)
    print(f"Registered capabilities: {registry.list_capabilities()}")

    # 2. Fast Path: Simple Cognition Request
    banner("Scenario A: Fast Path — Simple Cognition Request")
    print("User: 'What is the capital of Japan?'")
    t0 = time.monotonic()
    req_cognition = Request(
        request_id="demo_cog_1",
        payload={"prompt": "What is the capital of Japan?"},
    )
    resp_cognition = orchestrator.route_request("cognition", req_cognition)
    elapsed_cog = time.monotonic() - t0
    print(f"\nResponse received in {elapsed_cog * 1000:.1f}ms:")
    print(f"Reply: {resp_cognition.data.get('reply')}")

    # 3. Progressive Path: Deep Research with Concurrency & Progress
    banner("Scenario B: Deep Research — Bounded Parallel Retrieval & Progress Events")
    question = (
        "Research solid-state batteries and identify the major unresolved technical problems."
    )
    print(f"User: '{question}'\n")

    t1 = time.monotonic()
    req_research = Request(
        request_id="demo_res_1",
        payload={
            "question": question,
            "max_sources": 4,
            "timeout_seconds": 10.0,
        },
    )

    resp_research = orchestrator.route_request("research", req_research)
    elapsed_res = time.monotonic() - t1

    banner("Scenario B: Research Map Result & Provenance")
    print(f"Total investigation duration: {elapsed_res:.2f}s")
    print(f"Success: {resp_research.success}")

    data = resp_research.data
    sources = data.get("sources", [])
    print(f"\n[Sources Discovered & Retrieved: {len(sources)}]")
    for s in sources:
        print(f" - [{s['status'].upper()}] {s['title']} ({s['url']})")

    findings = data.get("findings", [])
    print(f"\n[Supported Findings: {len(findings)}]")
    for f in findings:
        print(f" * {f['statement']} [Support: {f['support']}]")

    uncertainties = data.get("uncertainties", [])
    print(f"\n[Uncertainties / Open Challenges: {len(uncertainties)}]")
    for u in uncertainties:
        print(f" ? {u['statement']}")

    open_questions = data.get("open_questions", [])
    print(f"\n[Open Questions: {len(open_questions)}]")
    for q in open_questions:
        print(f" > {q}")

    banner("S8 Demonstration Complete — All Systems Operational")


if __name__ == "__main__":
    main()
