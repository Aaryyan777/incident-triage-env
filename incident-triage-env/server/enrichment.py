"""
Enrichment data for incident templates: cascade events, specialist responses,
time-series metrics, and 35 new incident templates.
"""

from __future__ import annotations
from typing import Any, Dict, List


# ── Cascade Events by Template Title ─────────────────────────────────────────

CASCADE_EVENTS: Dict[str, List[Dict[str, Any]]] = {
    "API Gateway 5xx Error Spike": [
        {"trigger_step": 3, "condition": "not_remediated",
         "new_symptoms": ["Database connection pool exhausted due to retry storms"],
         "new_logs": ["[ERROR] retry-storm detected: 50k retries/s from downstream services"],
         "metric_changes": {"error_rate_pct": 60.0, "db_connections_active": 500},
         "affected_users_delta": 15000,
         "feedback": "⚠️ CASCADE: Retry storms are now overwhelming the database!"},
        {"trigger_step": 5, "condition": "not_remediated",
         "new_symptoms": ["Payment service now returning 503 — cascading failure"],
         "new_logs": ["[CRITICAL] payment-svc: Circuit breaker OPEN, all payments failing"],
         "metric_changes": {"error_rate_pct": 85.0},
         "severity_escalation": "SEV1", "affected_users_delta": 35000,
         "feedback": "🔥 CASCADE: Payment processing has failed — revenue impact accelerating!"},
    ],
    "Database Primary Node Unresponsive": [
        {"trigger_step": 3, "condition": "not_remediated",
         "new_symptoms": ["Read replicas now 2+ minutes behind — stale reads causing data inconsistency"],
         "new_logs": ["[ERROR] pg-replica-02: replication lag exceeded 120s, data drift detected"],
         "metric_changes": {"replication_lag_sec": 130},
         "affected_users_delta": 30000,
         "feedback": "⚠️ CASCADE: Read replicas are now dangerously behind — users seeing stale data!"},
    ],
    "Authentication Service Intermittent Failures": [
        {"trigger_step": 4, "condition": "not_remediated",
         "new_symptoms": ["Admin console locked out — operations team cannot access management tools"],
         "new_logs": ["[ERROR] admin-console: All admin sessions invalidated by broken OIDC config"],
         "metric_changes": {"error_rate_pct": 55.0},
         "affected_users_delta": 500,
         "feedback": "⚠️ CASCADE: Admin access is also affected — cannot manage the system!"},
    ],
    "CDN Cache Purge Storm": [
        {"trigger_step": 3, "condition": "not_remediated",
         "new_symptoms": ["Origin servers running out of memory — OOM kills starting"],
         "new_logs": ["[CRITICAL] origin-web-02: OOM killed, 3 of 5 origin pods down"],
         "metric_changes": {"origin_cpu_pct": 100, "origin_memory_pct": 100},
         "affected_users_delta": 200000,
         "feedback": "🔥 CASCADE: Origin servers are crashing under the load!"},
    ],
    "Message Queue Consumer Lag": [
        {"trigger_step": 4, "condition": "not_remediated",
         "new_symptoms": ["Order processing backlog exceeding SLA — customer complaints rising"],
         "new_logs": ["[WARN] order-svc: 500+ orders past SLA deadline, customer escalations incoming"],
         "metric_changes": {"consumer_lag_messages": 150000, "processing_latency_min": 35},
         "affected_users_delta": 5000,
         "feedback": "⚠️ CASCADE: Order backlog is growing — SLAs being breached!"},
    ],
    "SSL Certificate Expiry on Payment Gateway": [
        {"trigger_step": 2, "condition": "not_remediated",
         "new_symptoms": ["Mobile app crashing due to certificate pinning failure"],
         "new_logs": ["[ERROR] mobile-backend: 100% of mobile API calls failing — cert pin mismatch"],
         "metric_changes": {"revenue_loss_usd_per_hour": 320000},
         "affected_users_delta": 50000,
         "feedback": "🔥 CASCADE: Mobile app is now completely broken — all mobile users affected!"},
    ],
    "DNS Resolution Failures for Internal Services": [
        {"trigger_step": 4, "condition": "not_remediated",
         "new_symptoms": ["CI/CD pipeline failing — cannot resolve container registry DNS"],
         "new_logs": ["[ERROR] ci-runner: docker pull failed — DNS resolution timeout for registry.internal"],
         "metric_changes": {"dns_failure_rate_pct": 35.0},
         "affected_users_delta": 100,
         "feedback": "⚠️ CASCADE: CI/CD is down — no new deployments possible!"},
    ],
    "Memory Leak in User Profile Service": [
        {"trigger_step": 5, "condition": "not_remediated",
         "new_symptoms": ["User profile cache fully corrupted — serving wrong profiles to users"],
         "new_logs": ["[ERROR] user-prof-01: Cache corruption detected — mixing user profile data across sessions"],
         "metric_changes": {"error_rate_pct": 25.0},
         "severity_escalation": "SEV2", "affected_users_delta": 10000,
         "feedback": "🔥 CASCADE: Data integrity issue — users seeing OTHER users' profiles!"},
    ],
    "Sudden Traffic Spike from Bot Activity": [
        {"trigger_step": 3, "condition": "not_remediated",
         "new_symptoms": ["Elasticsearch cluster entering red state — indices becoming read-only"],
         "new_logs": ["[CRITICAL] elasticsearch: Cluster health RED — disk watermark exceeded"],
         "metric_changes": {"error_rate_pct": 75.0, "cpu_pct": 100},
         "affected_users_delta": 20000,
         "feedback": "🔥 CASCADE: Search backend is failing — product search completely down!"},
    ],
    "Redis Cache Cluster Split-Brain": [
        {"trigger_step": 4, "condition": "not_remediated",
         "new_symptoms": ["Shopping cart data lost for active sessions due to split-brain writes"],
         "new_logs": ["[ERROR] cart-svc: Cart data mismatch detected — user seeing empty cart after adding items"],
         "metric_changes": {"stale_reads_pct": 40.0, "write_conflicts_per_min": 200},
         "affected_users_delta": 15000,
         "feedback": "⚠️ CASCADE: Shopping carts are being corrupted — e-commerce functionality degraded!"},
    ],
    "Third-Party Payment Provider Outage": [
        {"trigger_step": 4, "condition": "not_remediated",
         "new_symptoms": ["Subscription renewal failures — users being downgraded automatically"],
         "new_logs": ["[ERROR] billing-svc: 230 subscription renewals failed — auto-downgrade triggered"],
         "metric_changes": {"orders_pending_count": 5000},
         "affected_users_delta": 4000,
         "feedback": "⚠️ CASCADE: Subscription renewals are failing — users losing paid features!"},
    ],
    "Kubernetes Node NotReady Events": [
        {"trigger_step": 3, "condition": "not_remediated",
         "new_symptoms": ["HPA unable to scale — insufficient cluster capacity for autoscaling"],
         "new_logs": ["[WARN] hpa: Cannot scale deployment api-server — insufficient CPU in cluster"],
         "metric_changes": {"pods_pending": 35, "cluster_cpu_available_pct": 8},
         "affected_users_delta": 5000,
         "feedback": "⚠️ CASCADE: Cluster cannot autoscale — capacity critically low!"},
    ],
    "Suspicious Login Pattern Detected": [
        {"trigger_step": 3, "condition": "not_remediated",
         "new_symptoms": ["Compromised accounts used to access internal API — data exfiltration risk"],
         "new_logs": ["[ALERT] security-monitor: Compromised account admin@corp used to query user PII endpoint"],
         "metric_changes": {"compromised_accounts": 28},
         "severity_escalation": "SEV1", "affected_users_delta": 100000,
         "feedback": "🔥 CASCADE: Compromised accounts accessing sensitive data — potential data breach!"},
    ],
    "Slow Query Degrading Dashboard Performance": [
        {"trigger_step": 5, "condition": "not_remediated",
         "new_symptoms": ["Database connection pool exhausted — other queries also failing"],
         "new_logs": ["[ERROR] pg-analytics: max connections (100) reached — rejecting new queries"],
         "metric_changes": {"db_cpu_pct": 100},
         "affected_users_delta": 200,
         "feedback": "⚠️ CASCADE: Database overloaded — affecting other analytics queries too!"},
    ],
    "Scheduled Job Execution Failure": [
        {"trigger_step": 5, "condition": "not_remediated",
         "new_symptoms": ["Executive weekly report contains completely stale data — board meeting tomorrow"],
         "new_logs": ["[WARN] reporting-svc: Executive dashboard sourced from 3-day-old data"],
         "metric_changes": {"dashboard_data_age_hours": 72},
         "affected_users_delta": 20,
         "feedback": "⚠️ CASCADE: Executive reports are stale — C-suite visibility affected!"},
    ],
}


