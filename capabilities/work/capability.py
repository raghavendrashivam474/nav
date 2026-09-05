"""WorkCapability — S17.

Wraps WorkService as a standard NAV Capability so it can be
discovered and invoked through the Orchestrator / CapabilityRegistry.
"""

from __future__ import annotations

from capabilities.work.service import WorkService
from core.contracts.capability import Capability, Request, Response
from core.log import get_logger

logger = get_logger(__name__)


class WorkCapability(Capability):
    """NAV Capability interface for the Work subsystem."""

    def __init__(self, service: WorkService) -> None:
        self._service = service

    @property
    def name(self) -> str:
        return "work"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Goal-directed, bounded, multi-step work execution"

    def invoke(self, request: Request) -> Response:
        action = request.payload.get("action", "")
        try:
            if action == "create":
                return self._handle_create(request)
            elif action == "plan":
                return self._handle_plan(request)
            elif action == "execute_step":
                return self._handle_execute_step(request)
            elif action == "run_bounded":
                return self._handle_run_bounded(request)
            elif action == "status":
                return self._handle_status(request)
            elif action == "pause":
                return self._handle_pause(request)
            elif action == "cancel":
                return self._handle_cancel(request)
            else:
                return Response(
                    request_id=request.request_id,
                    success=False,
                    error=f"Unknown work action: {action}",
                )
        except Exception as e:
            logger.error("WorkCapability error: %s", e)
            return Response(
                request_id=request.request_id,
                success=False,
                error=str(e),
            )

    def _handle_create(self, request: Request) -> Response:
        objective = str(request.payload.get("objective", ""))
        if not objective:
            return Response(
                request_id=request.request_id,
                success=False,
                error="Missing 'objective' in payload",
            )
        tags = tuple(request.payload.get("tags", []))
        work = self._service.create_work(
            objective=objective,
            tags=tags,
            project_id=request.payload.get("project_id"),
            goal_id=request.payload.get("goal_id"),
            investigation_id=request.payload.get("investigation_id"),
        )
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_plan(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        work = self._service.auto_plan(work_id)
        step_count = len(work.plan.steps) if work.plan else 0
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "plan_steps": step_count},
        )

    def _handle_execute_step(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        work = self._service.execute_next_step(work_id)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_run_bounded(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        max_steps = int(request.payload.get("max_steps", 5))
        work = self._service.run_bounded(work_id, max_steps=max_steps)
        return Response(
            request_id=request.request_id,
            data={
                "work_id": work.work_id,
                "status": work.status.value,
                "completed": len(work.completed_steps()),
                "pending": len(work.pending_steps()),
            },
        )

    def _handle_status(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        work = self._service.get_work(work_id)
        if work is None:
            return Response(
                request_id=request.request_id,
                success=False,
                error=f"Work {work_id} not found",
            )
        return Response(
            request_id=request.request_id,
            data={
                "work_id": work.work_id,
                "objective": work.objective,
                "status": work.status.value,
                "completed_steps": len(work.completed_steps()),
                "pending_steps": len(work.pending_steps()),
                "activity_count": len(work.activity_log),
            },
        )

    def _handle_pause(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        work = self._service.pause_work(work_id)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_cancel(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        work = self._service.cancel_work(work_id)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )
