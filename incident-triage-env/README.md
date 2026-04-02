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

> An OpenEnv environment that simulates real-world IT incident response. Train AI agents to classify severity, diagnose root causes, apply remediations, communicate status, and resolve incidents end-to-end.

## 🎯 Motivation

IT incident triage is a **genuine, high-stakes task** performed daily by SREs, DevOps engineers, and on-call teams. A typical incident requires:

- Assessing severity under time pressure
- Diagnosing root cause from logs, metrics, and symptoms
- Routing to the correct response team
- Applying the right remediation action
- Communicating status to stakeholders
- Writing a post-incident summary

This environment provides a realistic simulation of that workflow with **15 diverse incident scenarios**, spanning outages, memory leaks, security breaches, certificate expiry, DNS issues, and more.

---

## 📋 Tasks

| Task ID | Name | Difficulty | Max Steps | Description |
|---------|------|-----------|-----------|-------------|
| `task_1_classify` | Severity Classification & Team Assignment | **Easy** | 5 | Classify incident severity (SEV1–SEV4) and assign to correct team |
| `task_2_diagnose` | Root Cause Diagnosis | **Medium** | 10 | Classify severity, identify root cause, explain, and assign team |
| `task_3_resolve` | Full Incident Resolution | **Hard** | 20 | End-to-end: classify, diagnose, remediate, communicate, and resolve |

### Grading Criteria (scores 0.0 – 1.0)

**Task 1:** Severity accuracy (50%) + Team accuracy (50%)

**Task 2:** Severity (20%) + Root cause (40%) + Explanation quality (20%) + Team (20%)

**Task 3:** Severity (10%) + Root cause (20%) + Remediation (25%) + Communication (15%) + Resolution (15%) + Time efficiency (15%)

---

## 🎮 Action Space

| Action Type | Fields | Description |
|-------------|--------|-------------|
| `classify_severity` | `severity` | Set severity: `SEV1`, `SEV2`, `SEV3`, `SEV4` |
| `diagnose` | `root_cause`, `explanation` | Identify root cause and explain |
| `assign_team` | `team` | Route to: `platform`, `database`, `networking`, `security`, `application`, `infrastructure` |
| `remediate` | `remediation` | Fix: `rollback_deploy`, `restart_service`, `scale_horizontally`, `fix_config`, `failover_db`, `flush_cache`, `block_traffic`, `rotate_credentials` |
| `communicate` | `message`, `audience` | Status update to `engineering`/`management`/`customers` |
| `escalate` | `reason` | Escalate to senior on-call |
| `resolve` | `summary` | Close incident with resolution summary |

---

## 👁️ Observation Space

Each observation includes:

| Field | Type | Description |
|-------|------|-------------|
| `incident_id` | `str` | Unique incident identifier |
| `incident_title` | `str` | Short title of the incident |
| `incident_description` | `str` | Detailed description with context |
| `service_affected` | `str` | The affected service/component |
| `symptoms` | `list[str]` | Observable symptoms |
| `logs` | `list[str]` | Relevant log entries |
| `metrics` | `dict` | Key metrics (error rate, latency, CPU, memory, etc.) |
| `affected_users` | `int` | Number of affected users |
| `timeline` | `list[str]` | Actions taken so far |
| `available_actions` | `list[str]` | What actions can be taken |
| `hints` | `list[str]` | Context clues (more in easy, fewer in hard) |
| `elapsed_minutes` | `float` | Simulated time elapsed |
| `step_feedback` | `str` | Feedback from last action |
| `done` | `bool` | Whether episode is complete |
| `reward` | `float` | Step reward |

---

## 🏗️ Setup & Usage

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the server
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload

# Run baseline (heuristic - no API key needed)
python baseline.py --heuristic

# Run baseline (with OpenAI)
export OPENAI_API_KEY=sk-...
python baseline.py
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
    # Reset
    obs = client.reset(task_id="task_1_classify", seed=42)
    print(f"Incident: {obs['incident_title']}")

    # Classify severity
    result = client.step({"action_type": "classify_severity", "severity": "SEV1"})
    print(f"Feedback: {result['observation']['step_feedback']}")

    # Assign team
    result = client.step({"action_type": "assign_team", "team": "platform"})
    print(f"Score: {client.grade()['score']}")
```

---

## 📊 Baseline Scores

Heuristic baseline agent (keyword-matching, deterministic):

| Task | Difficulty | Average Score | Score Range |
|------|-----------|---------------|-------------|
| Severity Classification | Easy | ~0.65 | [0.35, 1.00] |
| Root Cause Diagnosis | Medium | ~0.50 | [0.20, 0.80] |
| Full Incident Resolution | Hard | ~0.55 | [0.30, 0.75] |

*Scores are deterministic and reproducible with `python baseline.py --heuristic`.*

---

## 🔧 Reward Function

The reward function provides **continuous signal** throughout the episode:

- **+0.20** correct severity classification
- **+0.30** correct root cause identification
- **+0.25** correct remediation action
- **+0.20** correct team assignment
- **+0.10** clear communication
- **+0.10** resolution with summary
- **-0.02** per step (time penalty — rewards efficiency)
- **-0.10 to -0.20** incorrect answers
- **Partial credit** for close-but-not-exact answers

---

## 📁 Project Structure

```
incident-triage-env/
├── __init__.py              # Package exports
├── models.py                # Typed Action, Observation, State models
├── client.py                # HTTP client
├── baseline.py              # Baseline inference script
├── openenv.yaml             # OpenEnv manifest
├── pyproject.toml           # Dependencies
├── Dockerfile               # Container image
├── README.md                # This file
└── server/
    ├── __init__.py
    ├── app.py               # FastAPI server with all endpoints
    ├── incident_env.py      # Core environment (reset/step/state)
    ├── incidents.py          # 15 incident scenario templates
    ├── tasks.py              # Task definitions + graders
    ├── baseline_agent.py     # Heuristic baseline agent
    └── requirements.txt      # Server dependencies
```

---

## 🚀 Hugging Face Spaces Deployment

1. Create a new Space with Docker SDK
2. Push this directory to the Space repo
3. The Dockerfile will build and serve on port 8000
4. Tag the Space with `openenv`

---

## License

MIT
