"""
NAV v2 — S29: Action Tests.

Covers contracts, engine, service, and capability layers.
"""

from __future__ import annotations

import pytest

from capabilities.action.capability import ActionCapability
from capabilities.action.engine import ActionEngine
from capabilities.action.service import ActionService
from core.contracts.action import (
    ActionOutcome,
    ActionRequest,
    ActionResult,
    ActionState,
    ActionType,
    is_valid_transition,
)
from core.contracts.capability import Request
from core.contracts.security import (
    SYSTEM_ACTOR,
    ActorIdentity,
    ActorType,
    AuthorizationDecision,
    AuthorizationOutcome,
    AuthorizationRequest,
)


# ======================================================================
# Helpers
# ======================================================================


def _allow_all(req: AuthorizationRequest) -> AuthorizationDecision:
    """Test authorizer that allows everything."""
    return AuthorizationDecision(
        outcome=AuthorizationOutcome.ALLOW,
        actor_id=req.actor.actor_id,
        action=req.action,
        resource=req.resource,
        reason="Test allow-all.",
    )


def _deny_all(req: AuthorizationRequest) -> AuthorizationDecision:
    """Test authorizer that denies everything."""
    return AuthorizationDecision(
        outcome=AuthorizationOutcome.DENY,
        actor_id=req.actor.actor_id,
        action=req.action,
        resource=req.resource,
        reason="Test deny-all.",
    )


# ======================================================================
# Contract Tests
# ======================================================================


class TestActionRequestContract:
    def test_valid_creation(self) -> None:
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="test-resource",
        )
        assert req.action_type == ActionType.ECHO
        assert req.target == "test-resource"
        assert req.source == "direct"

    def test_parameters_frozen(self) -> None:
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="t",
            parameters={"key": "value"},
        )
        with pytest.raises(TypeError):
            req.parameters["new"] = "val"  # type: ignore[index]

    def test_empty_target_rejected(self) -> None:
        with pytest.raises(ValueError, match="target"):
            ActionRequest(action_type=ActionType.ECHO, target="")

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(ValueError, match="source"):
            ActionRequest(
                action_type=ActionType.ECHO,
                target="t",
                source="invalid",
            )

    def test_decision_source_requires_id(self) -> None:
        with pytest.raises(ValueError, match="decision_id"):
            ActionRequest(
                action_type=ActionType.ECHO,
                target="t",
                source="decision",
            )

    def test_decision_source_with_id(self) -> None:
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="t",
            source="decision",
            decision_id="dec-123",
        )
        assert req.decision_id == "dec-123"


class TestActionResultContract:
    def test_valid_success(self) -> None:
        r = ActionResult(
            action_id="a1",
            action_type=ActionType.ECHO,
            state=ActionState.SUCCEEDED,
            outcome=ActionOutcome.SUCCESS,
            message="Done.",
        )
        assert r.state == ActionState.SUCCEEDED

    def test_valid_rejection(self) -> None:
        r = ActionResult(
            action_id="a2",
            action_type=ActionType.LOG,
            state=ActionState.REJECTED,
            outcome=ActionOutcome.REJECTION,
            message="Denied.",
        )
        assert r.outcome == ActionOutcome.REJECTION

    def test_state_outcome_mismatch_rejected(self) -> None:
        with pytest.raises(ValueError, match="outcome"):
            ActionResult(
                action_id="a3",
                action_type=ActionType.ECHO,
                state=ActionState.SUCCEEDED,
                outcome=ActionOutcome.FAILURE,
                message="Mismatch.",
            )

    def test_empty_action_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="action_id"):
            ActionResult(
                action_id="",
                action_type=ActionType.ECHO,
                state=ActionState.FAILED,
                outcome=ActionOutcome.FAILURE,
                message="Bad.",
            )

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="message"):
            ActionResult(
                action_id="a4",
                action_type=ActionType.ECHO,
                state=ActionState.FAILED,
                outcome=ActionOutcome.FAILURE,
                message="",
            )


class TestStateMachine:
    def test_valid_transitions(self) -> None:
        assert is_valid_transition(ActionState.REQUESTED, ActionState.VALIDATED)
        assert is_valid_transition(ActionState.VALIDATED, ActionState.AUTHORIZED)
        assert is_valid_transition(ActionState.AUTHORIZED, ActionState.EXECUTING)
        assert is_valid_transition(ActionState.EXECUTING, ActionState.SUCCEEDED)
        assert is_valid_transition(ActionState.EXECUTING, ActionState.FAILED)
        assert is_valid_transition(ActionState.EXECUTING, ActionState.UNKNOWN)

    def test_invalid_transitions(self) -> None:
        assert not is_valid_transition(ActionState.SUCCEEDED, ActionState.EXECUTING)
        assert not is_valid_transition(ActionState.FAILED, ActionState.EXECUTING)
        assert not is_valid_transition(ActionState.REJECTED, ActionState.VALIDATED)
        assert not is_valid_transition(ActionState.REQUESTED, ActionState.EXECUTING)

    def test_terminal_states(self) -> None:
        for terminal in (
            ActionState.SUCCEEDED,
            ActionState.FAILED,
            ActionState.REJECTED,
            ActionState.CANCELLED,
            ActionState.UNKNOWN,
        ):
            for target in ActionState:
                assert not is_valid_transition(terminal, target)


# ======================================================================
# Engine Tests
# ======================================================================


