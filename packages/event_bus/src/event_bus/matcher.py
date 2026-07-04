"""
Topic Matcher Abstraction.

Provides an interface for matching wildcard event topics to handler subscriptions.
This abstracts away the internal mechanism (Regex vs. Prefix Tree), allowing future scaling
without breaking the EventBus API.
"""
import re
from typing import Any, Protocol


class TopicMatcher(Protocol):
    """Protocol for event topic matching engines."""

    def is_wildcard(self, topic: str) -> bool:
        """Determines if a topic string contains wildcard characters."""
        ...

    def compile(self, pattern: str) -> Any:
        """Compiles a wildcard topic into the internal matching representation."""
        ...

    def match(self, compiled_pattern: Any, topic: str) -> bool:
        """Determines if a concrete topic string matches the compiled pattern."""
        ...


class RegexTopicMatcher:
    """
    A basic Topic Matcher implementation using Python's regular expressions.
    Converts simple wildcard strings (e.g. "agent.*.completed") into regex logic.
    """

    def is_wildcard(self, topic: str) -> bool:
        return "*" in topic

    def compile(self, pattern: str) -> re.Pattern[str]:
        # Convert simple wildcard "agent.*" into regex "^agent\..*$"
        pattern_str = "^" + pattern.replace(".", r"\.").replace("*", ".*") + "$"
        return re.compile(pattern_str)

    def match(self, compiled_pattern: re.Pattern[str], topic: str) -> bool:
        return bool(compiled_pattern.match(topic))
