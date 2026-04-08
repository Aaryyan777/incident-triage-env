"""
Inference Script for IT Incident Triage Environment.

Uses the OpenAI Client with the following environment variables:
  - API_BASE_URL: The API endpoint for the LLM
  - MODEL_NAME: The model identifier to use for inference
  - HF_TOKEN: Your Hugging Face / API key

Usage:
    export API_BASE_URL=https://api.openai.com/v1
    export MODEL_NAME=gpt-4o-mini
    export HF_TOKEN=your-token-here
    python inference.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List

sys.path.insert(0, os.path.dirname(__file__))

from openai import OpenAI

from server.incident_env import IncidentTriageEnvironment
from server.tasks import TASKS, grade


# ── Configuration from environment variables ──────────────────────────────────

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
if not API_KEY:
    pass

SYSTEM_PROMPT = """You are an experienced Site Reliability Engineer (SRE) handling IT incidents.
You will be given an IT incident with symptoms, logs, metrics, and context.
Your task is to triage and resolve the incident by taking appropriate actions.

For each step, respond with a JSON object containing:
- "action_type": The action to take
- Plus the relevant fields for that action type

Available action types and their fields:
- classify_severity: {"severity": "SEV1|SEV2|SEV3|SEV4"}
- diagnose: {"root_cause": "bad_deployment|infrastructure_failure|config_change|traffic_spike|dependency_outage|memory_leak|security_breach|database_corruption|certificate_expiry|dns_misconfiguration", "explanation": "..."}
- assign_team: {"team": "platform|database|networking|security|application|infrastructure"}
- remediate: {"remediation": "rollback_deploy|restart_service|scale_horizontally|fix_config|failover_db|flush_cache|block_traffic|rotate_credentials"}
- communicate: {"message": "...", "audience": "engineering|management|customers"}
- escalate: {"reason": "..."}
- resolve: {"summary": "..."}

