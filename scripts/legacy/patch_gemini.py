with open("backend/main.py", "r") as f:
    content = f.read()

target = """
    analysis = _call_gemini(req.model, prompt)

    return {
"""
replacement = """
    if gold_stop_event.is_set():
        raise Exception("Stopped by user")

    analysis = _call_gemini(req.model, prompt)

    return {
"""
content = content.replace(target, replacement)

with open("backend/main.py", "w") as f:
    f.write(content)
