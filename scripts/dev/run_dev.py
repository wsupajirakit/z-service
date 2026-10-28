import os
import sys
import subprocess
import time
import signal

# Read .env file to check dev_mode setting
dev_mode = False
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("dev_mode="):
                val = line.split("=", 1)[1].strip()
                if val == "1":
                    dev_mode = True

# If dev_mode is not 1 (or absent), fall back to original concurrently behavior
if not dev_mode:
    print("[dev_mode] dev_mode is not 1. Running original concurrently command...")
    try:
        cmd = "npx concurrently \"npm run serv:backend\" \"npm run serv:frontend\""
        sys.exit(subprocess.call(cmd, shell=True))
    except KeyboardInterrupt:
        sys.exit(0)

# If dev_mode = 1:
print("[dev_mode] dev_mode=1 detected. Enforcing strict ports and clearing listening processes.")

def kill_ports(ports):
    for port in ports:
        try:
            # lsof -t -iTCP:port -sTCP:LISTEN returns PIDs of listening processes
            cmd = ["lsof", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            pids = [int(pid) for pid in output.split() if pid.isdigit()]
            for pid in pids:
                print(f"[dev_mode] Killing PID {pid} listening on port {port}")
                os.kill(pid, signal.SIGKILL)
        except subprocess.CalledProcessError:
            # lsof returns non-zero code if no process is found
            pass
        except Exception as e:
            print(f"[dev_mode] Error killing port {port}: {e}")

kill_ports([6600, 9999])

backend_cmd = "cd backend && source venv/bin/activate && uvicorn main:app --reload --port 9999"
frontend_cmd = "cd dash && npm run dev -- --port 6600 --strictPort"

print(f"[dev_mode] Starting backend: {backend_cmd}")
print(f"[dev_mode] Starting frontend: {frontend_cmd}")

# Launch processes in their own process groups (preexec_fn=os.setsid) so we can clean them up completely
backend_proc = subprocess.Popen(backend_cmd, shell=True, preexec_fn=os.setsid)
frontend_proc = subprocess.Popen(frontend_cmd, shell=True, preexec_fn=os.setsid)

def shutdown():
    print("\n[dev_mode] Stopping development servers...")
    # Kill the entire process groups
    for proc in (backend_proc, frontend_proc):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
    time.sleep(1)
    for proc in (backend_proc, frontend_proc):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception:
            pass
    sys.exit(0)

# Register signals for clean exit
def signal_handler(sig, frame):
    shutdown()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

try:
    while True:
        if backend_proc.poll() is not None:
            print("[dev_mode] Backend process exited.")
            shutdown()
        if frontend_proc.poll() is not None:
            print("[dev_mode] Frontend process exited.")
            shutdown()
        time.sleep(1)
except KeyboardInterrupt:
    shutdown()
