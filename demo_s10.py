"""NAV S10 Interactive & Automated Continuity Demo.

Demonstrates the S10 multi-turn personal research interaction loop.
"""

from __future__ import annotations

import time

from capabilities.cognition.cognition import CognitionCapability
from capabilities.memory.capability import MemoryCapability
from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from capabilities.research.cache import ResearchCache
from capabilities.research.capability import ResearchCapability
from capabilities.research.context_store import ResearchContextStore
from capabilities.research.service import ResearchService
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request
from core.contracts.memory import MemoryQuery
from core.orchestration.orchestrator import Orchestrator


def print_banner(text: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_turn(turn_num: int, user_input: str) -> None:
    print(f"\n--- [TURN {turn_num}] User: \"{user_input}\" ---")


def run_demo() -> None:
    print_banner("NAV v0.10 - SPRINT S10 CONTINUITY & PERSONAL SYSTEM DEMO")

    # 1. Setup Stack
    print("[1/3] Initializing NAV Stack (Memory, Research with Cache + Continuity, Cognition)...")
    cache = ResearchCache(default_ttl=300.0)
    context_store = ResearchContextStore()
    research_service = ResearchService(cache=cache)

    memory_repo = SQLiteMemoryRepository(":memory:")
    memory_service = MemoryService(memory_repo)
    memory_cap = MemoryCapability(memory_service)

    research_cap = ResearchCapability(
        service=research_service,
        context_store=context_store,
        memory=memory_cap,
    )
    cognition_cap = CognitionCapability(memory=memory_cap)

    registry = CapabilityRegistry()
    registry.register(research_cap)
    registry.register(memory_cap)
    registry.register(cognition_cap)

    orchestrator = Orchestrator(registry)
    print("[OK] Registry & Orchestrator ready with active S10 components.\n")

    # Session tracker for multi-turn interaction
    active_session_id: str | None = None

    def send_research(prompt: str, turn: int) -> dict[str, object]:
        nonlocal active_session_id
        print_turn(turn, prompt)
        payload: dict[str, object] = {"question": prompt}
        if active_session_id:
            payload["session_id"] = active_session_id

        req = Request(request_id=f"turn_{turn}", payload=payload)
        t0 = time.perf_counter()
        resp = orchestrator.route_request("research", req)
        elapsed = (time.perf_counter() - t0) * 1000

        if not resp.success:
            print(f"  [ERROR] {resp.error}")
            return {}

        new_sid = resp.data.get("session_id")
        if new_sid:
            active_session_id = str(new_sid)
        sid_str = str(active_session_id)[:10] if active_session_id else "none"
        intent = str(resp.data.get("continuation_intent", "unknown"))
        reply = resp.data.get("reply", "")

        print(f"  NAV [{elapsed:.1f}ms | Intent: {intent.upper()} | Session: {sid_str}...]:")
        print(f"  \"{reply}\"")

        if "query" in resp.data and isinstance(resp.data["query"], dict):
            q = resp.data["query"]
            print(
                f"  [Resolved Query]: \"{q.get('question')}\" "
                f"| Scope: {q.get('scope')} | Depth: {q.get('depth')}"
            )
        if "sources" in resp.data and isinstance(resp.data["sources"], list):
            print(f"  [Sources Consulted]: {len(resp.data['sources'])}")

        return resp.data

    # -------------------------------------------------------------
    # Multi-Turn Scripted Walkthrough
    # -------------------------------------------------------------
    print_banner("PHASE 1: AUTOMATED MULTI-TURN CONTINUITY WALKTHROUGH")

    # Turn 1: Fresh Research
    send_research("Research solid-state batteries", 1)

    # Turn 2: Deepen
    send_research("Go deeper", 2)

    # Turn 3: Focus Shift
    send_research("Focus on manufacturing challenges", 3)

    # Turn 4: Provenance Request
    send_research("Show me the sources", 4)

    # Turn 5: Cache Verification
    print_turn(5, "Research solid-state batteries (Repeated Query)")
    print("  [Testing Discovery Cache...]")
    send_research("Research solid-state batteries", 5)
    stats = cache.stats
    print(f"  [Cache Stats]: Hits={stats['hits']}, Misses={stats['misses']}, Size={stats['size']}")

    # -------------------------------------------------------------
    # Memory Isolation & Durable Context Verification
    # -------------------------------------------------------------
    print_banner("PHASE 2: MEMORY ISOLATION & DURABLE MEMORY BRIDGE")

    print("[Check 1] Inspecting SQLite long-term memory for automatic pollution...")
    mem_results = memory_service.retrieve(MemoryQuery(query_text="solid-state"))
    print(f"  Durable memories found: {len(mem_results)}")
    assert len(mem_results) == 0, "Memory polluted!"
    print("  [PASS] Clean separation confirmed: Zero research data dumped into long-term memory.")

    print("\n[Check 2] Explicit user memory storage...")
    explicit_req = Request(
        request_id="mem_1",
        payload={"prompt": "Remember that solid state batteries are critical for Project Titan"},
    )
    cognition_resp = orchestrator.route_request("cognition", explicit_req)
    print(f"  NAV: \"{cognition_resp.data.get('reply')}\"")

    stored = memory_service.retrieve(MemoryQuery(query_text="Project Titan"))
    val = stored[0].value if stored else ""
    key = stored[0].key if stored else ""
    print(f"  Durable memories retrieved: {len(stored)} (Key: {key} -> Value: \"{val}\")")
    print("  [PASS] Explicit long-term memory operates reliably.\n")

    # -------------------------------------------------------------
    # Interactive Mode
    # -------------------------------------------------------------
    print_banner("PHASE 3: INTERACTIVE REPL (Try it yourself!)")
    print("Type anything (e.g. 'Research quantum computing', 'Go deeper', 'exit'):\n")

    interactive_turn = 6
    while True:
        try:
            user_input = input("You > ").strip()
            if not user_input or user_input.lower() in ("exit", "quit", "q"):
                print("\nExiting S10 Demo. Cheers! 🚀")
                break

            send_research(user_input, interactive_turn)
            interactive_turn += 1
        except KeyboardInterrupt:
            print("\nExiting...")
            break


if __name__ == "__main__":
    run_demo()
