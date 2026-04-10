"""
EnvClient for the IT Incident Triage Environment.

Provides typed client-side access to the environment via HTTP.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, Optional

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from models import IncidentAction, IncidentObservation, IncidentState


class IncidentTriageClient:
    """
    Synchronous HTTP client for the IT Incident Triage Environment.

    Usage:
        client = IncidentTriageClient("http://localhost:8000")
        obs = client.reset(task_id="task_1_classify", seed=42)
        obs = client.step({"action_type": "classify_severity", "severity": "SEV1"})
        state = client.state()
        score = client.grade()
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        if not HAS_REQUESTS:
            raise ImportError("Install 'requests' package: pip install requests")
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def health(self) -> Dict[str, Any]:
        """Check environment health."""
        resp = self.session.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def reset(
        self,
        task_id: str = "task_1_classify",
        seed: Optional[int] = None,
        incident_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Reset the environment for a new episode."""
        payload = {"task_id": task_id}
        if seed is not None:
            payload["seed"] = seed
        if incident_index is not None:
            payload["incident_index"] = incident_index

        resp = self.session.post(f"{self.base_url}/reset", json=payload)
        resp.raise_for_status()
        return resp.json()["observation"]

    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action step."""
        resp = self.session.post(f"{self.base_url}/step", json=action)
        resp.raise_for_status()
        return resp.json()

    def state(self) -> Dict[str, Any]:
        """Get current environment state."""
        resp = self.session.get(f"{self.base_url}/state")
        resp.raise_for_status()
        return resp.json()["state"]

    def tasks(self) -> list:
        """List all available tasks."""
        resp = self.session.get(f"{self.base_url}/tasks")
        resp.raise_for_status()
        return resp.json()["tasks"]

    def grade(self) -> Dict[str, Any]:
        """Get grader score for current episode."""
        resp = self.session.post(f"{self.base_url}/grader")
        resp.raise_for_status()
        return resp.json()

    def baseline(self) -> list:
        """Run baseline inference."""
        resp = self.session.post(f"{self.base_url}/baseline")
        resp.raise_for_status()
        return resp.json()["baseline_results"]

    def close(self):
        """Close the client session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
