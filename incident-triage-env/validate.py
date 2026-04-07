"""
Pre-Submission Validator for OpenEnv Competition.

Replicates the exact checks from the problem statement:
1. HF Space deploys and responds to reset()
2. OpenEnv spec compliance (openenv.yaml, typed models, step/reset/state)
3. Dockerfile builds (verified separately)
4. Baseline reproduces (inference script completes, produces scores)
5. 3+ tasks with graders (scores in 0.0-1.0 range)
"""

import json
import os
import sys
import time
import requests
import yaml

SPACE_URL = "https://emerald789-incident-triage-env.hf.space"
PROJECT_DIR = r"C:\Users\DELL\.gemini\antigravity\scratch\incident-triage-env"

passed = 0
failed = 0
total = 0

def check(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} — {detail}")

def main():
    global passed, failed

    print("=" * 60)
    print("OpenEnv Pre-Submission Validator")
    print(f"Space: {SPACE_URL}")
    print("=" * 60)

    # ── CHECK 1: HF Space deploys and responds ───────────────────
    print("\n1. HF Space Deployment")
    try:
        r = requests.get(f"{SPACE_URL}/health", timeout=30)
        check("Space responds to /health", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        check("Health returns valid JSON", "status" in data, str(data))
    except Exception as e:
        check("Space is reachable", False, str(e))

    # ── CHECK 2: reset() works ─────────────────────────────────
    print("\n2. reset() Endpoint")
    try:
        r = requests.post(f"{SPACE_URL}/reset", json={"task_id": "task_1_classify", "seed": 42}, timeout=30)
        check("POST /reset returns 200", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        obs = data.get("observation", {})
        check("reset() returns observation", "observation" in data)
        check("Observation has incident_title", bool(obs.get("incident_title")))
        check("Observation has symptoms", len(obs.get("symptoms", [])) > 0)
        check("Observation has logs", len(obs.get("logs", [])) > 0)
        check("Observation has metrics", len(obs.get("metrics", {})) > 0)
        check("Observation has done=False", obs.get("done") == False)
        check("Observation has available_actions", len(obs.get("available_actions", [])) > 0)
    except Exception as e:
        check("reset() works", False, str(e))

    # ── CHECK 3: step() works ─────────────────────────────────
    print("\n3. step() Endpoint")
    try:
        r = requests.post(f"{SPACE_URL}/step",
            json={"action_type": "classify_severity", "severity": "SEV1"}, timeout=30)
        check("POST /step returns 200", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        check("step() returns observation", "observation" in data)
        check("step() returns reward", "reward" in data)
        check("step() returns done", "done" in data)
        check("step() returns info", "info" in data)
    except Exception as e:
        check("step() works", False, str(e))

    # ── CHECK 4: state() works ─────────────────────────────────
    print("\n4. state() Endpoint")
    try:
        r = requests.get(f"{SPACE_URL}/state", timeout=30)
        check("GET /state returns 200", r.status_code == 200, f"status={r.status_code}")
        data = r.json()
        state = data.get("state", {})
        check("state() returns state object", "state" in data)
        check("State has episode_id", bool(state.get("episode_id")))
        check("State has step_count", "step_count" in state)
    except Exception as e:
        check("state() works", False, str(e))

    # ── CHECK 5: openenv.yaml exists and is valid ──────────────
    print("\n5. OpenEnv Spec Compliance")
    yaml_path = os.path.join(PROJECT_DIR, "openenv.yaml")
    check("openenv.yaml exists", os.path.exists(yaml_path))
    if os.path.exists(yaml_path):
        with open(yaml_path) as f:
            spec = yaml.safe_load(f)
        check("spec_version present", "spec_version" in spec)
        check("name present", "name" in spec)
        check("type present", "type" in spec)
        check("runtime present", "runtime" in spec)
        check("app present", "app" in spec)
        check("port present", "port" in spec)

    # ── CHECK 6: 3+ tasks with graders ─────────────────────────
    print("\n6. Tasks & Graders")
    try:
        r = requests.get(f"{SPACE_URL}/tasks", timeout=30)
        check("GET /tasks returns 200", r.status_code == 200)
        tasks = r.json().get("tasks", [])
        check("3+ tasks defined", len(tasks) >= 3, f"found {len(tasks)}")

        difficulties = [t.get("difficulty") for t in tasks]
        check("Has easy task", "easy" in difficulties)
        check("Has medium task", "medium" in difficulties)
        check("Has hard task", "hard" in difficulties)

        for t in tasks:
            check(f"Task '{t['task_id']}' has action_fields", len(t.get("action_fields", {})) > 0)
            check(f"Task '{t['task_id']}' has grading_criteria", len(t.get("grading_criteria", {})) > 0)
    except Exception as e:
        check("Tasks endpoint works", False, str(e))

    # ── CHECK 7: Grader returns score in [0.0, 1.0] ───────────
    print("\n7. Grader Scores")
    try:
        # Reset and play a quick episode
        requests.post(f"{SPACE_URL}/reset", json={"task_id": "task_1_classify", "seed": 99}, timeout=30)
        requests.post(f"{SPACE_URL}/step", json={"action_type": "classify_severity", "severity": "SEV1"}, timeout=30)
        requests.post(f"{SPACE_URL}/step", json={"action_type": "assign_team", "team": "platform"}, timeout=30)

        r = requests.post(f"{SPACE_URL}/grader", timeout=30)
        check("POST /grader returns 200", r.status_code == 200)
        grader = r.json()
        score = grader.get("score", -1)
        check("Grader score is a number", isinstance(score, (int, float)))
        check("Grader score in [0.0, 1.0]", 0.0 <= score <= 1.0, f"score={score}")
        check("Grader returns done flag", "done" in grader)
    except Exception as e:
        check("Grader works", False, str(e))

    # ── CHECK 8: Baseline endpoint ─────────────────────────────
    print("\n8. Baseline Endpoint")
    try:
        r = requests.post(f"{SPACE_URL}/baseline", timeout=120)
        check("POST /baseline returns 200", r.status_code == 200, f"status={r.status_code}")
        results = r.json().get("baseline_results", [])
        check("Baseline returns results for 3 tasks", len(results) >= 3, f"got {len(results)}")
        for res in results:
            avg = res.get("average_score", -1)
            check(f"Baseline '{res['task_name']}' score in [0,1]", 0.0 <= avg <= 1.0, f"avg={avg}")
    except Exception as e:
        check("Baseline works", False, str(e))

    # ── CHECK 9: Dockerfile exists ─────────────────────────────
    print("\n9. Dockerfile")
    df_path = os.path.join(PROJECT_DIR, "Dockerfile")
    check("Dockerfile exists", os.path.exists(df_path))

    # ── CHECK 10: Baseline script exists ────────────────────────
    print("\n10. Baseline Script")
    bl_path = os.path.join(PROJECT_DIR, "baseline.py")
    check("baseline.py exists", os.path.exists(bl_path))
    if os.path.exists(bl_path):
        with open(bl_path) as f:
            content = f.read()
        check("Reads OPENAI_API_KEY from env", "OPENAI_API_KEY" in content)
        check("Uses OpenAI client", "OpenAI" in content)

    # ── SUMMARY ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed}/{total} checks passed, {failed} failed")
    if failed == 0:
        print("STATUS: ALL CHECKS PASSED — READY TO SUBMIT!")
    else:
        print("STATUS: SOME CHECKS FAILED — review above")
    print("=" * 60)

if __name__ == "__main__":
    main()
