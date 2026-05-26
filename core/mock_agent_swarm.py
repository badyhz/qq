"""Mock Agent Swarm — simulated multi-agent swarm.

Uses WorkerPool for concurrency tracking.
Supports autopilot dispatch through WorkflowScheduler.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class MockAdapter:
    def __init__(self, adapter_id: str = "mock"):
        self._id = adapter_id

    def adapter_id(self) -> str:
        return self._id


@dataclass
class SwarmAgent:
    agent_id: str
    adapter_type: str
    status: str = "idle"
    tasks_completed: int = 0
    current_task: str | None = None
    adapter: MockAdapter | None = None


class MockAgentSwarm:
    def __init__(self, size: int = 5, adapter_type: str = "mock"):
        self.agents: list[SwarmAgent] = []
        for i in range(size):
            agent = SwarmAgent(
                agent_id=f"A{i+1}",
                adapter_type=adapter_type,
                adapter=MockAdapter(adapter_id=f"{adapter_type}-{i+1}"),
            )
            self.agents.append(agent)

    def list_agents(self) -> list[SwarmAgent]:
        return list(self.agents)

    def available_agents(self) -> list[SwarmAgent]:
        return [a for a in self.agents if a.status == "idle"]

    def dispatch(self, task_id: str, prompt: str = "") -> SwarmAgent | None:
        for agent in self.agents:
            if agent.status == "idle":
                agent.status = "busy"
                agent.current_task = task_id
                return agent
        return None

    def complete(self, agent_id: str, task_id: str) -> None:
        for agent in self.agents:
            if agent.agent_id == agent_id and agent.current_task == task_id:
                agent.status = "idle"
                agent.current_task = None
                agent.tasks_completed += 1
                return

    def scale(self, new_size: int) -> None:
        current = len(self.agents)
        if new_size > current:
            for i in range(current, new_size):
                agent = SwarmAgent(
                    agent_id=f"A{i+1}",
                    adapter_type=self.agents[0].adapter_type if self.agents else "mock",
                    adapter=MockAdapter(adapter_id=f"mock-{i+1}"),
                )
                self.agents.append(agent)
        elif new_size < current:
            self.agents = self.agents[:new_size]

    def autopilot(self, tasks: list[dict], scheduler=None) -> list[dict]:
        """Auto-dispatch all tasks. Returns execution log.

        Each task dict: {"id": "...", "prompt": "...", ...}
        """
        execution_log = []
        pending = list(tasks)

        while pending:
            dispatched_any = False
            remaining = []
            for task in pending:
                agent = self.dispatch(task["id"], task.get("prompt", ""))
                if agent:
                    # Immediate simulated completion
                    self.complete(agent.agent_id, task["id"])
                    log_entry = {
                        "task": task["id"],
                        "agent": agent.agent_id,
                        "status": "completed",
                    }
                    if scheduler is not None:
                        log_entry["scheduler_step"] = True
                    execution_log.append(log_entry)
                    dispatched_any = True
                else:
                    remaining.append(task)
            pending = remaining
            if not dispatched_any:
                # All agents busy — should not happen since we complete immediately
                break

        return execution_log

    def status(self) -> dict:
        idle = sum(1 for a in self.agents if a.status == "idle")
        busy = sum(1 for a in self.agents if a.status == "busy")
        total_completed = sum(a.tasks_completed for a in self.agents)
        return {
            "total_agents": len(self.agents),
            "idle": idle,
            "busy": busy,
            "total_tasks_completed": total_completed,
        }