IMPORTANT: Respond ONLY with a single valid JSON object. No additional text, no markdown."""


def _build_incident_prompt(obs_dict: Dict, task: Any) -> str:
    """Build the initial prompt describing the incident."""
    symptoms = "\n".join(f"  - {s}" for s in obs_dict.get("symptoms", []))
    logs = "\n".join(f"  {l}" for l in obs_dict.get("logs", []))
    metrics = json.dumps(obs_dict.get("metrics", {}), indent=2)
    hints = "\n".join(f"  - {h}" for h in obs_dict.get("hints", []))

    return (
        f"TASK: {task.description}\n\n"
        f"INCIDENT: {obs_dict['incident_title']}\n"
        f"Description: {obs_dict['incident_description']}\n"
        f"Service: {obs_dict['service_affected']}\n"
        f"Affected Users: {obs_dict['affected_users']}\n\n"
        f"Symptoms:\n{symptoms}\n\n"
        f"Logs:\n{logs}\n\n"
        f"Metrics:\n{metrics}\n\n"
        f"Hints:\n{hints}\n\n"
        f"Available actions: {obs_dict['available_actions']}\n"
        f"Max steps: {task.max_steps}\n\n"
        f"Take your first action now. Respond with JSON only."
    )


def run_llm_episode(
    task_id: str,
    incident_index: int,
    seed: int,
    client: OpenAI,
) -> Dict[str, Any]:
    """Run an LLM agent on a single task/incident combination."""
    print(f"[START] task={task_id} env=incident-triage model={MODEL_NAME}", flush=True)
    env = IncidentTriageEnvironment()
    obs = env.reset(seed=seed, task_id=task_id, incident_index=incident_index)
    obs_dict = asdict(obs)
    task = TASKS[task_id]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_incident_prompt(obs_dict, task)},
    ]

    step_count = 0
    while not env.is_done and step_count < task.max_steps:
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.0,
                max_tokens=500,
            )
            action_text = response.choices[0].message.content.strip()

            # Parse JSON — handle markdown code blocks if model wraps response
            clean_text = action_text
            if clean_text.startswith("```"):
                lines = clean_text.split("\n")
                clean_text = "\n".join(lines[1:-1])

            action_dict = json.loads(clean_text)

            if "action_type" not in action_dict:
                break

            obs = env.step(action_dict)
            obs_dict = asdict(obs)
            step_count += 1
            print(f"[STEP] step={step_count} action={json.dumps(action_dict)} reward={obs_dict['reward']:.2f} done={str(obs_dict['done']).lower()} error=null", flush=True)

            messages.append({"role": "assistant", "content": action_text})
            messages.append({"role": "user", "content": (
                f"Feedback: {obs_dict['step_feedback']}\n"
                f"Reward: {obs_dict['reward']:.3f}\n"
                f"Done: {obs_dict['done']}\n"
                f"Steps taken: {step_count}/{task.max_steps}\n\n"
                f"Take your next action. Respond with JSON only."
            )})

        except json.JSONDecodeError as e:
            # If model doesn't return valid JSON, try to extract it
            action_fallback = {"action_type": "invalid_json"}
            print(f"[STEP] step={step_count} action={json.dumps(action_fallback)} reward=0.00 done=false error=\"{str(e)}\"", flush=True)
            break
        except Exception as e:
            action_fallback = {"action_type": "error"}
            print(f"[STEP] step={step_count} action={json.dumps(action_fallback)} reward=0.00 done=false error=\"{str(e)}\"", flush=True)
            break

    score = grade(task_id, env.state, env.current_incident)
    success_str = "true" if score >= 0.5 else "false"
    total_reward = env.state.total_reward
    print(f"[END] success={success_str} steps={step_count} rewards={total_reward:.2f}", flush=True)
    
    return {
        "task_id": task_id,
        "incident_index": incident_index,
        "score": score,
        "steps": step_count,
        "total_reward": round(env.state.total_reward, 4),
    }


# ── Heuristic Baseline Fallback ──────────────────────────────────────────────

def _heuristic_classify_severity(obs: Dict) -> str:
    metrics = obs.get("metrics", {})
    error_rate = metrics.get("error_rate_pct", 0)
    affected = obs.get("affected_users", 0)
    if error_rate >= 80 or affected >= 50000:
        return "SEV1"
    elif error_rate >= 25 or affected >= 10000:
        return "SEV2"
    elif error_rate >= 5 or affected >= 1000:
        return "SEV3"
    return "SEV4"


def _heuristic_diagnose(obs: Dict) -> tuple:
    combined = (" ".join(obs.get("logs", [])) + " " + obs.get("incident_description", "")).lower()
    if "deploy" in combined or "canary" in combined:
        return "bad_deployment", "Recent deployment correlates with incident."
    elif "certificate" in combined or "ssl" in combined or "tls" in combined:
        return "certificate_expiry", "TLS/SSL certificate issues detected."
    elif "dns" in combined or "coredns" in combined or "servfail" in combined:
        return "dns_misconfiguration", "DNS resolution failures detected."
    elif "oom" in combined or "memory" in combined or "heap" in combined:
        return "memory_leak", "Memory-related issues detected."
    elif "credential" in combined or "stuffing" in combined or "attack" in combined:
        return "security_breach", "Security threat pattern detected."
    elif "traffic" in combined or "bot" in combined:
        return "traffic_spike", "Abnormal traffic detected."
    elif "stripe" in combined or "webhook" in combined:
        return "dependency_outage", "External dependency failure."
    elif "disk" in combined or "wal" in combined or "notready" in combined:
        return "infrastructure_failure", "Infrastructure-level failure."
    elif "config" in combined or "configmap" in combined or "oidc" in combined:
        return "config_change", "Configuration change correlating with incident."
    return "infrastructure_failure", "Unable to determine specific cause."


def _heuristic_assign_team(obs: Dict) -> str:
    service = obs.get("service_affected", "").lower()
    if "db" in service or "postgres" in service or "redis" in service:
        return "database"
    elif "dns" in service or "cdn" in service:
        return "networking"
    elif "auth" in service or "payment" in service or "cert" in service:
        return "security"
    elif "k8s" in service or "kubernetes" in service or "node" in service:
        return "infrastructure"
    elif "api" in service or "gateway" in service or "stripe" in service:
        return "platform"
    return "application"


def _heuristic_remediate(root_cause: str) -> str:
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


def run_heuristic_episode(task_id: str, incident_index: int, seed: int) -> Dict:
    """Run a heuristic baseline on a single episode."""
    print(f"[START] task={task_id} env=incident-triage model=baseline_heuristic", flush=True)
    env = IncidentTriageEnvironment()
    obs = env.reset(seed=seed, task_id=task_id, incident_index=incident_index)
    obs_dict = asdict(obs)
    task = TASKS[task_id]

    def _step(action: dict):
        nonlocal obs, obs_dict
        try:
            obs = env.step(action)
            obs_dict = asdict(obs)
            print(f"[STEP] step={env.state.step_count} action={json.dumps(action)} reward={obs_dict['reward']:.2f} done={str(obs_dict['done']).lower()} error=null", flush=True)
        except Exception as e:
            print(f"[STEP] step={env.state.step_count} action={json.dumps(action)} reward=0.00 done=false error=\"{str(e)}\"", flush=True)

    severity = _heuristic_classify_severity(obs_dict)
    _step({"action_type": "classify_severity", "severity": severity})
    team = _heuristic_assign_team(obs_dict)
    _step({"action_type": "assign_team", "team": team})

    root_cause, explanation = "", ""
    if task_id in ("task_2_diagnose", "task_3_resolve"):
        root_cause, explanation = _heuristic_diagnose(obs_dict)
        _step({"action_type": "diagnose", "root_cause": root_cause, "explanation": explanation})

    if task_id == "task_3_resolve":
        remediation = _heuristic_remediate(root_cause)
        _step({"action_type": "remediate", "remediation": remediation})
        _step({
            "action_type": "communicate",
            "message": f"Incident on {obs_dict['service_affected']}: severity {severity}. Root cause: {root_cause}. Applied {remediation}.",
            "audience": "engineering",
        })
        _step({
            "action_type": "resolve",
            "summary": f"Resolved. Root cause was {root_cause.replace('_', ' ')}. Applied {remediation.replace('_', ' ')} to remediate.",
        })

    score = grade(task_id, env.state, env.current_incident)
    success_str = "true" if score >= 0.5 else "false"
    total_reward = env.state.total_reward
    print(f"[END] success={success_str} steps={env.state.step_count} rewards={total_reward:.2f}", flush=True)
    return {"task_id": task_id, "incident_index": incident_index, "score": score, "steps": env.state.step_count}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    start_time = time.time()

    use_llm = bool(API_KEY)

    if use_llm:
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
        )
    else:
        client = None

    # Run 5 incidents per task for reasonable runtime (< 20 min)
    NUM_INCIDENTS = 5
    all_results = []

    for task_id in TASKS:
        task = TASKS[task_id]

        task_scores = []
        for i in range(NUM_INCIDENTS):
            seed = 3000 + i
            if use_llm:
                result = run_llm_episode(task_id, i, seed, client)
            else:
                result = run_heuristic_episode(task_id, i, seed)
            
            task_scores.append(result["score"])

        avg = sum(task_scores) / len(task_scores)
        all_results.append({
            "task_id": task_id,
            "task_name": task.name,
            "difficulty": task.difficulty,
            "average_score": round(avg, 4),
            "min_score": round(min(task_scores), 4),
            "max_score": round(max(task_scores), 4),
            "scores": task_scores,
        })

    elapsed = time.time() - start_time

    # Write results to JSON for reproducibility
    output = {
        "model": MODEL_NAME,
        "api_base_url": API_BASE_URL,
        "mode": "llm" if use_llm else "heuristic",
        "runtime_seconds": round(elapsed, 1),
        "results": all_results,
    }
    with open("inference_results.json", "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
