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
    print("WARNING: HF_TOKEN not set. Falling back to heuristic baseline.")


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
            print(f"[STEP] step={step_count} reward={obs_dict['reward']}", flush=True)

            messages.append({"role": "assistant", "content": action_text})
            messages.append({"role": "user", "content": (
                f"Feedback: {obs_dict['step_feedback']}\n"
                f"Reward: {obs_dict['reward']:.3f}\n"
                f"Done: {obs_dict['done']}\n"
                f"Steps taken: {step_count}/{task.max_steps}\n\n"
                f"Take your next action. Respond with JSON only."
            )})

        except json.JSONDecodeError:
            # If model doesn't return valid JSON, try to extract it
            break
        except Exception as e:
            print(f"    Error at step {step_count}: {e}")
            break

    score = grade(task_id, env.state, env.current_incident)
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
    env = IncidentTriageEnvironment()
    obs = env.reset(seed=seed, task_id=task_id, incident_index=incident_index)
    obs_dict = asdict(obs)
    task = TASKS[task_id]

    def _step(action: dict):
        nonlocal obs, obs_dict
        obs = env.step(action)
        obs_dict = asdict(obs)
        print(f"[STEP] step={env.state.step_count} reward={obs_dict['reward']}", flush=True)

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
    return {"task_id": task_id, "incident_index": incident_index, "score": score, "steps": env.state.step_count}


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    start_time = time.time()

    print("=" * 60)
    print("IT Incident Triage Environment — Inference Script")
    print("=" * 60)
    print(f"API_BASE_URL: {API_BASE_URL}")
    print(f"MODEL_NAME:   {MODEL_NAME}")
    print(f"API_KEY:      {'***' + API_KEY[-4:] if API_KEY and len(API_KEY) > 4 else '(not set)'}")

    use_llm = bool(API_KEY)

    if use_llm:
        print("\nMode: LLM Agent (using OpenAI Client)")
        client = OpenAI(
            api_key=API_KEY,
            base_url=API_BASE_URL,
        )
    else:
        print("\nMode: Heuristic Baseline (HF_TOKEN not set)")
        client = None

    # Run 5 incidents per task for reasonable runtime (< 20 min)
    NUM_INCIDENTS = 5
    all_results = []

    for task_id in TASKS:
        task = TASKS[task_id]
        print(f"\n{'-' * 50}")
        print(f"Task: {task.name} ({task.difficulty})")
        print(f"{'-' * 50}")

        task_scores = []
        for i in range(NUM_INCIDENTS):
            seed = 3000 + i
            print(f"[START] task={task_id}", flush=True)
            if use_llm:
                result = run_llm_episode(task_id, i, seed, client)
            else:
                result = run_heuristic_episode(task_id, i, seed)

            print(f"[END] task={task_id} score={result['score']} steps={result['steps']}", flush=True)
            task_scores.append(result["score"])
            print(f"  Incident {i}: score={result['score']:.4f}, steps={result['steps']}")

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

    # Print summary
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print("INFERENCE RESULTS")
    print(f"{'=' * 60}")
    for r in all_results:
        print(f"\n  Task: {r['task_name']} ({r['difficulty']})")
        print(f"  Average Score: {r['average_score']:.4f}")
        print(f"  Score Range:   [{r['min_score']:.4f}, {r['max_score']:.4f}]")

    print(f"\n  Mode:    {'LLM Agent' if use_llm else 'Heuristic Baseline'}")
    print(f"  Model:   {MODEL_NAME}")
    print(f"  Runtime: {elapsed:.1f}s")
    print(f"{'=' * 60}")

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
    print(f"\nResults saved to inference_results.json")


if __name__ == "__main__":
    main()