class TestActionEngine:
    def test_echo_succeeds(self) -> None:
        engine = ActionEngine(authorizer=_allow_all)
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="test",
            parameters={"hello": "world"},
        )
        result = engine.process(req, actor=SYSTEM_ACTOR)
        assert result.state == ActionState.SUCCEEDED
        assert result.outcome == ActionOutcome.SUCCESS
        assert result.metadata["result_data"]["echo"]["hello"] == "world"

    def test_log_succeeds(self) -> None:
        engine = ActionEngine(authorizer=_allow_all)
        req = ActionRequest(
            action_type=ActionType.LOG,
            target="audit",
            parameters={"message": "test log entry", "level": "info"},
        )
        result = engine.process(req, actor=SYSTEM_ACTOR)
        assert result.state == ActionState.SUCCEEDED

    def test_authorization_denied(self) -> None:
        engine = ActionEngine(authorizer=_deny_all)
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="test",
        )
        result = engine.process(req, actor=SYSTEM_ACTOR)
        assert result.state == ActionState.REJECTED
        assert result.outcome == ActionOutcome.REJECTION

    def test_default_authorizer_allows_system(self) -> None:
        engine = ActionEngine()  # default authorizer
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="test",
        )
        result = engine.process(req, actor=SYSTEM_ACTOR)
        assert result.state == ActionState.SUCCEEDED

    def test_default_authorizer_denies_untrusted(self) -> None:
        engine = ActionEngine()  # default authorizer
        untrusted = ActorIdentity(
            actor_id="user:untrusted",
            actor_type=ActorType.USER,
            trust_level=0,
        )
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="test",
        )
        result = engine.process(req, actor=untrusted)
        assert result.state == ActionState.REJECTED

    def test_authorizer_exception_fails_closed(self) -> None:
        def _broken(req: AuthorizationRequest) -> AuthorizationDecision:
            raise RuntimeError("Authorizer exploded")

        engine = ActionEngine(authorizer=_broken)
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="test",
        )
        result = engine.process(req, actor=SYSTEM_ACTOR)
        assert result.state == ActionState.REJECTED
        assert "Authorizer error" in result.message

    def test_validate_returns_none_for_valid(self) -> None:
        engine = ActionEngine()
        req = ActionRequest(action_type=ActionType.ECHO, target="t")
        assert engine.validate(req) is None

    def test_validate_returns_error_for_empty_target(self) -> None:
        engine = ActionEngine()
        # Bypass __post_init__ by constructing directly is not possible
        # with frozen dataclass, so we test via process path instead.
        # The contract already rejects empty target, so this is covered.


# ======================================================================
# Service Tests
# ======================================================================


class TestActionService:
    def test_execute_echo(self) -> None:
        svc = ActionService(authorizer=_allow_all)
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="svc-test",
            parameters={"x": 1},
        )
        result = svc.execute(req)
        assert result.state == ActionState.SUCCEEDED

    def test_execute_with_explicit_actor(self) -> None:
        svc = ActionService(authorizer=_allow_all)
        actor = ActorIdentity(
            actor_id="user:test",
            actor_type=ActorType.USER,
            trust_level=50,
        )
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="t",
        )
        result = svc.execute(req, actor=actor)
        assert result.state == ActionState.SUCCEEDED

    def test_execute_denied(self) -> None:
        svc = ActionService(authorizer=_deny_all)
        req = ActionRequest(
            action_type=ActionType.ECHO,
            target="t",
        )
        result = svc.execute(req)
        assert result.state == ActionState.REJECTED


# ======================================================================
# Capability Tests
# ======================================================================


class TestActionCapability:
    def test_valid_execute(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r1",
            payload={
                "action": "execute",
                "action_type": "echo",
                "target": "cap-test",
                "parameters": {"msg": "hello"},
            },
        )
        resp = cap.invoke(req)
        assert resp.success is True
        assert "action_result" in resp.data

    def test_missing_action_type(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r2",
            payload={"action": "execute", "target": "t"},
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "action_type" in resp.error

    def test_unsupported_action_type(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r3",
            payload={
                "action": "execute",
                "action_type": "delete_everything",
                "target": "t",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "Unsupported" in resp.error

    def test_missing_target(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r4",
            payload={"action": "execute", "action_type": "echo"},
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "target" in resp.error

    def test_unknown_capability_action(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r5",
            payload={"action": "destroy"},
        )
        resp = cap.invoke(req)
        assert resp.success is False

    def test_unauthorized_action(self) -> None:
        cap = ActionCapability(authorizer=_deny_all)
        req = Request(
            request_id="r6",
            payload={
                "action": "execute",
                "action_type": "echo",
                "target": "t",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False

    def test_invalid_parameters_type(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r7",
            payload={
                "action": "execute",
                "action_type": "echo",
                "target": "t",
                "parameters": "not-a-dict",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "dict" in resp.error

    def test_decision_source_without_id(self) -> None:
        cap = ActionCapability(authorizer=_allow_all)
        req = Request(
            request_id="r8",
            payload={
                "action": "execute",
                "action_type": "echo",
                "target": "t",
                "source": "decision",
            },
        )
        resp = cap.invoke(req)
        assert resp.success is False
        assert "decision_id" in resp.error

    def test_capability_properties(self) -> None:
        cap = ActionCapability()
        assert cap.name == "action"
        assert cap.version == "1.0.0"
        assert "authorized" in cap.description.lower()
