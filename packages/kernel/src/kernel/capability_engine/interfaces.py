from typing import Protocol

from kernel.capability_engine.models import CapabilityContext, CapabilityResult


class CapabilityExecutor(Protocol):
    """Protocol for the physical execution of a capability."""

    async def execute(self, context: CapabilityContext) -> CapabilityResult: ...


class CapabilityResolver(Protocol):
    """Protocol for resolving the capability name to an executor."""

    async def resolve(self, capability_name: str) -> CapabilityExecutor: ...


class CapabilityMiddleware(Protocol):
    """Middleware pipeline hooks."""

    async def before_execute(self, context: CapabilityContext) -> None: ...
    async def after_execute(
        self, context: CapabilityContext, result: CapabilityResult
    ) -> CapabilityResult: ...


class CapabilityPipeline(Protocol):
    """Protocol for the composed execution pipeline."""

    def add_middleware(self, middleware: CapabilityMiddleware) -> None: ...
    async def run(
        self, context: CapabilityContext, executor: CapabilityExecutor
    ) -> CapabilityResult: ...
