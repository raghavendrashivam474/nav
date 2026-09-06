"""Orchestrator — capability dispatch with S20 security enforcement.

Routes requests to registered capabilities. When a SecurityService is
configured, authorization is checked before dispatch.
"""

import logging
from typing import TYPE_CHECKING

from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Request, Response

if TYPE_CHECKING:
    from core.security.service import SecurityService

logger = logging.getLogger("NAV.Orchestrator")


class Orchestrator:
    def __init__(
        self,
        registry: CapabilityRegistry,
        security_service: "SecurityService | None" = None,
    ) -> None:
        self.registry = registry
        self._security_service = security_service

    def route_request(
        self, target_capability: str, request: Request
    ) -> Response:
        # S20 / Sx1.1: Authorization check before capability dispatch
        if self._security_service is not None:
            from core.contracts.security import (
                ActorIdentity,
                ActorType,
                AuthorizationOutcome,
            )

            # Extract and sanitize actor from request payload
            actor_data = request.payload.get("_actor")
            actor: ActorIdentity
            if isinstance(actor_data, ActorIdentity):
                actor = actor_data
            elif isinstance(actor_data, dict):
                raw_type = str(actor_data.get("actor_type", "user")).lower()
                # Untrusted payload dicts cannot claim SYSTEM privileges directly
                if raw_type == ActorType.SYSTEM.value:
                    actor_type = ActorType.USER
                else:
                    try:
                        actor_type = ActorType(raw_type)
                    except ValueError:
                        actor_type = ActorType.USER

                actor = ActorIdentity(
                    actor_id=str(actor_data.get("actor_id", "anonymous")),
                    actor_type=actor_type,
                    trust_level=0,  # Unverified payload dicts cannot assert trust level
                )
            else:
                # When omitted or invalid, default to standard unprivileged user actor
                actor = ActorIdentity(
                    actor_id="anonymous",
                    actor_type=ActorType.USER,
                    trust_level=0,
                )

            action = (
                f"{target_capability}"
                f".{request.payload.get('action', 'invoke')}"
            )
            resource = str(
                request.payload.get(
                    "work_id",
                    request.payload.get("resource", ""),
                )
            )

            decision = self._security_service.authorize(
                actor=actor,
                action=action,
                resource=resource,
            )

            if decision.outcome == AuthorizationOutcome.DENY:
                logger.warning(
                    "Authorization DENIED: actor=%s action=%s",
                    decision.actor_id,
                    action,
                )
                return Response(
                    request_id=request.request_id,
                    data={
                        "security_decision": decision.outcome.value,
                        "reason": decision.reason,
                    },
                    success=False,
                    error=(
                        "Authorization denied: "
                        f"{decision.reason}"
                    ),
                )

            if (
                decision.outcome
                == AuthorizationOutcome.REQUIRE_APPROVAL
            ):
                logger.info(
                    "Approval required: actor=%s action=%s",
                    decision.actor_id,
                    action,
                )
                # Enrich payload so S18 approval gate can see it.
                # Request is frozen, so create a new instance.
                enriched = dict(request.payload)
                enriched["_security_requires_approval"] = True
                enriched["_security_reason"] = decision.reason
                request = Request(
                    request_id=request.request_id,
                    payload=enriched,
                )

        try:
            capability = self.registry.get(target_capability)
            return capability.invoke(request)
        except Exception as e:
            logger.error(
                "Routing failed for '%s': %s",
                target_capability,
                e,
            )
            return Response(
                request_id=request.request_id,
                data={},
                success=False,
                error=f"Orchestration failure: {e!s}",
            )
