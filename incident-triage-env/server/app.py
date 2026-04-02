"""
FastAPI application for the IT Incident Triage Environment.

Exposes the environment over HTTP with endpoints for:
- POST /reset       — Reset environment for new episode
- POST /step        — Execute an action
- GET  /state       — Get current state
- GET  /health      — Health check
- GET  /tasks       — List available tasks with action schemas
- POST /grader      — Get grader score for completed episode
- POST /baseline    — Run baseline inference on all tasks
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.incident_env import IncidentTriageEnvironment
from server.tasks import TASKS, grade
from models import IncidentAction


# ── Pydantic request/response models for the API ─────────────────────────────

class ResetRequest(BaseModel):
    seed: Optional[int] = None
    task_id: Optional[str] = "task_1_classify"
    incident_index: Optional[int] = None
    episode_id: Optional[str] = None


class StepRequest(BaseModel):
    action_type: str
    severity: Optional[str] = None
    root_cause: Optional[str] = None
    explanation: Optional[str] = None
    team: Optional[str] = None
    remediation: Optional[str] = None
    message: Optional[str] = None
    audience: Optional[str] = None
    reason: Optional[str] = None
    summary: Optional[str] = None


class GraderRequest(BaseModel):
    """Optional — if empty, grades the current episode."""
    pass


class BaselineRequest(BaseModel):
    """Trigger baseline inference."""
    api_key: Optional[str] = None  # Override env var


# ── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="IT Incident Triage Environment",
    description=(
        "An OpenEnv environment that simulates IT incident triage and resolution. "
        "Train AI agents to classify severity, diagnose root causes, apply remediations, "
        "and resolve incidents end-to-end."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance
env = IncidentTriageEnvironment()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "environment": "incident_triage_env", "version": "1.0.0"}


@app.post("/reset")
async def reset(request: Optional[ResetRequest] = None):
    """Reset the environment for a new episode."""
    try:
        if request is None:
            request = ResetRequest()
        obs = env.reset(
            seed=request.seed,
            task_id=request.task_id,
            incident_index=request.incident_index,
            episode_id=request.episode_id,
        )
        return {"observation": asdict(obs)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/step")
async def step(request: StepRequest):
    """Execute an action step in the environment."""
    action_dict = request.model_dump(exclude_none=True)
    obs = env.step(action_dict)
    return {
        "observation": asdict(obs),
        "reward": obs.reward,
        "done": obs.done,
        "info": {
            "step_count": env.state.step_count,
            "total_reward": env.state.total_reward,
            "grader_score": env.state.grader_score,
        },
    }


@app.get("/state")
async def get_state():
    """Get the current environment state."""
    return {"state": asdict(env.state)}


@app.get("/tasks")
async def list_tasks():
    """List all available tasks with their action schemas."""
    tasks_out = []
    for tid, task in TASKS.items():
        tasks_out.append({
            "task_id": task.task_id,
            "name": task.name,
            "difficulty": task.difficulty,
            "description": task.description,
            "max_steps": task.max_steps,
            "action_fields": task.action_fields,
            "grading_criteria": task.grading_criteria,
        })
    return {"tasks": tasks_out}


@app.post("/grader")
async def run_grader():
    """
    Get the grader score for the current/completed episode.
    Returns the deterministic grading score in [0.0, 1.0].
    """
    if env.current_incident is None:
        raise HTTPException(status_code=400, detail="No episode in progress. Call /reset first.")

    score = grade(env.state.task_id, env.state, env.current_incident)
    return {
        "task_id": env.state.task_id,
        "score": score,
        "done": env.is_done,
        "step_count": env.state.step_count,
        "details": {
            "severity_classified": env.state.severity_classified,
            "severity_value": env.state.severity_value,
            "diagnosed": env.state.diagnosed,
            "diagnosis_value": env.state.diagnosis_value,
            "team_assigned": env.state.team_assigned,
            "team_value": env.state.team_value,
            "remediation_applied": env.state.remediation_applied,
            "remediation_value": env.state.remediation_value,
            "communicated": env.state.communicated,
            "resolved": env.state.resolved,
        },
    }


@app.post("/baseline")
async def run_baseline():
    """
    Run the baseline inference script against all 3 tasks.
    Uses a heuristic agent (not the OpenAI API) for reproducibility without API keys.
    Returns deterministic scores.
    """
    from server.baseline_agent import run_heuristic_baseline

    results = run_heuristic_baseline()
    return {"baseline_results": results}


# ── Main entry point ──────────────────────────────────────────────────────────

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
