"""
Incident scenario generator for realistic IT incident simulation.

Generates diverse, deterministic incident scenarios with varying complexity,
services, symptoms, log snippets, metrics, and ground-truth labels.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CascadeEvent:
    """An event that fires after N steps if the agent hasn't resolved the issue."""
    trigger_step: int          # Fires after this many steps
    condition: str             # e.g., "not_remediated", "not_classified", "not_diagnosed"
    new_symptoms: List[str] = field(default_factory=list)
    new_logs: List[str] = field(default_factory=list)
    metric_changes: Dict[str, Any] = field(default_factory=dict)
    severity_escalation: Optional[str] = None   # Auto-escalate severity
    affected_users_delta: int = 0               # Additional users affected
    feedback: str = ""                          # Shown to agent


@dataclass
class IncidentScenario:
    """A fully-specified incident scenario with ground truth."""
    incident_id: str
    title: str
    description: str
    service: str
    severity: str          # Ground truth SEV1–SEV4
    root_cause: str        # Ground truth root cause
    correct_team: str      # Ground truth team
    correct_remediation: str  # Ground truth remediation action
    symptoms: List[str] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    affected_users: int = 0
    hints_easy: List[str] = field(default_factory=list)
    hints_medium: List[str] = field(default_factory=list)
    hints_hard: List[str] = field(default_factory=list)
    # Dynamic incidents
    cascade_events: List[CascadeEvent] = field(default_factory=list)
    # Multi-agent
    specialist_responses: Dict[str, str] = field(default_factory=dict)
    # Time-series metrics
    metrics_timeseries: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)


# ── Incident Template Pool ────────────────────────────────────────────────────

