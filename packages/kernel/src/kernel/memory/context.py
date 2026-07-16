from typing import Any


class ContextBuilderStub:
    """
    Stub for the token-budget aware ContextBuilder.
    This will be implemented in future milestones.
    """

    def build_context(self, current_memory: Any, token_budget: int) -> dict[str, Any]:
        """Builds context payload fitting the token budget."""
        return {"context": "stub_context"}
