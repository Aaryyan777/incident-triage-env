"""
Task definitions and graders for the IT Incident Triage Environment.

Three tasks with increasing difficulty:
  Task 1 (Easy):   Severity Classification & Team Assignment
  Task 2 (Medium): Root Cause Diagnosis
  Task 3 (Hard):   Full Incident Resolution
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TaskDefinition:
    """Definition of a task with grading criteria."""
    task_id: str
    name: str
    difficulty: str
    description: str
    max_steps: int
    action_fields: Dict[str, str]  # field_name -> description
    grading_criteria: Dict[str, float]  # criterion -> weight


# ── Task Definitions ──────────────────────────────────────────────────────────

TASKS: Dict[str, TaskDefinition] = {
    "task_1_classify": TaskDefinition(
        task_id="task_1_classify",
        name="Severity Classification & Team Assignment",
        difficulty="easy",
        description=(
            "Given an IT incident with symptoms, logs, and metrics, correctly classify "
            "the incident severity (SEV1–SEV4) and assign it to the correct response team. "
            "You have up to 5 steps. Use the 'classify_severity' and 'assign_team' actions."
        ),
        max_steps=5,
        action_fields={
            "classify_severity": "Set severity to one of: SEV1, SEV2, SEV3, SEV4",
            "assign_team": "Assign to one of: platform, database, networking, security, application, infrastructure",
        },
        grading_criteria={
            "severity_accuracy": 0.50,
            "team_accuracy": 0.50,
        },
    ),
    "task_2_diagnose": TaskDefinition(
        task_id="task_2_diagnose",
        name="Root Cause Diagnosis",
        difficulty="medium",
        description=(
            "Classify the incident severity, identify the root cause, provide an explanation, "
            "and assign the correct team. You have up to 10 steps. Use 'classify_severity', "
            "'diagnose', and 'assign_team' actions."
        ),
        max_steps=10,
        action_fields={
            "classify_severity": "Set severity to one of: SEV1, SEV2, SEV3, SEV4",
            "diagnose": "Identify root cause (bad_deployment, infrastructure_failure, config_change, traffic_spike, dependency_outage, memory_leak, security_breach, database_corruption, certificate_expiry, dns_misconfiguration) and provide explanation",
            "assign_team": "Assign to correct team",
        },
        grading_criteria={
            "severity_accuracy": 0.20,
            "root_cause_accuracy": 0.40,
            "explanation_quality": 0.20,
            "team_accuracy": 0.20,
        },
    ),
    "task_3_resolve": TaskDefinition(
        task_id="task_3_resolve",
        name="Full Incident Resolution",
        difficulty="hard",
        description=(
            "Handle the incident end-to-end: classify severity, diagnose root cause, "
            "assign to the correct team, apply the right remediation action, communicate "
            "status to stakeholders, and close the incident with a resolution summary. "
            "You may also consult specialists or hand off to other teams. "
            "You have up to 20 steps."
        ),
        max_steps=20,
        action_fields={
            "classify_severity": "Set severity (SEV1–SEV4)",
            "diagnose": "Identify root cause and explain",
            "assign_team": "Assign to correct team",
            "remediate": "Apply remediation (rollback_deploy, restart_service, scale_horizontally, fix_config, failover_db, flush_cache, block_traffic, rotate_credentials)",
            "communicate": "Send status update with message and audience (engineering/management/customers)",
            "resolve": "Close incident with resolution summary",
            "request_specialist": "Consult a specialist team for expert input",
            "handoff": "Hand off incident ownership to another team",
        },
        grading_criteria={
            "severity_accuracy": 0.10,
            "root_cause_accuracy": 0.15,
            "remediation_accuracy": 0.20,
            "communication_quality": 0.10,
            "resolution_quality": 0.10,
            "postmortem_quality": 0.10,
            "coordination_quality": 0.05,
            "time_efficiency": 0.10,
            "cascade_avoidance": 0.10,
        },
    ),
}


# ── Grader Functions ──────────────────────────────────────────────────────────

def _keyword_overlap(text: str, keywords: List[str]) -> float:
    """Calculate keyword overlap score between text and keywords."""
    if not text or not keywords:
        return 0.0
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return min(1.0, matches / max(1, len(keywords)))


def grade_task_1(state: Any, incident: Any) -> float:
    """
    Grade Task 1: Severity Classification & Team Assignment.
    Returns score in [0.0, 1.0].
    """
    score = 0.0

    # Severity accuracy (0.5)
    if state.severity_classified:
        if state.severity_value and state.severity_value.upper() == incident.severity.upper():
            score += 0.50
        elif state.severity_value:
            # Partial credit for being one level off
            sev_order = {"SEV1": 1, "SEV2": 2, "SEV3": 3, "SEV4": 4}
            actual = sev_order.get(incident.severity.upper(), 0)
            guessed = sev_order.get(state.severity_value.upper(), 0)
            if actual and guessed:
                diff = abs(actual - guessed)
                if diff == 1:
                    score += 0.25  # One level off
                elif diff == 2:
                    score += 0.10  # Two levels off

    # Team accuracy (0.5)
    if state.team_assigned:
        if state.team_value and state.team_value.lower() == incident.correct_team.lower():
            score += 0.50
        elif state.team_value:
            # Small partial credit for reasonable but wrong team
            score += 0.10

    return round(min(1.0, max(0.0, score)), 4)


def grade_task_2(state: Any, incident: Any) -> float:
    """
    Grade Task 2: Root Cause Diagnosis.
    Returns score in [0.0, 1.0].
    """
    score = 0.0

    # Severity accuracy (0.2)
    if state.severity_classified:
        if state.severity_value and state.severity_value.upper() == incident.severity.upper():
            score += 0.20
        elif state.severity_value:
            sev_order = {"SEV1": 1, "SEV2": 2, "SEV3": 3, "SEV4": 4}
            actual = sev_order.get(incident.severity.upper(), 0)
            guessed = sev_order.get(state.severity_value.upper(), 0)
            if actual and guessed and abs(actual - guessed) == 1:
                score += 0.10

    # Root cause accuracy (0.4)
    if state.diagnosed:
        if state.diagnosis_value and state.diagnosis_value.lower() == incident.root_cause.lower():
            score += 0.40
        elif state.diagnosis_value:
            # Partial credit for related root causes
            related_causes = {
                "bad_deployment": ["config_change"],
                "config_change": ["bad_deployment", "dns_misconfiguration"],
                "infrastructure_failure": ["database_corruption"],
                "memory_leak": ["infrastructure_failure"],
                "certificate_expiry": ["config_change", "security_breach"],
                "dns_misconfiguration": ["config_change", "infrastructure_failure"],
                "security_breach": ["traffic_spike"],
                "traffic_spike": ["dependency_outage"],
            }
            related = related_causes.get(incident.root_cause.lower(), [])
            if state.diagnosis_value.lower() in related:
                score += 0.15

    # Explanation quality (0.2) — keyword match against incident field
    explanation_keywords = [
        incident.service,
        incident.root_cause.replace("_", " "),
        incident.severity,
    ]
    # Add symptom keywords
    for symptom in incident.symptoms[:2]:
        for word in symptom.split()[:3]:
            if len(word) > 4:
                explanation_keywords.append(word.lower())

    if hasattr(state, 'actions_taken'):
        explanation_text = " ".join(state.actions_taken)
        explanation_score = _keyword_overlap(explanation_text, explanation_keywords)
        score += 0.20 * explanation_score

    # Team accuracy (0.2)
    if state.team_assigned:
        if state.team_value and state.team_value.lower() == incident.correct_team.lower():
            score += 0.20
        elif state.team_value:
            score += 0.05

    return round(min(1.0, max(0.0, score)), 4)


def _grade_postmortem(summary: str, incident: Any) -> float:
    """Grade resolution summary quality (0.0–1.0)."""
    if not summary:
        return 0.0
    score = 0.0
    summary_lower = summary.lower()

    # 1. Length check (0.15) — summaries should be substantive
    word_count = len(summary.split())
    if word_count >= 30:
        score += 0.15
    elif word_count >= 15:
        score += 0.08

    # 2. Mentions root cause (0.25)
    root_cause_terms = incident.root_cause.replace("_", " ").lower()
    if root_cause_terms in summary_lower:
        score += 0.25
    elif any(w in summary_lower for w in root_cause_terms.split()):
        score += 0.10

    # 3. Mentions remediation taken (0.25)
    remediation_terms = incident.correct_remediation.replace("_", " ").lower()
    if remediation_terms in summary_lower:
        score += 0.25
    elif any(w in summary_lower for w in remediation_terms.split()):
        score += 0.10

    # 4. Mentions affected service (0.15)
    service_name = incident.service.replace("-", " ").lower()
    if service_name in summary_lower or incident.service.lower() in summary_lower:
        score += 0.15

    # 5. Mentions prevention/follow-up (0.10)
    prevention_terms = ["prevent", "follow-up", "follow up", "action item",
                        "monitoring", "alert", "future", "avoid", "improve"]
    if any(t in summary_lower for t in prevention_terms):
        score += 0.10

    # 6. Structure bonus (0.10) — has sections or bullet points
    if any(marker in summary for marker in ["- ", "* ", "1.", "Root Cause:", "Impact:", "\n"]):
        score += 0.10

    return min(score, 1.0)


def grade_task_3(state: Any, incident: Any) -> float:
    """
    Grade Task 3: Full Incident Resolution.
    Returns score in [0.0, 1.0].
    """
    score = 0.0

    # Severity accuracy (0.10)
    if state.severity_classified:
        if state.severity_value and state.severity_value.upper() == incident.severity.upper():
            score += 0.10

    # Root cause accuracy (0.15)
    if state.diagnosed:
        if state.diagnosis_value and state.diagnosis_value.lower() == incident.root_cause.lower():
            score += 0.15
        elif state.diagnosis_value:
            related_causes = {
                "bad_deployment": ["config_change"],
                "config_change": ["bad_deployment", "dns_misconfiguration"],
                "infrastructure_failure": ["database_corruption"],
                "memory_leak": ["infrastructure_failure"],
            }
            related = related_causes.get(incident.root_cause.lower(), [])
            if state.diagnosis_value.lower() in related:
                score += 0.06

    # Remediation accuracy (0.20)
    if state.remediation_applied:
        if state.remediation_value and state.remediation_value.lower() == incident.correct_remediation.lower():
            score += 0.20
        elif state.remediation_value:
            reasonable_remediations = {
                "rollback_deploy": ["restart_service", "fix_config"],
                "restart_service": ["scale_horizontally"],
                "scale_horizontally": ["restart_service"],
                "fix_config": ["rollback_deploy", "restart_service"],
                "failover_db": ["restart_service"],
                "block_traffic": ["scale_horizontally"],
                "rotate_credentials": ["fix_config"],
                "flush_cache": ["restart_service"],
            }
            reasonable = reasonable_remediations.get(incident.correct_remediation.lower(), [])
            if state.remediation_value.lower() in reasonable:
                score += 0.08

    # Communication quality (0.10)
    if state.communicated:
        score += 0.07
        action_text = " ".join(state.actions_taken).lower()
        if incident.service.lower() in action_text:
            score += 0.015
        if any(sev in action_text for sev in ["sev1", "sev2", "sev3", "sev4"]):
            score += 0.015

    # Resolution quality (0.10)
    if state.resolved:
        score += 0.07
        action_text = " ".join(state.actions_taken).lower()
        if incident.root_cause.replace("_", " ").lower() in action_text:
            score += 0.015
        if incident.correct_remediation.replace("_", " ").lower() in action_text:
            score += 0.015

    # Postmortem quality (0.10) — NLP-based grading of resolution summary
    summary = getattr(state, 'resolution_summary', '')
    postmortem_score = _grade_postmortem(summary, incident)
    score += 0.10 * postmortem_score

    # Coordination quality (0.05) — bonus for consulting specialists
    if getattr(state, 'specialist_consulted', False):
        coord_score = getattr(state, 'coordination_score', 0.0)
        score += 0.05 * coord_score

    # Time efficiency (0.10)
    task = TASKS["task_3_resolve"]
    if state.resolved or state.step_count > 0:
        max_steps = task.max_steps
        efficiency = max(0.0, 1.0 - (state.step_count / max_steps))
        score += 0.10 * efficiency

    # Cascade avoidance (0.10) — penalize for letting cascades fire
    cascade_count = getattr(state, 'cascade_count', 0)
    if cascade_count == 0:
        score += 0.10  # Full credit for no cascades
    elif cascade_count == 1:
        score += 0.05  # Partial credit
    # 0 credit for 2+ cascades

    return round(min(1.0, max(0.0, score)), 4)


GRADERS = {
    "task_1_classify": grade_task_1,
    "task_2_diagnose": grade_task_2,
    "task_3_resolve": grade_task_3,
}


def grade(task_id: str, state: Any, incident: Any) -> float:
    """Grade an episode for the given task. Returns score in [0.0, 1.0]."""
    grader = GRADERS.get(task_id)
    if grader is None:
        raise ValueError(f"Unknown task: {task_id}. Available: {list(GRADERS.keys())}")
    return grader(state, incident)

