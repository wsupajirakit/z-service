import concurrent.futures
import time

def hang():
    time.sleep(100)
    return "done"

def test_context_manager():
    print("Starting context manager test")
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(hang)
            future.result(timeout=1)
    except Exception as e:
        print("Caught exception:", e)
    print("Context manager exited")

def test_no_wait():
    print("Starting no-wait test")
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(hang)
    try:
        future.result(timeout=1)
    except Exception as e:
        print("Caught exception:", e)
    executor.shutdown(wait=False, cancel_futures=True)
    print("No-wait test exited")

test_no_wait()