# ── Specialist Responses by Template Title ────────────────────────────────────

SPECIALIST_RESPONSES: Dict[str, Dict[str, str]] = {
    "API Gateway 5xx Error Spike": {
        "platform": "Deploy #4821 changed the health check endpoint from /healthz to /ready. The new pods pass readiness but fail liveness. Recommend immediate rollback.",
        "database": "Database connections are normal from our side. The issue appears to be upstream — likely a deployment problem.",
        "networking": "Network metrics look normal. No packet loss or latency anomalies. The issue is application-level.",
    },
    "Database Primary Node Unresponsive": {
        "database": "WAL disk is 100% full. Immediate failover to pg-replica-01 recommended. We can then add disk space to the old primary.",
        "infrastructure": "The underlying EBS volume hit IOPS limits. We need to resize the volume type from gp2 to io2.",
        "platform": "All application connection pools are exhausted. We need the DB team to fix the primary first.",
    },
    "Authentication Service Intermittent Failures": {
        "security": "The OIDC provider config was changed in us-west-2 and eu-west-1. The JWT signing key was rotated but the new key wasn't propagated. Reverting the config change will fix it.",
        "platform": "Auth failures correlate with the config-sync push. Not a platform issue.",
        "networking": "No network issues between regions. The requests are reaching the auth service fine.",
    },
    "SSL Certificate Expiry on Payment Gateway": {
        "security": "Certificate for payments.example.com expired 2 hours ago. We have a new cert ready in Vault — need to deploy it to the nginx instances.",
        "platform": "Payment service is healthy — the TLS termination at nginx is the problem.",
        "infrastructure": "Certificate auto-renewal was disabled 3 months ago during a migration.",
    },
    "Suspicious Login Pattern Detected": {
        "security": "Credential stuffing from a botnet. We need to block the user-agent pattern and force password resets on the 12 compromised accounts. Enable CAPTCHA on login.",
        "platform": "Rate limiting is being evaded because the bot rotates API keys. We need IP-based blocking.",
        "networking": "The traffic is coming from a distributed botnet across 30+ countries. WAF IP blocking won't be enough — need user-agent and behavior-based rules.",
    },
}

