from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentStep:
    kind: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)
    output: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "name": self.name, "input": self.input, "output": self.output}


class AgentBackend:
    def __init__(self, app):
        self.app = app

    def run(self, goal: str, *, tools: list[dict[str, Any]] | None = None, llm_provider: str = "echo", model: str = "echo-local") -> dict[str, Any]:
        steps: list[AgentStep] = []
        prompt = [{"role": "user", "content": goal}]
        llm = self.app.llm.complete(prompt, provider=llm_provider, model=model)
        steps.append(AgentStep("llm", llm_provider, {"model": model, "goal": goal}, llm.to_dict()))
        for tool in tools or []:
            if tool.get("type") == "plugin":
                result = self.app.plugins.call(tool["name"], tool.get("action", "run"), **tool.get("args", {}))
                steps.append(AgentStep("plugin", tool["name"], tool, result.to_dict()))
            elif tool.get("type") == "command":
                result = self.app.tools.run(tool.get("command", []), timeout=tool.get("timeout"))
                steps.append(AgentStep("command", tool.get("command", [""])[0], tool, result.to_dict()))
        return {"goal": goal, "steps": [step.to_dict() for step in steps]}
