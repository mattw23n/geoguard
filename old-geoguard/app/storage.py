
# Audit trail persistence
import json
import os

def persist_audit(record, path="audit/audit.jsonl"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
