"""Exception types used to normalise tool failures inside the agent loop."""
from __future__ import annotations


class ToolUnavailable(Exception):
    """The backing source cannot be reached (down, refused connection, ...)."""


class ToolTimeout(Exception):
    """The tool did not answer within the per-tool deadline."""


class MalformedToolOutput(Exception):
    """The source answered, but not with the shape the application expects."""
