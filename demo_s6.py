"""S6 cross-session demonstration script.

Run this twice:
  python demo_s6.py store   → Session A: stores a memory
  python demo_s6.py recall  → Session B: retrieves + forgets it
"""

import sys

from capabilities.memory.service import MemoryService
from capabilities.memory.sqlite_repo import SQLiteMemoryRepository
from core.contracts.memory import MemoryQuery, MemoryRecord


def main():
    repo = SQLiteMemoryRepository(db_path="data/nav_memory.db")
    svc = MemoryService(repository=repo)
    action = sys.argv[1] if len(sys.argv) > 1 else "store"

    if action == "store":
        rec = MemoryRecord(
            key="demo_backend",
            value="The initial NAV memory backend is SQLite.",
            tags=["decision", "project_context"],
            metadata={"source": "demo", "importance": 0.9},
        )
        ok = svc.store(rec)
        print(f"[Session A] Stored memory: {ok}")

    elif action == "recall":
        results = svc.retrieve(MemoryQuery(query_text="memory backend"))
        if results:
            print(f"[Session B] Retrieved: {results[0].value}")
            svc.forget(results[0].key)
            print("[Session B] Forgotten.")
            # Verify deletion
            again = svc.retrieve(MemoryQuery(query_text="memory backend"))
            print(f"[Session B] After forget: {len(again)} result(s)")
        else:
            print("[Session B] No memory found. Run 'store' first.")


if __name__ == "__main__":
    main()
