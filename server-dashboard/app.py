from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import quote

from flask import (
    Flask,
    Response,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = (
    BASE_DIR / "server-dashboard"
    if (BASE_DIR / "server-dashboard").is_dir()
    else BASE_DIR
)
TEMPLATES_DIR = PROJECT_DIR / "templates"
STATIC_DIR = PROJECT_DIR / "static"
DATA_DIR = PROJECT_DIR / "data"
RODS_FILE = DATA_DIR / "rods.json"
ENCHANTS_FILE = DATA_DIR / "enchants.json"
FEEDBACK_FILE = DATA_DIR / "feedback.json"
USERS_FILE = DATA_DIR / "users.json"
CHAT_FILE = DATA_DIR / "chat.json"
ACTIVITY_FILE = DATA_DIR / "activity.json"
TUTORIALS_DIR = STATIC_DIR / "tutorials"

DEFAULT_PORT = int(os.environ.get("PORT", "3030"))
PASSWORD_ITERATIONS = 200_000
OWNER_USERNAME = "Makoral.Dev"
OWNER_PASSWORD = "TeamTea2421"

DEFAULT_CHANNELS = [
    {"name": "general", "topic": "General discussion"},
    {"name": "support", "topic": "User help and issue triage"},
    {"name": "announcements", "topic": "Release notes and updates"},
]

ALLOWED_TUTORIAL_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}

DEFAULT_ENCHANTS = [
    {"name": "Swift", "type": "primary", "effect": "+30% Lure Speed"},
    {"name": "Hasty", "type": "primary", "effect": "+55% Lure Speed"},
    {"name": "Lucky", "type": "primary", "effect": "+20% Luck, +15% Lure Speed"},
    {"name": "Divine", "type": "primary", "effect": "+45% Luck, +20% Resilience, +20% Lure Speed"},
    {"name": "Breezed", "type": "primary", "effect": "+65% Luck, +10% Lure Speed"},
    {"name": "Quantum", "type": "primary", "effect": "+25% Luck"},
    {"name": "Piercing", "type": "primary", "effect": "+0.2 Control"},
    {"name": "Invincible", "type": "primary", "effect": "Inf Max Kg"},
    {"name": "Herculean", "type": "primary", "effect": "+25000 Max Kg, +0.2 Control"},
    {"name": "Mystical", "type": "primary", "effect": "+25% Luck, +45% Resilience, +15% Lure Speed"},
    {"name": "Resilient", "type": "primary", "effect": "+35% Resilience"},
    {"name": "Controlled", "type": "primary", "effect": "+0.05 Control"},
    {"name": "Abyssal", "type": "primary", "effect": "+10% Resilience"},
    {"name": "Quality", "type": "primary", "effect": "+15% Lure Speed, +15% Luck"},
    {"name": "Rapid", "type": "primary", "effect": "+30% Lure Speed"},
    {"name": "Unbreakable", "type": "primary", "effect": "+10000 Max Kg"},
    {"name": "Noir", "type": "secondary", "effect": "Mutation luck bonus."},
    {"name": "Sea Overlord", "type": "secondary", "effect": "Progress speed bonus."},
    {"name": "Blessed Song", "type": "secondary", "effect": "Chance to instantly catch fish."},
    {"name": "Wormhole", "type": "secondary", "effect": "Chance to wormhole fish."},
]

DEFAULT_CATCHING_TUNING = {
    "centerRatio": 0.35,
    "lookaheadMs": 60,
    "brakeSpeed": 0.95,
    "deadzonePx": 3,
    "fishVelocitySmoothing": 0.45,
    "barVelocitySmoothing": 0.40,
}

CATCHING_TUNING_LIMITS: dict[str, tuple[float, float]] = {
    "centerRatio": (0.15, 0.48),
    "lookaheadMs": (15, 120),
    "brakeSpeed": (0.20, 1.60),
    "deadzonePx": (1, 10),
    "fishVelocitySmoothing": (0.05, 0.95),
    "barVelocitySmoothing": (0.05, 0.95),
}

DISCRETE_CATCHING_FIELDS = {"lookaheadMs", "deadzonePx"}

DATA_LOCK = Lock()

