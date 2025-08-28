import json
import os
import uuid

from datetime import datetime

DB_FILE = os.path.join("data", "database.json")


def load_database():
    """Loads the entire database (features and scans) from the JSON file."""
    if not os.path.exists(DB_FILE):
        return {"features": [], "scans": []}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"features": [], "scans": []}


def save_database(data):
    """Saves the entire database to the JSON file."""
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        print(f"Error saving database: {e}")


def add_or_update_feature(db_data, feature_details):
    """Adds a new feature or updates an existing one."""
    feature_id = feature_details.get("id")
    if feature_id:  # Update existing
        for i, feature in enumerate(db_data["features"]):
            if feature["id"] == feature_id:
                db_data["features"][i] = feature_details
                return feature_id
    else:  # Add new
        feature_id = str(uuid.uuid4())
        feature_details["id"] = feature_id
        db_data["features"].append(feature_details)
        return feature_id
    return None


def add_scan(db_data, feature_id, feature_snapshot, analysis):
    """Adds a new scan result to the database."""
    scan_entry = {
        "scan_id": str(uuid.uuid4()),
        "feature_id": feature_id,
        "timestamp": datetime.now().isoformat(),
        "feature_snapshot": feature_snapshot,
        "analysis": analysis,
    }
    db_data["scans"].append(scan_entry)


def get_scans_for_feature(db_data, feature_id):
    """Retrieves all scans associated with a specific feature ID."""
    scans = [
        scan for scan in db_data["scans"] if scan["feature_id"] == feature_id
    ]
    # Sort by timestamp, newest first
    return sorted(scans, key=lambda x: x["timestamp"], reverse=True)