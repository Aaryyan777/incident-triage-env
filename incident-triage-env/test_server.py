"""Server endpoint integration test."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

import requests

BASE = "http://localhost:8000"

def test_endpoints():
    # 1. Health
    r = requests.get(f"{BASE}/health")
    assert r.status_code == 200
    print(f"✓ /health: {r.json()['status']}")

    # 2. Tasks
    r = requests.get(f"{BASE}/tasks")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    assert len(tasks) == 3
    print(f"✓ /tasks: {len(tasks)} tasks returned")

    # 3. Reset
    r = requests.post(f"{BASE}/reset", json={"task_id": "task_1_classify", "seed": 42})
    assert r.status_code == 200
    obs = r.json()["observation"]
    print(f"✓ /reset: incident={obs['incident_title']}")

    # 4. Step — classify severity
    r = requests.post(f"{BASE}/step", json={"action_type": "classify_severity", "severity": "SEV1"})
    assert r.status_code == 200
    data = r.json()
    print(f"✓ /step (classify): reward={data['reward']}, done={data['done']}")

    # 5. Step — assign team
    r = requests.post(f"{BASE}/step", json={"action_type": "assign_team", "team": "platform"})
    assert r.status_code == 200
    data = r.json()
    print(f"✓ /step (assign): reward={data['reward']}, done={data['done']}")

    # 6. State
    r = requests.get(f"{BASE}/state")
    assert r.status_code == 200
    state = r.json()["state"]
    print(f"✓ /state: step_count={state['step_count']}, grader_score={state['grader_score']}")

    # 7. Grader
    r = requests.post(f"{BASE}/grader")
    assert r.status_code == 200
    grader = r.json()
    print(f"✓ /grader: score={grader['score']}, done={grader['done']}")

    # 8. Baseline
    r = requests.post(f"{BASE}/baseline", timeout=60)
    assert r.status_code == 200
    baseline = r.json()["baseline_results"]
    for b in baseline:
        print(f"✓ /baseline: {b['task_name']} avg={b['average_score']}")

    print("\n" + "=" * 50)
    print("ALL ENDPOINT TESTS PASSED")
    print("=" * 50)

if __name__ == "__main__":
    test_endpoints()
