"""
Telemetry

Structured logging and observability package.
"""

class Logger:
    """A basic structured logger."""
    def info(self, message: str) -> None:
        print(f"[INFO] {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {message}")
