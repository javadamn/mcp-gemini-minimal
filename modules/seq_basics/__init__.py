"""Example module: seq_basics

This is the "starter example" module. Teams can copy this module into a new
folder (or start from the team_template module) and then add their own tools,
resources, and prompts.
"""

from __future__ import annotations

from .tools import register_tools
from .resources import register_resources

# Prompts are optional. We keep the starter minimal: no prompts by default.
def register_prompts(mcp) -> None:
    return
