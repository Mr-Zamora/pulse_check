#!/usr/bin/env python3
"""
Race condition test script for Pulse Check
Simulates concurrent student submissions to verify thread safety
"""

import requests
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "http://localhost:5000"
ROOM_ID = "race_test"
QUESTION_ID = "q_test"

def submit_answer(student_id, answer):
    """Submit an answer as a student"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/submit",
            json={
                "room_id": ROOM_ID,
                "q_id": QUESTION_ID,
                "student_name": f"Student{student_id}",
                "ans": answer
            },
            timeout=10
        )
        return {
            "student_id": student_id,
            "status": response.status_code,
            "success": response.status_code == 200,
            "response": response.json() if response.status_code == 200 else None
        }
    except Exception as e:
        return {
            "student_id": student_id,
            "status": 0,
            "success": False,
            "error": str(e)
        }

def poll_status(student_id):
    """Poll room status as a student"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/room/status",
            params={
                "room_id": ROOM_ID,
                "student_name": f"Student{student_id}"
            },
            timeout=10
        )
        return response.status_code == 200
    except:
        return False

def test_concurrent_submissions(num_students=10):
    """Test concurrent answer submissions"""
    print(f"\n{'='*60}")
    print(f"TEST 1: Concurrent Submissions ({num_students} students)")
    print(f"{'='*60}")
    
    results = []
    start_time = time.time()
    
    # Submit answers concurrently
    with ThreadPoolExecutor(max_workers=num_students) as executor:
        futures = [
            executor.submit(submit_answer, i, "A")
            for i in range(num_students)
        ]
        
        for future in as_completed(futures):
            results.append(future.result())
    
    elapsed = time.time() - start_time
    
    # Analyze results
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"\n✓ Completed in {elapsed:.2f} seconds")
    print(f"✓ Successful submissions: {successful}/{num_students}")
    print(f"✗ Failed submissions: {failed}/{num_students}")
    
    if failed > 0:
        print("\n⚠️  Failed submissions:")
        for r in results:
            if not r['success']:
                print(f"  - Student{r['student_id']}: {r.get('error', 'Unknown error')}")
    
    return successful == num_students

def test_concurrent_polling(num_students=10, duration=5):
    """Test concurrent status polling"""
    print(f"\n{'='*60}")
    print(f"TEST 2: Concurrent Polling ({num_students} students, {duration}s)")
    print(f"{'='*60}")
    
    stop_flag = threading.Event()
    poll_counts = [0] * num_students
    error_counts = [0] * num_students
    
    def poll_worker(student_id):
        while not stop_flag.is_set():
            success = poll_status(student_id)
            if success:
                poll_counts[student_id] += 1
            else:
                error_counts[student_id] += 1
            time.sleep(0.5)  # Poll every 500ms
    
    # Start polling threads
    threads = [
        threading.Thread(target=poll_worker, args=(i,))
        for i in range(num_students)
    ]
    
    start_time = time.time()
    for t in threads:
        t.start()
    
    # Run for specified duration
    time.sleep(duration)
    stop_flag.set()
    
    # Wait for all threads to finish
    for t in threads:
        t.join()
    
    elapsed = time.time() - start_time
    total_polls = sum(poll_counts)
    total_errors = sum(error_counts)
    
    print(f"\n✓ Completed in {elapsed:.2f} seconds")
    print(f"✓ Total successful polls: {total_polls}")
    print(f"✗ Total errors: {total_errors}")
    print(f"✓ Average polls per student: {total_polls/num_students:.1f}")
    
    if total_errors > 0:
        print(f"\n⚠️  Error rate: {total_errors/(total_polls+total_errors)*100:.1f}%")
    
    return total_errors == 0

def test_short_answer_resubmission(num_resubmissions=5):
    """Test SHORT answer resubmission race conditions"""
    print(f"\n{'='*60}")
    print(f"TEST 3: SHORT Answer Resubmission ({num_resubmissions} times)")
    print(f"{'='*60}")
    
    student_name = "ResubmitTester"
    
    for i in range(num_resubmissions):
        result = submit_answer(student_name, f"Answer_{i}")
        if not result['success']:
            print(f"✗ Resubmission {i+1} failed")
            return False
        time.sleep(0.1)  # Small delay between resubmissions
    
    print(f"✓ All {num_resubmissions} resubmissions successful")
    return True

def main():
    print("\n" + "="*60)
    print("PULSE CHECK - RACE CONDITION TEST SUITE")
    print("="*60)
    print("\nMake sure the server is running on http://localhost:5000")
    print("Press Ctrl+C to cancel\n")
    
    try:
        # Check server is running
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code != 200:
            print("✗ Server not responding correctly")
            return
    except:
        print("✗ Cannot connect to server. Is it running?")
        return
    
    print("✓ Server is running\n")
    
    # Run tests
    test_results = []
    
    test_results.append(("Concurrent Submissions (10)", test_concurrent_submissions(10)))
    time.sleep(1)
    
    test_results.append(("Concurrent Submissions (20)", test_concurrent_submissions(20)))
    time.sleep(1)
    
    test_results.append(("Concurrent Polling", test_concurrent_polling(10, 5)))
    time.sleep(1)
    
    test_results.append(("SHORT Answer Resubmission", test_short_answer_resubmission(5)))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}\n")
    
    for test_name, passed in test_results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(result for _, result in test_results)
    
    print(f"\n{'='*60}")
    if all_passed:
        print("✓ ALL TESTS PASSED - No race conditions detected")
    else:
        print("✗ SOME TESTS FAILED - Race conditions may exist")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Tests cancelled by user\n")
    except Exception as e:
        print(f"\n✗ Test suite error: {e}\n")