INCIDENT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "title": "API Gateway 5xx Error Spike",
        "description": (
            "Alert triggered: API Gateway returning 502/503 errors at 5x normal rate. "
            "Multiple downstream services affected. Customer complaints rising on social media. "
            "Started approximately 12 minutes ago, coinciding with deploy #4821."
        ),
        "service": "api-gateway",
        "severity": "SEV1",
        "root_cause": "bad_deployment",
        "correct_team": "platform",
        "correct_remediation": "rollback_deploy",
        "symptoms": [
            "HTTP 502/503 errors spiking to 35% of requests",
            "P99 latency increased from 200ms to 8500ms",
            "Downstream service health checks failing",
            "Customer-facing dashboard showing degraded status",
        ],
        "logs": [
            "[ERROR] 2024-01-15T14:23:01Z api-gw-prod-03: upstream connect error, reset reason: connection failure",
            "[ERROR] 2024-01-15T14:23:02Z api-gw-prod-01: no healthy upstream targets for route /api/v2/users",
            "[WARN]  2024-01-15T14:22:55Z deploy-agent: Canary check skipped — fast-track deployment #4821",
            "[ERROR] 2024-01-15T14:23:05Z api-gw-prod-02: circuit breaker OPEN for service user-service",
        ],
        "metrics": {
            "error_rate_pct": 35.2,
            "p99_latency_ms": 8500,
            "requests_per_sec": 12400,
            "cpu_pct": 78,
            "memory_pct": 62,
            "healthy_instances": 1,
            "total_instances": 4,
        },
        "affected_users": 45000,
        "hints_easy": [
            "A deployment (#4821) was pushed 12 minutes ago with canary checks skipped",
            "Error messages mention 'upstream connect error' — the new code may be crashing",
            "The correct severity for a customer-facing outage affecting 45k users is SEV1",
        ],
        "hints_medium": [
            "The deployment timeline correlates with the error spike",
            "Check which service was deployed recently",
        ],
        "hints_hard": [],
    },
    {
        "title": "Database Primary Node Unresponsive",
        "description": (
            "PostgreSQL primary node stopped accepting connections. Read replicas are serving "
            "stale data. Write operations failing across all services. Connection pool exhausted."
        ),
        "service": "postgresql-primary",
        "severity": "SEV1",
        "root_cause": "infrastructure_failure",
        "correct_team": "database",
        "correct_remediation": "failover_db",
        "symptoms": [
            "All write operations returning 'connection refused'",
            "Read replicas lagging by 45+ seconds",
            "Connection pool at 100% capacity across all app servers",
            "Transaction queue growing unboundedly",
        ],
        "logs": [
            "[FATAL] 2024-01-15T10:05:33Z pg-primary: could not write to WAL: No space left on device",
            "[ERROR] 2024-01-15T10:05:34Z pg-primary: PANIC: WAL write failed",
            "[WARN]  2024-01-15T10:05:35Z pg-replica-01: replication lag exceeding 30s threshold",
            "[ERROR] 2024-01-15T10:06:01Z app-server-05: FATAL: remaining connection slots reserved for superuser",
        ],
        "metrics": {
            "error_rate_pct": 89.0,
            "p99_latency_ms": 30000,
            "db_connections_active": 500,
            "db_connections_max": 500,
            "replication_lag_sec": 47,
            "disk_usage_pct": 100,
            "cpu_pct": 95,
        },
        "affected_users": 120000,
        "hints_easy": [
            "The logs show 'No space left on device' — disk is completely full",
            "This is a database infrastructure failure requiring failover",
            "All writes are failing, indicating SEV1",
        ],
        "hints_medium": [
            "WAL write failures suggest a disk space issue on the primary",
            "A failover to a healthy replica would restore write capability",
        ],
        "hints_hard": [],
    },
    {
        "title": "Authentication Service Intermittent Failures",
        "description": (
            "Users reporting sporadic login failures. Auth service returning 401 for valid "
            "credentials approximately 30% of the time. Issue appears to affect specific regions."
        ),
        "service": "auth-service",
        "severity": "SEV2",
        "root_cause": "config_change",
        "correct_team": "security",
        "correct_remediation": "fix_config",
        "symptoms": [
            "30% of authentication requests returning 401",
            "Session token validation failing intermittently",
            "Issue concentrated in us-west-2 and eu-west-1 regions",
            "No recent deployments to auth service",
        ],
        "logs": [
            "[ERROR] 2024-01-15T08:12:44Z auth-svc-uw2-03: JWT signature verification failed: key mismatch",
            "[WARN]  2024-01-15T08:10:01Z config-sync: Updated OIDC provider config for regions us-west-2, eu-west-1",
            "[ERROR] 2024-01-15T08:12:45Z auth-svc-ew1-01: Token issuer does not match expected value",
            "[INFO]  2024-01-15T08:09:55Z config-sync: Propagating config change #7892 from admin console",
        ],
        "metrics": {
            "error_rate_pct": 30.5,
            "p99_latency_ms": 1200,
            "auth_success_rate_pct": 69.5,
            "active_sessions": 85000,
            "cpu_pct": 45,
            "memory_pct": 55,
        },
        "affected_users": 28000,
        "hints_easy": [
            "Logs show a config change was pushed to specific regions right before failures started",
            "JWT key mismatch indicates the OIDC config was updated incorrectly",
            "This is a SEV2 — significant degradation but not total outage",
        ],
        "hints_medium": [
            "The config-sync service pushed an update shortly before errors began",
            "Affected regions correlate with the config propagation targets",
        ],
        "hints_hard": [],
    },
    {
        "title": "CDN Cache Purge Storm",
        "description": (
            "Origin servers overwhelmed by cache miss traffic after an accidental full CDN cache purge. "
            "Static assets loading slowly or timing out for all users."
        ),
        "service": "cdn-edge",
        "severity": "SEV2",
        "root_cause": "config_change",
        "correct_team": "infrastructure",
        "correct_remediation": "scale_horizontally",
        "symptoms": [
            "Cache hit ratio dropped from 95% to 2%",
            "Origin server CPU at 100%",
            "Static asset load times increased from 50ms to 12s",
            "CDN bandwidth costs spiking 20x",
        ],
        "logs": [
            "[INFO]  2024-01-15T16:00:01Z cdn-mgmt: Cache purge initiated — scope: ALL (*.*)",
            "[WARN]  2024-01-15T16:00:05Z cdn-mgmt: Full cache purge completed across 42 edge locations",
            "[ERROR] 2024-01-15T16:01:30Z origin-web-01: Connection pool exhausted, rejecting requests",
            "[ERROR] 2024-01-15T16:01:45Z origin-web-03: OOM killed by kernel — RSS exceeded 8GB limit",
        ],
        "metrics": {
            "cache_hit_ratio_pct": 2.1,
            "origin_cpu_pct": 100,
            "origin_memory_pct": 98,
            "p99_latency_ms": 12000,
            "bandwidth_gbps": 45.2,
            "requests_to_origin_per_sec": 85000,
        },
        "affected_users": 500000,
        "hints_easy": [
            "A full cache purge (ALL) was triggered — this is the root cause",
            "Origin servers need more capacity to handle the thundering herd",
            "Scale horizontally to absorb the traffic until cache warms up",
        ],
        "hints_medium": [
            "Check when the cache hit ratio dropped and what happened at that time",
        ],
        "hints_hard": [],
    },
    {
        "title": "Message Queue Consumer Lag",
        "description": (
            "Kafka consumer group 'order-processor' showing increasing lag. Order processing "
            "delayed by 15+ minutes. No errors in producer, consumers appear stuck."
        ),
        "service": "kafka-cluster",
        "severity": "SEV3",
        "root_cause": "memory_leak",
        "correct_team": "application",
        "correct_remediation": "restart_service",
        "symptoms": [
            "Consumer lag growing at ~5000 messages/min",
            "Order processing latency increased to 15 minutes",
            "Consumer instances memory usage trending upward linearly",
            "No producer-side errors or unusual throughput",
        ],
        "logs": [
            "[WARN]  2024-01-15T11:30:00Z order-proc-02: GC pause exceeded 5s threshold (actual: 8.2s)",
            "[WARN]  2024-01-15T11:32:15Z order-proc-01: Heap usage at 92% — 7.4GB of 8GB",
            "[INFO]  2024-01-15T11:33:00Z order-proc-03: Consumer rebalance triggered due to session timeout",
            "[WARN]  2024-01-15T11:35:20Z order-proc-02: GC pause exceeded 5s threshold (actual: 12.1s)",
        ],
        "metrics": {
            "consumer_lag_messages": 75000,
            "processing_latency_min": 15.3,
            "consumer_heap_pct": 92,
            "gc_pause_avg_ms": 8200,
            "messages_produced_per_sec": 2200,
            "messages_consumed_per_sec": 800,
        },
        "affected_users": 3500,
        "hints_easy": [
            "Consumer instances are running out of memory — heap at 92%",
            "Long GC pauses indicate a memory leak in the order processor",
            "Restarting the consumers will temporarily fix the issue",
        ],
        "hints_medium": [
            "Memory usage is growing linearly, suggesting a leak",
        ],
        "hints_hard": [],
    },
    {
        "title": "SSL Certificate Expiry on Payment Gateway",
        "description": (
            "Payment processing failing with SSL handshake errors. The TLS certificate for "
            "payments.example.com expired 2 hours ago. All payment transactions blocked."
        ),
        "service": "payment-gateway",
        "severity": "SEV1",
        "root_cause": "certificate_expiry",
        "correct_team": "security",
        "correct_remediation": "rotate_credentials",
        "symptoms": [
            "All payment API calls returning SSL_ERROR_EXPIRED_CERT_ALERT",
            "Zero successful transactions in past 2 hours",
            "Revenue impact estimated at $180K/hour",
            "Certificate expired at 2024-01-15T06:00:00Z",
        ],
        "logs": [
            "[ERROR] 2024-01-15T06:00:05Z nginx-pay-01: SSL_do_handshake() failed: certificate has expired",
            "[ERROR] 2024-01-15T06:00:06Z payment-svc: TLS handshake timeout to payments.example.com:443",
            "[WARN]  2024-01-14T06:00:00Z cert-monitor: Certificate for payments.example.com expires in 24h (IGNORED — alert suppression active)",
            "[ERROR] 2024-01-15T06:01:00Z checkout-svc: Payment processing unavailable — circuit breaker OPEN",
        ],
        "metrics": {
            "error_rate_pct": 100,
            "successful_transactions": 0,
            "failed_transactions_per_min": 340,
            "revenue_loss_usd_per_hour": 180000,
            "cert_days_remaining": -0.08,
        },
        "affected_users": 15000,
        "hints_easy": [
            "The SSL certificate expired exactly 2 hours ago",
            "Renewing/rotating the certificate will fix this immediately",
            "100% error rate on payments = SEV1",
        ],
        "hints_medium": [
            "Check certificate expiry dates in the error logs",
        ],
        "hints_hard": [],
    },
    {
        "title": "DNS Resolution Failures for Internal Services",
        "description": (
            "Internal service discovery failing sporadically. CoreDNS pods in Kubernetes "
            "returning SERVFAIL for approximately 15% of queries. Microservices unable to "
            "locate each other reliably."
        ),
        "service": "coredns",
        "severity": "SEV2",
        "root_cause": "dns_misconfiguration",
        "correct_team": "networking",
        "correct_remediation": "fix_config",
        "symptoms": [
            "15% of DNS queries returning SERVFAIL",
            "Intermittent connection failures between microservices",
            "Service mesh health checks flapping",
            "CoreDNS pod restarts increasing",
        ],
        "logs": [
            "[ERROR] 2024-01-15T09:45:12Z coredns-5d78c: SERVFAIL for user-service.default.svc.cluster.local",
            "[WARN]  2024-01-15T09:44:00Z k8s-admin: ConfigMap kube-system/coredns updated by user ops-bot@ci",
            "[ERROR] 2024-01-15T09:45:15Z coredns-5d78c: plugin/forward: no healthy upstreams for zone '.'",
            "[INFO]  2024-01-15T09:44:01Z coredns-a3f12: Reloading Corefile due to ConfigMap change",
        ],
        "metrics": {
            "dns_failure_rate_pct": 15.2,
            "dns_latency_p99_ms": 2500,
            "coredns_pod_restarts": 8,
            "service_mesh_health_pct": 84,
            "cpu_pct": 35,
        },
        "affected_users": 0,  # Internal only
        "hints_easy": [
            "CoreDNS ConfigMap was recently modified by ops-bot",
            "The forward plugin has no healthy upstreams — upstream DNS config is wrong",
            "This is a config change issue affecting DNS resolution",
        ],
        "hints_medium": [
            "A ConfigMap change was applied right before the failures started",
        ],
        "hints_hard": [],
    },
    {
        "title": "Memory Leak in User Profile Service",
        "description": (
            "User profile service pods being OOM-killed every 4-6 hours. Each restart causes "
            "brief elevation in error rates. Heap dumps show growing collection of unclosed "
            "HTTP client connections."
        ),
        "service": "user-profile-service",
        "severity": "SEV3",
        "root_cause": "memory_leak",
        "correct_team": "application",
        "correct_remediation": "restart_service",
        "symptoms": [
            "Pods restarting every 4-6 hours due to OOM",
            "Memory usage increases linearly after each restart",
            "Brief error spikes during pod restarts",
            "Heap dump shows 50k+ unclosed HTTP client instances",
        ],
        "logs": [
            "[WARN]  2024-01-15T12:00:00Z user-prof-02: Memory usage at 85% (6.8GB / 8GB)",
            "[ERROR] 2024-01-15T14:15:33Z user-prof-02: OOMKilled — container exceeded memory limit",
            "[INFO]  2024-01-15T14:15:35Z k8s: Pod user-profile-7f8d9-x2k4p restarting (restart count: 4)",
            "[WARN]  2024-01-15T14:16:00Z user-prof-02: Heap analysis: 52,431 instances of org.apache.http.impl.conn.PoolingHttpClientConnectionManager",
        ],
        "metrics": {
            "error_rate_pct": 5.2,
            "memory_growth_mb_per_hour": 450,
            "pod_restart_count_24h": 5,
            "p99_latency_ms": 800,
            "open_http_connections": 52431,
        },
        "affected_users": 1200,
        "hints_easy": [
            "The service has a memory leak — unclosed HTTP connections accumulating",
            "Restarting clears the leaked memory temporarily",
            "This is SEV3 — the service auto-recovers via restarts, limited user impact",
        ],
        "hints_medium": [
            "Memory is growing linearly, and pods restart every few hours",
        ],
        "hints_hard": [],
    },
    {
        "title": "Sudden Traffic Spike from Bot Activity",
        "description": (
            "Search API receiving 10x normal traffic from a small number of IPs. "
            "Legitimate user requests timing out. Rate limiting not kicking in because "
            "requests are distributed across many API keys."
        ),
        "service": "search-api",
        "severity": "SEV2",
        "root_cause": "traffic_spike",
        "correct_team": "platform",
        "correct_remediation": "block_traffic",
        "symptoms": [
            "Search API latency increased from 100ms to 5s",
            "10x normal request volume from ~50 IP addresses",
            "Legitimate user searches timing out",
            "Rate limiter not triggering (requests spread across 200+ API keys)",
        ],
        "logs": [
            "[WARN]  2024-01-15T13:00:15Z search-api-01: Request rate 45,000/s exceeds expected 4,500/s",
            "[INFO]  2024-01-15T13:00:20Z waf: Top requester IPs: 198.51.100.x (12 unique), all with valid API keys",
            "[ERROR] 2024-01-15T13:01:00Z search-api-03: Elasticsearch query timeout after 30s",
            "[WARN]  2024-01-15T13:01:05Z search-api-02: Thread pool exhausted — rejecting new requests",
        ],
        "metrics": {
            "error_rate_pct": 45.0,
            "p99_latency_ms": 5200,
            "requests_per_sec": 45000,
            "normal_rps": 4500,
            "unique_bot_ips": 50,
            "unique_api_keys_involved": 215,
            "cpu_pct": 100,
        },
        "affected_users": 35000,
        "hints_easy": [
            "Traffic is 10x normal from a small set of IPs — likely bots",
            "Block the offending IPs/API keys at the WAF or load balancer level",
            "SEV2 — significant degradation but service is still partially up",
        ],
        "hints_medium": [
            "Compare current RPS to normal baseline — what's causing the spike?",
        ],
        "hints_hard": [],
    },
    {
        "title": "Redis Cache Cluster Split-Brain",
        "description": (
            "Redis Sentinel detected a network partition. Two nodes both claiming to be primary. "
            "Data inconsistency risk. Some reads returning stale data."
        ),
        "service": "redis-cluster",
        "severity": "SEV2",
        "root_cause": "infrastructure_failure",
        "correct_team": "database",
        "correct_remediation": "restart_service",
        "symptoms": [
            "Two Redis nodes both reporting as primary",
            "Sentinel quorum disagreement across availability zones",
            "Intermittent stale data in user sessions",
            "Write conflicts detected on key ownership",
        ],
        "logs": [
            "[WARN]  2024-01-15T15:30:00Z redis-sentinel-01: +sdown master redis-primary 10.0.1.5 6379",
            "[ERROR] 2024-01-15T15:30:02Z redis-sentinel-03: Failover triggered — electing redis-02 as new primary",
            "[WARN]  2024-01-15T15:30:05Z redis-01: Still accepting writes as primary (network partition suspected)",
            "[ERROR] 2024-01-15T15:30:10Z app-server-02: READONLY You can't write against a read-only replica",
        ],
        "metrics": {
            "primary_nodes_count": 2,
            "sentinel_quorum_agreement": False,
            "stale_reads_pct": 12.5,
            "write_conflicts_per_min": 45,
            "replication_link_status": "disconnected",
        },
        "affected_users": 18000,
        "hints_easy": [
            "Two nodes are claiming to be primary — this is a split-brain scenario",
            "Restart the old primary to force it to rejoin as a replica",
            "The database team should handle Redis cluster issues",
        ],
        "hints_medium": [
            "Check how many nodes think they are primary — should be exactly 1",
        ],
        "hints_hard": [],
    },
    {
        "title": "Scheduled Job Execution Failure",
        "description": (
            "Nightly data pipeline ETL job failing silently. Reports dashboard showing data "
            "from 2 days ago. Airflow DAG marked as 'success' but output tables are empty."
        ),
        "service": "airflow-scheduler",
        "severity": "SEV4",
        "root_cause": "config_change",
        "correct_team": "application",
        "correct_remediation": "fix_config",
        "symptoms": [
            "Report dashboard showing stale data (2 days old)",
            "Airflow DAG 'nightly_etl' status shows success",
            "Output BigQuery tables have zero rows for last 2 runs",
            "No alerts triggered because job exit code was 0",
        ],
        "logs": [
            "[INFO]  2024-01-14T02:00:00Z airflow: DAG nightly_etl started",
            "[WARN]  2024-01-14T02:00:05Z etl-worker: Source table 'events_v2' not found, using fallback: 'events_v1' (DEPRECATED)",
            "[INFO]  2024-01-14T02:00:06Z etl-worker: Fallback table 'events_v1' is empty (migration completed last week)",
            "[INFO]  2024-01-14T02:05:00Z airflow: DAG nightly_etl completed — status: SUCCESS",
        ],
        "metrics": {
            "etl_rows_processed": 0,
            "etl_execution_time_sec": 300,
            "dashboard_data_age_hours": 48,
            "alert_count": 0,
        },
        "affected_users": 50,  # Internal analysts
        "hints_easy": [
            "The ETL is reading from a deprecated empty table due to config pointing to wrong table",
            "Fix the DAG configuration to point to 'events_v2'",
            "SEV4 — internal impact only, no customer-facing degradation",
        ],
        "hints_medium": [
            "The job succeeds but produces zero output. Check the source table config.",
        ],
        "hints_hard": [],
    },
    {
        "title": "Third-Party Payment Provider Outage",
        "description": (
            "Stripe webhook endpoint returning 503. Payment confirmations not being received. "
            "Order status stuck at 'payment_pending'. Support tickets increasing."
        ),
        "service": "stripe-integration",
        "severity": "SEV2",
        "root_cause": "dependency_outage",
        "correct_team": "platform",
        "correct_remediation": "scale_horizontally",
        "symptoms": [
            "Stripe webhook delivery failing — HTTP 503 from Stripe status page",
            "Payment confirmation callbacks not arriving",
            "Orders stuck in 'payment_pending' state",
            "Customer support ticket volume up 300%",
        ],
        "logs": [
            "[ERROR] 2024-01-15T17:00:00Z webhook-svc: Failed to process Stripe webhook: upstream timeout",
            "[INFO]  2024-01-15T17:00:05Z stripe-sdk: Stripe status page reports 'Elevated Error Rates'",
            "[WARN]  2024-01-15T17:01:00Z order-svc: 2,340 orders stuck in payment_pending > 30 minutes",
            "[INFO]  2024-01-15T17:01:30Z webhook-svc: Retry queue depth: 15,432 webhooks",
        ],
        "metrics": {
            "webhook_success_rate_pct": 12.0,
            "orders_pending_count": 2340,
            "retry_queue_depth": 15432,
            "support_ticket_rate_per_hour": 180,
            "stripe_api_availability_pct": 45.0,
        },
        "affected_users": 8500,
        "hints_easy": [
            "Stripe itself is experiencing an outage — this is a dependency issue",
            "Scale up webhook retry workers to process the backlog when Stripe recovers",
            "SEV2 — payments degraded but core platform is functional",
        ],
        "hints_medium": [
            "Check the Stripe status page — is the issue on their end?",
        ],
        "hints_hard": [],
    },
    {
        "title": "Kubernetes Node NotReady Events",
        "description": (
            "Three Kubernetes worker nodes entered NotReady state in us-east-1c AZ. "
            "Pods being evicted and rescheduled. Some pods stuck in Pending due to "
            "insufficient resources in remaining nodes."
        ),
        "service": "kubernetes-cluster",
        "severity": "SEV3",
        "root_cause": "infrastructure_failure",
        "correct_team": "infrastructure",
        "correct_remediation": "scale_horizontally",
        "symptoms": [
            "3 out of 12 nodes in NotReady state",
            "42 pods evicted, 15 stuck in Pending",
            "All affected nodes are in us-east-1c",
            "Node kubelet process not responding to API server",
        ],
        "logs": [
            "[WARN]  2024-01-15T11:00:00Z k8s-api: Node ip-10-0-3-45 status changed to NotReady",
            "[WARN]  2024-01-15T11:00:02Z k8s-api: Node ip-10-0-3-67 status changed to NotReady",
            "[WARN]  2024-01-15T11:00:03Z k8s-api: Node ip-10-0-3-89 status changed to NotReady",
            "[INFO]  2024-01-15T11:01:00Z aws-health: Degraded hardware in us-east-1c — maintenance scheduled",
        ],
        "metrics": {
            "nodes_ready": 9,
            "nodes_total": 12,
            "pods_pending": 15,
            "pods_evicted": 42,
            "cluster_cpu_available_pct": 22,
            "cluster_memory_available_pct": 18,
        },
        "affected_users": 2000,
        "hints_easy": [
            "AWS reports hardware degradation in us-east-1c",
            "Scale up nodes in other AZs to compensate",
            "SEV3 — the cluster is handling most traffic, just some pods are pending",
        ],
        "hints_medium": [
            "All affected nodes are in the same availability zone",
        ],
        "hints_hard": [],
    },
    {
        "title": "Suspicious Login Pattern Detected",
        "description": (
            "Security monitoring detected credential stuffing attack. 50,000+ failed login "
            "attempts from rotating IPs in the past hour. A handful of accounts may have "
            "been compromised."
        ),
        "service": "auth-service",
        "severity": "SEV2",
        "root_cause": "security_breach",
        "correct_team": "security",
        "correct_remediation": "block_traffic",
        "symptoms": [
            "50,000+ failed login attempts in 1 hour (normal: 500)",
            "Requests from 2,000+ unique IPs across 30 countries",
            "12 accounts successfully accessed from unusual locations",
            "Rate limiting partially effective but being evaded",
        ],
        "logs": [
            "[WARN]  2024-01-15T20:00:00Z auth-svc: Failed login rate 50x above baseline",
            "[ALERT] 2024-01-15T20:00:05Z security-monitor: Credential stuffing pattern detected",
            "[WARN]  2024-01-15T20:01:00Z auth-svc: 12 accounts logged in from new geolocation (flagged)",
            "[INFO]  2024-01-15T20:01:10Z waf: IP rotation detected — same user-agent across 2,000+ IPs",
        ],
        "metrics": {
            "failed_login_rate_per_hour": 50000,
            "normal_failed_login_rate": 500,
            "unique_attacker_ips": 2100,
            "compromised_accounts": 12,
            "waf_blocked_requests": 15000,
            "waf_bypassed_requests": 35000,
        },
        "affected_users": 12,  # Compromised accounts
        "hints_easy": [
            "This is a credential stuffing attack — block the traffic patterns at WAF",
            "Security team should handle account compromise investigation",
            "SEV2 — active security incident with potential data exposure",
        ],
        "hints_medium": [
            "The failed login rate is 100x normal. Check the IP patterns.",
        ],
        "hints_hard": [],
    },
    {
        "title": "Slow Query Degrading Dashboard Performance",
        "description": (
            "Analytics dashboard page load time increased to 45 seconds. A newly added "
            "query is performing a full table scan on a 2B row table without an index."
        ),
        "service": "analytics-dashboard",
        "severity": "SEV4",
        "root_cause": "bad_deployment",
        "correct_team": "application",
        "correct_remediation": "rollback_deploy",
        "symptoms": [
            "Dashboard load time increased from 2s to 45s",
            "Database CPU spiking to 80% during dashboard queries",
            "A new analytics query added in yesterday's deploy",
            "Query EXPLAIN shows sequential scan on 2B row table",
        ],
        "logs": [
            "[WARN]  2024-01-15T09:00:00Z pg-analytics: Slow query detected — 42.3s execution time",
            "[INFO]  2024-01-15T09:00:01Z pg-analytics: Query: SELECT * FROM events WHERE category = $1 AND date > $2",
            "[WARN]  2024-01-15T09:00:02Z pg-analytics: Seq Scan on events (rows=2,100,000,000, actual time=42300ms)",
            "[INFO]  2024-01-14T18:00:00Z deploy-log: Dashboard v2.14.0 deployed — includes new category filter query",
        ],
        "metrics": {
            "dashboard_load_time_sec": 45,
            "db_cpu_pct": 80,
            "slow_query_count": 340,
            "table_row_count": 2_100_000_000,
            "missing_index": True,
        },
        "affected_users": 25,  # Internal analysts
        "hints_easy": [
            "A new query from yesterday's deploy is doing a full table scan",
            "Rolling back the deploy will remove the problematic query",
            "SEV4 — internal tool degradation only",
        ],
        "hints_medium": [
            "Check recent deploys and correlate with the slow query timing",
        ],
        "hints_hard": [],
    },
]