app = Flask(
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
)
app.config["SECRET_KEY"] = os.environ.get(
    "DASHBOARD_SECRET_KEY", "fisch-dashboard-change-this-secret"
)
app.config["JSON_SORT_KEYS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def clone_json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def read_json(path: Path, fallback: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return clone_json(fallback)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, indent=2)
    temp_path.replace(path)


def generate_password_hash(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password_hash(password: str, stored_hash: str) -> bool:
    try:
        algo, iteration_str, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iteration_count = int(iteration_str)
        candidate_digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iteration_count
        ).hex()
        return hmac.compare_digest(candidate_digest, digest_hex)
    except Exception:
        return False


def normalize_feedback_entry(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(raw.get("id") or uuid.uuid4().hex[:12]),
        "createdAt": str(raw.get("createdAt") or now_iso()),
        "type": str(raw.get("type") or "General"),
        "description": str(raw.get("description") or ""),
        "rodName": str(raw.get("rodName") or ""),
        "clientTitle": str(raw.get("clientTitle") or ""),
        "clientVersion": str(raw.get("clientVersion") or ""),
        "read": bool(raw.get("read", False)),
        "archived": bool(raw.get("archived", False)),
    }


def sanitize_enchant_type(value: Any) -> str:
    return "secondary" if str(value or "").strip().lower() == "secondary" else "primary"


def normalize_enchant_record(raw: dict[str, Any]) -> dict[str, Any]:
    stats_raw = raw.get("stats", {}) if isinstance(raw.get("stats"), dict) else {}
    lure = safe_number(stats_raw.get("lure", raw.get("lure")))
    luck = safe_number(stats_raw.get("luck", raw.get("luck")))
    control = safe_number(stats_raw.get("control", raw.get("control")))
    resilience = safe_number(stats_raw.get("resilience", raw.get("resilience")))
    max_kg = normalize_max_kg(stats_raw.get("maxKg", raw.get("maxKg")))
    max_kg_percent = safe_number(stats_raw.get("maxKgPercent", raw.get("maxKgPercent")))

    return {
        "name": str(raw.get("name") or "").strip(),
        "type": sanitize_enchant_type(raw.get("type")),
        "effect": str(raw.get("effect") or raw.get("rawEffect") or "").strip(),
        "stats": {
            "lure": lure,
            "luck": luck,
            "control": control,
            "resilience": resilience,
            "maxKg": max_kg,
            "maxKgPercent": max_kg_percent,
        },
        "notes": str(raw.get("notes") or "").strip(),
        "updatedAt": str(raw.get("updatedAt") or now_iso()),
    }


def default_enchants_payload() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for item in DEFAULT_ENCHANTS:
        payload.append(normalize_enchant_record(item))
    return payload


def normalize_chat_payload(raw: dict[str, Any]) -> dict[str, Any]:
    channels_raw = raw.get("channels", [])
    messages_raw = raw.get("messages", [])

    channels: list[dict[str, Any]] = []
    seen = set()
    for channel in channels_raw if isinstance(channels_raw, list) else []:
        if isinstance(channel, str):
            name = channel.strip()
            topic = ""
            created_at = now_iso()
            created_by = "system"
        elif isinstance(channel, dict):
            name = str(channel.get("name", "")).strip()
            topic = str(channel.get("topic", "")).strip()
            created_at = str(channel.get("createdAt") or now_iso())
            created_by = str(channel.get("createdBy") or "system")
        else:
            continue

        if not name:
            continue
        lower_name = name.lower()
        if lower_name in seen:
            continue
        seen.add(lower_name)
        channels.append(
            {
                "name": name,
                "topic": topic,
                "createdAt": created_at,
                "createdBy": created_by,
            }
        )

    for default_channel in DEFAULT_CHANNELS:
        if default_channel["name"].lower() in seen:
            continue
        channels.append(
            {
                "name": default_channel["name"],
                "topic": default_channel["topic"],
                "createdAt": now_iso(),
                "createdBy": "system",
            }
        )
        seen.add(default_channel["name"].lower())

    valid_channel_names = {channel["name"].lower(): channel["name"] for channel in channels}

    messages: list[dict[str, Any]] = []
    for message in messages_raw if isinstance(messages_raw, list) else []:
        if not isinstance(message, dict):
            continue
        channel_name = str(message.get("channel", "")).strip()
        if channel_name.lower() not in valid_channel_names:
            continue
        message_text = str(message.get("text", "")).strip()
        if not message_text:
            continue
        messages.append(
            {
                "id": str(message.get("id") or uuid.uuid4().hex[:12]),
                "channel": valid_channel_names[channel_name.lower()],
                "author": str(message.get("author") or "unknown"),
                "text": message_text,
                "createdAt": str(message.get("createdAt") or now_iso()),
            }
        )

    return {"channels": channels, "messages": messages}


def append_activity(
    event_type: str, message: str, actor: str, meta: dict[str, Any] | None = None
) -> None:
    entry = {
        "id": uuid.uuid4().hex[:12],
        "type": event_type,
        "message": message,
        "actor": actor,
        "meta": meta or {},
        "createdAt": now_iso(),
    }
    with DATA_LOCK:
        activity = read_json(ACTIVITY_FILE, [])
        if not isinstance(activity, list):
            activity = []
        activity.insert(0, entry)
        write_json(ACTIVITY_FILE, activity[:500])


def find_user(users: list[dict[str, Any]], username: str) -> dict[str, Any] | None:
    lower_username = username.lower()
    for user in users:
        if str(user.get("username", "")).lower() == lower_username:
            return user
    return None


def get_password_version(user: dict[str, Any]) -> str:
    return str(user.get("passwordUpdatedAt") or user.get("createdAt") or "")


def ensure_data_files() -> None:
    with DATA_LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        TUTORIALS_DIR.mkdir(parents=True, exist_ok=True)

        if not RODS_FILE.exists():
            write_json(RODS_FILE, [])
        if not ENCHANTS_FILE.exists():
            write_json(ENCHANTS_FILE, default_enchants_payload())
        if not FEEDBACK_FILE.exists():
            write_json(FEEDBACK_FILE, [])
        if not USERS_FILE.exists():
            write_json(USERS_FILE, [])
        if not CHAT_FILE.exists():
            write_json(CHAT_FILE, {"channels": clone_json(DEFAULT_CHANNELS), "messages": []})
        if not ACTIVITY_FILE.exists():
            write_json(ACTIVITY_FILE, [])

        rods_raw = read_json(RODS_FILE, [])
        rods_normalized: list[dict[str, Any]] = []
        seen_rods: set[str] = set()
        for item in rods_raw if isinstance(rods_raw, list) else []:
            normalized = normalize_rod_record(item)
            if not normalized["name"]:
                continue
            key = normalized["name"].lower()
            if key in seen_rods:
                continue
            seen_rods.add(key)
            rods_normalized.append(normalized)
        write_json(RODS_FILE, rods_normalized)

        chat_payload = normalize_chat_payload(read_json(CHAT_FILE, {}))
        write_json(CHAT_FILE, chat_payload)

        enchants_raw = read_json(ENCHANTS_FILE, [])
        enchants_normalized: list[dict[str, Any]] = []
        seen_enchants: set[str] = set()
        for item in enchants_raw if isinstance(enchants_raw, list) else []:
            if not isinstance(item, dict):
                continue
            normalized = normalize_enchant_record(item)
            if not normalized["name"]:
                continue
            key = normalized["name"].lower()
            if key in seen_enchants:
                continue
            seen_enchants.add(key)
            enchants_normalized.append(normalized)

        if not enchants_normalized:
            enchants_normalized = default_enchants_payload()
        write_json(ENCHANTS_FILE, enchants_normalized)

        users = read_json(USERS_FILE, [])
        if not isinstance(users, list):
            users = []
        owner = find_user(users, OWNER_USERNAME)
        owner_hash = generate_password_hash(OWNER_PASSWORD)
        if owner:
            owner["passwordHash"] = owner_hash
            owner["role"] = "owner"
            owner["username"] = OWNER_USERNAME
            owner.setdefault("createdAt", now_iso())
            owner["passwordUpdatedAt"] = now_iso()
            owner.setdefault("lastLoginAt", "")
        else:
            users.append(
                {
                    "username": OWNER_USERNAME,
                    "passwordHash": owner_hash,
                    "role": "owner",
                    "createdAt": now_iso(),
                    "passwordUpdatedAt": now_iso(),
                    "lastLoginAt": "",
                }
            )
        write_json(USERS_FILE, users)


def get_session_user() -> dict[str, str] | None:
    username = str(session.get("username") or "").strip()
    session_version = str(session.get("passwordVersion") or "")
    if not username:
        return None

    users = read_json(USERS_FILE, [])
    if not isinstance(users, list):
        session.clear()
        return None

    user = find_user(users, username)
    if not user:
        session.clear()
        return None

    current_version = get_password_version(user)
    if session_version != current_version:
        session.clear()
        return None

    current_role = str(user.get("role") or "viewer")
    if str(session.get("role") or "") != current_role:
        session["role"] = current_role

    canonical_username = str(user.get("username") or username)
    if str(session.get("username") or "") != canonical_username:
        session["username"] = canonical_username

    return {"username": canonical_username, "role": current_role}


def is_role(user: dict[str, str] | None, allowed_roles: set[str]) -> bool:
    if not user:
        return False
    return user.get("role", "").lower() in allowed_roles


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if get_session_user():
            return view(*args, **kwargs)

        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "auth_required"}), 401
        return redirect(url_for("login_page"))

    return wrapped


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_session_user()
        if not user:
            return jsonify({"ok": False, "error": "auth_required"}), 401
        if not is_role(user, {"owner"}):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = get_session_user()
        if not user:
            return jsonify({"ok": False, "error": "auth_required"}), 401
        if not is_role(user, {"owner", "admin"}):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        return view(*args, **kwargs)

    return wrapped


def safe_number(value: Any) -> float | int | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except Exception:
        return None
    if number.is_integer():
        return int(number)
    return number


