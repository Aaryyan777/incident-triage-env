"""
Pydantic models for the IT Incident Triage & Resolution Environment.

Defines typed Action, Observation, and State models for the OpenEnv spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class Severity(str, Enum):
    SEV1 = "SEV1"  # Critical – full outage
    SEV2 = "SEV2"  # Major – significant degradation
    SEV3 = "SEV3"  # Minor – limited impact
    SEV4 = "SEV4"  # Low – cosmetic / no user impact


class ActionType(str, Enum):
    CLASSIFY_SEVERITY = "classify_severity"
    DIAGNOSE = "diagnose"
    ASSIGN_TEAM = "assign_team"
    REMEDIATE = "remediate"
    COMMUNICATE = "communicate"
    ESCALATE = "escalate"
    RESOLVE = "resolve"
    REQUEST_SPECIALIST = "request_specialist"
    HANDOFF = "handoff"


class Team(str, Enum):
    PLATFORM = "platform"
    DATABASE = "database"
    NETWORKING = "networking"
    SECURITY = "security"
    APPLICATION = "application"
    INFRASTRUCTURE = "infrastructure"
    ON_CALL_LEAD = "on_call_lead"


class RemediationAction(str, Enum):
    ROLLBACK_DEPLOY = "rollback_deploy"
    RESTART_SERVICE = "restart_service"
    SCALE_HORIZONTALLY = "scale_horizontally"
    FIX_CONFIG = "fix_config"
    FAILOVER_DB = "failover_db"
    FLUSH_CACHE = "flush_cache"
    BLOCK_TRAFFIC = "block_traffic"
    ROTATE_CREDENTIALS = "rotate_credentials"


class RootCause(str, Enum):
    BAD_DEPLOYMENT = "bad_deployment"
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"
    CONFIG_CHANGE = "config_change"
    TRAFFIC_SPIKE = "traffic_spike"
    DEPENDENCY_OUTAGE = "dependency_outage"
    MEMORY_LEAK = "memory_leak"
    SECURITY_BREACH = "security_breach"
    DATABASE_CORRUPTION = "database_corruption"
    CERTIFICATE_EXPIRY = "certificate_expiry"
    DNS_MISCONFIGURATION = "dns_misconfiguration"


# ── Action Model ──────────────────────────────────────────────────────────────

@dataclass
class IncidentAction:
    """Action the agent takes during incident response."""
    action_type: str  # One of ActionType values
    severity: Optional[str] = None  # For classify_severity
    root_cause: Optional[str] = None  # For diagnose
    explanation: Optional[str] = None  # For diagnose
    team: Optional[str] = None  # For assign_team
    remediation: Optional[str] = None  # For remediate
    message: Optional[str] = None  # For communicate
    audience: Optional[str] = None  # For communicate (engineering/management/customers)
    reason: Optional[str] = None  # For escalate
    summary: Optional[str] = None  # For resolve


# ── Observation Model ─────────────────────────────────────────────────────────

@dataclass
class IncidentObservation:
    """Observation returned to the agent after each step."""
    incident_id: str = ""
    incident_title: str = ""
    incident_description: str = ""
    service_affected: str = ""
    symptoms: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    affected_users: int = 0
    timeline: List[str] = field(default_factory=list)
    available_actions: List[str] = field(default_factory=list)
    hints: List[str] = field(default_factory=list)
    elapsed_minutes: float = 0.0
    step_feedback: str = ""
    done: bool = False
    reward: float = 0.0
    task_id: str = ""
    task_description: str = ""


# ── State Model ───────────────────────────────────────────────────────────────

@dataclass
class IncidentState:
    """Internal state of the environment."""
    episode_id: str = ""
    step_count: int = 0
    task_id: str = ""
    incident_id: str = ""
    severity_classified: bool = False
    severity_value: Optional[str] = None
    diagnosed: bool = False
    diagnosis_value: Optional[str] = None
    team_assigned: bool = False
    team_value: Optional[str] = None
    remediation_applied: bool = False
    remediation_value: Optional[str] = None
    communicated: bool = False
    escalated: bool = False
    resolved: bool = False
    total_reward: float = 0.0
    actions_taken: List[str] = field(default_factory=list)
    grader_score: Optional[float] = None
    # Dynamic incident tracking
    cascade_count: int = 0
    cascades_fired: List[str] = field(default_factory=list)
    # Multi-agent coordination
    specialist_consulted: bool = False
    specialist_team: Optional[str] = None
    specialist_response: str = ""
    handoff_team: Optional[str] = None
    coordination_score: float = 0.0
    # Postmortem
    resolution_summary: str = ""
