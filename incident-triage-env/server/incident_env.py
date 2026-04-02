"""
IT Incident Triage & Resolution Environment.

Core environment implementing the OpenEnv spec with step(), reset(), state().
Simulates realistic IT incident response workflow.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .incidents import IncidentScenario, generate_incident, get_incident_count
from .tasks import TASKS, grade

# Import models — support both in-repo and standalone
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import (
    ActionType,
    IncidentAction,
    IncidentObservation,
    IncidentState,
)


class IncidentTriageEnvironment:
    """
    IT Incident Triage & Resolution Environment.

    Simulates real-world IT incident response where an agent must:
    - Classify incident severity (SEV1–SEV4)
    - Diagnose root cause
    - Assign to the correct response team
    - Apply appropriate remediation
    - Communicate status to stakeholders
    - Close the incident with a resolution summary

    Supports 3 tasks with increasing difficulty.
    """

    def __init__(self) -> None:
        self._state = IncidentState(episode_id=str(uuid4()))
        self._incident: Optional[IncidentScenario] = None
        self._task_id: str = "task_1_classify"
        self._done: bool = False
        self._total_reward: float = 0.0
        self._timeline: List[str] = []
        self._seed: Optional[int] = None

    def reset(
        self,
        seed: Optional[int] = None,
        task_id: Optional[str] = None,
        incident_index: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> IncidentObservation:
        """
        Reset the environment for a new episode.

        Args:
            seed: Random seed for reproducibility
            task_id: Which task to run (task_1_classify, task_2_diagnose, task_3_resolve)
            incident_index: Specific incident scenario to use (0-14)
            episode_id: Optional episode ID

        Returns:
            Initial observation with incident details
        """
        # Set task
        if task_id and task_id in TASKS:
            self._task_id = task_id
        elif task_id:
            raise ValueError(f"Unknown task_id: {task_id}. Available: {list(TASKS.keys())}")

        task = TASKS[self._task_id]
        self._seed = seed

        # Generate incident
        self._incident = generate_incident(seed=seed, incident_index=incident_index)
        self._done = False
        self._total_reward = 0.0
        self._timeline = []

        # Reset state
        self._state = IncidentState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_id=self._task_id,
            incident_id=self._incident.incident_id,
        )

        # Determine hints based on difficulty
        if task.difficulty == "easy":
            hints = self._incident.hints_easy
        elif task.difficulty == "medium":
            hints = self._incident.hints_medium
        else:
            hints = self._incident.hints_hard

        # Determine available actions based on task
        available_actions = list(task.action_fields.keys())

        return IncidentObservation(
            incident_id=self._incident.incident_id,
            incident_title=self._incident.title,
            incident_description=self._incident.description,
            service_affected=self._incident.service,
            symptoms=self._incident.symptoms,
            logs=self._incident.logs,
            metrics=self._incident.metrics,
            affected_users=self._incident.affected_users,
            timeline=[],
            available_actions=available_actions,
            hints=hints,
            elapsed_minutes=0.0,
            step_feedback="Incident reported. Begin triage.",
            done=False,
            reward=0.0,
            task_id=self._task_id,
            task_description=task.description,
        )

    def step(
        self,
        action: Dict[str, Any],
        **kwargs: Any,
    ) -> IncidentObservation:
        """
        Execute one step in the environment.

        Args:
            action: Dictionary with 'action_type' and relevant fields

        Returns:
            Observation with updated state, feedback, and reward
        """
        if self._done:
            return self._make_observation(
                feedback="Episode already done. Call reset() to start a new episode.",
                reward=0.0,
            )

        if self._incident is None:
            return self._make_observation(
                feedback="No incident loaded. Call reset() first.",
                reward=0.0,
            )

        task = TASKS[self._task_id]
        self._state.step_count += 1

        # Parse action
        if isinstance(action, dict):
            action_type = action.get("action_type", "")
        else:
            action_type = getattr(action, "action_type", "")

        # Validate action type
        valid_actions = list(task.action_fields.keys())
        if action_type not in [a.value if hasattr(a, 'value') else a for a in ActionType]:
            return self._make_observation(
                feedback=f"Invalid action_type: '{action_type}'. Valid types: {valid_actions}",
                reward=-0.05,
            )

        # Process action
        reward = 0.0
        feedback = ""

        if action_type == "classify_severity":
            reward, feedback = self._handle_classify_severity(action)
        elif action_type == "diagnose":
            reward, feedback = self._handle_diagnose(action)
        elif action_type == "assign_team":
            reward, feedback = self._handle_assign_team(action)
        elif action_type == "remediate":
            reward, feedback = self._handle_remediate(action)
        elif action_type == "communicate":
            reward, feedback = self._handle_communicate(action)
        elif action_type == "escalate":
            reward, feedback = self._handle_escalate(action)
        elif action_type == "resolve":
            reward, feedback = self._handle_resolve(action)
        else:
            feedback = f"Action '{action_type}' not available for task '{self._task_id}'."
            reward = -0.05

        # Time penalty per step
        time_penalty = -0.02
        reward += time_penalty
        self._total_reward += reward
        self._state.total_reward = self._total_reward

        # Record in timeline
        action_summary = f"Step {self._state.step_count}: {action_type}"
        self._timeline.append(action_summary)
        self._state.actions_taken.append(json.dumps(action) if isinstance(action, dict) else str(action))

        # Check episode end
        if self._state.step_count >= task.max_steps:
            self._done = True
            feedback += " | Max steps reached. Episode ended."

        # Auto-end for task 1 if both actions are done
        if self._task_id == "task_1_classify":
            if self._state.severity_classified and self._state.team_assigned:
                self._done = True

        # Auto-end for task 3 if resolved
        if self._task_id == "task_3_resolve" and self._state.resolved:
            self._done = True

        # Compute grader score when done
        if self._done:
            self._state.grader_score = grade(self._task_id, self._state, self._incident)
            feedback += f" | Final grader score: {self._state.grader_score}"

        return self._make_observation(feedback=feedback, reward=reward)

    def _handle_classify_severity(self, action: Dict[str, Any]) -> tuple:
        """Handle severity classification action."""
        severity = action.get("severity", "") if isinstance(action, dict) else getattr(action, "severity", "")
        severity = str(severity).upper().strip()

        valid_severities = ["SEV1", "SEV2", "SEV3", "SEV4"]
        if severity not in valid_severities:
            return -0.05, f"Invalid severity: '{severity}'. Must be one of {valid_severities}."

        if self._state.severity_classified:
            return -0.03, f"Severity already classified as {self._state.severity_value}. Cannot reclassify."

        self._state.severity_classified = True
        self._state.severity_value = severity

        correct = self._incident.severity.upper()
        if severity == correct:
            return 0.20, f"Correct! Severity classified as {severity}."
        else:
            sev_order = {"SEV1": 1, "SEV2": 2, "SEV3": 3, "SEV4": 4}
            diff = abs(sev_order[severity] - sev_order[correct])
            if diff == 1:
                return 0.05, f"Severity classified as {severity}. Close, but not quite right."
            elif diff >= 3:
                return -0.20, f"Severity classified as {severity}. This is significantly off."
            else:
                return -0.10, f"Severity classified as {severity}. Not correct."

    def _handle_diagnose(self, action: Dict[str, Any]) -> tuple:
        """Handle root cause diagnosis action."""
        root_cause = action.get("root_cause", "") if isinstance(action, dict) else getattr(action, "root_cause", "")
        explanation = action.get("explanation", "") if isinstance(action, dict) else getattr(action, "explanation", "")
        root_cause = str(root_cause).lower().strip()

        if self._state.diagnosed:
            return -0.03, f"Already diagnosed as '{self._state.diagnosis_value}'. Cannot re-diagnose."

        self._state.diagnosed = True
        self._state.diagnosis_value = root_cause

        correct = self._incident.root_cause.lower()
        if root_cause == correct:
            reward = 0.30
            feedback = f"Correct root cause identified: {root_cause}."
        else:
            # Check for related causes
            related = {
                "bad_deployment": ["config_change"],
                "config_change": ["bad_deployment", "dns_misconfiguration"],
                "infrastructure_failure": ["database_corruption"],
                "memory_leak": ["infrastructure_failure"],
                "certificate_expiry": ["config_change"],
                "security_breach": ["traffic_spike"],
            }
            if root_cause in related.get(correct, []):
                reward = 0.10
                feedback = f"Root cause identified as '{root_cause}'. Related but not the primary cause."
            else:
                reward = -0.10
                feedback = f"Root cause identified as '{root_cause}'. Incorrect diagnosis."

        # Bonus for good explanation
        if explanation and len(explanation) > 20:
            reward += 0.05
            feedback += " Good explanation provided."

        return reward, feedback

    def _handle_assign_team(self, action: Dict[str, Any]) -> tuple:
        """Handle team assignment action."""
        team = action.get("team", "") if isinstance(action, dict) else getattr(action, "team", "")
        team = str(team).lower().strip()

        valid_teams = ["platform", "database", "networking", "security", "application", "infrastructure", "on_call_lead"]
        if team not in valid_teams:
            return -0.05, f"Invalid team: '{team}'. Must be one of {valid_teams}."

        if self._state.team_assigned:
            return -0.03, f"Team already assigned: {self._state.team_value}. Cannot reassign."

        self._state.team_assigned = True
        self._state.team_value = team

        correct = self._incident.correct_team.lower()
        if team == correct:
            return 0.20, f"Correct! Incident assigned to {team} team."
        else:
            return -0.10, f"Incident assigned to {team} team. Not the optimal assignment."

    def _handle_remediate(self, action: Dict[str, Any]) -> tuple:
        """Handle remediation action."""
        remediation = action.get("remediation", "") if isinstance(action, dict) else getattr(action, "remediation", "")
        remediation = str(remediation).lower().strip()

        valid = [
            "rollback_deploy", "restart_service", "scale_horizontally",
            "fix_config", "failover_db", "flush_cache", "block_traffic", "rotate_credentials"
        ]
        if remediation not in valid:
            return -0.05, f"Invalid remediation: '{remediation}'. Must be one of {valid}."

        if self._state.remediation_applied:
            return -0.03, f"Remediation already applied: {self._state.remediation_value}."

        self._state.remediation_applied = True
        self._state.remediation_value = remediation

        correct = self._incident.correct_remediation.lower()
        if remediation == correct:
            return 0.25, f"Correct remediation applied: {remediation}. Issue being resolved."
        else:
            # Partial credit
            reasonable = {
                "rollback_deploy": ["restart_service", "fix_config"],
                "restart_service": ["scale_horizontally"],
                "scale_horizontally": ["restart_service"],
                "fix_config": ["rollback_deploy"],
                "failover_db": ["restart_service"],
                "block_traffic": ["scale_horizontally"],
                "rotate_credentials": ["fix_config"],
            }
            if remediation in reasonable.get(correct, []):
                return 0.08, f"Applied {remediation}. This helps but isn't the optimal fix."
            else:
                return -0.10, f"Applied {remediation}. This is not effective for this incident."

    def _handle_communicate(self, action: Dict[str, Any]) -> tuple:
        """Handle communication action."""
        message = action.get("message", "") if isinstance(action, dict) else getattr(action, "message", "")
        audience = action.get("audience", "") if isinstance(action, dict) else getattr(action, "audience", "")

        if not message:
            return -0.05, "Communication requires a message."

        self._state.communicated = True

        reward = 0.10
        feedback = f"Status update sent to {audience or 'stakeholders'}."

        # Bonus for mentioning relevant details
        msg_lower = str(message).lower()
        if self._incident.service.lower() in msg_lower:
            reward += 0.02
        if any(sev in msg_lower for sev in ["sev1", "sev2", "sev3", "sev4"]):
            reward += 0.02

        return reward, feedback

    def _handle_escalate(self, action: Dict[str, Any]) -> tuple:
        """Handle escalation action."""
        reason = action.get("reason", "") if isinstance(action, dict) else getattr(action, "reason", "")

        self._state.escalated = True

        # Escalation is appropriate for SEV1/SEV2
        if self._incident.severity.upper() in ["SEV1", "SEV2"]:
            return 0.05, f"Escalated to on-call lead. Reason: {reason or 'unspecified'}."
        else:
            return -0.05, f"Escalation may not be necessary for {self._incident.severity} incidents."

    def _handle_resolve(self, action: Dict[str, Any]) -> tuple:
        """Handle incident resolution action."""
        summary = action.get("summary", "") if isinstance(action, dict) else getattr(action, "summary", "")

        if not summary:
            return -0.05, "Resolution requires a summary."

        self._state.resolved = True
        self._done = True

        reward = 0.10
        feedback = "Incident marked as resolved."

        # Bonus for quality resolution summary
        summary_lower = str(summary).lower()
        if self._incident.root_cause.replace("_", " ").lower() in summary_lower:
            reward += 0.03
            feedback += " Summary mentions root cause."
        if self._incident.correct_remediation.replace("_", " ").lower() in summary_lower:
            reward += 0.02
            feedback += " Summary mentions remediation."
        if len(summary) > 50:
            reward += 0.02
            feedback += " Detailed summary provided."

        return reward, feedback

    def _make_observation(self, feedback: str, reward: float) -> IncidentObservation:
        """Create an observation from current state."""
        task = TASKS.get(self._task_id, TASKS["task_1_classify"])

        if self._incident is None:
            return IncidentObservation(
                step_feedback=feedback,
                done=self._done,
                reward=reward,
                task_id=self._task_id,
            )

        return IncidentObservation(
            incident_id=self._incident.incident_id,
            incident_title=self._incident.title,
            incident_description=self._incident.description,
            service_affected=self._incident.service,
            symptoms=self._incident.symptoms,
            logs=self._incident.logs,
            metrics=self._incident.metrics,
            affected_users=self._incident.affected_users,
            timeline=list(self._timeline),
            available_actions=list(task.action_fields.keys()),
            hints=self._incident.hints_easy if task.difficulty == "easy"
                  else self._incident.hints_medium if task.difficulty == "medium"
                  else self._incident.hints_hard,
            elapsed_minutes=self._state.step_count * 3.0,  # ~3 min per step
            step_feedback=feedback,
            done=self._done,
            reward=reward,
            task_id=self._task_id,
            task_description=task.description,
        )

    @property
    def state(self) -> IncidentState:
        """Get the current environment state."""
        return self._state

    @property
    def current_incident(self) -> Optional[IncidentScenario]:
        """Get the current incident (for grading)."""
        return self._incident

    @property
    def is_done(self) -> bool:
        """Check if the episode is done."""
        return self._done