# Merge in the 35 new templates
from server.new_templates import NEW_INCIDENT_TEMPLATES
INCIDENT_TEMPLATES.extend(NEW_INCIDENT_TEMPLATES)

def generate_incident(seed: Optional[int] = None, incident_index: Optional[int] = None) -> IncidentScenario:
    """Generate an incident scenario, optionally with a specific seed for reproducibility."""
    from server.enrichment import enrich_template

    rng = random.Random(seed)

    if incident_index is not None:
        idx = incident_index % len(INCIDENT_TEMPLATES)
    else:
        idx = rng.randint(0, len(INCIDENT_TEMPLATES) - 1)

    template = enrich_template(dict(INCIDENT_TEMPLATES[idx]))

    # Build cascade events from template data
    cascade_events = []
    for ce in template.get("cascade_events", []):
        cascade_events.append(CascadeEvent(
            trigger_step=ce["trigger_step"],
            condition=ce["condition"],
            new_symptoms=ce.get("new_symptoms", []),
            new_logs=ce.get("new_logs", []),
            metric_changes=ce.get("metric_changes", {}),
            severity_escalation=ce.get("severity_escalation"),
            affected_users_delta=ce.get("affected_users_delta", 0),
            feedback=ce.get("feedback", ""),
        ))

    return IncidentScenario(
        incident_id=f"INC-{(seed or rng.randint(1000, 9999)):04d}",
        title=template["title"],
        description=template["description"],
        service=template["service"],
        severity=template["severity"],
        root_cause=template["root_cause"],
        correct_team=template["correct_team"],
        correct_remediation=template["correct_remediation"],
        symptoms=list(template["symptoms"]),
        logs=list(template["logs"]),
        metrics=dict(template["metrics"]),
        affected_users=template["affected_users"],
        hints_easy=template.get("hints_easy", []),
        hints_medium=template.get("hints_medium", []),
        hints_hard=template.get("hints_hard", []),
        cascade_events=cascade_events,
        specialist_responses=template.get("specialist_responses", {}),
        metrics_timeseries=template.get("metrics_timeseries", {}),
    )


def get_incident_count() -> int:
    """Return the number of available incident templates."""
    return len(INCIDENT_TEMPLATES)

