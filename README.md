[README.md](https://github.com/user-attachments/files/26480465/README.md)
---
title: IT Incident Triage Environment
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 8000
tags:
  - openenv
pinned: false
---

# IT Incident Triage & Resolution — OpenEnv Environment

> An OpenEnv environment that simulates real-world IT incident response. Train AI agents to classify severity, diagnose root causes, apply remediations, coordinate with specialist teams, manage cascading failures, and resolve incidents end-to-end.

## Motivation

IT incident triage is a **genuine, high-stakes task** performed daily by SREs, DevOps engineers, and on-call teams. A typical incident requires:

- Assessing severity under time pressure
- Diagnosing root cause from logs, metrics, and symptoms
- Routing to the correct response team
- Consulting domain specialists for expert input
- Applying the right remediation before cascading failures occur
- Communicating status to stakeholders
- Writing a structured post-incident summary

This environment provides a realistic simulation of that workflow with **50 diverse incident scenarios** across 12 categories, featuring **dynamic cascading failures**, **multi-agent coordination**, **NLP-based postmortem grading**, and **Prometheus-style time-series metrics**.

---

## Key Features

### Dynamic Cascading Failures
Incidents evolve in real-time. If the agent doesn't act fast enough, cascading failures fire — adding new symptoms, degrading metrics, escalating severity, and penalizing the agent's score.

### 50 Incident Scenarios
Covering 12 categories: API/Backend, Database, Auth, CDN, Message Queues, SSL/TLS, DNS, Memory, Bot Traffic, Redis, Third-Party, Kubernetes, Cloud Provider, CI/CD Pipeline, Data Pipeline, Networking, Security, Observability, and Application.

### Multi-Agent Coordination
The agent can request specialist consultations from domain teams (platform, database, networking, security, application, infrastructure) and hand off incidents — simulating real team collaboration.

### NLP Postmortem Grading
Resolution summaries are graded on root cause mention, remediation description, affected service, prevention/follow-up steps, structure, and substance.

### Time-Series Metrics
Observations include Prometheus-style metric history (e.g., `error_rate_pct` over the last 30 minutes) to help agents identify trends and anomalies.

---

## Tasks

| Task ID | Name | Difficulty | Max Steps | Description |
|---------|------|-----------|-----------|-------------|
| `task_1_classify` | Severity Classification & Team Assignment | **Easy** | 5 | Classify incident severity (SEV1–SEV4) and assign to correct team |
| `task_2_diagnose` | Root Cause Diagnosis | **Medium** | 10 | Classify severity, identify root cause, explain, and assign team |
| `task_3_resolve` | Full Incident Resolution | **Hard** | 20 | End-to-end: classify, diagnose, remediate, coordinate, communicate, and resolve |

### Grading Criteria (scores 0.0 – 1.0)

**Task 1:** Severity accuracy (50%) + Team accuracy (50%)

**Task 2:** Severity (20%) + Root cause (40%) + Explanation quality (20%) + Team (20%)

**Task 3:**

| Component | Weight | Description |
|-----------|--------|-------------|
| Severity | 10% | Correct SEV classification |
| Root Cause | 15% | Correct diagnosis |
| Remediation | 20% | Correct fix applied |
| Communication | 10% | Status updates sent |
| Resolution | 10% | Incident closed properly |
| Postmortem Quality | 10% | NLP-graded resolution summary |
| Coordination | 5% | Specialist consultation quality |
| Time Efficiency | 10% | Steps used vs max |
| Cascade Avoidance | 10% | Prevented cascading failures |

---

## Action Space

| Action Type | Fields | Description |
|-------------|--------|-------------|
| `classify_severity` | `severity` | Set severity: `SEV1`, `SEV2`, `SEV3`, `SEV4` |
| `diagnose` | `root_cause`, `explanation` | Identify root cause and explain |
| `assign_team` | `team` | Route to: `platform`, `database`, `networking`, `security`, `application`, `infrastructure` |
| `remediate` | `remediation` | Fix: `rollback_deploy`, `restart_service`, `scale_horizontally`, `fix_config`, `failover_db`, `flush_cache`, `block_traffic`, `rotate_credentials` |
| `communicate` | `message`, `audience` | Status update to `engineering`/`management`/`customers` |
| `escalate` | `reason` | Escalate to senior on-call |
| `resolve` | `summary` | Close incident with resolution summary |
| `request_specialist` | `team` | Consult a specialist team for domain-specific input |
| `handoff` | `team`, `reason` | Hand off incident ownership to another team |

---

## Observation Space

Each observation includes:

| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | `str` | Unique incident identifier |
| `incident_title` | `str` | Short title of the incident |
| `incident_description` | `str` | Detailed description with context |
| `service_affected` | `str` | The affected service/component |
| `symptoms` | `list[str]` | Observable symptoms (grows dynamically with cascades) |
| `logs` | `list[str]` | Relevant log entries (grows dynamically with cascades) |
| `metrics` | `dict` | Key metrics (error rate, latency, CPU, memory, etc.) — updated by cascades |
| `affected_users` | `int` | Number of affected users (increases with cascades) |
| `timeline` | `list[str]` | Actions taken so far |
| `available_actions` | `list[str]` | What actions can be taken |
| `hints` | `list[str]` | Context clues (more in easy, fewer in hard) |
| `elapsed_minutes` | `float` | Simulated time elapsed |
| `step_feedback` | `str` | Feedback from last action (includes cascade alerts) |
| `done` | `bool` | Whether episode is complete |
| `reward` | `float` | Step reward |

---

## Setup & Usage

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Run baseline (heuristic - no API key needed)
python baseline.py --heuristic

# Run inference (with LLM)
export HF_TOKEN=hf_...
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
python inference.py
```

### Docker

```bash
# Build
docker build -t incident-triage-env .

# Run
docker run -p 8000:8000 incident-triage-env

# Verify
curl http://localhost:8000/health
```

### API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List tasks
curl http://localhost:8000/tasks

# Reset environment
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_1_classify", "seed": 42}'

# Take an action
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "classify_severity", "severity": "SEV1"}'

# Consult a specialist
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"action_type": "request_specialist", "team": "security"}'

# Get state
curl http://localhost:8000/state

# Get grader score
curl -X POST http://localhost:8000/grader

# Run baseline
curl -X POST http://localhost:8000/baseline
```

### Python Client

```python
from client import IncidentTriageClient

with IncidentTriageClient("http://localhost:8000") as client:
    # Reset with hard task
    obs = client.reset(task_id="task_3_resolve", seed=42)
    print(f"Incident: {obs['incident_title']}")

    # Consult specialist
    result = client.step({"action_type": "request_specialist", "team": "platform"})
    print(f"Specialist: {result['observation']['step_feedback']}")

    # Classify severity
    result = client.step({"action_type": "classify_severity", "severity": "SEV1"})

    # Diagnose
    result = client.step({"action_type": "diagnose", "root_cause": "bad_deployment",
                          "explanation": "Deployment #4821 caused the 5xx spike"})

    # Remediate
    result = client.step({"action_type": "remediate", "remediation": "rollback_deploy"})

    # Resolve with detailed postmortem
    result = client.step({"action_type": "resolve",
                          "summary": "Root Cause: bad deployment #4821. Remediation: rollback. "
                                     "Impact: 45k users. Follow-up: add canary checks."})
    print(f"Score: {client.grade()['score']}")
```

---

## Reward Function

The reward function provides **continuous signal** throughout the episode:

| Signal | Reward | Condition |
|--------|--------|-----------|
| Correct severity | +0.20 | Exact match |
| Correct root cause | +0.30 | Exact match |
| Correct remediation | +0.25 | Exact match |
| Correct team | +0.20 | Exact match |
| Communication | +0.10 | Status update sent |
| Resolution | +0.10 | Incident closed |
| Specialist (correct team) | +0.10 | Consulted right team |
| Handoff (correct team) | +0.15 | Handed off to right team |
| Partial credit | +0.05–0.10 | Close but not exact |
| Time penalty | -0.02 | Per step |
| Cascade penalty | -0.10 | Per cascading failure |
| Incorrect answers | -0.05–0.20 | Wrong classification/diagnosis |

---

## Incident Categories

| Category | Count | Examples |
|----------|-------|---------|
| API/Backend | 1 | Gateway 5xx error spike |
| Database | 1 | Primary node unresponsive |
| Auth | 1 | Intermittent auth failures |
| CDN | 1 | Cache purge storm |
| Message Queue | 1 | Consumer lag |
| SSL/TLS | 1 | Certificate expiry |
| DNS | 1 | Resolution failures |
| Memory | 1 | Profile service memory leak |
| Bot/Traffic | 1 | Sudden traffic spike |
| Redis | 1 | Cache split-brain |
| Third-Party | 1 | Payment provider outage |
| Kubernetes | 1 | Node NotReady events |
| Security (Original) | 1 | Suspicious login patterns |
| Analytics | 1 | Slow query degradation |
| Scheduling | 1 | Job execution failure |
| **Cloud Provider** | **5** | AWS region degradation, GCP quota, Azure AD sync, S3 misconfiguration, Lambda cold start |
| **CI/CD Pipeline** | **5** | Build server OOM, registry full, flaky tests, secret rotation, container CVE |
| **Data Pipeline** | **5** | Kafka overflow, Spark OOM, schema drift, streaming backpressure, data quality |
| **Networking** | **5** | VPN flap, ALB misconfigured, mTLS expired, BGP route leak, sidecar throttling |
| **Security** | **5** | API key leaked, DDoS, privilege escalation, data exfiltration, WAF false positive |
| **Observability** | **5** | Prometheus OOM, log saturation, alert fatigue, tracing OOM, cardinality explosion |
| **Application** | **5** | Checkout race condition, redirect loop, GraphQL N+1, feature flag, session fixation |

---

## Project Structure

```
incident-triage-env/
├── __init__.py              # Package exports
├── models.py                # Typed Action, Observation, State models (9 action types)
├── client.py                # HTTP client
├── baseline.py              # Baseline inference script
├── inference.py             # Competition-compliant inference script
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Dependencies
├── Dockerfile               # Container image
├── README.md                # This file
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI server with all endpoints
    ├── incident_env.py      # Core environment (reset/step/state + cascades + coordination)
    ├── incidents.py          # 15 original incident scenario templates
    ├── new_templates.py      # 35 new incident templates (7 categories)
    ├── enrichment.py         # Cascade events, specialist responses, time-series data
    ├── tasks.py              # Task definitions + graders (including postmortem NLP)
    ├── baseline_agent.py     # Heuristic baseline agent
    └── requirements.txt      # Server dependencies
```

---

## Hugging Face Spaces Deployment

1. Create a new Space with Docker SDK
2. Push this directory to the Space repo
3. The Dockerfile will build and serve on port 8000
4. Tag the Space with `openenv`

---

## License

MIT
