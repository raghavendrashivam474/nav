"""
NAV v2 — S30: Observation Contracts.

Defines the structured observation boundary. Represents explicit,
inspectable, and honest representation of what NAV can establish
about external state or effects after actions or direct inspection.

Key Principles:
- S30 §5: Distinguish action execution status from observed external
  consequence.
- S30 §12: Unknown observation must remain unknown. Lack of evidence
  is not a negative observation.
- S30 §13: ActionResult answers "what happened during execution";
  Observation answers "what can NAV establish about the resulting
  external state."
- S30 §19: No automatic action loop. Observation does not trigger
  Action.
- S30 §22: Contradictory observations are preserved, not silently
  resolved.
- S30 §23: An observation never claims more than the source
  establishes.
- S30 §24: Observed data is data, not instructions.
- Frozen dataclasses enforce immutability across capability boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any


class ObservationSource(str, Enum):
    """How the observation was obtained.

    DIRECT_INSPECTION: NAV directly inspected the target state.
    ACTION_RESULT:     Derived from an S29 ActionResult.
    EXTERNAL_REPORT:   Reported by an external system or API.
    LOCAL_STATE:       Read from NAV's local runtime state.
    UNKNOWN:           Source cannot be determined.
    """

    DIRECT_INSPECTION = "direct_inspection"
    ACTION_RESULT = "action_result"
    EXTERNAL_REPORT = "external_report"
    LOCAL_STATE = "local_state"
    UNKNOWN = "unknown"


class ObservationState(str, Enum):
    """Epistemological status of an observation.

    OBSERVED:     State was successfully established.
    NOT_OBSERVED: Target was inspected; expected state was not found.
                  Distinct from UNKNOWN — NAV looked and confirmed
                  absence.
    CONFLICTING:  Multiple observations of the same subject disagree.
    UNKNOWN:      State could not be established. NAV did not or
                  could not inspect the target. NOT the same as
                  NOT_OBSERVED.
    INVALID:      Observation data is malformed or unverifiable.
    """

    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"
    INVALID = "invalid"


@dataclass(frozen=True)
class ObservationRequest:
    """A request to observe the state of a subject.

    Attributes:
        subject: What to observe (resource identifier or description).
        source: The observation mechanism to use.
        action_id: Optional link to an S29 ActionResult.
        parameters: Observation-specific parameters (frozen).
        requester_id: Identity of who/what requested the observation.
        metadata: Optional extension data (frozen).
    """

    subject: str
    source: ObservationSource
    action_id: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    requester_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.subject or not self.subject.strip():
            raise ValueError("ObservationRequest.subject must not be empty.")
        if not isinstance(self.source, ObservationSource):
            raise ValueError(
                f"ObservationRequest.source must be an ObservationSource, "
                f"got {type(self.source).__name__}."
            )
        if not isinstance(self.parameters, MappingProxyType):
            object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class Observation:
    """A structured representation of what NAV has established.

    Attributes:
        observation_id: Unique identifier for this observation.
        source: How the observation was obtained.
        subject: What was observed.
        observed_state: What was established about the subject.
        state: Epistemological status of this observation.
        observed_at: When the observation was made (UTC).
        action_id: Optional link to an S29 action.
        provenance: Human-readable provenance description.
        metadata: Optional extension data (frozen).
    """

    observation_id: str
    source: ObservationSource
    subject: str
    observed_state: str
    state: ObservationState
    observed_at: datetime
    action_id: str | None = None
    provenance: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id or not self.observation_id.strip():
            raise ValueError("Observation.observation_id must not be empty.")
        if not self.subject or not self.subject.strip():
            raise ValueError("Observation.subject must not be empty.")
        if not self.observed_state or not self.observed_state.strip():
            raise ValueError("Observation.observed_state must not be empty.")
        if not isinstance(self.state, ObservationState):
            raise ValueError(
                f"Observation.state must be an ObservationState, got {type(self.state).__name__}."
            )
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))


@dataclass(frozen=True)
class ObservationResult:
    """The outcome of an observation attempt.

    Attributes:
        observation_id: Unique identifier for this observation attempt.
        subject: The subject that was (or was to be) observed.
        state: Overall epistemological status.
        observation: The structured observation, if one was produced.
                     None if the observation process itself was invalid.
        message: Human-readable description of what happened.
        observed_at: When the observation was made (None if invalid).
        metadata: Optional extension data (frozen).
    """

    observation_id: str
    subject: str
    state: ObservationState
    observation: Observation | None = None
    message: str = ""
    observed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id or not self.observation_id.strip():
            raise ValueError("ObservationResult.observation_id must not be empty.")
        if not self.subject or not self.subject.strip():
            raise ValueError("ObservationResult.subject must not be empty.")
        if not self.message or not self.message.strip():
            raise ValueError("ObservationResult.message must not be empty.")
        if not isinstance(self.metadata, MappingProxyType):
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
