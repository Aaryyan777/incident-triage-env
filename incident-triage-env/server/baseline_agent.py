"""
Heuristic baseline agent for deterministic, reproducible scoring.

This agent uses simple keyword-matching heuristics on the incident data
to make decisions. It's used by the /baseline endpoint for reproducible scores
without requiring an API key.
"""

from __future__ import annotations

import sys
import os
from dataclasses import asdict
from typing import Any, Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from server.incident_env import IncidentTriageEnvironment
from server.tasks import TASKS, grade


def _heuristic_classify_severity(obs: Dict[str, Any]) -> str:
    """Heuristic severity classification based on error rate and affected users."""
    metrics = obs.get("metrics", {})
    error_rate = metrics.get("error_rate_pct", 0)
    affected = obs.get("affected_users", 0)

    if error_rate >= 80 or affected >= 50000:
        return "SEV1"
    elif error_rate >= 25 or affected >= 10000:
        return "SEV2"
    elif error_rate >= 5 or affected >= 1000:
        return "SEV3"
    else:
        return "SEV4"


def _heuristic_diagnose(obs: Dict[str, Any]) -> tuple:
    """Heuristic root cause detection based on log keyword matching."""
    logs_text = " ".join(obs.get("logs", [])).lower()
    desc = obs.get("incident_description", "").lower()
    combined = logs_text + " " + desc

    if "deploy" in combined or "canary" in combined:
        return "bad_deployment", "Recent deployment correlates with the incident timeline."
    elif "certificate" in combined or "ssl" in combined or "tls" in combined:
        return "certificate_expiry", "TLS/SSL certificate issues detected in logs."
    elif "dns" in combined or "coredns" in combined or "servfail" in combined:
        return "dns_misconfiguration", "DNS resolution failures detected."
    elif "oom" in combined or "memory" in combined or "heap" in combined or "gc pause" in combined:
        return "memory_leak", "Memory-related issues found in logs."
    elif "credential" in combined or "stuffing" in combined or "attack" in combined:
        return "security_breach", "Security threat pattern detected."
    elif "traffic" in combined or "bot" in combined or "spike" in combined and "rps" in combined:
        return "traffic_spike", "Abnormal traffic patterns detected."
    elif "stripe" in combined or "webhook" in combined or "third-party" in combined:
        return "dependency_outage", "External dependency failure detected."
    elif "disk" in combined or "wal" in combined or "no space" in combined or "notready" in combined:
        return "infrastructure_failure", "Infrastructure-level failure detected."
    elif "config" in combined or "configmap" in combined or "oidc" in combined or "cache purge" in combined:
        return "config_change", "Configuration change correlating with incident."
    else:
        return "infrastructure_failure", "Unable to determine specific cause; defaulting to infrastructure."


def _heuristic_assign_team(obs: Dict[str, Any]) -> str:
    """Heuristic team assignment based on service name."""
    service = obs.get("service_affected", "").lower()

    if "db" in service or "postgres" in service or "redis" in service:
        return "database"
    elif "dns" in service or "cdn" in service:
        return "networking"
    elif "auth" in service or "payment" in service or "ssl" in service or "cert" in service:
        return "security"
    elif "k8s" in service or "kubernetes" in service or "node" in service:
        return "infrastructure"
    elif "api" in service or "gateway" in service or "stripe" in service:
        return "platform"
    elif "user" in service or "order" in service or "kafka" in service or "airflow" in service or "analytics" in service:
        return "application"
    else:
        return "platform"


def _heuristic_remediate(root_cause: str) -> str:
    """Heuristic remediation based on root cause."""
    mapping = {
        "bad_deployment": "rollback_deploy",
        "infrastructure_failure": "restart_service",
        "config_change": "fix_config",
        "traffic_spike": "block_traffic",
        "dependency_outage": "scale_horizontally",
        "memory_leak": "restart_service",
        "security_breach": "block_traffic",
        "database_corruption": "failover_db",
        "certificate_expiry": "rotate_credentials",
        "dns_misconfiguration": "fix_config",
    }
    return mapping.get(root_cause, "restart_service")


def run_heuristic_baseline() -> List[Dict[str, Any]]:
    """Run the heuristic baseline agent on all 3 tasks across multiple incidents."""
    results = []

    for task_id in TASKS:
        task = TASKS[task_id]
        task_scores = []

        # Test on incidents 0–14 with fixed seeds for reproducibility
        for incident_idx in range(15):
            env = IncidentTriageEnvironment()
            seed = 1000 + incident_idx
            obs = env.reset(seed=seed, task_id=task_id, incident_index=incident_idx)
            obs_dict = asdict(obs)

            # Task 1: classify + assign
            severity = _heuristic_classify_severity(obs_dict)
            env.step({"action_type": "classify_severity", "severity": severity})

            team = _heuristic_assign_team(obs_dict)
            env.step({"action_type": "assign_team", "team": team})

            if task_id in ("task_2_diagnose", "task_3_resolve"):
                root_cause, explanation = _heuristic_diagnose(obs_dict)
                env.step({
                    "action_type": "diagnose",
                    "root_cause": root_cause,
                    "explanation": explanation,
                })

            if task_id == "task_3_resolve":
                remediation = _heuristic_remediate(root_cause)
                env.step({
                    "action_type": "remediate",
                    "remediation": remediation,
                })

                env.step({
                    "action_type": "communicate",
                    "message": f"Incident {obs_dict['incident_id']} on {obs_dict['service_affected']}: severity {severity}. Root cause: {root_cause}. Remediation: {remediation} applied.",
                    "audience": "engineering",
                })

                env.step({
                    "action_type": "resolve",
                    "summary": f"Resolved {obs_dict['incident_title']}. Root cause was {root_cause.replace('_', ' ')}. Applied {remediation.replace('_', ' ')} to remediate. Service {obs_dict['service_affected']} restored.",
                })

            score = grade(task_id, env.state, env.current_incident)
            task_scores.append(score)

        avg_score = round(sum(task_scores) / len(task_scores), 4)
        results.append({
            "task_id": task_id,
            "task_name": task.name,
            "difficulty": task.difficulty,
            "average_score": avg_score,
            "min_score": round(min(task_scores), 4),
            "max_score": round(max(task_scores), 4),
            "individual_scores": task_scores,
        })

    return results
