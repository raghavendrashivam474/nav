"""Step evaluation subsystem — S17.

DeterministicEvaluator inspects capability invocation results and
determines the appropriate next step status.

No AI dependency. Pure logic based on success flags and error content.
"""

from __future__ import annotations

from core.contracts.work import StepStatus, WorkStep
from core.log import get_logger

logger = get_logger(__name__)


class DeterministicEvaluator:
    """Evaluates step execution results deterministically."""

    def evaluate_step(
        self,
        step: WorkStep,
        result_payload: dict,
        is_success: bool,
    ) -> tuple[StepStatus, str | None]:
        """Return (new_status, error_message | None)."""
        if is_success:
            # Check for empty results that might indicate incomplete work
            if not result_payload and step.capability == "research":
                logger.info(
                    "Step %s returned empty result; marking completed with note",
                    step.step_id,
                )
            return StepStatus.COMPLETED, None

        # Failure path
        error_msg = "Step execution failed"
        if "error" in result_payload:
            error_msg = str(result_payload["error"])

        if step.retry_count < step.max_retries:
            logger.info(
                "Step %s failed but retries remain (%d/%d)",
                step.step_id,
                step.retry_count,
                step.max_retries,
            )
            return StepStatus.FAILED, error_msg

        logger.warning("Step %s failed with no retries remaining", step.step_id)
        return StepStatus.FAILED, error_msg
