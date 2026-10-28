with open("backend/main.py", "r") as f:
    content = f.read()

# Add gold_stop_event
content = content.replace(
    'gold_job_lock = threading.Lock()',
    'gold_job_lock = threading.Lock()\ngold_stop_event = threading.Event()'
)

# Clear event on start
content = content.replace(
    'gold_job.update({"status": "running", "message": "", "started_at": datetime.now(current_tz()).isoformat(),\n                     "finished_at": None, "folder_link": None, "folder_name": None, "result": None})\n    try:',
    'gold_job.update({"status": "running", "message": "", "started_at": datetime.now(current_tz()).isoformat(),\n                     "finished_at": None, "folder_link": None, "folder_name": None, "result": None})\n    gold_stop_event.clear()\n    try:'
)

# Add stop endpoint
stop_endpoint = """
@app.post("/api/gold/automate/stop")
async def stop_gold_job():
    if gold_job["status"] == "running":
        gold_stop_event.set()
        return {"detail": "Stop signal sent"}
    return {"detail": "No job running"}
"""
content = content.replace(
    '@app.post("/api/gold/automate")\nasync def start_gold_job(req: GoldAnalyzeRequest):',
    stop_endpoint.strip() + '\n\n@app.post("/api/gold/automate")\nasync def start_gold_job(req: GoldAnalyzeRequest):'
)

# Add checks in _gold_analyze_core
target_loop = """
    for tf in GOLD_TIMEFRAMES:
        try:
"""
replaced_loop = """
    for tf in GOLD_TIMEFRAMES:
        if gold_stop_event.is_set():
            raise Exception("Stopped by user")
        try:
"""
content = content.replace(target_loop, replaced_loop)

target_gemini = """
    # 3) Build Prompt & Call Gemini
"""
replaced_gemini = """
    if gold_stop_event.is_set():
        raise Exception("Stopped by user")

    # 3) Build Prompt & Call Gemini
"""
content = content.replace(target_gemini, replaced_gemini)

with open("backend/main.py", "w") as f:
    f.write(content)
