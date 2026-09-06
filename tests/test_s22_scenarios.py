"""S22 Integration & Real-world Validation Scenarios.

Validates the complete NAV v1 architecture across all subsystems:
Interaction -> Orchestrator -> Security -> Work -> Human Control -> Presence -> Environment
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capabilities.work.capability import WorkCapability
from capabilities.work.service import WorkService
from capabilities.work.sqlite_repo import SQLiteWorkRepository
from core.capabilities.registry import CapabilityRegistry
from core.contracts.capability import Capability, Request, Response
from core.contracts.context import (
    ConversationContext,
    NavContext,
    SessionContext,
    UserContext,
)
from core.contracts.environment import (
    RuntimeDescriptor,
    StateOrigin,
)
from core.contracts.security import (
    ActorType,
    AuthorizationOutcome,
)
from core.contracts.work import StepStatus, WorkPlan, WorkStatus, WorkStep
from core.environment.identity import (
    create_device_identity,
    create_runtime_identity,
    generate_device_id,
    generate_environment_id,
    generate_runtime_id,
)
from core.environment.registry import RuntimeRegistry
from core.orchestration.orchestrator import Orchestrator
from core.security.events import SecurityEventLog
from core.security.policy import PolicyEngine, PolicyRule, create_default_policy
from core.security.service import SecurityService
from interfaces.interaction.contracts import (
    InteractionInput,
    InteractionInputKind,
    InteractionOutputKind,
    NAVInteractionState,
)
from interfaces.interaction.interaction_layer import InteractionLayer
from interfaces.voice.audio import AudioInput, AudioOutput
from interfaces.voice.contracts import SpeechToText, TextToSpeech
from interfaces.voice.errors import MicrophoneError, STTError
from interfaces.voice.interaction_voice_adapter import InteractionVoiceAdapter
from interfaces.voice.microphone import MicrophoneProtocol
from interfaces.voice.speaker import SpeakerProtocol

# ==================================================================
# TEST STUBS & FIXTURES
# ==================================================================


class EchoCognitionCapability(Capability):
    """Stub cognition capability that echoes conversational requests."""

    @property
    def name(self) -> str:
        return "cognition"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Conversational cognition stub"

    def invoke(self, request: Request) -> Response:
        prompt = request.payload.get("prompt", "")
        return Response(
            request_id=request.request_id,
            data={"reply": f"Understood: {prompt}"},
            success=True,
        )


class EchoStepCapability(Capability):
    """Echo capability for executing work steps."""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Echo execution capability"

    def invoke(self, request: Request) -> Response:
        return Response(
            request_id=request.request_id,
            data={"result": "step completed successfully", "input": request.payload},
            success=True,
        )


class CrashingCapability(Capability):
    """A capability that deliberately fails."""

    @property
    def name(self) -> str:
        return "faulty_cap"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Fails deliberately for testing"

    def invoke(self, request: Request) -> Response:
        return Response(
            request_id=request.request_id,
            success=False,
            error="Database connection timeout / unrecoverable failure",
        )


class FakeMicrophone(MicrophoneProtocol):
    """Configurable microphone fixture for voice testing."""

    def __init__(self, audio_data: bytes | None = b"sample_audio") -> None:
        self._audio_data = audio_data

    def record(self, seconds: float = 5.0) -> AudioInput:
        if self._audio_data is None:
            raise MicrophoneError("Microphone hardware error / unreadable")
        return AudioInput(
            samples=self._audio_data,
            sample_rate=16000,
            channels=1,
            duration_seconds=seconds,
        )


class FakeSTT(SpeechToText):
    """Configurable STT fixture for voice testing."""

    def __init__(self, text: str = "Status", fail: bool = False) -> None:
        self.text = text
        self.fail = fail

    @property
    def name(self) -> str:
        return "fake_stt"

    def transcribe(self, audio: AudioInput) -> str:
        if self.fail:
            raise STTError("STT transcription crashed")
        return self.text


class FakeTTS(TextToSpeech):
    """Fake TTS returning dummy audio output."""

    def __init__(self) -> None:
        self.synthesized: list[str] = []

    @property
    def name(self) -> str:
        return "fake_tts"

    def synthesize(self, text: str) -> AudioOutput:
        self.synthesized.append(text)
        return AudioOutput(
            samples=b"fake_synthesized_wav",
            sample_rate=24000,
            channels=1,
            metadata={"text": text},
        )


class FakeSpeaker(SpeakerProtocol):
    """Fake Speaker collecting audio outputs."""

    def __init__(self) -> None:
        self.played: list[AudioOutput] = []

    def play(self, audio: AudioOutput) -> None:
        self.played.append(audio)


@pytest.fixture
def nav_context() -> NavContext:
    return NavContext(
        user=UserContext(user_id="u1"),
        session=SessionContext(session_id="s1"),
        conversation=ConversationContext(conversation_id="c1"),
    )


@pytest.fixture
def security_policy() -> PolicyEngine:
    return create_default_policy()


@pytest.fixture
def security_service(security_policy: PolicyEngine) -> SecurityService:
    events = SecurityEventLog()
    return SecurityService(policy_engine=security_policy, event_log=events)


@pytest.fixture
def work_repo(tmp_path: Path) -> SQLiteWorkRepository:
    db_path = tmp_path / "test_work.db"
    repo = SQLiteWorkRepository(db_path=db_path)
    repo.initialize()
    return repo


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(EchoCognitionCapability())
    registry.register(EchoStepCapability())
    return registry


@pytest.fixture
def orchestrator(
    capability_registry: CapabilityRegistry,
    security_service: SecurityService,
) -> Orchestrator:
    return Orchestrator(registry=capability_registry, security_service=security_service)


@pytest.fixture
def work_service(
    work_repo: SQLiteWorkRepository,
    orchestrator: Orchestrator,
) -> WorkService:
    service = WorkService(repository=work_repo, orchestrator=orchestrator)
    work_cap = WorkCapability(service)
    orchestrator.registry.register(work_cap)
    return service


@pytest.fixture
def interaction_layer(
    orchestrator: Orchestrator,
    work_service: WorkService,
) -> InteractionLayer:
    return InteractionLayer(orchestrator=orchestrator)


@pytest.fixture
def microphone() -> FakeMicrophone:
    return FakeMicrophone(b"fake_voice_data")


@pytest.fixture
def stt() -> FakeSTT:
    return FakeSTT("What is the status?")


@pytest.fixture
def tts() -> FakeTTS:
    return FakeTTS()


@pytest.fixture
def speaker() -> FakeSpeaker:
    return FakeSpeaker()


@pytest.fixture
def voice_adapter(
    interaction_layer: InteractionLayer,
    microphone: FakeMicrophone,
    stt: FakeSTT,
    tts: FakeTTS,
    speaker: FakeSpeaker,
) -> InteractionVoiceAdapter:
    return InteractionVoiceAdapter(
        interaction_layer=interaction_layer,
        microphone=microphone,
        stt=stt,
        tts=tts,
        speaker=speaker,
    )


# ==================================================================
# SCENARIOS A - H
# ==================================================================


class TestScenarioANaturalWorkRequest:
    """End-to-end: user requests work, NAV executes it, reports result."""

    def test_text_request_creates_and_executes_work(
        self,
        orchestrator: Orchestrator,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Text input routes through InteractionLayer and Orchestrator to execute work."""
        create_req = Request(
            request_id="test_req_create",
            payload={
                "action": "create",
                "objective": "Build S22 Integration Suite",
                "tags": ["s22", "validation"],
                "_actor": {"actor_id": "operator", "actor_type": "user", "trust_level": 2},
            },
        )
        resp = orchestrator.route_request("work", create_req)
        assert resp.success is True
        work_id = resp.data["work_id"]
        assert work_id.startswith("work_")

        interaction_layer.session.focused_work_id = work_id

        plan_req = Request(
            request_id="test_req_plan",
            payload={"action": "plan", "work_id": work_id},
        )
        plan_resp = orchestrator.route_request("work", plan_req)
        assert plan_resp.success is True

        run_req = Request(
            request_id="test_req_run",
            payload={"action": "run_bounded", "work_id": work_id, "max_steps": 5},
        )
        run_resp = orchestrator.route_request("work", run_req)
        assert run_resp.success is True
        assert run_resp.data["status"] == WorkStatus.COMPLETED.value

        presence = interaction_layer.get_presence_state()
        assert presence == NAVInteractionState.COMPLETED

    def test_voice_request_runs_through_adapter(
        self,
        voice_adapter: InteractionVoiceAdapter,
        interaction_layer: InteractionLayer,
        stt: FakeSTT,
    ) -> None:
        """Voice cycle captures audio, transcribes it, and routes to interaction layer."""
        stt.text = "Hello NAV, can you hear me?"
        output = voice_adapter.run_voice_cycle(max_seconds=2.0)

        assert output is not None
        assert output.kind == InteractionOutputKind.SPEAK
        assert "Hello NAV" in output.utterance or "Understood" in output.utterance
        assert voice_adapter.last_transcript == "Hello NAV, can you hear me?"

    def test_security_enforced_on_work_dispatch(
        self,
        orchestrator: Orchestrator,
        security_service: SecurityService,
        work_service: WorkService,
    ) -> None:
        """Every capability route passes through the independent S20 SecurityService."""
        events_before = security_service.event_log.count

        req = Request(
            request_id="sec_chk_01",
            payload={
                "action": "create",
                "objective": "Protected operation",
                "_actor": {"actor_id": "test_actor", "actor_type": "user", "trust_level": 1},
            },
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is True
        assert security_service.event_log.count > events_before

    def test_completed_work_returns_meaningful_response(
        self,
        orchestrator: Orchestrator,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Completed work produces explicit, human-readable status."""
        create_req = Request(
            request_id="cr_resp_01",
            payload={"action": "create", "objective": "Verify response"},
        )
        c_resp = orchestrator.route_request("work", create_req)
        work_id = c_resp.data["work_id"]

        stat_req = Request(
            request_id="st_resp_01",
            payload={"action": "status", "work_id": work_id, "include_activity": True},
        )
        stat_resp = orchestrator.route_request("work", stat_req)
        assert stat_resp.success is True
        assert stat_resp.data["status"] == "pending"
        assert "objective" in stat_resp.data
        assert stat_resp.data["objective"] == "Verify response"


class TestScenarioBStatusQuery:
    """Status inspection through unified interaction layer."""

    def test_status_query_during_active_work(
        self,
        orchestrator: Orchestrator,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Status query while work is paused returns explicit status."""
        create_req = Request(
            request_id="stat_b_1",
            payload={"action": "create", "objective": "Long running task"},
        )
        resp = orchestrator.route_request("work", create_req)
        work_id = resp.data["work_id"]

        orchestrator.route_request(
            "work",
            Request(request_id="stat_b_pause", payload={"action": "pause", "work_id": work_id}),
        )

        interaction_layer.session.focused_work_id = work_id

        user_input = InteractionInput(text="What is the status?", kind=InteractionInputKind.TEXT)
        output = interaction_layer.process_input(user_input)

        assert output.kind == InteractionOutputKind.CONTROL_ACK
        assert "PAUSED" in output.utterance
        assert output.interaction_state == NAVInteractionState.PAUSED
        assert output.focused_work_id == work_id

    def test_status_query_no_active_work(
        self,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Status query when no work is active returns graceful response."""
        interaction_layer.session.focused_work_id = None

        user_input = InteractionInput(text="Status", kind=InteractionInputKind.TEXT)
        output = interaction_layer.process_input(user_input)

        assert output.kind == InteractionOutputKind.ERROR
        assert "no active goal context" in output.utterance
        assert output.interaction_state == NAVInteractionState.IDLE


class TestScenarioCPauseResume:
    """Human control: pause and resume active workflows."""

    def test_pause_active_work(
        self,
        orchestrator: Orchestrator,
        interaction_layer: InteractionLayer,
        work_service: WorkService,
    ) -> None:
        """'Pause that' transitions work to PAUSED through interaction layer."""
        work = work_service.create_work(objective="Task to pause")
        interaction_layer.session.focused_work_id = work.work_id

        user_input = InteractionInput(text="Pause that", kind=InteractionInputKind.TEXT)
        output = interaction_layer.process_input(user_input)

        assert output.kind == InteractionOutputKind.CONTROL_ACK
        assert "paused" in output.utterance.lower()

        updated_work = work_service.get_work(work.work_id)
        assert updated_work is not None
        assert updated_work.status == WorkStatus.PAUSED
        assert interaction_layer.get_presence_state() == NAVInteractionState.PAUSED

    def test_resume_paused_work(
        self,
        orchestrator: Orchestrator,
        interaction_layer: InteractionLayer,
        work_service: WorkService,
    ) -> None:
        """'Resume' transitions PAUSED work back to READY state."""
        work = work_service.create_work(objective="Task to resume")
        work_service.pause_work(work.work_id)
        interaction_layer.session.focused_work_id = work.work_id

        user_input = InteractionInput(text="Resume work", kind=InteractionInputKind.TEXT)
        output = interaction_layer.process_input(user_input)

        assert output.kind == InteractionOutputKind.CONTROL_ACK
        assert "resuming" in output.utterance.lower()

        updated_work = work_service.get_work(work.work_id)
        assert updated_work is not None
        assert updated_work.status == WorkStatus.READY

    def test_pause_nonexistent_work(
        self,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Pausing when no work is active produces deterministic fallback."""
        interaction_layer.session.focused_work_id = None

        user_input = InteractionInput(text="Pause", kind=InteractionInputKind.TEXT)
        output = interaction_layer.process_input(user_input)

        assert output.kind == InteractionOutputKind.ERROR
        assert "no active goal context" in output.utterance.lower()


class TestScenarioDRedirect:
    """Goal redirection under S18 / S19."""

    def test_redirect_preserves_work_id(
        self,
        orchestrator: Orchestrator,
        work_service: WorkService,
    ) -> None:
        """Redirect updates the objective while keeping work_id intact."""
        work = work_service.create_work(objective="Original objective")
        original_id = work.work_id

        req = Request(
            request_id="redir_01",
            payload={
                "action": "redirect",
                "work_id": original_id,
                "new_objective": "Redirected new objective",
                "reason": "Priorities shifted",
            },
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is True
        assert resp.data["work_id"] == original_id

        updated = work_service.get_work(original_id)
        assert updated is not None
        assert updated.work_id == original_id
        assert updated.objective == "Redirected new objective"

    def test_redirect_via_interaction_layer(
        self,
        interaction_layer: InteractionLayer,
        work_service: WorkService,
    ) -> None:
        """Redirect initiated through natural interaction boundary."""
        work = work_service.create_work(objective="Initial plan")
        interaction_layer.session.focused_work_id = work.work_id

        user_input = InteractionInput(
            text="focus on deploying the service instead",
            kind=InteractionInputKind.TEXT,
        )
        output = interaction_layer.process_input(user_input)

        assert output.kind == InteractionOutputKind.CONTROL_ACK
        assert "Goal redirected" in output.utterance
        assert output.focused_work_id == work.work_id

        updated = work_service.get_work(work.work_id)
        assert updated is not None
        assert updated.objective == "deploying the service"


class TestScenarioEApprovalAndDenial:
    """Security authorization and human approval gates."""

    def test_approval_required_step_pauses_for_human(
        self,
        orchestrator: Orchestrator,
        work_service: WorkService,
        interaction_layer: InteractionLayer,
    ) -> None:
        """A step configured with requires_approval=True halts until approved."""
        work = work_service.create_work(objective="Deploy system")
        step = WorkStep(
            step_id="step_deploy",
            name="Deploy DB",
            description="Deploy production database",
            capability="echo",
            input_payload={"target": "prod"},
            metadata={"requires_approval": True},
        )
        work_service.set_plan(work.work_id, WorkPlan(plan_id="plan_dep", steps=(step,)))

        # Execute next step -> should pause for approval
        updated = work_service.execute_next_step(work.work_id)
        assert updated.status == WorkStatus.WAITING_FOR_APPROVAL
        assert updated.plan is not None
        assert updated.plan.steps[0].status == StepStatus.WAITING_FOR_APPROVAL
        assert updated.current_step_id == "step_deploy"

        # Presence state reflects waiting for approval
        interaction_layer.session.focused_work_id = work.work_id
        assert interaction_layer.get_presence_state() == NAVInteractionState.WAITING_FOR_APPROVAL

        # Now approve via interaction layer
        user_input = InteractionInput(text="Approve step", kind=InteractionInputKind.TEXT)
        out = interaction_layer.process_input(user_input)
        assert out.kind == InteractionOutputKind.CONTROL_ACK
        assert "Approval registered" in out.utterance

        # Work can now execute to completion
        completed = work_service.execute_next_step(work.work_id)
        assert completed.status == WorkStatus.COMPLETED

    def test_security_deny_blocks_capability_execution(
        self,
        orchestrator: Orchestrator,
        security_service: SecurityService,
    ) -> None:
        """A DENY rule in SecurityService halts dispatch before capability invocation."""
        deny_rule = PolicyRule(
            actor_type=ActorType.USER,
            action_pattern="work.destroy",
            resource_pattern="*",
            outcome=AuthorizationOutcome.DENY,
            reason="Destructive operations forbidden",
            priority=100,
        )
        security_service.policy_engine.add_rule(deny_rule)

        req = Request(
            request_id="sec_deny_req",
            payload={
                "action": "destroy",
                "work_id": "work_123",
                "_actor": {"actor_id": "operator", "actor_type": "user", "trust_level": 1},
            },
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "Authorization denied" in (resp.error or "")
        assert resp.data.get("security_decision") == AuthorizationOutcome.DENY.value

    def test_security_deny_cannot_be_overridden_by_approval(
        self,
        orchestrator: Orchestrator,
        security_service: SecurityService,
    ) -> None:
        """Security DENY overrides any downstream approval or user intent."""
        deny_approve = PolicyRule(
            actor_type=ActorType.USER,
            action_pattern="work.approve",
            resource_pattern="work_locked*",
            outcome=AuthorizationOutcome.DENY,
            reason="Locked work cannot be approved",
            priority=100,
        )
        security_service.policy_engine.add_rule(deny_approve)

        req = Request(
            request_id="deny_app_01",
            payload={
                "action": "approve",
                "work_id": "work_locked_01",
                "step_id": "step_1",
                "_actor": {"actor_id": "user_low_trust", "actor_type": "user", "trust_level": 0},
            },
        )
        resp = orchestrator.route_request("work", req)
        assert resp.success is False
        assert "Authorization denied" in (resp.error or "")


class TestScenarioFFailure:
    """Honest failure handling across work and interaction."""

    def test_failed_step_transitions_work_to_failed(
        self,
        orchestrator: Orchestrator,
        work_service: WorkService,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Failed step explicitly records failure and does not pretend success."""
        orchestrator.registry.register(CrashingCapability())

        work = work_service.create_work(objective="Test failure recovery")
        step = WorkStep(
            step_id="step_fail",
            name="Crash step",
            description="Run faulty capability",
            capability="faulty_cap",
        )
        work_service.set_plan(work.work_id, WorkPlan(plan_id="p_fail", steps=(step,)))

        # Step 1: execute -> fails once, retries remaining
        work_service.execute_next_step(work.work_id)
        # Step 2: retry execute -> fails again, retries exhausted -> FAILED
        updated = work_service.execute_next_step(work.work_id)

        assert updated.status == WorkStatus.FAILED
        assert updated.plan is not None
        assert updated.plan.steps[0].status == StepStatus.FAILED
        assert updated.plan.steps[0].error is not None
        assert "failed" in updated.plan.steps[0].error.lower()

        # Presence check
        interaction_layer.session.focused_work_id = work.work_id
        assert interaction_layer.get_presence_state() == NAVInteractionState.ERROR

    def test_user_can_redirect_after_intervention_or_pause(
        self,
        work_service: WorkService,
        interaction_layer: InteractionLayer,
    ) -> None:
        """Human control can redirect paused or blocked workflow towards an alternative."""
        work = work_service.create_work(objective="Blocked work")
        work_service.pause_work(work.work_id)
        interaction_layer.session.focused_work_id = work.work_id

        user_input = InteractionInput(
            text="focus on the backup service instead",
            kind=InteractionInputKind.TEXT,
        )
        out = interaction_layer.process_input(user_input)
        assert out.kind == InteractionOutputKind.CONTROL_ACK

        updated = work_service.get_work(work.work_id)
        assert updated is not None
        assert updated.objective == "the backup service"


class TestScenarioGVoiceFailure:
    """Voice failure handling & fallbacks."""

    def test_microphone_hardware_error_returns_none_cleanly(
        self,
        interaction_layer: InteractionLayer,
        stt: FakeSTT,
        tts: FakeTTS,
        speaker: FakeSpeaker,
    ) -> None:
        """Microphone error is handled without crashing the process."""
        bad_mic = FakeMicrophone(audio_data=None)
        adapter = InteractionVoiceAdapter(
            interaction_layer=interaction_layer,
            microphone=bad_mic,
            stt=stt,
            tts=tts,
            speaker=speaker,
        )

        output = adapter.run_voice_cycle()
        assert output is None
        assert interaction_layer.session.is_listening is False

    def test_stt_transcription_crash_returns_none_cleanly(
        self,
        interaction_layer: InteractionLayer,
        microphone: FakeMicrophone,
        tts: FakeTTS,
        speaker: FakeSpeaker,
    ) -> None:
        """STT crash is caught gracefully."""
        failing_stt = FakeSTT(fail=True)
        adapter = InteractionVoiceAdapter(
            interaction_layer=interaction_layer,
            microphone=microphone,
            stt=failing_stt,
            tts=tts,
            speaker=speaker,
        )

        output = adapter.run_voice_cycle()
        assert output is None
        assert interaction_layer.session.is_thinking is False

    def test_empty_audio_or_silence_produces_no_action(
        self,
        interaction_layer: InteractionLayer,
        microphone: FakeMicrophone,
        tts: FakeTTS,
        speaker: FakeSpeaker,
    ) -> None:
        """Empty transcription produces no side effects."""
        silent_stt = FakeSTT(text="")
        adapter = InteractionVoiceAdapter(
            interaction_layer=interaction_layer,
            microphone=microphone,
            stt=silent_stt,
            tts=tts,
            speaker=speaker,
        )

        output = adapter.run_voice_cycle()
        assert output is None
        assert interaction_layer.session.is_thinking is False


class TestScenarioHEnvironmentIdentity:
    """S21 identity substrate coherence."""

    def test_runtime_identities_are_distinguishable(self) -> None:
        """Multiple runtimes in the same environment maintain distinct identities."""
        env_id = generate_environment_id()
        reg = RuntimeRegistry(environment_id=env_id)

        dev_id1 = generate_device_id()
        dev_id2 = generate_device_id()

        rt1 = create_runtime_identity(env_id, dev_id1)
        rt2 = create_runtime_identity(env_id, dev_id2)

        assert rt1.runtime_id != rt2.runtime_id
        assert rt1.environment_id == rt2.environment_id

        desc1 = RuntimeDescriptor(runtime=rt1, device=create_device_identity(dev_id1))
        desc2 = RuntimeDescriptor(runtime=rt2, device=create_device_identity(dev_id2))

        reg.register(desc1)
        reg.register(desc2)

        assert reg.count == 2
        assert len(reg.active_runtimes()) == 2

    def test_state_origin_preserves_device_runtime_lineage(self) -> None:
        """StateOrigin accurately models where state originated."""
        env_id = generate_environment_id()
        dev_id = generate_device_id()
        rt_id = generate_runtime_id()

        origin = StateOrigin(
            environment_id=env_id,
            origin_device_id=dev_id,
            origin_runtime_id=rt_id,
        )

        assert origin.environment_id == env_id
        assert origin.origin_device_id == dev_id
        assert origin.origin_runtime_id == rt_id

    def test_environment_context_coexists_with_orchestrator(
        self,
        orchestrator: Orchestrator,
        work_service: WorkService,
    ) -> None:
        """Orchestrator handles requests carrying S21 origin and actor metadata seamlessly."""
        dev_id = generate_device_id()
        env_id = generate_environment_id()

        req = Request(
            request_id="env_orch_01",
            payload={
                "action": "create",
                "objective": "Context test",
                "_origin": {
                    "environment_id": env_id,
                    "device_id": dev_id,
                },
                "_actor": {
                    "actor_id": "operator",
                    "actor_type": "user",
                    "trust_level": 2,
                },
            },
        )

        resp = orchestrator.route_request("work", req)
        assert resp.success is True
        assert resp.data["work_id"].startswith("work_")