# Default specialist response for templates without specific ones
DEFAULT_SPECIALIST = "I've reviewed the incident. The symptoms are consistent with the reported issue. I recommend proceeding with the standard remediation for this type of problem."


# ── Time-Series Metrics by Template Title ─────────────────────────────────────

METRICS_TIMESERIES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "API Gateway 5xx Error Spike": {
        "error_rate_pct": [
            {"t": "-30m", "v": 0.5}, {"t": "-20m", "v": 0.6}, {"t": "-12m", "v": 5.8},
            {"t": "-10m", "v": 18.2}, {"t": "-5m", "v": 28.5}, {"t": "now", "v": 35.2},
        ],
        "p99_latency_ms": [
            {"t": "-30m", "v": 180}, {"t": "-20m", "v": 195}, {"t": "-12m", "v": 1200},
            {"t": "-10m", "v": 3500}, {"t": "-5m", "v": 6800}, {"t": "now", "v": 8500},
        ],
    },
    "Database Primary Node Unresponsive": {
        "error_rate_pct": [
            {"t": "-60m", "v": 0.1}, {"t": "-30m", "v": 0.2}, {"t": "-10m", "v": 45.0},
            {"t": "-5m", "v": 75.0}, {"t": "now", "v": 89.0},
        ],
        "disk_usage_pct": [
            {"t": "-24h", "v": 75}, {"t": "-12h", "v": 82}, {"t": "-6h", "v": 90},
            {"t": "-1h", "v": 97}, {"t": "-10m", "v": 99.5}, {"t": "now", "v": 100},
        ],
    },
    "SSL Certificate Expiry on Payment Gateway": {
        "error_rate_pct": [
            {"t": "-24h", "v": 0.0}, {"t": "-12h", "v": 0.0}, {"t": "-2h", "v": 100.0},
            {"t": "-1h", "v": 100.0}, {"t": "now", "v": 100.0},
        ],
        "failed_transactions_per_min": [
            {"t": "-24h", "v": 0}, {"t": "-12h", "v": 0}, {"t": "-2h", "v": 340},
            {"t": "-1h", "v": 340}, {"t": "now", "v": 340},
        ],
    },
    "Sudden Traffic Spike from Bot Activity": {
        "requests_per_sec": [
            {"t": "-30m", "v": 4500}, {"t": "-20m", "v": 4600}, {"t": "-10m", "v": 12000},
            {"t": "-5m", "v": 28000}, {"t": "now", "v": 45000},
        ],
        "p99_latency_ms": [
            {"t": "-30m", "v": 95}, {"t": "-20m", "v": 100}, {"t": "-10m", "v": 800},
            {"t": "-5m", "v": 2800}, {"t": "now", "v": 5200},
        ],
    },
    "Suspicious Login Pattern Detected": {
        "failed_login_rate_per_hour": [
            {"t": "-3h", "v": 450}, {"t": "-2h", "v": 500}, {"t": "-1h", "v": 5000},
            {"t": "-30m", "v": 25000}, {"t": "now", "v": 50000},
        ],
    },
}


def enrich_template(template: Dict[str, Any]) -> Dict[str, Any]:
    """Add cascade events, specialist responses, and timeseries to a template."""
    title = template["title"]
    if "cascade_events" not in template:
        template["cascade_events"] = CASCADE_EVENTS.get(title, [])
    if "specialist_responses" not in template:
        sr = SPECIALIST_RESPONSES.get(title, {})
        # Add default response for teams not specifically listed
        for team in ["platform", "database", "networking", "security", "application", "infrastructure"]:
            if team not in sr:
                sr[team] = DEFAULT_SPECIALIST
        template["specialist_responses"] = sr
    if "metrics_timeseries" not in template:
        template["metrics_timeseries"] = METRICS_TIMESERIES.get(title, {})
    return template
