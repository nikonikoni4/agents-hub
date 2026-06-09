from agents_hub.api.app import app
for i, r in enumerate(app.routes):
    if hasattr(r, "path"):
        m = getattr(r, "methods", "WS")
        if "files" in r.path or "group-chat" in r.path:
            print(f"{i}: {r.path} {m}")
