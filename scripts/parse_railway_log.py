import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
print("entries:", len(data))
keys = (
    "ERROR",
    "WARNING",
    "CRITICAL",
    "Exception",
    "Traceback",
    "Conflict",
    "sent ",
    "campaign",
    "NameError",
    "IMAP",
    "imap",
    "stop",
    "paused",
    "launch",
    'File "/app',
)
for e in data:
    m = e.get("message", "")
    if any(k.lower() in m.lower() for k in keys):
        print(e.get("timestamp", "")[:19], m[:280])
print("--- last 20 ---")
for e in data[-20:]:
    print(e.get("timestamp", "")[:19], e.get("message", "")[:220])