def normalize_max_kg(value: Any) -> float | int | str | None:
    if value in (None, ""):
        return None
    if isinstance(value, str) and value.lower() == "inf":
        return "inf"
    return safe_number(value)


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def clamp_number(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def normalize_catching_value(field_name: str, value: Any) -> float | int:
    parsed = safe_number(value)
    if parsed is None:
        parsed = DEFAULT_CATCHING_TUNING[field_name]

    lower, upper = CATCHING_TUNING_LIMITS[field_name]
    clamped = clamp_number(float(parsed), lower, upper)
    if field_name in DISCRETE_CATCHING_FIELDS:
        return int(round(clamped))
    return round(clamped, 4)


def default_learning_record() -> dict[str, Any]:
    return {
        "sampleCount": 0,
        "successCount": 0,
        "failureCount": 0,
        "popupDetectedCount": 0,
        "rollingAvgErrorPx": None,
        "multicolorRatio": None,
        "lastOutcome": "",
        "lastClientAt": "",
        "lastMergedAt": "",
    }


def normalize_rod_learning(raw: Any) -> dict[str, Any]:
    learning = default_learning_record()
    if not isinstance(raw, dict):
        return learning

    for key in ("sampleCount", "successCount", "failureCount", "popupDetectedCount"):
        parsed = safe_number(raw.get(key))
        if parsed is not None:
            learning[key] = max(0, int(parsed))

    avg_error = safe_number(raw.get("rollingAvgErrorPx"))
    if avg_error is not None:
        learning["rollingAvgErrorPx"] = round(max(0.0, float(avg_error)), 3)

    multicolor_ratio = safe_number(raw.get("multicolorRatio"))
    if multicolor_ratio is not None:
        learning["multicolorRatio"] = round(clamp_number(float(multicolor_ratio), 0.0, 1.0), 4)

    learning["lastOutcome"] = str(raw.get("lastOutcome") or "").strip().lower()
    learning["lastClientAt"] = str(raw.get("lastClientAt") or "")
    learning["lastMergedAt"] = str(raw.get("lastMergedAt") or "")
    return learning


def normalize_rod_record(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}

    stats_raw = raw.get("stats") if isinstance(raw.get("stats"), dict) else {}
    catching_raw = raw.get("catching") if isinstance(raw.get("catching"), dict) else {}

    if not stats_raw:
        stats_raw = raw
    if not catching_raw:
        catching_raw = raw

    name = str(raw.get("name") or "").strip()
    stats = {
        "lure": safe_number(stats_raw.get("lure")),
        "luck": safe_number(stats_raw.get("luck")),
        "control": safe_number(stats_raw.get("control")),
        "resilience": safe_number(stats_raw.get("resilience")),
        "maxKg": normalize_max_kg(stats_raw.get("maxKg")),
    }
    catching = {
        key: normalize_catching_value(key, catching_raw.get(key))
        for key in DEFAULT_CATCHING_TUNING.keys()
    }

    return {
        "name": name,
        "active": True if "active" not in raw else to_bool(raw.get("active")),
        "stats": stats,
        "catching": catching,
        "notes": str(raw.get("notes") or "").strip(),
        "passiveInfo": str(raw.get("passiveInfo") or "").strip(),
        "tutorialUrl": str(raw.get("tutorialUrl") or "").strip(),
        "learning": normalize_rod_learning(raw.get("learning")),
        "createdAt": str(raw.get("createdAt") or now_iso()),
        "updatedAt": str(raw.get("updatedAt") or now_iso()),
    }


def parse_client_result(payload: dict[str, Any]) -> bool:
    raw_result = str(payload.get("result") or payload.get("outcome") or "").strip().lower()
    if raw_result in {"success", "ok", "1", "true", "caught", "pass"}:
        return True
    if raw_result in {"failure", "fail", "0", "false", "miss", "timeout"}:
        return False
    return to_bool(payload.get("success"))


def merge_rod_learning_sample(rod: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    success = parse_client_result(payload)
    now = now_iso()

    catching = rod.setdefault("catching", {})
    for field_name in DEFAULT_CATCHING_TUNING.keys():
        catching[field_name] = normalize_catching_value(field_name, catching.get(field_name))

    incoming_tuning: dict[str, float | int] = {}
    for field_name in DEFAULT_CATCHING_TUNING.keys():
        parsed = safe_number(payload.get(field_name))
        if parsed is None:
            continue
        incoming_tuning[field_name] = normalize_catching_value(field_name, parsed)

    blend_weight = 0.16 if success else 0.08
    for field_name, incoming in incoming_tuning.items():
        current = float(catching.get(field_name, DEFAULT_CATCHING_TUNING[field_name]))
        merged = (current * (1 - blend_weight)) + (float(incoming) * blend_weight)
        catching[field_name] = normalize_catching_value(field_name, merged)

    if not success:
        # Failure samples nudge the model toward safer control until enough success data accumulates.
        catching["centerRatio"] = normalize_catching_value(
            "centerRatio", float(catching["centerRatio"]) + 0.004
        )
        catching["lookaheadMs"] = normalize_catching_value(
            "lookaheadMs", float(catching["lookaheadMs"]) + 1.0
        )
        catching["deadzonePx"] = normalize_catching_value(
            "deadzonePx", float(catching["deadzonePx"]) + 0.4
        )

    learning = normalize_rod_learning(rod.get("learning"))
    learning["sampleCount"] += 1
    if success:
        learning["successCount"] += 1
    else:
        learning["failureCount"] += 1

    popup_detected = to_bool(payload.get("popupDetected"))
    if popup_detected:
        learning["popupDetectedCount"] += 1

    avg_error = safe_number(payload.get("avgAbsErrorPx"))
    if avg_error is not None:
        prior_error = safe_number(learning.get("rollingAvgErrorPx"))
        next_error = float(avg_error) if prior_error is None else (float(prior_error) * 0.8) + (float(avg_error) * 0.2)
        learning["rollingAvgErrorPx"] = round(max(0.0, next_error), 3)

    frames = safe_number(payload.get("frames"))
    multicolor_frames = safe_number(payload.get("multicolorFrames"))
    if frames and multicolor_frames is not None and float(frames) > 0:
        ratio = clamp_number(float(multicolor_frames) / float(frames), 0.0, 1.0)
        prior_ratio = safe_number(learning.get("multicolorRatio"))
        merged_ratio = ratio if prior_ratio is None else (float(prior_ratio) * 0.75) + (ratio * 0.25)
        learning["multicolorRatio"] = round(clamp_number(merged_ratio, 0.0, 1.0), 4)

    learning["lastOutcome"] = "success" if success else "failure"
    learning["lastClientAt"] = str(payload.get("clientTimestamp") or now)
    learning["lastMergedAt"] = now

    rod["learning"] = learning
    rod["active"] = to_bool(rod.get("active", True))
    rod["updatedAt"] = now

    sample_count = max(1, int(learning["sampleCount"]))
    success_rate = round((int(learning["successCount"]) / sample_count) * 100, 2)
    return {"success": success, "successRate": success_rate, "sampleCount": sample_count}


def find_rod(rods: list[dict[str, Any]], rod_name: str) -> dict[str, Any] | None:
    lower_name = rod_name.lower()
    for rod in rods:
        if str(rod.get("name", "")).lower() == lower_name:
            return rod
    return None


def find_enchant(enchants: list[dict[str, Any]], enchant_name: str) -> dict[str, Any] | None:
    lower_name = enchant_name.lower()
    for enchant in enchants:
        if str(enchant.get("name", "")).lower() == lower_name:
            return enchant
    return None


def update_rod_record_from_payload(rod: dict[str, Any], payload: dict[str, Any]) -> None:
    stats_payload = payload.get("stats") if isinstance(payload.get("stats"), dict) else payload
    catching_payload = (
        payload.get("catching") if isinstance(payload.get("catching"), dict) else payload
    )

    stats = rod.setdefault("stats", {})
    catching = rod.setdefault("catching", {})

    for field_name in DEFAULT_CATCHING_TUNING.keys():
        catching[field_name] = normalize_catching_value(field_name, catching.get(field_name))

    if "lure" in stats_payload:
        stats["lure"] = safe_number(stats_payload.get("lure"))
    if "luck" in stats_payload:
        stats["luck"] = safe_number(stats_payload.get("luck"))
    if "control" in stats_payload:
        stats["control"] = safe_number(stats_payload.get("control"))
    if "resilience" in stats_payload:
        stats["resilience"] = safe_number(stats_payload.get("resilience"))
    if "maxKg" in stats_payload:
        stats["maxKg"] = normalize_max_kg(stats_payload.get("maxKg"))

    for key in (
        "centerRatio",
        "lookaheadMs",
        "brakeSpeed",
        "deadzonePx",
        "fishVelocitySmoothing",
        "barVelocitySmoothing",
    ):
        if key in catching_payload:
            parsed = safe_number(catching_payload.get(key))
            if parsed is not None:
                catching[key] = normalize_catching_value(key, parsed)

    if "notes" in payload:
        rod["notes"] = str(payload.get("notes") or "")
    if "passiveInfo" in payload:
        rod["passiveInfo"] = str(payload.get("passiveInfo") or "")
    if "tutorialUrl" in payload:
        rod["tutorialUrl"] = str(payload.get("tutorialUrl") or "")
    if "active" in payload:
        rod["active"] = to_bool(payload.get("active"))
    elif "active" not in rod:
        rod["active"] = True
    if "learning" not in rod:
        rod["learning"] = default_learning_record()
    rod["updatedAt"] = now_iso()


def update_enchant_record_from_payload(enchant: dict[str, Any], payload: dict[str, Any]) -> None:
    stats_payload = payload.get("stats") if isinstance(payload.get("stats"), dict) else payload
    stats = enchant.setdefault("stats", {})

    if "name" in payload:
        enchant["name"] = str(payload.get("name") or "").strip()
    if "type" in payload:
        enchant["type"] = sanitize_enchant_type(payload.get("type"))
    if "effect" in payload:
        enchant["effect"] = str(payload.get("effect") or "").strip()
    if "notes" in payload:
        enchant["notes"] = str(payload.get("notes") or "").strip()

    if "lure" in stats_payload:
        stats["lure"] = safe_number(stats_payload.get("lure"))
    if "luck" in stats_payload:
        stats["luck"] = safe_number(stats_payload.get("luck"))
    if "control" in stats_payload:
        stats["control"] = safe_number(stats_payload.get("control"))
    if "resilience" in stats_payload:
        stats["resilience"] = safe_number(stats_payload.get("resilience"))
    if "maxKg" in stats_payload:
        stats["maxKg"] = normalize_max_kg(stats_payload.get("maxKg"))
    if "maxKgPercent" in stats_payload:
        stats["maxKgPercent"] = safe_number(stats_payload.get("maxKgPercent"))

    enchant["updatedAt"] = now_iso()


def kv_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def kv_encode(value: Any) -> str:
    if value is None:
        return ""
    safe_value = str(value).replace("\r", " ").replace("\n", " ")
    return quote(safe_value, safe="")


def to_kv_record(record_type: str, fields: dict[str, Any]) -> str:
    parts = [record_type]
    for key, value in fields.items():
        parts.append(f"{key}={kv_encode(value)}")
    return "|".join(parts)


def to_client_rod_kv(rod: dict[str, Any]) -> str:
    stats = rod.get("stats", {})
    catching = rod.get("catching", {})
    learning = normalize_rod_learning(rod.get("learning"))
    sample_count = max(1, int(learning.get("sampleCount", 0) or 1))
    success_rate = round((int(learning.get("successCount", 0)) / sample_count) * 100, 2)
    lines = [
        "status=ok",
        f"name={kv_value(rod.get('name'))}",
        f"active={kv_value('true' if to_bool(rod.get('active', True)) else 'false')}",
        f"lure={kv_value(stats.get('lure'))}",
        f"luck={kv_value(stats.get('luck'))}",
        f"control={kv_value(stats.get('control'))}",
        f"resilience={kv_value(stats.get('resilience'))}",
        f"maxKg={kv_value(stats.get('maxKg'))}",
        f"centerRatio={kv_value(catching.get('centerRatio'))}",
        f"lookaheadMs={kv_value(catching.get('lookaheadMs'))}",
        f"brakeSpeed={kv_value(catching.get('brakeSpeed'))}",
        f"deadzonePx={kv_value(catching.get('deadzonePx'))}",
        f"fishVelocitySmoothing={kv_value(catching.get('fishVelocitySmoothing'))}",
        f"barVelocitySmoothing={kv_value(catching.get('barVelocitySmoothing'))}",
        f"passiveInfo={kv_value(rod.get('passiveInfo'))}",
        f"tutorialUrl={kv_value(rod.get('tutorialUrl'))}",
        f"sampleCount={kv_value(learning.get('sampleCount'))}",
        f"successCount={kv_value(learning.get('successCount'))}",
        f"failureCount={kv_value(learning.get('failureCount'))}",
        f"successRate={kv_value(success_rate)}",
        f"lastOutcome={kv_value(learning.get('lastOutcome'))}",
        f"updatedAt={kv_value(rod.get('updatedAt'))}",
    ]
    return "\n".join(lines)


def to_client_catalog_kv(rods: list[dict[str, Any]], enchants: list[dict[str, Any]]) -> str:
    lines = [
        "status=ok",
        f"updatedAt={kv_value(now_iso())}",
        f"rodCount={len(rods)}",
        f"enchantCount={len(enchants)}",
    ]

    sorted_rods = sorted(rods, key=lambda rod: str(rod.get("name", "")).lower())
    for rod in sorted_rods:
        stats = rod.get("stats", {})
        catching = rod.get("catching", {})
        learning = normalize_rod_learning(rod.get("learning"))
        sample_count = max(1, int(learning.get("sampleCount", 0) or 1))
        success_rate = round((int(learning.get("successCount", 0)) / sample_count) * 100, 2)
        lines.append(
            to_kv_record(
                "rod",
                {
                    "name": rod.get("name"),
                    "active": "true" if to_bool(rod.get("active", True)) else "false",
                    "lure": stats.get("lure"),
                    "luck": stats.get("luck"),
                    "control": stats.get("control"),
                    "resilience": stats.get("resilience"),
                    "maxKg": stats.get("maxKg"),
                    "centerRatio": catching.get("centerRatio"),
                    "lookaheadMs": catching.get("lookaheadMs"),
                    "brakeSpeed": catching.get("brakeSpeed"),
                    "deadzonePx": catching.get("deadzonePx"),
                    "fishVelocitySmoothing": catching.get("fishVelocitySmoothing"),
                    "barVelocitySmoothing": catching.get("barVelocitySmoothing"),
                    "passiveInfo": rod.get("passiveInfo"),
                    "tutorialUrl": rod.get("tutorialUrl"),
                    "sampleCount": learning.get("sampleCount"),
                    "successRate": success_rate,
                    "lastOutcome": learning.get("lastOutcome"),
                    "updatedAt": rod.get("updatedAt"),
                },
            )
        )

    sorted_enchants = sorted(
        [normalize_enchant_record(enchant) for enchant in enchants],
        key=lambda enchant: str(enchant.get("name", "")).lower(),
    )
    for enchant in sorted_enchants:
        stats = enchant.get("stats", {})
        lines.append(
            to_kv_record(
                "enchant",
                {
                    "name": enchant.get("name"),
                    "type": sanitize_enchant_type(enchant.get("type")),
                    "effect": enchant.get("effect"),
                    "lure": stats.get("lure"),
                    "luck": stats.get("luck"),
                    "control": stats.get("control"),
                    "resilience": stats.get("resilience"),
                    "maxKg": stats.get("maxKg"),
                    "maxKgPercent": stats.get("maxKgPercent"),
                    "notes": enchant.get("notes"),
                    "updatedAt": enchant.get("updatedAt"),
                },
            )
        )

    return "\n".join(lines)


def build_feedback_entry(payload: dict[str, Any]) -> dict[str, Any]:
    entry = normalize_feedback_entry(
        {
            "id": uuid.uuid4().hex[:12],
            "createdAt": now_iso(),
            "type": str(payload.get("type") or "General").strip() or "General",
            "description": str(payload.get("description") or payload.get("message") or "").strip(),
            "rodName": str(payload.get("rodName") or "").strip(),
            "clientTitle": str(payload.get("clientTitle") or "").strip(),
            "clientVersion": str(payload.get("clientVersion") or "").strip(),
            "read": to_bool(payload.get("read", False)),
            "archived": to_bool(payload.get("archived", False)),
        }
    )
    return entry


def parse_body_object() -> dict[str, Any]:
    if request.is_json:
        payload = request.get_json(silent=True)
        return payload if isinstance(payload, dict) else {}
    return {k: v for k, v in request.form.items()}


def sanitize_channel_name(value: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9._ -]", "", value).strip()
    name = re.sub(r"\s+", "-", name)
    return name[:32]


def get_chat_data() -> dict[str, Any]:
    return normalize_chat_payload(read_json(CHAT_FILE, {}))


def save_chat_data(chat_data: dict[str, Any]) -> None:
    write_json(CHAT_FILE, normalize_chat_payload(chat_data))


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return make_response("", 204)
    return None


@app.after_request
def set_cors_headers(response: Response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        if get_session_user():
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="")

    username = str(request.form.get("username") or "").strip()
    password = str(request.form.get("password") or "")
    if not username or not password:
        return render_template("login.html", error="Enter username and password."), 400

    with DATA_LOCK:
        users = read_json(USERS_FILE, [])
        user = find_user(users, username)
        if not user or not verify_password_hash(password, str(user.get("passwordHash") or "")):
            return render_template("login.html", error="Invalid username or password."), 401

        session.clear()
        session["username"] = user.get("username", username)
        session["role"] = user.get("role", "viewer")
        session["passwordVersion"] = get_password_version(user)

        user["lastLoginAt"] = now_iso()
        write_json(USERS_FILE, users)

    append_activity("login", f"{session['username']} logged in", session["username"])
    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    actor = str(session.get("username") or "unknown")
    session.clear()
    append_activity("logout", f"{actor} logged out", actor)
    return redirect(url_for("login_page"))


@app.route("/", methods=["GET"])
@login_required
def dashboard():
    user = get_session_user()
    return render_template("dashboard.html", user=user)


@app.route("/api/session", methods=["GET"])
@login_required
def api_session():
    return jsonify({"ok": True, "user": get_session_user()})


@app.route("/api/health", methods=["GET"])
def api_health():
    with DATA_LOCK:
        rods = read_json(RODS_FILE, [])
        enchants = read_json(ENCHANTS_FILE, [])
        feedback = read_json(FEEDBACK_FILE, [])
    login_template = TEMPLATES_DIR / "login.html"
    dashboard_template = TEMPLATES_DIR / "dashboard.html"
    return jsonify(
        {
            "ok": True,
            "now": now_iso(),
            "runtime": "python-flask",
            "counts": {"rods": len(rods), "enchants": len(enchants), "feedback": len(feedback)},
            "paths": {
                "baseDir": str(BASE_DIR),
                "projectDir": str(PROJECT_DIR),
                "templatesDir": str(TEMPLATES_DIR),
                "staticDir": str(STATIC_DIR),
                "templatesExists": TEMPLATES_DIR.is_dir(),
                "loginTemplateExists": login_template.is_file(),
                "dashboardTemplateExists": dashboard_template.is_file(),
            },
        }
    )


@app.route("/api/dashboard/summary", methods=["GET"])
@login_required
def api_dashboard_summary():
    with DATA_LOCK:
        rods = read_json(RODS_FILE, [])
        enchants = read_json(ENCHANTS_FILE, [])
        feedback = [normalize_feedback_entry(item) for item in read_json(FEEDBACK_FILE, [])]
        users = read_json(USERS_FILE, [])
        chat = get_chat_data()

    unread_feedback = len(
        [item for item in feedback if not item.get("read") and not item.get("archived")]
    )
    archived_feedback = len([item for item in feedback if item.get("archived")])
    return jsonify(
        {
            "ok": True,
            "summary": {
                "rodCount": len(rods),
                "enchantCount": len(enchants),
                "feedbackCount": len(feedback),
                "feedbackUnread": unread_feedback,
                "feedbackArchived": archived_feedback,
                "userCount": len(users),
                "channelCount": len(chat.get("channels", [])),
                "chatMessageCount": len(chat.get("messages", [])),
            },
        }
    )


@app.route("/api/rods", methods=["GET"])
@login_required
def api_rods():
    include_inactive = to_bool(request.args.get("includeInactive", "true"))
    with DATA_LOCK:
        rods_raw = read_json(RODS_FILE, [])
        rods = [normalize_rod_record(item) for item in rods_raw if isinstance(item, dict)]
        write_json(RODS_FILE, rods)
    if not include_inactive:
        rods = [rod for rod in rods if to_bool(rod.get("active", True))]
    rods.sort(key=lambda rod: str(rod.get("name", "")).lower())
    return jsonify({"ok": True, "count": len(rods), "rods": rods})


@app.route("/api/rods", methods=["POST"])
@admin_required
def api_rods_create():
    payload = parse_body_object()
    rod_payload = payload.get("rod") if isinstance(payload.get("rod"), dict) else payload
    if not isinstance(rod_payload, dict):
        rod_payload = {}

    rod_name = str(rod_payload.get("name") or payload.get("name") or "").strip()
    if not rod_name:
        return jsonify({"ok": False, "error": "missing_name"}), 400

    with DATA_LOCK:
        rods = [normalize_rod_record(item) for item in read_json(RODS_FILE, []) if isinstance(item, dict)]
        if find_rod(rods, rod_name):
            return jsonify({"ok": False, "error": "rod_exists"}), 409

        rod = normalize_rod_record({"name": rod_name, "active": True})
        update_rod_record_from_payload(rod, rod_payload)
        rods.append(rod)
        rods.sort(key=lambda item: str(item.get("name", "")).lower())
        write_json(RODS_FILE, rods)

    actor = get_session_user()
    append_activity(
        "rod_created",
        f"Created rod {rod.get('name', rod_name)}",
        actor["username"] if actor else "system",
        {"rodName": rod.get("name", rod_name)},
    )
    return jsonify({"ok": True, "rod": rod}), 201


@app.route("/api/enchants", methods=["GET"])
@login_required
def api_enchants():
    with DATA_LOCK:
        enchants_raw = read_json(ENCHANTS_FILE, [])
        enchants = [normalize_enchant_record(item) for item in enchants_raw if isinstance(item, dict)]
        write_json(ENCHANTS_FILE, enchants)
    enchants.sort(key=lambda enchant: str(enchant.get("name", "")).lower())
    return jsonify({"ok": True, "count": len(enchants), "enchants": enchants})


@app.route("/api/enchants/<path:enchant_name>", methods=["GET", "PUT"])
@login_required
def api_enchant_details(enchant_name: str):
    with DATA_LOCK:
        enchants = [normalize_enchant_record(item) for item in read_json(ENCHANTS_FILE, []) if isinstance(item, dict)]
        enchant = find_enchant(enchants, enchant_name)

        if request.method == "GET":
            if not enchant:
                return jsonify({"ok": False, "error": "enchant_not_found"}), 404
            return jsonify({"ok": True, "enchant": enchant})

        payload = parse_body_object()
        enchant_payload = payload.get("enchant") if isinstance(payload.get("enchant"), dict) else payload
        if not isinstance(enchant_payload, dict):
            enchant_payload = {}

        if enchant:
            old_name = str(enchant.get("name", "")).strip()
            update_enchant_record_from_payload(enchant, enchant_payload)
            if not str(enchant.get("name", "")).strip():
                return jsonify({"ok": False, "error": "missing_name"}), 400
            new_name = str(enchant.get("name", "")).strip()
            if new_name.lower() != old_name.lower():
                duplicate = find_enchant(enchants, new_name)
                if duplicate and duplicate is not enchant:
                    return jsonify({"ok": False, "error": "enchant_exists"}), 409
        else:
            source_name = str(enchant_payload.get("name") or enchant_name).strip()
            if not source_name:
                return jsonify({"ok": False, "error": "missing_name"}), 400
            enchant = normalize_enchant_record({"name": source_name})
            update_enchant_record_from_payload(enchant, enchant_payload)
            if not str(enchant.get("name", "")).strip():
                return jsonify({"ok": False, "error": "missing_name"}), 400
            if find_enchant(enchants, enchant["name"]):
                return jsonify({"ok": False, "error": "enchant_exists"}), 409
            enchants.append(enchant)

        write_json(ENCHANTS_FILE, enchants)

    actor = get_session_user()
    append_activity(
        "enchant_updated",
        f"Updated enchant data for {enchant.get('name', 'unknown')}",
        actor["username"] if actor else "system",
        {"enchantName": enchant.get("name", "")},
    )
    return jsonify({"ok": True, "enchant": enchant})


@app.route("/api/tutorials/upload", methods=["POST"])
@login_required
def api_tutorial_upload():
    upload = request.files.get("file")
    if not upload:
        return jsonify({"ok": False, "error": "missing_file"}), 400

    safe_name = secure_filename(upload.filename or "")
    if not safe_name:
        return jsonify({"ok": False, "error": "invalid_filename"}), 400

    extension = Path(safe_name).suffix.lower()
    if extension not in ALLOWED_TUTORIAL_EXTENSIONS:
        return jsonify({"ok": False, "error": "unsupported_file_type"}), 400

    file_name = f"{uuid.uuid4().hex[:12]}-{safe_name}"
    target_path = TUTORIALS_DIR / file_name
    upload.save(target_path)
    url = f"/static/tutorials/{file_name}"

    actor = get_session_user()
    append_activity(
        "tutorial_uploaded",
        f"Uploaded tutorial video {safe_name}",
        actor["username"] if actor else "system",
        {"url": url},
    )

    return jsonify({"ok": True, "url": url, "filename": file_name})


@app.route("/api/rods/<path:rod_name>", methods=["GET", "PUT", "DELETE"])
@login_required
def api_rod_details(rod_name: str):
    if request.method in {"PUT", "DELETE"}:
        user = get_session_user()
        if not is_role(user, {"owner", "admin"}):
            return jsonify({"ok": False, "error": "forbidden"}), 403

    with DATA_LOCK:
        rods = [normalize_rod_record(item) for item in read_json(RODS_FILE, []) if isinstance(item, dict)]
        rod = find_rod(rods, rod_name)
        if not rod:
            return jsonify({"ok": False, "error": "rod_not_found"}), 404

        if request.method == "DELETE":
            rod["active"] = False
            rod["updatedAt"] = now_iso()
            write_json(RODS_FILE, rods)
            actor = get_session_user()
            append_activity(
                "rod_deactivated",
                f"Deactivated rod {rod.get('name', rod_name)}",
                actor["username"] if actor else "system",
                {"rodName": rod.get("name", rod_name)},
            )
            return jsonify({"ok": True, "rod": rod})

        if request.method == "GET":
            write_json(RODS_FILE, rods)
            return jsonify({"ok": True, "rod": rod})

        payload = parse_body_object()
        rod_payload = payload.get("rod") if isinstance(payload.get("rod"), dict) else payload
        if not isinstance(rod_payload, dict):
            rod_payload = {}
        update_rod_record_from_payload(rod, rod_payload)
        write_json(RODS_FILE, rods)

    actor = get_session_user()
    append_activity(
        "rod_updated",
        f"Updated rod tuning for {rod.get('name', 'unknown')}",
        actor["username"] if actor else "system",
        {"rodName": rod.get("name", "")},
    )
    return jsonify({"ok": True, "rod": rod})


@app.route("/api/feedback", methods=["GET", "POST"])
@login_required
def api_feedback():
    if request.method == "POST":
        payload = parse_body_object()
        entry = build_feedback_entry(payload)
        if not entry["description"]:
            return jsonify({"ok": False, "error": "missing_description"}), 400

        with DATA_LOCK:
            feedback = [normalize_feedback_entry(item) for item in read_json(FEEDBACK_FILE, [])]
            feedback.insert(0, entry)
            write_json(FEEDBACK_FILE, feedback)

        actor = get_session_user()
        append_activity(
            "feedback_created",
            f"New feedback added ({entry['type']})",
            actor["username"] if actor else "system",
        )
        return jsonify({"ok": True, "feedback": entry}), 201

    query = str(request.args.get("q") or "").strip().lower()
    archived_filter = str(request.args.get("archived") or "false").lower()

    with DATA_LOCK:
        feedback = [normalize_feedback_entry(item) for item in read_json(FEEDBACK_FILE, [])]
        write_json(FEEDBACK_FILE, feedback)

    if archived_filter != "all":
        archived_value = archived_filter == "true"
        feedback = [item for item in feedback if bool(item.get("archived")) == archived_value]

    if query:
        feedback = [
            item
            for item in feedback
            if query
            in " ".join(
                [
                    str(item.get("type", "")),
                    str(item.get("description", "")),
                    str(item.get("rodName", "")),
                    str(item.get("clientTitle", "")),
                    str(item.get("clientVersion", "")),
                ]
            ).lower()
        ]

    feedback.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return jsonify({"ok": True, "count": len(feedback), "feedback": feedback})


@app.route("/api/feedback/<feedback_id>", methods=["PUT"])
@login_required
def api_feedback_update(feedback_id: str):
    payload = parse_body_object()
    with DATA_LOCK:
        feedback = [normalize_feedback_entry(item) for item in read_json(FEEDBACK_FILE, [])]
        target = next((item for item in feedback if str(item.get("id")) == feedback_id), None)
        if not target:
            return jsonify({"ok": False, "error": "feedback_not_found"}), 404

        if "read" in payload:
            target["read"] = to_bool(payload.get("read"))
        if "archived" in payload:
            target["archived"] = to_bool(payload.get("archived"))
        if "type" in payload and str(payload.get("type") or "").strip():
            target["type"] = str(payload.get("type")).strip()

        write_json(FEEDBACK_FILE, feedback)

    actor = get_session_user()
    append_activity(
        "feedback_updated",
        f"Updated feedback {feedback_id}",
        actor["username"] if actor else "system",
        {"feedbackId": feedback_id},
    )
    return jsonify({"ok": True, "feedback": target})


@app.route("/api/feedback/export", methods=["GET"])
@login_required
def api_feedback_export():
    with DATA_LOCK:
        feedback = [normalize_feedback_entry(item) for item in read_json(FEEDBACK_FILE, [])]
    response = make_response(json.dumps(feedback, indent=2))
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=feedback-export.json"
    return response


@app.route("/api/client/feedback", methods=["POST"])
def api_client_feedback():
    payload = parse_body_object()
    entry = build_feedback_entry(payload)
    if not entry["description"]:
        return Response(
            "status=error\nmessage=missing_description", status=400, mimetype="text/plain"
        )

    with DATA_LOCK:
        feedback = [normalize_feedback_entry(item) for item in read_json(FEEDBACK_FILE, [])]
        feedback.insert(0, entry)
        write_json(FEEDBACK_FILE, feedback)

    append_activity(
        "client_feedback",
        f"Client feedback received ({entry['type']})",
        entry.get("clientTitle") or "client",
    )
    return Response(f"status=ok\nid={entry['id']}", status=201, mimetype="text/plain")


@app.route("/api/client/rod-tuning", methods=["GET"])
def api_client_rod_tuning():
    rod_name = str(request.args.get("name") or "").strip()
    if not rod_name:
        return Response("status=error\nmessage=missing_name", status=400, mimetype="text/plain")

    with DATA_LOCK:
        rods = [normalize_rod_record(item) for item in read_json(RODS_FILE, []) if isinstance(item, dict)]
        write_json(RODS_FILE, rods)
    rod = find_rod(rods, rod_name)
    if not rod:
        return Response("status=error\nmessage=rod_not_found", status=404, mimetype="text/plain")
    if not to_bool(rod.get("active", True)):
        return Response("status=error\nmessage=rod_inactive", status=404, mimetype="text/plain")

    return Response(to_client_rod_kv(rod), status=200, mimetype="text/plain")


@app.route("/api/client/catch-learning", methods=["POST"])
def api_client_catch_learning():
    payload = parse_body_object()
    rod_name = str(payload.get("rodName") or payload.get("name") or "").strip()
    if not rod_name:
        return Response("status=error\nmessage=missing_rod_name", status=400, mimetype="text/plain")

    with DATA_LOCK:
        rods = [normalize_rod_record(item) for item in read_json(RODS_FILE, []) if isinstance(item, dict)]
        rod = find_rod(rods, rod_name)
        if not rod:
            return Response("status=error\nmessage=rod_not_found", status=404, mimetype="text/plain")
        if not to_bool(rod.get("active", True)):
            return Response("status=error\nmessage=rod_inactive", status=404, mimetype="text/plain")

        merge_info = merge_rod_learning_sample(rod, payload)
        write_json(RODS_FILE, rods)

    append_activity(
        "client_learning",
        f"Learning sample for {rod.get('name', rod_name)} ({'success' if merge_info['success'] else 'failure'})",
        str(payload.get("clientTitle") or "client"),
        {
            "rodName": rod.get("name", rod_name),
            "sampleCount": merge_info["sampleCount"],
            "successRate": merge_info["successRate"],
        },
    )

    lines = [
        "status=ok",
        f"rodName={kv_value(rod.get('name', rod_name))}",
        f"result={kv_value('success' if merge_info['success'] else 'failure')}",
        f"sampleCount={kv_value(merge_info['sampleCount'])}",
        f"successRate={kv_value(merge_info['successRate'])}",
        f"updatedAt={kv_value(rod.get('updatedAt'))}",
    ]
    return Response("\n".join(lines), status=201, mimetype="text/plain")


@app.route("/api/client/catalog", methods=["GET"])
def api_client_catalog():
    with DATA_LOCK:
        all_rods = [normalize_rod_record(item) for item in read_json(RODS_FILE, []) if isinstance(item, dict)]
        rods = [rod for rod in all_rods if to_bool(rod.get("active", True))]
        write_json(RODS_FILE, all_rods)
        enchants = [normalize_enchant_record(item) for item in read_json(ENCHANTS_FILE, []) if isinstance(item, dict)]
        if not enchants:
            enchants = default_enchants_payload()
            write_json(ENCHANTS_FILE, enchants)

    return Response(to_client_catalog_kv(rods, enchants), status=200, mimetype="text/plain")


@app.route("/api/chat/channels", methods=["GET"])
@login_required
def api_chat_channels():
    with DATA_LOCK:
        chat_data = get_chat_data()
        save_chat_data(chat_data)
    channels = chat_data.get("channels", [])
    channels.sort(key=lambda channel: str(channel.get("name", "")).lower())
    return jsonify({"ok": True, "count": len(channels), "channels": channels})


@app.route("/api/chat/channels", methods=["POST"])
@admin_required
def api_chat_create_channel():
    payload = parse_body_object()
    raw_name = str(payload.get("name") or "").strip()
    topic = str(payload.get("topic") or "").strip()
    channel_name = sanitize_channel_name(raw_name)
    if len(channel_name) < 2:
        return jsonify({"ok": False, "error": "invalid_channel_name"}), 400

    actor = get_session_user()
    with DATA_LOCK:
        chat_data = get_chat_data()
        channels = chat_data.get("channels", [])
        if any(str(channel.get("name", "")).lower() == channel_name.lower() for channel in channels):
            return jsonify({"ok": False, "error": "channel_exists"}), 409
        new_channel = {
            "name": channel_name,
            "topic": topic,
            "createdAt": now_iso(),
            "createdBy": actor["username"] if actor else "system",
        }
        channels.append(new_channel)
        chat_data["channels"] = channels
        save_chat_data(chat_data)

    append_activity(
        "channel_created",
        f"Created chat channel #{channel_name}",
        actor["username"] if actor else "system",
    )
    return jsonify({"ok": True, "channel": new_channel}), 201


@app.route("/api/chat/messages", methods=["GET"])
@login_required
def api_chat_messages():
    requested_channel = str(request.args.get("channel") or "general").strip()
    if not requested_channel:
        requested_channel = "general"

    try:
        limit = int(request.args.get("limit") or 150)
    except Exception:
        limit = 150
    limit = max(1, min(limit, 500))

    with DATA_LOCK:
        chat_data = get_chat_data()
        channel_map = {
            str(channel.get("name", "")).lower(): str(channel.get("name", ""))
            for channel in chat_data.get("channels", [])
        }
        if requested_channel.lower() not in channel_map:
            return jsonify({"ok": False, "error": "channel_not_found"}), 404
        canonical_name = channel_map[requested_channel.lower()]
        messages = [
            message
            for message in chat_data.get("messages", [])
            if str(message.get("channel", "")).lower() == canonical_name.lower()
        ]

    messages.sort(key=lambda message: message.get("createdAt", ""))
    return jsonify({"ok": True, "count": len(messages[-limit:]), "messages": messages[-limit:]})


@app.route("/api/chat/messages", methods=["POST"])
@login_required
def api_chat_post_message():
    payload = parse_body_object()
    requested_channel = str(payload.get("channel") or "").strip()
    message_text = str(payload.get("text") or "").strip()
    if not requested_channel:
        return jsonify({"ok": False, "error": "missing_channel"}), 400
    if not message_text:
        return jsonify({"ok": False, "error": "missing_message"}), 400

    if len(message_text) > 2000:
        message_text = message_text[:2000]

    actor = get_session_user()
    with DATA_LOCK:
        chat_data = get_chat_data()
        channel_map = {
            str(channel.get("name", "")).lower(): str(channel.get("name", ""))
            for channel in chat_data.get("channels", [])
        }
        if requested_channel.lower() not in channel_map:
            return jsonify({"ok": False, "error": "channel_not_found"}), 404
        canonical_name = channel_map[requested_channel.lower()]

        message = {
            "id": uuid.uuid4().hex[:12],
            "channel": canonical_name,
            "author": actor["username"] if actor else "unknown",
            "text": message_text,
            "createdAt": now_iso(),
        }
        messages = chat_data.get("messages", [])
        messages.append(message)
        if len(messages) > 5000:
            messages = messages[-5000:]
        chat_data["messages"] = messages
        save_chat_data(chat_data)

    return jsonify({"ok": True, "message": message}), 201


@app.route("/api/users", methods=["GET"])
@owner_required
def api_users_get():
    with DATA_LOCK:
        users = read_json(USERS_FILE, [])

    sanitized_users = [
        {
            "username": str(user.get("username", "")),
            "role": str(user.get("role", "viewer")),
            "createdAt": str(user.get("createdAt") or ""),
            "lastLoginAt": str(user.get("lastLoginAt") or ""),
        }
        for user in users
    ]
    sanitized_users.sort(key=lambda user: user["username"].lower())
    return jsonify({"ok": True, "count": len(sanitized_users), "users": sanitized_users})


@app.route("/api/users", methods=["POST"])
@owner_required
def api_users_create():
    payload = parse_body_object()
    username = str(payload.get("username") or "").strip()
    password = str(payload.get("password") or "")
    role = str(payload.get("role") or "viewer").strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9._-]{3,40}", username):
        return jsonify({"ok": False, "error": "invalid_username"}), 400
    if len(password) < 6:
        return jsonify({"ok": False, "error": "weak_password"}), 400
    if role not in {"admin", "viewer"}:
        return jsonify({"ok": False, "error": "invalid_role"}), 400

    with DATA_LOCK:
        users = read_json(USERS_FILE, [])
        if find_user(users, username):
            return jsonify({"ok": False, "error": "user_exists"}), 409

        new_user = {
            "username": username,
            "passwordHash": generate_password_hash(password),
            "role": role,
            "createdAt": now_iso(),
            "passwordUpdatedAt": now_iso(),
            "lastLoginAt": "",
        }
        users.append(new_user)
        write_json(USERS_FILE, users)

    actor = get_session_user()
    append_activity(
        "user_created",
        f"Created user {username}",
        actor["username"] if actor else "system",
        {"username": username, "role": role},
    )
    return (
        jsonify(
            {
                "ok": True,
                "user": {
                    "username": new_user["username"],
                    "role": new_user["role"],
                    "createdAt": new_user["createdAt"],
                    "lastLoginAt": new_user["lastLoginAt"],
                },
            }
        ),
        201,
    )


@app.route("/api/users/<path:username>/password", methods=["PUT"])
@owner_required
def api_users_reset_password(username: str):
    actor = get_session_user()
    actor_username = actor["username"] if actor else "system"
    payload = parse_body_object()
    password = str(payload.get("password") or "")
    if len(password) < 6:
        return jsonify({"ok": False, "error": "weak_password"}), 400

    with DATA_LOCK:
        users = read_json(USERS_FILE, [])
        user = find_user(users, username)
        if not user:
            return jsonify({"ok": False, "error": "user_not_found"}), 404
        user["passwordHash"] = generate_password_hash(password)
        user["passwordUpdatedAt"] = now_iso()
        write_json(USERS_FILE, users)

    is_self_reset = (
        actor is not None
        and str(user.get("username", "")).lower() == actor_username.lower()
    )
    if is_self_reset:
        session.clear()

    append_activity(
        "user_password_reset",
        f"Reset password for {user.get('username', username)}",
        actor_username,
    )
    return jsonify({"ok": True, "loggedOut": is_self_reset})


@app.route("/api/users/<path:username>", methods=["DELETE"])
@owner_required
def api_users_delete(username: str):
    if username.lower() == OWNER_USERNAME.lower():
        return jsonify({"ok": False, "error": "cannot_delete_owner"}), 400

    with DATA_LOCK:
        users = read_json(USERS_FILE, [])
        current_count = len(users)
        users = [user for user in users if str(user.get("username", "")).lower() != username.lower()]
        if len(users) == current_count:
            return jsonify({"ok": False, "error": "user_not_found"}), 404
        write_json(USERS_FILE, users)

    actor = get_session_user()
    append_activity(
        "user_deleted",
        f"Deleted user {username}",
        actor["username"] if actor else "system",
    )
    return jsonify({"ok": True})


@app.route("/api/activity", methods=["GET"])
@login_required
def api_activity():
    try:
        limit = int(request.args.get("limit") or 40)
    except Exception:
        limit = 40
    limit = max(1, min(limit, 100))

    with DATA_LOCK:
        activity = read_json(ACTIVITY_FILE, [])
    return jsonify({"ok": True, "count": min(limit, len(activity)), "activity": activity[:limit]})


ensure_data_files()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=DEFAULT_PORT, debug=False)
