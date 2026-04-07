"""
Baseline Inference Script for IT Incident Triage Environment.

Uses the OpenAI API client to run an LLM agent against all 3 tasks.
Reads OPENAI_API_KEY from environment variables.

Usage:
    export OPENAI_API_KEY=sk-...
    python baseline.py

    # Or with a specific base URL:
    export OPENAI_BASE_URL=http://localhost:8000/v1
    python baseline.py

    # Or run against a deployed environment:
    python baseline.py --env-url https://your-space.hf.space
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


from server.incident_env import IncidentTriageEnvironment
from server.tasks import TASKS, grade


SYSTEM_PROMPT = """You are an experienced Site Reliability Engineer (SRE) handling IT incidents.
You will be given an IT incident with symptoms, logs, metrics, and context.
Your task is to triage and resolve the incident by taking appropriate actions.

For each step, respond with a JSON object containing:
- "action_type": The action to take
- Plus the relevant fields for that action type

Available action types and their fields:
- classify_severity: {"severity": "SEV1|SEV2|SEV3|SEV4"}
- diagnose: {"root_cause": "...", "explanation": "..."}
- assign_team: {"team": "platform|database|networking|security|application|infrastructure"}
- remediate: {"remediation": "rollback_deploy|restart_service|scale_horizontally|fix_config|failover_db|flush_cache|block_traffic|rotate_credentials"}
- communicate: {"message": "...", "audience": "engineering|management|customers"}
- escalate: {"reason": "..."}
- resolve: {"summary": "..."}

Respond ONLY with valid JSON. No additional text."""


def run_llm_agent(
    task_id: str,
    incident_index: int,
    seed: int,
    client: Optional[Any] = None,
    model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """Run an LLM agent on a single task/incident combination."""
    env = IncidentTriageEnvironment()
    obs = env.reset(seed=seed, task_id=task_id, incident_index=incident_index)
    obs_dict = asdict(obs)
    task = TASKS[task_id]

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"TASK: {task.description}\n\n"
            f"INCIDENT: {obs_dict['incident_title']}\n"
            f"Description: {obs_dict['incident_description']}\n"
            f"Service: {obs_dict['service_affected']}\n"
            f"Affected Users: {obs_dict['affected_users']}\n"
            f"Symptoms:\n" + "\n".join(f"  - {s}" for s in obs_dict['symptoms']) + "\n"
            f"Logs:\n" + "\n".join(f"  {l}" for l in obs_dict['logs']) + "\n"
            f"Metrics: {json.dumps(obs_dict['metrics'], indent=2)}\n"
            f"Hints: {obs_dict['hints']}\n\n"
            f"Available actions: {obs_dict['available_actions']}\n"
            f"Max steps: {task.max_steps}\n\n"
            f"Take your actions one at a time. Respond with JSON for each action."
        )},
    ]

    step_count = 0
    while not env.is_done and step_count < task.max_steps:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.0,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            action_text = response.choices[0].message.content.strip()
            action_dict = json.loads(action_text)

            # Ensure action_type is present
            if "action_type" not in action_dict:
                break

            obs = env.step(action_dict)
            obs_dict = asdict(obs)
            step_count += 1

            messages.append({"role": "assistant", "content": action_text})
            messages.append({"role": "user", "content": (
                f"Feedback: {obs_dict['step_feedback']}\n"
                f"Reward: {obs_dict['reward']}\n"
                f"Done: {obs_dict['done']}\n"
                f"Steps taken: {step_count}/{task.max_steps}\n"
                "Take your next action (JSON only)."
            )})
        except Exception as e:
            print(f"  Error: {e}")
            break

    score = grade(task_id, env.state, env.current_incident)
    return {
        "task_id": task_id,
        "incident_index": incident_index,
        "score": score,
        "steps": step_count,
        "total_reward": env.state.total_reward,
    }


def run_heuristic_baseline_local() -> List[Dict[str, Any]]:
    """Run the heuristic (non-LLM) baseline locally."""
    from server.baseline_agent import run_heuristic_baseline
    return run_heuristic_baseline()


def main():
    parser = argparse.ArgumentParser(description="Baseline inference for IT Incident Triage")
    parser.add_argument("--model", default="gpt-4o-mini", help="OpenAI model to use")
    parser.add_argument("--heuristic", action="store_true", help="Run heuristic baseline instead of LLM")
    parser.add_argument("--incidents", type=int, default=5, help="Number of incidents per task")
    parser.add_argument("--env-url", default=None, help="URL of deployed environment")
    args = parser.parse_args()

    print("=" * 60)
    print("IT Incident Triage Environment — Baseline Inference")
    print("=" * 60)

    if args.heuristic or not HAS_OPENAI or not os.environ.get("OPENAI_API_KEY"):
        print("\nRunning HEURISTIC baseline (deterministic, no API key needed)...")
        results = run_heuristic_baseline_local()

        print("\n" + "=" * 60)
        print("BASELINE RESULTS")
        print("=" * 60)
        for r in results:
            print(f"\n  Task: {r['task_name']} ({r['difficulty']})")
            print(f"  Average Score: {r['average_score']:.4f}")
            print(f"  Score Range:   [{r['min_score']:.4f}, {r['max_score']:.4f}]")

    else:
        print(f"\nRunning LLM baseline with model: {args.model}")
        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )

        all_results = []
        for task_id in TASKS:
            task = TASKS[task_id]
            print(f"\n{'─'*40}")
            print(f"Task: {task.name} ({task.difficulty})")
            print(f"{'─'*40}")

            task_scores = []
            for i in range(min(args.incidents, 15)):
                seed = 2000 + i
                result = run_llm_agent(task_id, i, seed, client, args.model)
                task_scores.append(result["score"])
                print(f"  Incident {i}: score={result['score']:.4f}, steps={result['steps']}, reward={result['total_reward']:.3f}")

            avg = sum(task_scores) / len(task_scores)
            all_results.append({
                "task_id": task_id,
                "task_name": task.name,
                "difficulty": task.difficulty,
                "average_score": round(avg, 4),
                "individual_scores": task_scores,
            })

        print("\n" + "=" * 60)
        print("BASELINE RESULTS")
        print("=" * 60)
        for r in all_results:
            print(f"\n  Task: {r['task_name']} ({r['difficulty']})")
            print(f"  Average Score: {r['average_score']:.4f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
