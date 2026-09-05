"""WorkCapability — S17.

Wraps WorkService as a standard NAV Capability so it can be
discovered and invoked through the Orchestrator / CapabilityRegistry.
"""

from __future__ import annotations

from typing import Any

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
            elif action == "resume":
                return self._handle_resume(request)
            elif action == "request_intervention":
                return self._handle_request_intervention(request)
            elif action == "revise_plan":
                return self._handle_revise_plan(request)
            elif action == "redirect":
                return self._handle_redirect(request)
            elif action == "approve":
                return self._handle_approve(request)
            elif action == "reject":
                return self._handle_reject(request)
            elif action == "request_input":
                return self._handle_request_input(request)
            elif action == "provide_input":
                return self._handle_provide_input(request)
            elif action == "take_over":
                return self._handle_take_over(request)
            elif action == "return_control":
                return self._handle_return_control(request)
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
        data: dict[str, Any] = {
            "work_id": work.work_id,
            "objective": work.objective,
            "status": work.status.value,
            "completed_steps": len(work.completed_steps()),
            "pending_steps": len(work.pending_steps()),
            "activity_count": len(work.activity_log),
        }
        # S19: optional activity inclusion — additive, backward-compatible.
        # When include_activity is absent or falsy the payload is identical
        # to the S18 shape.  No existing caller is affected.
        if request.payload.get("include_activity"):
            limit = int(request.payload.get("activity_limit", 2))
            recent = list(work.activity_log[-limit:]) if work.activity_log else []
            recent.reverse()
            data["recent_activity"] = [
                {
                    "timestamp": a.timestamp,
                    "activity_type": a.activity_type.value,
                    "description": a.description,
                    "step_id": a.step_id,
                    "metadata": dict(a.metadata),
                }
                for a in recent
            ]
        return Response(request_id=request.request_id, data=data)

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

    def _handle_resume(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        work = self._service.resume_work(work_id)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_request_intervention(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        reason = str(request.payload.get("reason", ""))
        work = self._service.request_intervention(work_id, reason=reason)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_revise_plan(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        steps_data = request.payload.get("steps", [])
        reason = str(request.payload.get("reason", ""))

        from capabilities.work.sqlite_repo import _dict_to_step

        new_steps = [_dict_to_step(sd) for sd in steps_data]

        work = self._service.revise_plan(work_id, new_steps, reason=reason)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "plan_version": work.plan.version if work.plan else 1},
        )

    def _handle_redirect(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        new_objective = request.payload.get("new_objective")
        reason = str(request.payload.get("reason", ""))
        steps_data = request.payload.get("steps")

        new_steps = None
        if steps_data is not None:
            from capabilities.work.sqlite_repo import _dict_to_step

            new_steps = [_dict_to_step(sd) for sd in steps_data]

        work = self._service.redirect_work(
            work_id,
            new_objective=new_objective,
            new_steps=new_steps,
            reason=reason,
        )
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "objective": work.objective},
        )

    def _handle_approve(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        step_id = str(request.payload.get("step_id", ""))
        modified_payload = request.payload.get("modified_payload")
        work = self._service.approve_step(work_id, step_id, modified_payload=modified_payload)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_reject(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        step_id = str(request.payload.get("step_id", ""))
        reason = str(request.payload.get("reason", ""))
        work = self._service.reject_step(work_id, step_id, reason=reason)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_request_input(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        step_id = request.payload.get("step_id")
        prompt = str(request.payload.get("prompt", ""))
        work = self._service.request_input(work_id, step_id=step_id, prompt=prompt)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_provide_input(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        input_data = request.payload.get("input_data", {})
        step_id = request.payload.get("step_id")
        work = self._service.provide_input(work_id, input_data=input_data, step_id=step_id)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_take_over(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        reason = str(request.payload.get("reason", ""))
        work = self._service.take_over(work_id, reason=reason)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )

    def _handle_return_control(self, request: Request) -> Response:
        work_id = str(request.payload.get("work_id", ""))
        reason = str(request.payload.get("reason", ""))
        work = self._service.return_control(work_id, reason=reason)
        return Response(
            request_id=request.request_id,
            data={"work_id": work.work_id, "status": work.status.value},
        )
