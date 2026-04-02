"""Quick verification script for the IT Incident Triage Environment."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dataclasses import asdict
from server.incident_env import IncidentTriageEnvironment
from server.tasks import TASKS, grade
from server.baseline_agent import run_heuristic_baseline

def test_basic_flow():
    print("=== Test 1: Basic Environment Flow ===")
    env = IncidentTriageEnvironment()
    
    # Reset
    obs = env.reset(seed=42, task_id="task_1_classify", incident_index=0)
    print(f"Incident: {obs.incident_title}")
    print(f"Service:  {obs.service_affected}")
    print(f"Task:     {obs.task_id}")
    print(f"Done:     {obs.done}")
    assert not obs.done, "Should not be done after reset"
    
    # Classify severity
    obs = env.step({"action_type": "classify_severity", "severity": "SEV1"})
    print(f"Feedback: {obs.step_feedback}")
    print(f"Reward:   {obs.reward}")
    
    # Assign team
    obs = env.step({"action_type": "assign_team", "team": "platform"})
    print(f"Feedback: {obs.step_feedback}")
    print(f"Done:     {obs.done}")
    
    # Check grading
    score = grade("task_1_classify", env.state, env.current_incident)
    print(f"Score:    {score}")
    assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
    print("PASSED\n")

def test_all_tasks():
    print("=== Test 2: All Tasks ===")
    for task_id in TASKS:
        env = IncidentTriageEnvironment()
        obs = env.reset(seed=100, task_id=task_id, incident_index=0)
        assert obs.task_id == task_id
        print(f"  {task_id}: available_actions={obs.available_actions}")
    print("PASSED\n")

def test_graders_range():
    print("=== Test 3: Grader Score Range ===")
    for task_id in TASKS:
        for i in range(15):
            env = IncidentTriageEnvironment()
            env.reset(seed=i, task_id=task_id, incident_index=i)
            score = grade(task_id, env.state, env.current_incident)
            assert 0.0 <= score <= 1.0, f"Score {score} out of [0,1] for {task_id} incident {i}"
    print("  All grader scores in [0.0, 1.0]")
    print("PASSED\n")

def test_baseline():
    print("=== Test 4: Heuristic Baseline ===")
    results = run_heuristic_baseline()
    for r in results:
        print(f"  {r['task_name']} ({r['difficulty']})")
        print(f"    Average: {r['average_score']}")
        print(f"    Range:   [{r['min_score']}, {r['max_score']}]")
        assert 0.0 <= r['average_score'] <= 1.0
    print("PASSED\n")

def test_state():
    print("=== Test 5: State Management ===")
    env = IncidentTriageEnvironment()
    env.reset(seed=1, task_id="task_3_resolve", incident_index=2)
    
    s = env.state
    assert s.step_count == 0
    assert s.severity_classified == False
    assert s.diagnosed == False
    
    env.step({"action_type": "classify_severity", "severity": "SEV2"})
    s = env.state
    assert s.step_count == 1
    assert s.severity_classified == True
    assert s.severity_value == "SEV2"
    print("  State tracking correct")
    print("PASSED\n")

if __name__ == "__main__":
    test_basic_flow()
    test_all_tasks()
    test_graders_range()
    test_baseline()
    test_state()
    print("=" * 50)
    print("ALL TESTS PASSED")
    print("=" * 50)
