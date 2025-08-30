# src/db_utils.py
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

DB_FILE = os.path.join("data", "database.json")


# ============================ IO Helpers ============================

def load_database() -> Dict[str, Any]:
    """
    Load the entire database JSON into memory.
    Returns a structure with at least: {"features": [], "scans": []}
    """
    if not os.path.exists(DB_FILE):
        return {"features": [], "scans": []}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure keys exist
            data.setdefault("features", [])
            data.setdefault("scans", [])
            return data
    except (json.JSONDecodeError, IOError):
        return {"features": [], "scans": []}


def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    """Write JSON atomically to avoid partial writes."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def save_database(data: Dict[str, Any]) -> None:
    """Persist the database structure to disk."""
    data.setdefault("features", [])
    data.setdefault("scans", [])
    _atomic_write(DB_FILE, data)


# ============================ Features ==============================

def add_or_update_feature(db_data: Dict[str, Any], feature_details: Dict[str, Any]) -> str:
    """
    Add a new feature or update an existing one.
    - If feature_details['id'] exists, replace the stored feature with this dict.
    - Otherwise create a new feature id.
    Returns the feature id.
    """
    feature_id = feature_details.get("id")
    if feature_id:
        for i, feature in enumerate(db_data.get("features", [])):
            if feature.get("id") == feature_id:
                db_data["features"][i] = feature_details
                return feature_id
    # New feature
    feature_id = str(uuid.uuid4())
    feature_details = {**feature_details, "id": feature_id}
    db_data.setdefault("features", []).append(feature_details)
    return feature_id


def delete_features(db_data: Dict[str, Any], feature_ids: List[str]) -> Tuple[int, int]:
    """
    Delete features by id AND all associated scans.
    Returns (deleted_features_count, deleted_scans_count).
    """
    feature_ids_set = set(feature_ids or [])
    # Delete features
    features_before = len(db_data.get("features", []))
    db_data["features"] = [f for f in db_data.get("features", []) if f.get("id") not in feature_ids_set]
    features_after = len(db_data["features"])
    deleted_features = features_before - features_after

    # Delete scans linked to these features
    scans_before = len(db_data.get("scans", []))
    db_data["scans"] = [s for s in db_data.get("scans", []) if s.get("feature_id") not in feature_ids_set]
    scans_after = len(db_data["scans"])
    deleted_scans = scans_before - scans_after

    return deleted_features, deleted_scans


# ============================== Scans ===============================

def add_scan(
    db_data: Dict[str, Any],
    feature_id: str,
    feature_snapshot: Dict[str, Any],
    analysis: Dict[str, Any],
    *,
    audit_meta: Optional[Dict[str, Any]] = None,
    version: Optional[str] = "v1"
) -> str:
    """
    Append a new scan entry for a feature.
    - Stores minimal audit info (no feature-text hashes or terminology).
    - Uses timestamp_utc for ordering; also writes legacy 'timestamp' for back-compat.
    """
    scan_id = str(uuid.uuid4())
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    scan_entry: Dict[str, Any] = {
        "scan_id": scan_id,
        "feature_id": feature_id,
        "timestamp_utc": timestamp_utc,
        "timestamp": timestamp_utc,  # legacy alias for older UI code
        "version": version,
        "feature_snapshot": feature_snapshot,
        "analysis": analysis,
    }

    if audit_meta:
        allowed_keys = {
            "audit_id",
            "status",
            "model",
            "raw_output_hash",
            "legal_db_fingerprint",
            "rules_context_ids",
            "rules_context_fingerprint",
            "prompt_included",
            "context_text_included",
        }
        scan_entry["audit"] = {k: v for k, v in audit_meta.items() if k in allowed_keys}

    db_data.setdefault("scans", []).append(scan_entry)
    return scan_id


def get_scans_for_feature(db_data: Dict[str, Any], feature_id: str) -> List[Dict[str, Any]]:
    """
    Return scans for a feature, sorted newest-first.
    Supports both 'timestamp_utc' and legacy 'timestamp'.
    """
    scans = [s for s in db_data.get("scans", []) if s.get("feature_id") == feature_id]
    return sorted(
        scans,
        key=lambda s: (s.get("timestamp_utc") or s.get("timestamp") or ""),
        reverse=True
    )
