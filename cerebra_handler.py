#!/usr/bin/env python3
"""
Unified Python macro runner for Fisch.

Includes:
- Start-macro cycle (cast -> shake -> catch)
- Normal catch controller
- Cerebra state machine + heartbeat control
- Control-based bar scaling (0 => 30%, 0.2 => 50%)
- Startup/runtime logs to prove Python launched
"""

from __future__ import annotations
import pytesseract
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Lewis\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
import argparse
from collections import deque
import ctypes
import ctypes.wintypes as wintypes
from difflib import SequenceMatcher
import json
import random
import re
import threading
import traceback
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Tuple

from cerebra_redesign import CerebraVisionSystem, Measurement as VisionMeasurement, Rect as VisionRect, VisionConfig

IMPORT_ERROR = ""
OCR_IMPORT_ERROR = ""

# Requested HSV thresholds for Cerebra bar detection.
CEREBRA_BAR_HUE_MIN = 145
CEREBRA_BAR_HUE_MAX = 170
CEREBRA_BAR_SAT_MIN = 150
CEREBRA_BAR_VAL_MAX = 255

# Debug/tuning controls:
# - If mask is mostly empty, widen H range and/or lower SAT minimum.
# - If false positives appear, narrow H range and/or raise SAT minimum.
# - Keep V high (up to 255) so bright bar pixels are not missed.
DEBUG_CEREBRA_HSV = False
DEBUG_CEREBRA = True
CEREBRA_CAPTURE_MASK_ENABLE = True
CEREBRA_CAPTURE_MASK_PAD_X = 8
CEREBRA_CAPTURE_MASK_PAD_Y = 10
CEREBRA_DEBUG_LOG_EVERY_MS = 140
CEREBRA_HSV_MIN_AREA_DEFAULT = 25
CEREBRA_HSV_EMPTY_MASK_WARN_RATIO = 0.001
# Min-area used by runtime heartbeat detection (lower catches small segments).
CEREBRA_HSV_MIN_AREA_HEARTBEAT = 45
# Min-area used by generic bbox confirmation.
CEREBRA_HSV_MIN_AREA_BBOX = 70
CEREBRA_HSV_PASS_RATIO_MAX = 0.55
CEREBRA_BAR_ASPECT_MIN = 2.0
CEREBRA_BAR_ASPECT_MAX = 18.0
CEREBRA_BAR_FILL_MIN = 0.10
# Small-bar targeting thresholds (tune if target lock is unstable).
CEREBRA_SMALL_BAR_MIN_AREA = 8
CEREBRA_SMALL_BAR_MAX_AREA = 700
CEREBRA_SMALL_BAR_MIN_W = 2
CEREBRA_SMALL_BAR_MAX_W = 55
CEREBRA_SMALL_BAR_MIN_H = 2
CEREBRA_SMALL_BAR_MAX_H = 22
CEREBRA_TARGET_LOCK_MAX_JUMP_PX = 110
CEREBRA_TARGET_SMOOTHING = 0.55
CEREBRA_TARGET_MEDIAN_WINDOW = 5
CEREBRA_TARGET_MAX_MISSES_BEFORE_FALLBACK = 10
CEREBRA_FORCE_SMALL_BAR_TRACKING = True

# Dedicated SMALL-BAR HSV (pink/magenta) detector.
# Use high V min to avoid dark/black bar artifacts being selected.
CEREBRA_SMALL_HUE_MIN = 145
CEREBRA_SMALL_HUE_MAX = 179
CEREBRA_SMALL_SAT_MIN = 120
CEREBRA_SMALL_VAL_MIN = 110
CEREBRA_SMALL_VAL_MAX = 255
CEREBRA_SMALL_PROJ_MIN_HITS = 4
CEREBRA_SMALL_PROJ_SMOOTH_WINDOW = 7
CEREBRA_SMALL_MOTION_MIN_HITS = 3
CEREBRA_SMALL_MOTION_DIFF_THRESH = 18
CEREBRA_SMALL_LOCAL_DARK_MAX = 75
CEREBRA_SMALL_LOCAL_MIN_AREA = 3
CEREBRA_SMALL_LOCAL_MAX_AREA = 180
CEREBRA_SMALL_LOCAL_MIN_COL_HITS = 3
CEREBRA_SMALL_TRACK_SEARCH_RADIUS = 90
CEREBRA_STRIP_EDGE_IGNORE_PX = 2
CEREBRA_BLACK_WAVE_MAX_LUMA = 82
CEREBRA_BLACK_WAVE_MIN_COL_HITS = 2
CEREBRA_BLACK_WAVE_SMOOTH_WINDOW = 9
CEREBRA_BLACK_WAVE_EDGE_IGNORE_PX = 5
CEREBRA_BLACK_WAVE_TRACK_RADIUS = 70
CEREBRA_BLACK_WAVE_MIN_AREA = 12
CEREBRA_BLACK_WAVE_MAX_AREA = 900
CEREBRA_BLACK_WAVE_MIN_W = 5
CEREBRA_BLACK_WAVE_MAX_W = 130
CEREBRA_BLACK_WAVE_BAND_TOP_RATIO = 0.26
CEREBRA_BLACK_WAVE_BAND_BOTTOM_RATIO = 0.76
CEREBRA_BLACK_WAVE_IGNORE_LEFT_RATIO = 0.12
CEREBRA_BLACK_WAVE_IGNORE_RIGHT_RATIO = 0.12
CEREBRA_BLACK_WAVE_IGNORE_CENTER_ENABLE = True
CEREBRA_BLACK_WAVE_IGNORE_CENTER_HALF_RATIO = 0.10
CEREBRA_BORDER_HUE_MIN = 140
CEREBRA_BORDER_HUE_MAX = 179
CEREBRA_BORDER_SAT_MIN = 120
CEREBRA_BORDER_VAL_MIN = 100
CEREBRA_BORDER_MIN_AREA = 700
CEREBRA_BORDER_ASPECT_MIN = 4.0
CEREBRA_BORDER_ASPECT_MAX = 40.0
CEREBRA_LINE_EDGE_ENABLE = False
CEREBRA_LINE_EDGE_DIFF_THRESH = 14
CEREBRA_LINE_EDGE_MIN_SPAN = 40

# Prediction and smoothing controls:
# - Increase LOOKAHEAD_MS to react earlier to fast motion.
# - Increase PREDICT_SMOOTHING to reduce oscillation (too high adds lag).
CEREBRA_BAR_PREDICT_LOOKAHEAD_MS = 55
CEREBRA_BAR_PREDICT_SMOOTHING = 0.35
CEREBRA_DYNAMIC_LOOKAHEAD_BASE_MS = 45
CEREBRA_DYNAMIC_LOOKAHEAD_GAIN = 120
CEREBRA_DYNAMIC_LOOKAHEAD_MAX_MS = 95

# Multi-signal confidence scoring:
# Trigger/keep control only when score is high enough.
CEREBRA_SCORE_HEARTBEAT = 2
CEREBRA_SCORE_HSV_BAR = 2
CEREBRA_SCORE_UI_BAR = 1
CEREBRA_SCORE_ACTIVE_RUN = 1
CEREBRA_SCORE_TEMPLATE = 1
CEREBRA_ACTIVE_SCORE_MIN = 3

# OCR result detection region (client coordinates) and cadence.
# Tune region if your result popup appears elsewhere.
CEREBRA_RESULT_REGION = (259, 399, 645, 474)  # x1, y1, x2, y2
CEREBRA_RESULT_OCR_SCALE = 3.0
CEREBRA_RESULT_CHECK_EVERY_MS = 120
CEREBRA_RESULT_ACTIVE_CHECK_EVERY_MS = 1800
CEREBRA_RESULT_ACTIVE_LOW_CONF_CHECK_EVERY_MS = 900
CEREBRA_RESULT_WINDOW_MS = 3000
CEREBRA_RESULT_CONFIRM_FRAMES = 1
CEREBRA_RESULT_LOSS_CONFIRM_FRAMES = 2
CEREBRA_RESULT_FUZZY_THRESHOLD = 0.68
CEREBRA_BAR_MISSING_GRACE_FRAMES = 5
CEREBRA_BORDER_REUSE_MAX_FRAMES = 6
CEREBRA_BORDER_MAX_CENTER_JUMP_PX = 44.0
CEREBRA_BORDER_MIN_FILL_RATIO = 0.20
CEREBRA_STRIP_REUSE_MAX_FRAMES = 4
CEREBRA_STRIP_MAX_CENTER_JUMP_PX = 54.0
CEREBRA_STRIP_MIN_FILL_RATIO = 0.12
CEREBRA_CONTROL_MAX_JUMP_PX = 62.0
CEREBRA_TARGET_MAX_JUMP_PX_STRICT = 48.0
CEREBRA_CONFIDENCE_ACT_MIN_TARGET = 0.34
CEREBRA_CONFIDENCE_ACT_MIN_BAR = 0.34
CEREBRA_WEAK_FRAME_GRACE = 4
CEREBRA_RECOVERY_CONFIRM_FRAMES = 3
CEREBRA_ACTIVE_RECOVER_CONFIRM_FRAMES = 2
CEREBRA_END_STRONG_CONFIRM_FRAMES = 5
CEREBRA_END_LOSS_CONFIRM_FRAMES = 7
CEREBRA_ACTION_MIN_HOLD_MS = 80
CEREBRA_ACTION_MIN_RELEASE_MS = 80
CEREBRA_ACTION_SWITCH_COOLDOWN_MS = 95
CEREBRA_ACTION_REVERSE_ERR_PX = 8.5
CEREBRA_ACTION_STICKY_OVERLAP_PX = 6.0
CEREBRA_ACTION_COAST_MAX_MS = 180
CEREBRA_TARGET_PREDICTION_SHORT_FRAMES = 2
CEREBRA_TARGET_PREDICTION_HARD_FRAMES = 5
CEREBRA_TARGET_GRACE_HELD_FRAMES = 2
CEREBRA_TARGET_CONFIDENCE_STRONG = 0.58
CEREBRA_TARGET_CONFIDENCE_MEDIUM = 0.42
CEREBRA_TARGET_CONFIDENCE_FLOOR = 0.28
CEREBRA_BOOTSTRAP_CONFIRM_REQUIRED = 3
CEREBRA_BOOTSTRAP_CONFIRM_RADIUS_PX = 16.0
CEREBRA_BOOTSTRAP_EXPIRE_MS = 420
CEREBRA_BOOTSTRAP_FAILED_ZONE_MS = 1900
CEREBRA_BOOTSTRAP_FAILED_ZONE_RADIUS = 24.0
CEREBRA_BOOTSTRAP_FAILED_ZONE_PENALTY = 0.22


class _MissingModule:
    def __init__(self, module_name: str) -> None:
        self.module_name = module_name

    def __getattr__(self, item: str) -> Any:
        raise RuntimeError(f"Missing dependency: {self.module_name}")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(f"Missing dependency: {self.module_name}")


try:
    import cv2
    import numpy as np
    import pyautogui
    from mss import mss
    pyautogui.FAILSAFE = False
except Exception as exc:  # pragma: no cover
    IMPORT_ERROR = str(exc)
    cv2 = _MissingModule("cv2")
    np = _MissingModule("numpy")
    pyautogui = _MissingModule("pyautogui")
    mss = _MissingModule("mss")

try:
    import pytesseract
except Exception as exc:  # pragma: no cover
    OCR_IMPORT_ERROR = str(exc)
    pytesseract = None


@dataclass
class Region:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def w(self) -> int:
        return max(0, self.x2 - self.x1 + 1)

    @property
    def h(self) -> int:
        return max(0, self.y2 - self.y1 + 1)


@dataclass
class CatchState:
    has_fish: bool = False
    last_fish_x: float = 0.0
    fish_velocity: float = 0.0
    fish_direction: int = 0
    has_bar: bool = False
    last_bar_middle_x: float = 0.0
    bar_velocity: float = 0.0
    bar_direction: int = 0
    click_down: bool = False
    commanded_direction: int = 0
    last_switch_tick: int = 0
    last_tick: int = 0


@dataclass
class ResultDetection:
    outcome: Optional[bool]
    raw_text: str = ""
    normalized_text: str = ""
    matched_keyword: str = ""
    matched_score: float = 0.0
    variant: str = ""
    reason: str = ""


@dataclass
class CerebraTrackerState:
    position: float = 0.0
    velocity: float = 0.0
    confidence: float = 0.0
    missing_frames: int = 0
    last_measurement_source: str = "none"
    last_good_tick: int = 0
    predicted_position: float = 0.0


@dataclass
class CerebraVisionDebug:
    border_bbox: Optional[Tuple[int, int, int, int]] = None
    strip_bbox: Optional[Tuple[int, int, int, int]] = None
    border_confidence: float = 0.0
    strip_confidence: float = 0.0
    control_confidence: float = 0.0
    target_confidence: float = 0.0
    control_source: str = "none"
    target_source: str = "none"
    predicted_target_x: float = 0.0
    predicted_bar_x: float = 0.0
    error: float = 0.0
    chosen_action: str = "neutral"
    switch_reason: str = ""


@dataclass
class CerebraActuationState:
    direction: int = 0
    last_switch_tick: int = 0
    last_reason: str = "init"
    hold_since_tick: int = 0
    release_since_tick: int = 0
    weak_frame_streak: int = 0
    overlap_stick_until_tick: int = 0


@dataclass
class CerebraBootstrapState:
    candidate_x: float = 0.0
    candidate_confidence: float = 0.0
    candidate_source: str = "none"
    started_tick: int = 0
    confirm_frames: int = 0
    last_tick: int = 0
    active: bool = False


@dataclass
class CerebraFailedBootstrapZone:
    created_tick: int
    x: float
    radius: float
    reason: str = "failed_bootstrap"


def detect_cerebra_bar_hsv(
    frame_bgr: Any,
    min_area: int = CEREBRA_HSV_MIN_AREA_DEFAULT,
    morph_kernel: int = 3,
) -> Tuple[Optional[Tuple[int, int, int, int]], Any]:
    """
    Detect Cerebra bar-like region using HSV thresholds.
    Returns (bbox, mask), where bbox is (x, y, w, h) in frame-local coords.
    """
    mask, ratio = build_cerebra_hsv_mask(frame_bgr, morph_kernel=morph_kernel, refine_if_broad=True)
    found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = found[0] if len(found) == 2 else found[1]
    nonzero = int(cv2.countNonZero(mask))
    total = int(mask.shape[0] * mask.shape[1]) if mask.size else 0
    if DEBUG_CEREBRA_HSV:
        print(f"[CEREBRA_HSV] pass_pixels={nonzero}/{total} ({ratio:.4%}) min_area={min_area}", flush=True)
        if ratio < CEREBRA_HSV_EMPTY_MASK_WARN_RATIO:
            print(
                "[CEREBRA_HSV][WARN] Mask is mostly empty. Thresholds may be too strict for current lighting/colors.",
                flush=True,
            )

    best = None
    best_score = 0.0
    for c in contours:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(c)
        # Prefer bar-like shapes, but keep small segments if they are elongated.
        if w < 4 or h < 2:
            continue
        aspect = float(w) / float(max(h, 1))
        if aspect < CEREBRA_BAR_ASPECT_MIN or aspect > CEREBRA_BAR_ASPECT_MAX:
            continue
        fill = area / float(max(1, w * h))
        if fill < CEREBRA_BAR_FILL_MIN:
            continue
        score = area * max(1.0, aspect)
        if score > best_score:
            best_score = score
            best = (x, y, w, h)

    if DEBUG_CEREBRA_HSV:
        if best is not None:
            x, y, w, h = best
            print(f"[CEREBRA_HSV] bbox_found x={x} y={y} w={w} h={h}", flush=True)
        else:
            print("[CEREBRA_HSV] bbox_not_found", flush=True)

    if DEBUG_CEREBRA_HSV:
        dbg = frame_bgr.copy()
        if best is not None:
            x, y, w, h = best
            cv2.rectangle(dbg, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow("Cerebra HSV Frame", dbg)
        cv2.imshow("Cerebra HSV Mask", mask)
        cv2.waitKey(1)

    return best, mask


def build_cerebra_hsv_mask(
    frame_bgr: Any,
    morph_kernel: int = 3,
    refine_if_broad: bool = True,
) -> Tuple[Any, float]:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array([CEREBRA_BAR_HUE_MIN, CEREBRA_BAR_SAT_MIN, 0], dtype=np.uint8)
    upper = np.array([CEREBRA_BAR_HUE_MAX, 255, CEREBRA_BAR_VAL_MAX], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)

    if morph_kernel > 0:
        k = np.ones((morph_kernel, morph_kernel), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)

    total = int(mask.shape[0] * mask.shape[1]) if mask.size else 0
    ratio = (int(cv2.countNonZero(mask)) / total) if total > 0 else 0.0

    if refine_if_broad and ratio > CEREBRA_HSV_PASS_RATIO_MAX:
        lower_refined = np.array([CEREBRA_BAR_HUE_MIN, min(255, CEREBRA_BAR_SAT_MIN + 20), 0], dtype=np.uint8)
        upper_refined = np.array([CEREBRA_BAR_HUE_MAX, 255, min(255, CEREBRA_BAR_VAL_MAX)], dtype=np.uint8)
        mask_refined = cv2.inRange(hsv, lower_refined, upper_refined)
        if morph_kernel > 0:
            k = np.ones((morph_kernel, morph_kernel), dtype=np.uint8)
            mask_refined = cv2.morphologyEx(mask_refined, cv2.MORPH_OPEN, k, iterations=1)
            mask_refined = cv2.morphologyEx(mask_refined, cv2.MORPH_CLOSE, k, iterations=1)
        if cv2.countNonZero(mask_refined) > 0:
            mask = mask_refined
            total = int(mask.shape[0] * mask.shape[1]) if mask.size else 0
            ratio = (int(cv2.countNonZero(mask)) / total) if total > 0 else 0.0

    return mask, ratio


def build_cerebra_small_bar_mask(frame_bgr: Any, morph_kernel: int = 1) -> Any:
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    lower = np.array(
        [CEREBRA_SMALL_HUE_MIN, CEREBRA_SMALL_SAT_MIN, CEREBRA_SMALL_VAL_MIN],
        dtype=np.uint8,
    )
    upper = np.array(
        [CEREBRA_SMALL_HUE_MAX, 255, CEREBRA_SMALL_VAL_MAX],
        dtype=np.uint8,
    )
    mask = cv2.inRange(hsv, lower, upper)
    if morph_kernel > 0:
        k = np.ones((morph_kernel, morph_kernel), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)
    return mask


class Runner:
    CATCH_BAR = Region(234, 502, 565, 517)
    # User-calibrated border bar endpoints: (238,511) and (549,507).
    # Region uses normalized y-range: 507..511.
    CATCH_BORDER_SCAN = Region(228, 495, 572, 523)
    CATCH_BAR_TOP_LINE = Region(234, 513, 565, 513)
    CATCH_BAR_ARROW_LINE = Region(234, 513, 565, 513)
    CAST_BAR_SEARCH = Region(1, 57, 804, 620)
    SHAKE_AREA = Region(20, 40, 780, 580)
    UI_CATCH_BAR_PIXEL = (399, 505)

    CAST_BAR_GREEN = 0x5DA349
    CAST_BAR_WHITE = 0xFBFBF0
    CATCH_ARROW_COLOR = 0x7A7879
    CALIBRATION_FISH_COLOR = 0x434B5B
    HEARTBEAT_MARKER_COLOR = 0x000000

    CATCH_ARROW_TOL = 10
    FISH_TOL = 1
    HEARTBEAT_TOL = 5

    HEARTBEAT_BASE_RATIO = 0.30
    HEARTBEAT_MIN_RATIO = 0.18
    HEARTBEAT_MAX_RATIO = 0.92
    HEARTBEAT_MAX_JUMP_PX = 70

    CATCH_CENTER_RATIO = 0.35
    CATCH_LOOKAHEAD_MS = 60
    CATCH_BRAKE_SPEED = 0.95
    CATCH_DEADZONE_PX = 3
    CATCH_FISH_SMOOTH = 0.45
    CATCH_BAR_SMOOTH = 0.40
    CATCH_SWITCH_COOLDOWN_MS = 14
    CATCH_MAX_JUMP_PX = 140
    CATCH_MAX_DURATION_MS = 35000
    NORMAL_END_NO_SIGNAL_MS = 1100

    CATCH_BAR_ACTIVE_COLOR = 0x434B5B
    CATCH_BAR_ACTIVE_VAR = 18
    CATCH_BAR_ACTIVE_MIN_RUN = 52

    CEREBRA_START_PIXEL = (400, 513, 0x434B5B, 20)
    CEREBRA_START_TIMEOUT_MS = 5000
    CEREBRA_LOST_MAX_FRAMES = 20
    CEREBRA_START_CONFIRM = 2
    CEREBRA_START_SCORE_MIN = 2
    CEREBRA_REARM_MS = 700
    CEREBRA_ICON_COLOR = 0xFF00A8
    CEREBRA_ICON_TOL = 65
    CEREBRA_ICON_MIN_HITS = 6
    CEREBRA_POLL_MIN = 8
    CEREBRA_POLL_MAX = 16
    CEREBRA_CONTROL_MISS_MAX = 12
    CEREBRA_LOST_GRACE_MS = 1400
    CEREBRA_BAR_PREDICT_LOOKAHEAD_MS = 55
    CEREBRA_BAR_PREDICT_SMOOTHING = 0.35
    CEREBRA_DYNAMIC_LOOKAHEAD_BASE_MS = 45
    CEREBRA_DYNAMIC_LOOKAHEAD_GAIN = 120
    CEREBRA_DYNAMIC_LOOKAHEAD_MAX_MS = 95
    CEREBRA_DIRECTION_SWITCH_COOLDOWN_MS = 36
    CEREBRA_EXTRA_DEADZONE_PX = 2
    CEREBRA_ENTER_DEADZONE_EXTRA_PX = 1
    CEREBRA_RELEASE_DEADZONE_MULT = 0.75
    CEREBRA_REVERSE_THRESHOLD_MULT = 1.35
    CEREBRA_MIN_HOLD_MS = 34
    CEREBRA_CONTROL_SLEEP_MIN_MS = 8
    CEREBRA_CONTROL_SLEEP_MAX_MS = 18
    CEREBRA_RIGHT_HOLD_BIAS = True
    CEREBRA_RIGHT_HOLD_OVERSHOOT_MULT = 1.2
    CEREBRA_ALWAYS_OVERLAP_BIAS = True
    CEREBRA_OVERLAP_LOCK_PX = 7.0
    CEREBRA_OVERLAP_DRIFT_PX_PER_MS = 0.01
    CEREBRA_OVERLAP_HOLD_MS = 85
    CEREBRA_REENGAGE_ERR_PX = 5.0
    CEREBRA_REENGAGE_AFTER_UP_MS = 70
    CEREBRA_HOLD_REFRESH_MS = 220
    CEREBRA_FORCE_RELEASE_ERR_PX = 6.0
    CEREBRA_FORCE_RELEASE_VEL_PX_PER_MS = 0.015
    CEREBRA_SIMPLE_BINARY_CONTROL = True
    CEREBRA_PID_KP = 0.90
    CEREBRA_PID_KI = 0.10
    CEREBRA_PID_KD = 0.40
    CEREBRA_PID_CLAMP = 100.0
    CEREBRA_PID_THRESHOLD = 6.0
    CEREBRA_USE_PID_CONTROL = False
    CEREBRA_HOLD_ENTER_ERR_PX = 4.0
    CEREBRA_RELEASE_ENTER_ERR_PX = 4.0
    CEREBRA_HOLD_KEEP_BAND_PX = 1.8
    CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS = 45
    CEREBRA_ERR_SMOOTH_ALPHA = 0.22
    CEREBRA_OVERLAP_PAD_PX = 5.0
    CEREBRA_OVERLAP_EDGE_BIAS_PX = 9.0
    CEREBRA_OVERLAP_RIGHT_HOLD_BIAS = True
    CEREBRA_AUTO_TUNE_ENABLE = True
    CEREBRA_AUTO_TUNE_WINDOW = 90
    CEREBRA_AUTO_TUNE_APPLY_MS = 650
    CEREBRA_AUTO_TUNE_MIN_SAMPLES = 24
    CEREBRA_AUTO_TUNE_SWITCH_RATE_HIGH = 0.30
    CEREBRA_AUTO_TUNE_OVERLAP_LOW = 0.36
    CEREBRA_AUTO_TUNE_OVERLAP_GOOD = 0.62
    HOTKEY_POLL_MS = 10
    HOTKEY_DEBOUNCE_MS = 120
    LIVE_TUNING_FILE = "live_tuning.json"
    LIVE_TUNING_CHECK_MS = 250

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = Path(__file__).resolve().parent
        self.logs_dir = self.root / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.sct = mss()
        self.client_x = int(args.client_x)
        self.client_y = int(args.client_y)
        self.control = float(args.control)
        self.lure_speed = float(args.lure_speed)
        self.rod_name = args.rod_name or ""
        self.state = CatchState(last_tick=self.tick())
        self.last_heartbeat_x = 0
        self.control_bar_half_width = 15
        self.control_bar_width = 30
        self.left_arrow_off = 15
        self.right_arrow_off = 15
        self.cerebra_last_end = 0
        self.cerebra_last_result_check = 0
        self.cerebra_last_direction = 0
        self.cerebra_last_direction_tick = 0
        self.cerebra_err_smooth = 0.0
        self.cerebra_target_x = 0.0
        self.cerebra_target_v = 0.0
        self.cerebra_target_has = False
        self.cerebra_target_samples = deque(maxlen=CEREBRA_TARGET_MEDIAN_WINDOW)
        self.cerebra_target_misses = 0
        self.cerebra_prev_small_gray = None
        self.cerebra_pred_bar_x = 0.0
        self.cerebra_pred_bar_has = False
        self.cerebra_last_debug_tick = 0
        self.cerebra_last_command_tick = 0
        self.cerebra_missing_target_streak = 0
        self.cerebra_missing_hb_streak = 0
        self.cerebra_overlap_until_tick = 0
        self.cerebra_last_mouse_down_tick = 0
        self.cerebra_last_mouse_up_tick = 0
        self.cerebra_last_border_bbox = None
        self.cerebra_last_strip_bbox = None
        self.cerebra_border_miss_count = 0
        self.cerebra_strip_miss_count = 0
        self.cerebra_last_report = None
        self.cerebra_last_snapshot = None
        self.cerebra_last_start_debug_tick = 0
        self.cerebra_last_ocr_skip_tick = 0
        self.cerebra_last_bar_source = "none"
        self.cerebra_last_bar_source_x = 0.0
        self.cerebra_last_target_log_mode = ""
        self.cerebra_last_target_log_tick = 0
        self.cerebra_last_target_phase = "SEARCH_TARGET"
        self.cerebra_result_history = deque(maxlen=12)
        self.cerebra_result_window_started = 0
        self.cerebra_pid_integral = 0.0
        self.cerebra_pid_prev_error = 0.0
        self.cerebra_pid_last_time = None
        self.cerebra_deadzone_action = 0
        self.cerebra_last_actuation_switch_tick = 0
        self.cerebra_telemetry = deque(maxlen=self.CEREBRA_AUTO_TUNE_WINDOW)
        self.cerebra_last_autotune_tick = 0
        self.cerebra_caught_count = 0
        self.cerebra_lost_count = 0
        self.cerebra_target_tracker_state = CerebraTrackerState()
        self.cerebra_bar_tracker_state = CerebraTrackerState()
        self.cerebra_vision_debug = CerebraVisionDebug()
        self.cerebra_actuation = CerebraActuationState(release_since_tick=self.tick())
        self.cerebra_bootstrap = CerebraBootstrapState()
        self.cerebra_failed_bootstrap_zones = deque(maxlen=8)
        self.cerebra_target_last_real_tick = 0
        self.cerebra_target_frames_since_real = 0
        self.cerebra_target_frames_since_confirmed = 0
        self.cerebra_target_prediction_age = 0
        self.cerebra_bootstrap_started_tick = 0
        self.cerebra_bootstrap_confirm_frames = 0
        self.cerebra_recent_failed_bootstrap_positions = deque(maxlen=8)
        self.cerebra_last_target_trust = "invalid"
        self.cerebra_last_reject_log: dict[str, int] = {}
        self.roblox_hwnd = self._resolve_roblox_hwnd()
        self.paused = False
        self.exit_requested = False
        self._f2_prev = False
        self._f3_prev = False
        self._f2_last_tick = 0
        self._f3_last_tick = 0
        self.live_tuning_path = self.root / self.LIVE_TUNING_FILE
        self.live_tuning_mtime = 0.0
        self.live_tuning_last_check = 0
        self.shake_template = self._load_image(self.root / "Assets" / "Shake.png")
        self.cerebra_templates = self._load_cerebra_templates()
        self.cerebra_system = CerebraVisionSystem(cv2, np, self._build_cerebra_vision_config())
        self._init_live_tuning_file()
        self.update_stats_title()
        self.hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self.hotkey_thread.start()
        if pytesseract is None:
            self.log(
                "OCR disabled (pytesseract not available). "
                "Install with: py -m pip install pytesseract and install Tesseract OCR."
            )

    @staticmethod
    def _key_down(vk_code: int) -> bool:
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)

    def handle_hotkeys(self) -> None:
        # Kept for compatibility; hotkeys are handled in a dedicated polling thread.
        return

    def _hotkey_loop(self) -> None:
        while not self.exit_requested:
            try:
                now = self.tick()
                # low bit = key was pressed since previous GetAsyncKeyState call
                f2_state = ctypes.windll.user32.GetAsyncKeyState(0x71)
                f3_state = ctypes.windll.user32.GetAsyncKeyState(0x72)
                f2_down = bool(f2_state & 0x8000)
                f3_down = bool(f3_state & 0x8000)
                f2_pressed = bool(f2_state & 0x1) or (f2_down and not self._f2_prev)
                f3_pressed = bool(f3_state & 0x1) or (f3_down and not self._f3_prev)
                if f2_pressed and (now - self._f2_last_tick) >= self.HOTKEY_DEBOUNCE_MS:
                    self.paused = not self.paused
                    self._f2_last_tick = now
                    self.log("Python paused (F2)" if self.paused else "Python resumed (F2)")
                if f3_pressed and (now - self._f3_last_tick) >= self.HOTKEY_DEBOUNCE_MS:
                    self.exit_requested = True
                    self._f3_last_tick = now
                    self.log("Python exit requested (F3)")
                self._f2_prev = f2_down
                self._f3_prev = f3_down
            except Exception:
                pass
            time.sleep(max(0.001, self.HOTKEY_POLL_MS / 1000.0))

    def wait_if_paused(self) -> bool:
        while self.paused and not self.exit_requested:
            time.sleep(0.02)
        return self.exit_requested

    def log(self, msg: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
        print(line, flush=True)
        with (self.logs_dir / "cerebra_python_runtime.log").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _build_cerebra_vision_config(self) -> VisionConfig:
        return VisionConfig(
            border_hsv_low=(CEREBRA_BORDER_HUE_MIN, CEREBRA_BORDER_SAT_MIN, CEREBRA_BORDER_VAL_MIN),
            border_hsv_high=(CEREBRA_BORDER_HUE_MAX, 255, 255),
            border_min_area=CEREBRA_BORDER_MIN_AREA,
            border_aspect_range=(CEREBRA_BORDER_ASPECT_MIN, CEREBRA_BORDER_ASPECT_MAX),
            border_padding_x=CEREBRA_CAPTURE_MASK_PAD_X,
            border_padding_y=CEREBRA_CAPTURE_MASK_PAD_Y,
            target_dark_max=CEREBRA_BLACK_WAVE_MAX_LUMA,
            target_pink_hsv_low=(CEREBRA_SMALL_HUE_MIN, CEREBRA_SMALL_SAT_MIN, CEREBRA_SMALL_VAL_MIN),
            target_pink_hsv_high=(CEREBRA_SMALL_HUE_MAX, 255, CEREBRA_SMALL_VAL_MAX),
            target_gate_px=float(CEREBRA_TARGET_LOCK_MAX_JUMP_PX),
            target_max_jump_px=float(min(CEREBRA_TARGET_LOCK_MAX_JUMP_PX, CEREBRA_TARGET_MAX_JUMP_PX_STRICT + 10.0)),
            prediction_lead_ms=float(min(self.CEREBRA_DYNAMIC_LOOKAHEAD_MAX_MS, self.CEREBRA_DYNAMIC_LOOKAHEAD_BASE_MS + 18.0)),
            control_deadzone_px=float(self.CATCH_DEADZONE_PX + self.CEREBRA_EXTRA_DEADZONE_PX),
            control_hysteresis_px=float(max(2.0, self.CEREBRA_HOLD_KEEP_BAND_PX + 0.8)),
            control_switch_delay_ms=int(max(self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS, CEREBRA_ACTION_SWITCH_COOLDOWN_MS)),
            control_reengage_error_px=float(self.CEREBRA_REENGAGE_ERR_PX),
            control_hold_bias_px=float(self.CEREBRA_OVERLAP_EDGE_BIAS_PX * 0.20),
            control_keep_band_px=float(max(self.CEREBRA_HOLD_KEEP_BAND_PX + 1.5, CEREBRA_ACTION_STICKY_OVERLAP_PX * 0.55)),
            control_min_action_ms=int(max(self.CEREBRA_MIN_HOLD_MS, CEREBRA_ACTION_MIN_HOLD_MS)),
            control_strong_flip_px=float(max(self.CEREBRA_REENGAGE_ERR_PX + 4.0, CEREBRA_ACTION_REVERSE_ERR_PX)),
            control_startup_confidence=float(max(0.48, CEREBRA_CONFIDENCE_ACT_MIN_TARGET)),
        )

    def _sync_cerebra_vision_config(self) -> None:
        self.cerebra_system.update_config(self._build_cerebra_vision_config())

    def _cerebra_lane_rect(self) -> VisionRect:
        return VisionRect(
            x=int(self.CATCH_BAR.x1),
            y=int(self.CATCH_BAR.y1),
            w=int(self.CATCH_BAR.w),
            h=int(self.CATCH_BAR.h),
        )

    def _cerebra_border_scan_rect(self) -> VisionRect:
        return VisionRect(
            x=int(self.CATCH_BORDER_SCAN.x1),
            y=int(self.CATCH_BORDER_SCAN.y1),
            w=int(self.CATCH_BORDER_SCAN.w),
            h=int(self.CATCH_BORDER_SCAN.h),
        )

    def _measure_cerebra_bar(self, dt: int) -> Optional[VisionMeasurement]:
        # Keep bar measurement conservative: stable heartbeat first, then validated strip geometry, then short prediction grace.
        heartbeat = self.find_heartbeat_x()
        if heartbeat is not None:
            if self.cerebra_bar_tracker_state.last_good_tick > 0:
                jump = abs(float(heartbeat) - self.cerebra_bar_tracker_state.position)
                if jump > CEREBRA_CONTROL_MAX_JUMP_PX:
                    self._log_cerebra_rejection("control_bar", "jump_too_large", f"jump={jump:.1f} source=heartbeat")
                    heartbeat = int(round((self.cerebra_bar_tracker_state.position * 0.75) + (float(heartbeat) * 0.25)))
            self.cerebra_vision_debug.control_confidence = 0.95
            self.cerebra_vision_debug.control_source = "heartbeat"
            return VisionMeasurement(x=float(heartbeat), confidence=0.95, width=1.0, source="heartbeat")
        bbox = self.detect_cerebra_bar_bbox()
        if bbox is not None:
            x, _, w, _ = bbox
            center = float(x + (w / 2.0))
            if self.cerebra_bar_tracker_state.last_good_tick > 0:
                jump = abs(center - self.cerebra_bar_tracker_state.position)
                if jump > CEREBRA_CONTROL_MAX_JUMP_PX:
                    self._log_cerebra_rejection("control_bar", "jump_too_large", f"jump={jump:.1f} source=bar_bbox")
                    return None
            conf = max(0.32, min(0.88, self.cerebra_vision_debug.strip_confidence * 0.92))
            self.cerebra_vision_debug.control_confidence = conf
            self.cerebra_vision_debug.control_source = "bar_bbox"
            return VisionMeasurement(x=center, confidence=conf, width=float(w), source="bar_bbox")
        if self.state.has_bar or self.cerebra_bar_tracker_state.last_good_tick > 0:
            predicted = self.state.last_bar_middle_x + (self.state.bar_velocity * max(dt, 1))
            if self.cerebra_bar_tracker_state.last_good_tick > 0:
                predicted = self.cerebra_bar_tracker_state.position + (self.cerebra_bar_tracker_state.velocity * max(dt, 1))
            self.cerebra_vision_debug.control_confidence = max(0.0, self.cerebra_bar_tracker_state.confidence * 0.65)
            self.cerebra_vision_debug.control_source = "bar_prediction"
            return VisionMeasurement(
                x=float(self.clamp(predicted, self.CATCH_BAR_TOP_LINE.x1, self.CATCH_BAR_TOP_LINE.x2)),
                confidence=0.35,
                width=1.0,
                source="bar_prediction",
            )
        return None

    def _should_scan_result_ocr(self, state_name: str) -> bool:
        return state_name == "RESULT_OR_END"

    def _live_tuning_defaults(self) -> dict[str, Any]:
        return {
            "__note": "Edit values while macro is running; file is hot-reloaded automatically.",
            "enabled": True,
            "CEREBRA_HOLD_KEEP_BAND_PX": self.CEREBRA_HOLD_KEEP_BAND_PX,
            "CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS": self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS,
            "CEREBRA_OVERLAP_EDGE_BIAS_PX": self.CEREBRA_OVERLAP_EDGE_BIAS_PX,
            "CEREBRA_REENGAGE_ERR_PX": self.CEREBRA_REENGAGE_ERR_PX,
            "CEREBRA_DYNAMIC_LOOKAHEAD_BASE_MS": self.CEREBRA_DYNAMIC_LOOKAHEAD_BASE_MS,
            "CEREBRA_BLACK_WAVE_MAX_LUMA": CEREBRA_BLACK_WAVE_MAX_LUMA,
            "CEREBRA_TARGET_LOCK_MAX_JUMP_PX": CEREBRA_TARGET_LOCK_MAX_JUMP_PX,
            "CEREBRA_POLL_MIN": self.CEREBRA_POLL_MIN,
            "CEREBRA_POLL_MAX": self.CEREBRA_POLL_MAX,
            "HOTKEY_POLL_MS": self.HOTKEY_POLL_MS,
            "HOTKEY_DEBOUNCE_MS": self.HOTKEY_DEBOUNCE_MS,
        }

    def _init_live_tuning_file(self) -> None:
        try:
            if not self.live_tuning_path.exists():
                with self.live_tuning_path.open("w", encoding="utf-8") as f:
                    json.dump(self._live_tuning_defaults(), f, indent=2)
            self.live_tuning_mtime = self.live_tuning_path.stat().st_mtime
        except Exception as exc:
            self.log(f"Live tuning init failed: {exc}")

    def _coerce_live_tuning_value(self, key: str, value: Any) -> Any:
        schema: dict[str, tuple[type, Optional[float], Optional[float]]] = {
            "CEREBRA_HOLD_KEEP_BAND_PX": (float, 0.0, 40.0),
            "CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS": (int, 0.0, 1000.0),
            "CEREBRA_OVERLAP_EDGE_BIAS_PX": (float, 0.0, 80.0),
            "CEREBRA_REENGAGE_ERR_PX": (float, 0.0, 80.0),
            "CEREBRA_DYNAMIC_LOOKAHEAD_BASE_MS": (float, 0.0, 250.0),
            "CEREBRA_BLACK_WAVE_MAX_LUMA": (int, 0.0, 255.0),
            "CEREBRA_TARGET_LOCK_MAX_JUMP_PX": (float, 5.0, 200.0),
            "CEREBRA_POLL_MIN": (int, 1.0, 500.0),
            "CEREBRA_POLL_MAX": (int, 1.0, 500.0),
            "HOTKEY_POLL_MS": (int, 1.0, 1000.0),
            "HOTKEY_DEBOUNCE_MS": (int, 10.0, 2000.0),
        }
        if key not in schema:
            raise ValueError("unsupported_key")
        ktype, lo, hi = schema[key]
        if ktype is bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)
        if ktype is int:
            v = int(round(float(value)))
        else:
            v = float(value)
        if lo is not None and v < lo:
            v = lo
        if hi is not None and v > hi:
            v = hi
        return int(v) if ktype is int else float(v)

    def _reload_live_tuning_if_needed(self, force: bool = False) -> None:
        now = self.tick()
        if not force and (now - self.live_tuning_last_check) < self.LIVE_TUNING_CHECK_MS:
            return
        self.live_tuning_last_check = now
        try:
            if not self.live_tuning_path.exists():
                return
            mtime = self.live_tuning_path.stat().st_mtime
            if not force and mtime <= self.live_tuning_mtime:
                return
            with self.live_tuning_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            self.live_tuning_mtime = mtime
            if not isinstance(data, dict) or not data.get("enabled", True):
                return

            applied = []
            for key, raw in data.items():
                if key in {"enabled", "__note"}:
                    continue
                try:
                    val = self._coerce_live_tuning_value(key, raw)
                except Exception:
                    continue
                if key in {"CEREBRA_BLACK_WAVE_MAX_LUMA", "CEREBRA_TARGET_LOCK_MAX_JUMP_PX"}:
                    globals()[key] = val
                    applied.append(f"{key}={val}")
                    continue
                setattr(self, key, val)
                applied.append(f"{key}={val}")

            # keep polling bounds sane
            if int(self.CEREBRA_POLL_MIN) > int(self.CEREBRA_POLL_MAX):
                self.CEREBRA_POLL_MAX = int(self.CEREBRA_POLL_MIN)
            self._sync_cerebra_vision_config()
            if applied:
                self.log("Live tuning applied: " + ", ".join(applied[:8]) + (" ..." if len(applied) > 8 else ""))
        except Exception as exc:
            self.log(f"Live tuning reload failed: {exc}")

    def reset_cerebra_cycle_state(self) -> None:
        # Clear per-cycle detectors/predictors so previous catches cannot poison the next run.
        self.state = CatchState(last_tick=self.tick())
        self._sync_cerebra_vision_config()
        self.cerebra_system.reset()
        self.last_heartbeat_x = 0
        self.cerebra_last_direction = 0
        self.cerebra_last_direction_tick = 0
        self.cerebra_err_smooth = 0.0
        self.cerebra_target_x = 0.0
        self.cerebra_target_v = 0.0
        self.cerebra_target_has = False
        self.cerebra_target_samples.clear()
        self.cerebra_target_misses = 0
        self.cerebra_prev_small_gray = None
        self.cerebra_pred_bar_x = 0.0
        self.cerebra_pred_bar_has = False
        self.cerebra_last_debug_tick = 0
        self.cerebra_last_result_check = 0
        self.cerebra_missing_target_streak = 0
        self.cerebra_missing_hb_streak = 0
        self.cerebra_overlap_until_tick = 0
        self.cerebra_last_mouse_down_tick = 0
        self.cerebra_last_mouse_up_tick = 0
        self.cerebra_last_border_bbox = None
        self.cerebra_last_strip_bbox = None
        self.cerebra_border_miss_count = 0
        self.cerebra_strip_miss_count = 0
        self.cerebra_last_report = None
        self.cerebra_last_snapshot = None
        self.cerebra_target_tracker_state = CerebraTrackerState()
        self.cerebra_bar_tracker_state = CerebraTrackerState()
        self.cerebra_vision_debug = CerebraVisionDebug()
        self.cerebra_actuation = CerebraActuationState(release_since_tick=self.tick())
        self.cerebra_bootstrap = CerebraBootstrapState()
        self.cerebra_failed_bootstrap_zones.clear()
        self.cerebra_target_last_real_tick = 0
        self.cerebra_target_frames_since_real = 0
        self.cerebra_target_frames_since_confirmed = 0
        self.cerebra_target_prediction_age = 0
        self.cerebra_bootstrap_started_tick = 0
        self.cerebra_bootstrap_confirm_frames = 0
        self.cerebra_recent_failed_bootstrap_positions.clear()
        self.cerebra_last_target_trust = "invalid"
        self.cerebra_last_reject_log.clear()
        self.cerebra_last_start_debug_tick = 0
        self.cerebra_last_ocr_skip_tick = 0
        self.cerebra_last_bar_source = "none"
        self.cerebra_last_bar_source_x = 0.0
        self.cerebra_last_target_log_mode = ""
        self.cerebra_last_target_log_tick = 0
        self.cerebra_last_target_phase = "SEARCH_TARGET"
        self.cerebra_result_history.clear()
        self.cerebra_result_window_started = 0
        self.cerebra_pid_integral = 0.0
        self.cerebra_pid_prev_error = 0.0
        self.cerebra_pid_last_time = None
        self.cerebra_deadzone_action = 0
        self.cerebra_last_actuation_switch_tick = 0
        self.cerebra_telemetry.clear()
        self.cerebra_last_autotune_tick = 0

    def cerebra_pid_control(self, error: float) -> float:
        now = time.perf_counter()
        if self.cerebra_pid_last_time is None:
            self.cerebra_pid_last_time = now
            self.cerebra_pid_prev_error = error
            return 0.0

        dt = now - self.cerebra_pid_last_time
        if dt <= 0:
            return 0.0

        self.cerebra_pid_integral += error * dt
        clamp = float(self.CEREBRA_PID_CLAMP)
        self.cerebra_pid_integral = self.clamp(self.cerebra_pid_integral, -clamp, clamp)

        derivative = (error - self.cerebra_pid_prev_error) / dt
        out = (
            (self.CEREBRA_PID_KP * error)
            + (self.CEREBRA_PID_KI * self.cerebra_pid_integral)
            + (self.CEREBRA_PID_KD * derivative)
        )
        out = self.clamp(out, -clamp, clamp)

        self.cerebra_pid_prev_error = error
        self.cerebra_pid_last_time = now
        return float(out)

    def _cerebra_autotune_from_telemetry(self) -> None:
        if not self.CEREBRA_AUTO_TUNE_ENABLE:
            return
        now = self.tick()
        if (now - self.cerebra_last_autotune_tick) < int(self.CEREBRA_AUTO_TUNE_APPLY_MS):
            return
        self.cerebra_last_autotune_tick = now
        n = len(self.cerebra_telemetry)
        if n < int(self.CEREBRA_AUTO_TUNE_MIN_SAMPLES):
            return

        arr = list(self.cerebra_telemetry)
        overlap_rate = sum(1 for r in arr if r["overlap"]) / float(n)
        switch_rate = sum(1 for r in arr if r["switched"]) / float(n)
        mean_abs_err = sum(abs(float(r["err"])) for r in arr) / float(n)

        changed = []
        # Too jittery: damp and add stickiness.
        if switch_rate >= float(self.CEREBRA_AUTO_TUNE_SWITCH_RATE_HIGH):
            old = self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS
            self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS = int(min(120, old + 6))
            if self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS != old:
                changed.append(f"cooldown={self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS}")

            old = self.CEREBRA_HOLD_KEEP_BAND_PX
            self.CEREBRA_HOLD_KEEP_BAND_PX = float(min(6.0, old + 0.25))
            if self.CEREBRA_HOLD_KEEP_BAND_PX != old:
                changed.append(f"keep_band={self.CEREBRA_HOLD_KEEP_BAND_PX:.2f}")

            old = self.CEREBRA_ERR_SMOOTH_ALPHA
            self.CEREBRA_ERR_SMOOTH_ALPHA = float(max(0.10, old - 0.02))
            if self.CEREBRA_ERR_SMOOTH_ALPHA != old:
                changed.append(f"alpha={self.CEREBRA_ERR_SMOOTH_ALPHA:.2f}")

        # Poor overlap: make controller more responsive and easier to engage.
        if overlap_rate <= float(self.CEREBRA_AUTO_TUNE_OVERLAP_LOW) and mean_abs_err > 3.0:
            old = self.CEREBRA_HOLD_ENTER_ERR_PX
            self.CEREBRA_HOLD_ENTER_ERR_PX = float(max(1.2, old - 0.2))
            if self.CEREBRA_HOLD_ENTER_ERR_PX != old:
                changed.append(f"hold_enter={self.CEREBRA_HOLD_ENTER_ERR_PX:.2f}")

            old = self.CEREBRA_RELEASE_ENTER_ERR_PX
            self.CEREBRA_RELEASE_ENTER_ERR_PX = float(max(1.2, old - 0.2))
            if self.CEREBRA_RELEASE_ENTER_ERR_PX != old:
                changed.append(f"release_enter={self.CEREBRA_RELEASE_ENTER_ERR_PX:.2f}")

        # Stable and good overlap: slowly tighten so it doesn't feel sluggish.
        if overlap_rate >= float(self.CEREBRA_AUTO_TUNE_OVERLAP_GOOD) and switch_rate < 0.18 and mean_abs_err < 3.0:
            old = self.CEREBRA_HOLD_KEEP_BAND_PX
            self.CEREBRA_HOLD_KEEP_BAND_PX = float(max(1.0, old - 0.1))
            if self.CEREBRA_HOLD_KEEP_BAND_PX != old:
                changed.append(f"keep_band={self.CEREBRA_HOLD_KEEP_BAND_PX:.2f}")

            old = self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS
            self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS = int(max(24, old - 2))
            if self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS != old:
                changed.append(f"cooldown={self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS}")

        if changed:
            self.log(
                "AutoTune "
                f"ovr={overlap_rate:.2f} sw={switch_rate:.2f} err={mean_abs_err:.2f} -> "
                + ", ".join(changed)
            )

    def update_stats_title(self) -> None:
        title = f"caught : {self.cerebra_caught_count} lost: {self.cerebra_lost_count}"
        # 1) Console title (when launched in a console host).
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        except Exception:
            pass

        # 2) If no console is visible, update OpenCV debug window titles as fallback.
        for name in [
            "Cerebra HSV Frame",
            "Cerebra Debug Frame",
            "Cerebra Border Debug",
            "Cerebra Black Wave Debug",
        ]:
            try:
                cv2.setWindowTitle(name, f"{title} | {name}")
            except Exception:
                pass

        # 3) Roblox game window title (what AHK Window Spy shows as ahk_exe RobloxPlayerBeta.exe).
        try:
            if not self.roblox_hwnd:
                self.roblox_hwnd = self._resolve_roblox_hwnd()
            if self.roblox_hwnd:
                ctypes.windll.user32.SetWindowTextW(wintypes.HWND(self.roblox_hwnd), title)
        except Exception:
            pass

    def record_cerebra_result(self, won: bool) -> None:
        if won:
            self.cerebra_caught_count += 1
        else:
            self.cerebra_lost_count += 1
        self.update_stats_title()

    def _resolve_roblox_hwnd(self) -> int:
        """
        Find top-level window handle for Roblox near known client coords.
        """
        try:
            # Probe a point inside client content.
            px = int(self.client_x + 400)
            py = int(self.client_y + 300)
            pt = wintypes.POINT(px, py)
            hwnd = ctypes.windll.user32.WindowFromPoint(pt)
            if hwnd:
                # GA_ROOT = 2 -> top-level owner window.
                hwnd = ctypes.windll.user32.GetAncestor(wintypes.HWND(hwnd), 2)
                if hwnd:
                    return int(hwnd)
        except Exception:
            pass
        return 0

    def tick(self) -> int:
        return int(time.perf_counter() * 1000)

    @staticmethod
    def clamp(v: float, low: float, high: float) -> float:
        return low if v < low else high if v > high else v

    @staticmethod
    def _color_to_bgr(color: int) -> Any:
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return np.array([b, g, r], dtype=np.uint8)

    @staticmethod
    def _similar(ca: int, cb: int, tol: int) -> bool:
        ra, ga, ba = (ca >> 16) & 0xFF, (ca >> 8) & 0xFF, ca & 0xFF
        rb, gb, bb = (cb >> 16) & 0xFF, (cb >> 8) & 0xFF, cb & 0xFF
        return abs(ra - rb) <= tol and abs(ga - gb) <= tol and abs(ba - bb) <= tol

    def _norm_control(self, value: float) -> float:
        return value / 100.0 if abs(value) > 1.0 else value

    def heartbeat_ratio(self) -> float:
        return float(
            self.clamp(
                self.HEARTBEAT_BASE_RATIO + self._norm_control(self.control),
                self.HEARTBEAT_MIN_RATIO,
                self.HEARTBEAT_MAX_RATIO,
            )
        )

    def to_screen(self, x: int, y: int) -> Tuple[int, int]:
        return self.client_x + x, self.client_y + y

    def _mon(self, r: Region) -> dict:
        x, y = self.to_screen(r.x1, r.y1)
        return {"left": x, "top": y, "width": r.w, "height": r.h}

    def grab(self, r: Region) -> Any:
        shot = self.sct.grab(self._mon(r))
        return np.array(shot)[:, :, :3]

    def _cerebra_keep_region(self) -> Region:
        # Prefer detected big-border bounds (expanded), fallback to fixed catch-bar ROI.
        if self.cerebra_last_border_bbox is not None:
            bx, by, bw, bh = self.cerebra_last_border_bbox
            px = int(max(0, CEREBRA_CAPTURE_MASK_PAD_X))
            py = int(max(0, CEREBRA_CAPTURE_MASK_PAD_Y))
            x1 = max(self.CATCH_BAR.x1, bx - px)
            y1 = max(self.CATCH_BAR.y1, by - py)
            x2 = min(self.CATCH_BAR.x2, bx + bw + px)
            y2 = min(self.CATCH_BAR.y2, by + bh + py)
            if x2 > x1 and y2 > y1:
                return Region(x1, y1, x2, y2)
        return self.CATCH_BAR

    def grab_cerebra_masked(self, r: Region) -> Any:
        frame = self.grab(r)
        if not CEREBRA_CAPTURE_MASK_ENABLE:
            return frame

        keep = self._cerebra_keep_region()
        ix1 = max(r.x1, keep.x1)
        iy1 = max(r.y1, keep.y1)
        ix2 = min(r.x2, keep.x2)
        iy2 = min(r.y2, keep.y2)
        if ix2 <= ix1 or iy2 <= iy1:
            return np.zeros_like(frame)

        out = np.zeros_like(frame)
        sx1 = ix1 - r.x1
        sy1 = iy1 - r.y1
        sx2 = ix2 - r.x1 + 1
        sy2 = iy2 - r.y1 + 1
        out[sy1:sy2, sx1:sx2] = frame[sy1:sy2, sx1:sx2]
        return out

    def _log_cerebra_rejection(self, category: str, reason: str, detail: str = "") -> None:
        if not DEBUG_CEREBRA:
            return
        key = f"{category}:{reason}"
        now = self.tick()
        last = self.cerebra_last_reject_log.get(key, 0)
        if (now - last) < 250:
            return
        self.cerebra_last_reject_log[key] = now
        suffix = f" {detail}" if detail else ""
        self.log(f"Cerebra reject {category} reason={reason}{suffix}")

    @staticmethod
    def _bbox_center_x(bbox: Tuple[int, int, int, int]) -> float:
        x, _, w, _ = bbox
        return float(x + (w / 2.0))

    @staticmethod
    def _bbox_fill_ratio(area: float, w: int, h: int) -> float:
        return float(area) / float(max(1, w * h))

    def _update_local_tracker(
        self,
        tracker: CerebraTrackerState,
        measurement_x: Optional[float],
        confidence: float,
        source: str,
        dt: int,
        now: int,
        lane_min: float,
        lane_max: float,
    ) -> CerebraTrackerState:
        dt = max(int(dt), 1)
        if measurement_x is None:
            tracker.predicted_position = float(
                self.clamp(tracker.position + (tracker.velocity * dt), lane_min, lane_max)
            )
            tracker.position = tracker.predicted_position
            tracker.velocity *= 0.85
            tracker.confidence *= 0.84
            tracker.missing_frames += 1
            return tracker

        x = float(self.clamp(measurement_x, lane_min, lane_max))
        if tracker.last_good_tick > 0:
            inst_v = (x - tracker.position) / float(dt)
            tracker.velocity = (tracker.velocity * 0.72) + (inst_v * 0.28)
        else:
            tracker.velocity = 0.0
        tracker.position = x
        tracker.predicted_position = x
        tracker.confidence = float(max(0.0, min(1.0, confidence)))
        tracker.missing_frames = 0
        tracker.last_measurement_source = source
        tracker.last_good_tick = now
        return tracker

    def _sync_cerebra_trackers_from_report(self, report: Any, now: int, dt: int) -> None:
        lane_min = float(self.CATCH_BAR_TOP_LINE.x1)
        lane_max = float(self.CATCH_BAR_TOP_LINE.x2)
        target_measurement = report.target_measurement.x if report.target_measurement is not None else None
        target_source = report.target_measurement.source if report.target_measurement is not None else "predicted"
        target_conf = (
            report.target_measurement.confidence
            if report.target_measurement is not None
            else report.target_state.confidence
        )
        bar_measurement = report.control_measurement.x if report.control_measurement is not None else None
        bar_source = report.control_measurement.source if report.control_measurement is not None else "predicted"
        bar_conf = (
            report.control_measurement.confidence
            if report.control_measurement is not None
            else report.bar_state.confidence
        )

        self._update_local_tracker(
            self.cerebra_target_tracker_state,
            target_measurement if report.target_state.has_lock else None,
            target_conf,
            target_source,
            dt,
            now,
            lane_min,
            lane_max,
        )
        self._update_local_tracker(
            self.cerebra_bar_tracker_state,
            bar_measurement if report.bar_state.has_lock else None,
            bar_conf,
            bar_source,
            dt,
            now,
            lane_min,
            lane_max,
        )
        self.cerebra_target_tracker_state.position = float(report.target_state.position)
        self.cerebra_target_tracker_state.velocity = float(report.target_state.velocity)
        self.cerebra_target_tracker_state.confidence = float(report.target_state.confidence)
        self.cerebra_target_tracker_state.missing_frames = int(report.target_state.missing_frames)
        self.cerebra_target_tracker_state.predicted_position = float(
            self.clamp(
                report.target_state.position + (report.target_state.velocity * max(dt, 1)),
                lane_min,
                lane_max,
            )
        )
        self.cerebra_bar_tracker_state.position = float(report.bar_state.position)
        self.cerebra_bar_tracker_state.velocity = float(report.bar_state.velocity)
        self.cerebra_bar_tracker_state.confidence = float(report.bar_state.confidence)
        self.cerebra_bar_tracker_state.missing_frames = int(report.bar_state.missing_frames)
        self.cerebra_bar_tracker_state.predicted_position = float(
            self.clamp(
                report.bar_state.position + (report.bar_state.velocity * max(dt, 1)),
                lane_min,
                lane_max,
            )
        )

    def _score_cerebra_strip_bbox(
        self,
        bbox_local: Tuple[int, int, int, int],
        area: float,
        search: Region,
        previous_abs_bbox: Optional[Tuple[int, int, int, int]],
        jump_limit_px: float,
        min_fill_ratio: float,
    ) -> Tuple[float, Optional[str], Tuple[int, int, int, int]]:
        x, y, w, h = bbox_local
        abs_bbox = (search.x1 + x, search.y1 + y, w, h)
        if w < 14 or h < 4:
            return 0.0, "bad_geometry", abs_bbox
        aspect = float(w) / float(max(h, 1))
        fill_ratio = self._bbox_fill_ratio(area, w, h)
        if aspect < 2.2 or aspect > 32.0:
            return 0.0, "bad_geometry", abs_bbox
        if fill_ratio < min_fill_ratio:
            return 0.0, "noisy_mask", abs_bbox
        if previous_abs_bbox is not None:
            prev_center = self._bbox_center_x(previous_abs_bbox)
            center = self._bbox_center_x(abs_bbox)
            jump = abs(center - prev_center)
            if jump > jump_limit_px:
                return 0.0, "jump_too_large", abs_bbox
            continuity = max(0.0, 1.0 - (jump / max(1.0, jump_limit_px)))
        else:
            continuity = 0.45
        width_ratio = min(1.0, float(w) / max(24.0, float(self.CATCH_BAR.w) * 0.22))
        height_ratio = min(1.0, float(h) / max(6.0, float(self.CATCH_BAR.h) * 0.45))
        score = (0.40 * width_ratio) + (0.18 * height_ratio) + (0.20 * min(1.0, fill_ratio / 0.45)) + (0.22 * continuity)
        return float(max(0.0, min(1.0, score))), None, abs_bbox

    def _cerebra_border_search_region(self) -> Region:
        if self.cerebra_last_border_bbox is None:
            return self.CATCH_BORDER_SCAN
        bx, by, bw, bh = self.cerebra_last_border_bbox
        pad_x = max(18, int(round(bw * 0.18)))
        pad_y = max(10, int(round(bh * 1.20)))
        return Region(
            max(self.CATCH_BORDER_SCAN.x1, bx - pad_x),
            max(self.CATCH_BORDER_SCAN.y1, by - pad_y),
            min(self.CATCH_BORDER_SCAN.x2, bx + bw + pad_x),
            min(self.CATCH_BORDER_SCAN.y2, by + bh + pad_y),
        )

    def _expire_failed_bootstrap_zones(self, now: int) -> None:
        while self.cerebra_failed_bootstrap_zones and (now - self.cerebra_failed_bootstrap_zones[0].created_tick) > CEREBRA_BOOTSTRAP_FAILED_ZONE_MS:
            self.cerebra_failed_bootstrap_zones.popleft()

    def _record_failed_bootstrap_zone(self, now: int, x: float, reason: str) -> None:
        zone = CerebraFailedBootstrapZone(
            created_tick=now,
            x=float(x),
            radius=float(CEREBRA_BOOTSTRAP_FAILED_ZONE_RADIUS),
            reason=reason,
        )
        self.cerebra_failed_bootstrap_zones.append(zone)
        self.cerebra_recent_failed_bootstrap_positions.append(float(x))
        self.log(f"Cerebra failed zone add x={x:.1f} radius={zone.radius:.1f} reason={reason}")

    def _failed_zone_penalty(self, now: int, x: float) -> float:
        self._expire_failed_bootstrap_zones(now)
        penalty = 0.0
        for zone in self.cerebra_failed_bootstrap_zones:
            distance = abs(float(x) - zone.x)
            if distance > zone.radius:
                continue
            strength = 1.0 - (distance / max(1.0, zone.radius))
            penalty = max(penalty, CEREBRA_BOOTSTRAP_FAILED_ZONE_PENALTY * strength)
        return penalty

    def _bootstrap_candidate_allowed(
        self,
        now: int,
        candidate_x: float,
        candidate_conf: float,
        border_conf: float,
        strip_conf: float,
    ) -> Tuple[bool, str, float]:
        if border_conf < 0.42 or strip_conf < 0.24:
            return False, "weak_gate", 0.0
        penalty = self._failed_zone_penalty(now, candidate_x)
        effective_conf = max(0.0, float(candidate_conf) - penalty)
        if penalty > 0.0 and effective_conf < max(CEREBRA_TARGET_CONFIDENCE_MEDIUM, candidate_conf * 0.90):
            return False, "failed_zone_penalty", effective_conf
        return True, "ok", effective_conf

    def _target_measurement_kind(self, report: Any) -> str:
        if report.target_measurement is None:
            return "none"
        source = str(report.target_measurement.source or "").lower()
        if "bootstrap" in source:
            return "bootstrap"
        if source in {"projection", "contour", "black_wave", "black_wave_projection", "small_bar", "small_bar_contour"}:
            return "measured"
        if source in {"track_grace", "target_prediction", "prediction"}:
            return "predicted"
        return "measured"

    def _target_source_trust(self, report: Any, now: int) -> Tuple[str, float, str]:
        measurement = report.target_measurement
        target_conf = float(report.target_state.confidence)
        border_conf = float(report.border_confidence)
        strip_conf = float(report.inner_confidence)
        kind = self._target_measurement_kind(report)

        if measurement is None:
            if self.cerebra_target_frames_since_real <= CEREBRA_TARGET_GRACE_HELD_FRAMES and self.cerebra_target_last_real_tick > 0:
                grace_conf = max(0.0, target_conf * (0.82 ** self.cerebra_target_frames_since_real))
                return "grace_held", grace_conf, "recent_real_hold"
            if self.cerebra_target_prediction_age <= CEREBRA_TARGET_PREDICTION_SHORT_FRAMES and target_conf >= CEREBRA_TARGET_CONFIDENCE_FLOOR:
                pred_conf = max(0.0, target_conf * (0.72 ** max(0, self.cerebra_target_prediction_age - 1)))
                return "predicted_short", pred_conf, "short_prediction"
            if self.cerebra_target_prediction_age <= CEREBRA_TARGET_PREDICTION_HARD_FRAMES and self.cerebra_target_last_real_tick > 0:
                pred_conf = max(0.0, target_conf * (0.55 ** max(1, self.cerebra_target_prediction_age)))
                return "predicted_stale", pred_conf, "prediction_expiring"
            return "invalid", 0.0, "no_real_target"

        if kind == "bootstrap":
            return "bootstrap_unconfirmed", float(measurement.confidence), "bootstrap_source"

        if kind == "predicted":
            if self.cerebra_target_prediction_age <= CEREBRA_TARGET_PREDICTION_SHORT_FRAMES and measurement.confidence >= CEREBRA_TARGET_CONFIDENCE_FLOOR:
                return "predicted_short", float(measurement.confidence), "reported_prediction"
            return "predicted_stale", float(measurement.confidence) * 0.6, "reported_prediction_stale"

        if border_conf < 0.30 or strip_conf < 0.16:
            penalized = float(measurement.confidence) * 0.62
            if penalized >= CEREBRA_TARGET_CONFIDENCE_MEDIUM:
                return "grace_held", penalized, "weak_gate_penalty"
            return "invalid", penalized, "weak_gate_invalid"

        return "measured", float(measurement.confidence), "real_measurement"

    def _update_target_trust_state(self, report: Any, now: int) -> Tuple[str, float, str]:
        measurement = report.target_measurement
        kind = self._target_measurement_kind(report)
        if measurement is not None and kind == "measured":
            self.cerebra_target_last_real_tick = now
            self.cerebra_target_frames_since_real = 0
            self.cerebra_target_frames_since_confirmed = 0
            self.cerebra_target_prediction_age = 0
        else:
            self.cerebra_target_frames_since_real += 1
            self.cerebra_target_frames_since_confirmed += 1
            self.cerebra_target_prediction_age += 1

        trust, trust_conf, reason = self._target_source_trust(report, now)
        if trust != self.cerebra_last_target_trust:
            self.log(
                "Cerebra target trust "
                f"prev={self.cerebra_last_target_trust} new={trust} conf={trust_conf:.2f} "
                f"age_real={self.cerebra_target_frames_since_real} pred_age={self.cerebra_target_prediction_age} reason={reason}"
            )
            self.cerebra_last_target_trust = trust
        return trust, trust_conf, reason

    def _update_bootstrap_state(self, report: Any, now: int) -> Tuple[bool, str, float]:
        measurement = report.target_measurement
        if measurement is None:
            if self.cerebra_bootstrap.active and (now - self.cerebra_bootstrap.last_tick) > CEREBRA_BOOTSTRAP_EXPIRE_MS:
                self.log("Cerebra bootstrap reset reason=expired")
                self.cerebra_bootstrap = CerebraBootstrapState()
            return False, "no_bootstrap", 0.0

        source = str(measurement.source or "")
        if "bootstrap" not in source.lower():
            if self.cerebra_bootstrap.active and self.cerebra_bootstrap.confirm_frames < CEREBRA_BOOTSTRAP_CONFIRM_REQUIRED:
                self._record_failed_bootstrap_zone(now, self.cerebra_bootstrap.candidate_x, "replaced_before_confirm")
            self.cerebra_bootstrap = CerebraBootstrapState()
            return False, "not_bootstrap", float(measurement.confidence)

        allowed, allow_reason, effective_conf = self._bootstrap_candidate_allowed(
            now,
            measurement.x,
            float(measurement.confidence),
            float(report.border_confidence),
            float(report.inner_confidence),
        )
        if not allowed:
            self._log_cerebra_rejection(
                "bootstrap",
                allow_reason,
                f"x={measurement.x:.1f} conf={measurement.confidence:.2f} border={report.border_confidence:.2f} strip={report.inner_confidence:.2f}",
            )
            if self.cerebra_bootstrap.active and abs(self.cerebra_bootstrap.candidate_x - measurement.x) <= CEREBRA_BOOTSTRAP_CONFIRM_RADIUS_PX:
                self._record_failed_bootstrap_zone(now, measurement.x, allow_reason)
            self.cerebra_bootstrap = CerebraBootstrapState()
            return False, allow_reason, effective_conf

        if (
            self.cerebra_bootstrap.active
            and abs(self.cerebra_bootstrap.candidate_x - measurement.x) <= CEREBRA_BOOTSTRAP_CONFIRM_RADIUS_PX
        ):
            self.cerebra_bootstrap.confirm_frames += 1
            self.cerebra_bootstrap.candidate_confidence = max(self.cerebra_bootstrap.candidate_confidence, effective_conf)
            self.cerebra_bootstrap.last_tick = now
        else:
            self.cerebra_bootstrap = CerebraBootstrapState(
                candidate_x=float(measurement.x),
                candidate_confidence=float(effective_conf),
                candidate_source=source,
                started_tick=now,
                confirm_frames=1,
                last_tick=now,
                active=True,
            )
            self.cerebra_bootstrap_started_tick = now
            self.log(
                "Cerebra bootstrap start "
                f"x={measurement.x:.1f} conf={effective_conf:.2f} source={source} "
                f"border={report.border_confidence:.2f} strip={report.inner_confidence:.2f}"
            )
            return False, "bootstrap_started", effective_conf

        self.cerebra_bootstrap_confirm_frames = self.cerebra_bootstrap.confirm_frames
        if self.cerebra_bootstrap.confirm_frames >= CEREBRA_BOOTSTRAP_CONFIRM_REQUIRED:
            self.log(
                "Cerebra bootstrap promoted "
                f"x={self.cerebra_bootstrap.candidate_x:.1f} conf={self.cerebra_bootstrap.candidate_confidence:.2f} "
                f"frames={self.cerebra_bootstrap.confirm_frames}"
            )
            self.cerebra_target_last_real_tick = now
            self.cerebra_target_frames_since_real = 0
            self.cerebra_target_prediction_age = 0
            return True, "bootstrap_confirmed", self.cerebra_bootstrap.candidate_confidence
        self.log(
            "Cerebra bootstrap wait "
            f"x={self.cerebra_bootstrap.candidate_x:.1f} frames={self.cerebra_bootstrap.confirm_frames}/{CEREBRA_BOOTSTRAP_CONFIRM_REQUIRED} "
            f"conf={self.cerebra_bootstrap.candidate_confidence:.2f}"
        )
        return False, "bootstrap_wait", self.cerebra_bootstrap.candidate_confidence

    def _target_prediction_valid(self) -> bool:
        return (
            self.cerebra_target_last_real_tick > 0
            and self.cerebra_target_prediction_age <= CEREBRA_TARGET_PREDICTION_HARD_FRAMES
            and self.cerebra_target_frames_since_real <= CEREBRA_TARGET_PREDICTION_HARD_FRAMES
        )

    def _should_disable_target_control(self, trust: str, target_conf: float) -> bool:
        if trust in {"predicted_stale", "invalid", "bootstrap_unconfirmed"}:
            return True
        if trust == "predicted_short" and target_conf < CEREBRA_TARGET_CONFIDENCE_MEDIUM:
            return True
        return target_conf < CEREBRA_TARGET_CONFIDENCE_FLOOR

    def _control_mode_from_target_state(self, trust: str, target_conf: float) -> str:
        if trust == "measured" and target_conf >= CEREBRA_TARGET_CONFIDENCE_STRONG:
            return "strong"
        if trust in {"measured", "grace_held"} and target_conf >= CEREBRA_TARGET_CONFIDENCE_MEDIUM:
            return "medium"
        if trust == "predicted_short":
            return "weak"
        return "invalid"

    def pixel(self, cx: int, cy: int) -> int:
        sx, sy = self.to_screen(cx, cy)
        shot = self.sct.grab({"left": sx, "top": sy, "width": 1, "height": 1})
        px = shot.pixel(0, 0)
        if len(px) == 4:
            b, g, r, _ = px
        else:
            b, g, r = px
        return (r << 16) | (g << 8) | b

    def mouse_down(self) -> None:
        pyautogui.mouseDown(button="left")
        self.cerebra_last_mouse_down_tick = self.tick()

    def mouse_up(self) -> None:
        pyautogui.mouseUp(button="left")
        self.cerebra_last_mouse_up_tick = self.tick()

    def click_client(self, x: int, y: int) -> None:
        sx, sy = self.to_screen(x, y)
        pyautogui.click(x=sx, y=sy)

    def move_client(self, x: int, y: int) -> None:
        sx, sy = self.to_screen(x, y)
        pyautogui.moveTo(sx, sy)

    def _load_image(self, path: Path) -> Optional[Any]:
        if not path.exists():
            return None
        return cv2.imread(str(path), cv2.IMREAD_COLOR)

    def _load_cerebra_templates(self) -> list[Any]:
        out: list[Any] = []
        assets = self.root / "Assets"
        names = ["image.png", "image.webp", "CerebraMinigameUI.png", "CerebraMinigame.png"]
        for n in names:
            img = self._load_image(assets / n)
            if img is not None:
                out.append(img)
        if assets.exists():
            for p in assets.iterdir():
                if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}:
                    img = self._load_image(p)
                    if img is not None:
                        out.append(img)
        return out

    @staticmethod
    def _match(frame: Any, tmpl: Any, th: float) -> bool:
        if frame.shape[0] < tmpl.shape[0] or frame.shape[1] < tmpl.shape[1]:
            return False
        res = cv2.matchTemplate(frame, tmpl, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, _ = cv2.minMaxLoc(res)
        return maxv >= th

    def is_catch_bar_displayed(self) -> bool:
        area = Region(300, 503, 500, 513)
        frame = self.grab(area)
        target = self._color_to_bgr(self.CATCH_BAR_ACTIVE_COLOR)
        best = 0
        for y in range(0, frame.shape[0], 2):
            run = 0
            for x in range(frame.shape[1]):
                if np.all(np.abs(frame[y, x].astype(np.int16) - target.astype(np.int16)) <= self.CATCH_BAR_ACTIVE_VAR):
                    run += 1
                    best = max(best, run)
                else:
                    run = 0
        if best >= self.CATCH_BAR_ACTIVE_MIN_RUN:
            return True
        x, y = self.UI_CATCH_BAR_PIXEL
        return self._similar(self.pixel(x, y), self.CATCH_BAR_ACTIVE_COLOR, 2)

    def _find_color_on_line(self, line: Region, color: int, tol: int) -> Optional[int]:
        frame = self.grab(line)
        target = self._color_to_bgr(color)
        dif = np.abs(frame.astype(np.int16) - target.reshape(1, 1, 3).astype(np.int16))
        mask = np.all(dif <= tol, axis=2)
        xs = np.where(mask[0])[0] if mask.shape[0] else np.array([])
        if xs.size == 0:
            return None
        return int(line.x1 + xs[0])

    def find_fish_x(self) -> Optional[int]:
        return self._find_color_on_line(self.CATCH_BAR_TOP_LINE, self.CALIBRATION_FISH_COLOR, self.FISH_TOL)

    def find_arrow_x(self) -> Optional[int]:
        return self._find_color_on_line(self.CATCH_BAR_ARROW_LINE, self.CATCH_ARROW_COLOR, self.CATCH_ARROW_TOL)

    def find_heartbeat_x(self) -> Optional[int]:
        search = self.CATCH_BAR
        border_bbox = self.detect_cerebra_big_border_bbox()
        if border_bbox is not None:
            bx, by, bw, bh = border_bbox
            search = Region(
                max(self.CATCH_BAR.x1, bx - CEREBRA_CAPTURE_MASK_PAD_X),
                max(self.CATCH_BAR.y1, by - CEREBRA_CAPTURE_MASK_PAD_Y),
                min(self.CATCH_BAR.x2, bx + bw + CEREBRA_CAPTURE_MASK_PAD_X),
                min(self.CATCH_BAR.y2, by + bh + CEREBRA_CAPTURE_MASK_PAD_Y),
            )
        frame = self.grab(search)
        bbox, _ = detect_cerebra_bar_hsv(frame, min_area=CEREBRA_HSV_MIN_AREA_HEARTBEAT, morph_kernel=3)
        if bbox is None:
            line_bbox = self.detect_cerebra_bar_line_bbox(search)
            if line_bbox is None:
                return None
            lx, ly, lw, lh = line_bbox
            best_x = lx + (lw // 2)
        else:
            x, y, w, h = bbox
            best_x = search.x1 + x + (w // 2)
        if self.last_heartbeat_x > 0 and abs(best_x - self.last_heartbeat_x) > self.HEARTBEAT_MAX_JUMP_PX:
            best_x = int(round((self.last_heartbeat_x * 0.7) + (best_x * 0.3)))
        self.last_heartbeat_x = best_x
        return best_x

    def detect_cerebra_bar_bbox(self) -> Optional[Tuple[int, int, int, int]]:
        # The control strip is only trusted inside the validated border ROI.
        border_bbox = self.detect_cerebra_big_border_bbox()
        search = self.CATCH_BAR
        if border_bbox is not None:
            bx, by, bw, bh = border_bbox
            search = Region(
                max(self.CATCH_BAR.x1, bx - CEREBRA_CAPTURE_MASK_PAD_X),
                max(self.CATCH_BAR.y1, by - CEREBRA_CAPTURE_MASK_PAD_Y),
                min(self.CATCH_BAR.x2, bx + bw + CEREBRA_CAPTURE_MASK_PAD_X),
                min(self.CATCH_BAR.y2, by + bh + CEREBRA_CAPTURE_MASK_PAD_Y),
            )
        frame = self.grab(search)
        bbox, _ = detect_cerebra_bar_hsv(frame, min_area=CEREBRA_HSV_MIN_AREA_BBOX, morph_kernel=3)
        if bbox is None:
            self.cerebra_strip_miss_count += 1
            self.cerebra_vision_debug.strip_confidence = 0.0
            if self.cerebra_last_strip_bbox is not None and self.cerebra_strip_miss_count <= CEREBRA_STRIP_REUSE_MAX_FRAMES:
                self.cerebra_vision_debug.strip_bbox = self.cerebra_last_strip_bbox
                self.cerebra_vision_debug.strip_confidence = max(
                    0.18, self.cerebra_vision_debug.strip_confidence * 0.85
                )
                return self.cerebra_last_strip_bbox
            line = self.detect_cerebra_bar_line_bbox(search)
            if line is None:
                self._log_cerebra_rejection("strip", "low_confidence", "reason=not_found")
                self.cerebra_last_strip_bbox = None
                return None
            if self.cerebra_last_strip_bbox is not None:
                prev_center = self._bbox_center_x(self.cerebra_last_strip_bbox)
                center = self._bbox_center_x(line)
                if abs(center - prev_center) > CEREBRA_STRIP_MAX_CENTER_JUMP_PX:
                    self._log_cerebra_rejection(
                        "strip",
                        "jump_too_large",
                        f"jump={abs(center - prev_center):.1f} source=line",
                    )
                    return self.cerebra_last_strip_bbox if self.cerebra_strip_miss_count <= CEREBRA_STRIP_REUSE_MAX_FRAMES else None
            self.cerebra_last_strip_bbox = line
            self.cerebra_vision_debug.strip_bbox = line
            self.cerebra_vision_debug.strip_confidence = 0.26
            return line

        x, y, w, h = bbox
        area = float(max(1.0, cv2.contourArea(np.array([[[x, y]], [[x + w, y]], [[x + w, y + h]], [[x, y + h]]], dtype=np.int32))))
        score, reject_reason, abs_bbox = self._score_cerebra_strip_bbox(
            bbox_local=(x, y, w, h),
            area=area,
            search=search,
            previous_abs_bbox=self.cerebra_last_strip_bbox,
            jump_limit_px=CEREBRA_STRIP_MAX_CENTER_JUMP_PX,
            min_fill_ratio=CEREBRA_STRIP_MIN_FILL_RATIO,
        )
        if reject_reason is not None:
            self.cerebra_strip_miss_count += 1
            self._log_cerebra_rejection("strip", reject_reason, f"bbox={abs_bbox}")
            if self.cerebra_last_strip_bbox is not None and self.cerebra_strip_miss_count <= CEREBRA_STRIP_REUSE_MAX_FRAMES:
                self.cerebra_vision_debug.strip_bbox = self.cerebra_last_strip_bbox
                self.cerebra_vision_debug.strip_confidence = max(0.20, self.cerebra_vision_debug.strip_confidence * 0.88)
                return self.cerebra_last_strip_bbox
            return None

        self.cerebra_strip_miss_count = 0
        self.cerebra_last_strip_bbox = abs_bbox
        self.cerebra_vision_debug.strip_bbox = abs_bbox
        self.cerebra_vision_debug.strip_confidence = score
        return abs_bbox

    def detect_cerebra_bar_line_bbox(self, search: Region) -> Optional[Tuple[int, int, int, int]]:
        """
        Line mode:
        detect sharp brightness changes between adjacent columns on a horizontal scan.
        Returns absolute client bbox (x, y, w, h).
        """
        if not CEREBRA_LINE_EDGE_ENABLE:
            return None
        frame = self.grab(search)
        if frame is None or frame.size == 0:
            return None
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        if w < 6 or h < 2:
            return None

        y = int(max(0, min(h - 1, round(h * 0.52))))
        line = gray[y, :].astype(np.int16)
        d = np.abs(np.diff(line))
        if d.size < 3:
            return None
        thr = int(max(4, CEREBRA_LINE_EDGE_DIFF_THRESH))
        edges = np.where(d >= thr)[0]
        if edges.size < 2:
            return None

        # Score left/right edge pairs by combined edge strength and plausible width.
        best = None
        best_score = -1.0
        for li in range(min(24, edges.size)):
            left = int(edges[li])
            for ri in range(edges.size - 1, max(li + 1, edges.size - 26), -1):
                right = int(edges[ri])
                span = right - left
                if span < int(CEREBRA_LINE_EDGE_MIN_SPAN):
                    continue
                if span > int(w * 0.95):
                    continue
                score = float(d[left] + d[right]) + (span * 0.05)
                if score > best_score:
                    best_score = score
                    best = (left, right)
        if best is None:
            return None

        left, right = best
        bx = search.x1 + left
        by = search.y1 + max(0, y - 5)
        bw = max(2, right - left + 1)
        bh = min(14, search.h)
        return (bx, by, bw, bh)

    def detect_cerebra_big_border_bbox(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Detect the large pink border box of the minigame.
        Returns absolute client coords: (x, y, w, h).
        """
        search = self._cerebra_border_search_region()
        frame = self.grab(search)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower = np.array([CEREBRA_BORDER_HUE_MIN, CEREBRA_BORDER_SAT_MIN, CEREBRA_BORDER_VAL_MIN], dtype=np.uint8)
        upper = np.array([CEREBRA_BORDER_HUE_MAX, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        k = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

        found = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = found[0] if len(found) == 2 else found[1]
        best = None
        best_score = -1.0
        for c in contours:
            area = float(cv2.contourArea(c))
            if area < CEREBRA_BORDER_MIN_AREA:
                self._log_cerebra_rejection("border", "low_confidence", f"area={area:.1f}")
                continue
            x, y, w, h = cv2.boundingRect(c)
            if w < 40 or h < 8:
                self._log_cerebra_rejection("border", "bad_geometry", f"bbox=({x},{y},{w},{h})")
                continue
            aspect = float(w) / float(max(h, 1))
            fill_ratio = self._bbox_fill_ratio(area, w, h)
            if aspect < CEREBRA_BORDER_ASPECT_MIN or aspect > CEREBRA_BORDER_ASPECT_MAX:
                self._log_cerebra_rejection("border", "bad_geometry", f"aspect={aspect:.2f}")
                continue
            if fill_ratio < CEREBRA_BORDER_MIN_FILL_RATIO:
                self._log_cerebra_rejection("border", "noisy_mask", f"fill={fill_ratio:.2f}")
                continue
            abs_bbox = (search.x1 + x, search.y1 + y, w, h)
            continuity = 0.42
            if self.cerebra_last_border_bbox is not None:
                jump = abs(self._bbox_center_x(abs_bbox) - self._bbox_center_x(self.cerebra_last_border_bbox))
                if jump > CEREBRA_BORDER_MAX_CENTER_JUMP_PX:
                    self._log_cerebra_rejection("border", "jump_too_large", f"jump={jump:.1f}")
                    continue
                continuity = max(0.0, 1.0 - (jump / max(1.0, CEREBRA_BORDER_MAX_CENTER_JUMP_PX)))
            width_score = min(1.0, float(w) / max(70.0, float(self.CATCH_BAR.w) * 0.55))
            height_score = min(1.0, float(h) / max(8.0, float(self.CATCH_BORDER_SCAN.h) * 0.35))
            score = (
                (0.36 * width_score)
                + (0.14 * height_score)
                + (0.22 * min(1.0, fill_ratio / 0.42))
                + (0.12 * min(1.0, aspect / 10.0))
                + (0.16 * continuity)
            )
            if score > best_score:
                best_score = score
                best = abs_bbox

        if best is None:
            self.cerebra_border_miss_count += 1
            self.cerebra_vision_debug.border_confidence = 0.0
            if DEBUG_CEREBRA and self.cerebra_last_border_bbox is not None:
                self.log(
                    "Cerebra border miss "
                    f"count={self.cerebra_border_miss_count} reuse_last={int(self.cerebra_border_miss_count <= CEREBRA_BORDER_REUSE_MAX_FRAMES)}"
                )
            if self.cerebra_last_border_bbox is not None and self.cerebra_border_miss_count <= CEREBRA_BORDER_REUSE_MAX_FRAMES:
                self.cerebra_vision_debug.border_bbox = self.cerebra_last_border_bbox
                self.cerebra_vision_debug.border_confidence = max(0.20, self.cerebra_vision_debug.border_confidence * 0.85)
                return self.cerebra_last_border_bbox
            self.cerebra_last_border_bbox = None
            return None

        self.cerebra_border_miss_count = 0
        self.cerebra_last_border_bbox = best
        self.cerebra_vision_debug.border_bbox = best
        self.cerebra_vision_debug.border_confidence = float(max(0.0, min(1.0, best_score)))

        if DEBUG_CEREBRA_HSV:
            dbg = frame.copy()
            bx, by, bw, bh = best
            cv2.rectangle(dbg, (bx - search.x1, by - search.y1), (bx - search.x1 + bw, by - search.y1 + bh), (0, 255, 255), 2)
            cv2.imshow("Cerebra Border Mask", mask)
            cv2.imshow("Cerebra Border Debug", dbg)
            cv2.waitKey(1)

        return best

    def detect_cerebra_black_wave_x(self) -> Optional[float]:
        """
        Detect the black waveform/heartbeat center inside the pink Cerebra strip.
        This is the primary target the control bar should overlap.
        """
        strip_bbox = self.detect_cerebra_bar_bbox()
        if strip_bbox is None:
            self.cerebra_vision_debug.target_confidence = 0.0
            self.cerebra_vision_debug.target_source = "none"
            return None
        sx, sy, sw, sh = strip_bbox
        search = Region(
            max(self.CATCH_BAR.x1, sx + max(CEREBRA_STRIP_EDGE_IGNORE_PX, CEREBRA_BLACK_WAVE_EDGE_IGNORE_PX)),
            max(self.CATCH_BAR.y1, sy),
            min(self.CATCH_BAR.x2, sx + sw - max(CEREBRA_STRIP_EDGE_IGNORE_PX, CEREBRA_BLACK_WAVE_EDGE_IGNORE_PX)),
            min(self.CATCH_BAR.y2, sy + sh),
        )
        if search.w < 12 or search.h < 4:
            self._log_cerebra_rejection("target", "outside_roi", f"search=({search.x1},{search.y1},{search.w},{search.h})")
            return None
        frame = self.grab(search)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h = gray.shape[0]
        by1 = int(max(0, round(h * CEREBRA_BLACK_WAVE_BAND_TOP_RATIO)))
        by2 = int(min(h, round(h * CEREBRA_BLACK_WAVE_BAND_BOTTOM_RATIO)))
        band = gray[by1:by2, :] if by2 > by1 else gray
        if band.size == 0:
            return None
        dark = cv2.inRange(band, 0, CEREBRA_BLACK_WAVE_MAX_LUMA)
        k = np.ones((2, 2), dtype=np.uint8)
        dark = cv2.morphologyEx(dark, cv2.MORPH_OPEN, k, iterations=1)
        dark = cv2.morphologyEx(dark, cv2.MORPH_CLOSE, k, iterations=1)

        # Exclude known nuisance zones (bows/side ornaments/center marker zone).
        bw = dark.shape[1]
        if bw > 8:
            ig_l = int(max(0, round(bw * CEREBRA_BLACK_WAVE_IGNORE_LEFT_RATIO)))
            ig_r = int(max(0, round(bw * CEREBRA_BLACK_WAVE_IGNORE_RIGHT_RATIO)))
            if ig_l > 0:
                dark[:, :ig_l] = 0
            if ig_r > 0:
                dark[:, max(0, bw - ig_r):] = 0
            if CEREBRA_BLACK_WAVE_IGNORE_CENTER_ENABLE:
                c = bw // 2
                hw = int(max(1, round(bw * CEREBRA_BLACK_WAVE_IGNORE_CENTER_HALF_RATIO)))
                dark[:, max(0, c - hw):min(bw, c + hw)] = 0

        # Score contour candidates by darkness, compactness, and temporal continuity.
        found = cv2.findContours(dark, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = found[0] if len(found) == 2 else found[1]
        prefer_abs_x = self.cerebra_target_tracker_state.position if self.cerebra_target_tracker_state.last_good_tick > 0 else ((search.x1 + search.x2) / 2.0)
        best_measurement = None
        best_score = -1.0
        for c in contours:
            area = float(cv2.contourArea(c))
            if area < CEREBRA_BLACK_WAVE_MIN_AREA or area > CEREBRA_BLACK_WAVE_MAX_AREA:
                continue
            rx, ry, rw, rh = cv2.boundingRect(c)
            if rw < CEREBRA_BLACK_WAVE_MIN_W or rw > CEREBRA_BLACK_WAVE_MAX_W or rh < 2:
                self._log_cerebra_rejection("target", "bad_geometry", f"bbox=({rx},{ry},{rw},{rh})")
                continue
            m = cv2.moments(c)
            cx = float(m["m10"] / m["m00"]) if m["m00"] != 0 else float(rx + (rw / 2.0))
            abs_x = float(search.x1 + cx)
            jump = abs(abs_x - prefer_abs_x)
            if self.cerebra_target_tracker_state.last_good_tick > 0 and jump > CEREBRA_TARGET_MAX_JUMP_PX_STRICT:
                self._log_cerebra_rejection("target", "jump_too_large", f"jump={jump:.1f} source=wave")
                continue
            compactness = min(1.0, area / max(1.0, rw * rh))
            width_score = 1.0 - min(1.0, max(0.0, (rw - 22.0) / 48.0))
            continuity = max(0.0, 1.0 - (jump / max(1.0, CEREBRA_TARGET_LOCK_MAX_JUMP_PX)))
            darkness = min(1.0, area / max(10.0, float(dark.shape[0]) * 2.2))
            score = (0.30 * compactness) + (0.24 * width_score) + (0.26 * continuity) + (0.20 * darkness)
            if score > best_score:
                best_score = score
                best_measurement = abs_x

        if best_measurement is not None and best_score >= 0.34:
            self.cerebra_vision_debug.target_confidence = float(best_score)
            self.cerebra_vision_debug.target_source = "black_wave"
            return float(best_measurement)

        # Projection fallback is only used when the contour result is weak, and it stays gated near the tracked target.
        col_hits = np.sum(dark > 0, axis=0).astype(np.float32)
        if col_hits.size == 0:
            return None

        edge = int(max(1, CEREBRA_BLACK_WAVE_EDGE_IGNORE_PX))
        if (edge * 2) < col_hits.size:
            col_hits[:edge] = 0
            col_hits[-edge:] = 0

        w = int(max(1, CEREBRA_BLACK_WAVE_SMOOTH_WINDOW))
        kernel = np.ones((w,), dtype=np.float32) / float(w)
        smooth = np.convolve(col_hits, kernel, mode="same")

        if self.cerebra_target_tracker_state.last_good_tick > 0:
            prev_local = int(round(self.cerebra_target_tracker_state.position - search.x1))
            lo = max(0, prev_local - CEREBRA_BLACK_WAVE_TRACK_RADIUS)
            hi = min(smooth.size, prev_local + CEREBRA_BLACK_WAVE_TRACK_RADIUS + 1)
            gated = np.zeros_like(smooth)
            if hi > lo:
                gated[lo:hi] = smooth[lo:hi]
            smooth = gated

        peak_idx = int(np.argmax(smooth))
        peak_val = float(smooth[peak_idx])
        if peak_val < CEREBRA_BLACK_WAVE_MIN_COL_HITS:
            self._log_cerebra_rejection("target", "low_confidence", f"peak={peak_val:.1f} source=projection")
            return None

        lo = max(0, peak_idx - 6)
        hi = min(smooth.size, peak_idx + 7)
        weights = smooth[lo:hi]
        if weights.size == 0 or float(np.sum(weights)) <= 0.0:
            cx_local = float(peak_idx)
        else:
            xs = np.arange(lo, hi, dtype=np.float32)
            cx_local = float(np.sum(xs * weights) / np.sum(weights))

        candidate = float(search.x1 + cx_local)
        if self.cerebra_target_tracker_state.last_good_tick > 0:
            jump = abs(candidate - self.cerebra_target_tracker_state.position)
            if jump > CEREBRA_TARGET_MAX_JUMP_PX_STRICT:
                self._log_cerebra_rejection("target", "jump_too_large", f"jump={jump:.1f} source=projection")
                return None
            continuity = max(0.0, 1.0 - (jump / max(1.0, CEREBRA_TARGET_LOCK_MAX_JUMP_PX)))
        else:
            continuity = 0.45
        conf = max(0.0, min(1.0, (0.55 * min(1.0, peak_val / 8.0)) + (0.45 * continuity)))
        if conf < 0.28:
            self._log_cerebra_rejection("target", "low_confidence", f"conf={conf:.2f} source=projection")
            return None
        self.cerebra_vision_debug.target_confidence = conf
        self.cerebra_vision_debug.target_source = "black_wave_projection"
        return candidate

    def detect_cerebra_small_bar_x(self) -> Optional[float]:
        """
        Detect the small pink target bar, but only inside the validated strip ROI.
        This is a secondary signal and should not override a stable black-wave track without stronger confidence.
        """
        strip_bbox = self.detect_cerebra_bar_bbox()
        if strip_bbox is None:
            return None
        sx, sy, sw, sh = strip_bbox
        search = Region(
            max(self.CATCH_BAR.x1, sx + CEREBRA_STRIP_EDGE_IGNORE_PX),
            max(self.CATCH_BAR.y1, sy),
            min(self.CATCH_BAR.x2, sx + sw - CEREBRA_STRIP_EDGE_IGNORE_PX),
            min(self.CATCH_BAR.y2, sy + sh),
        )
        if search.w < 10 or search.h < 3:
            self._log_cerebra_rejection("small_target", "outside_roi", f"search=({search.x1},{search.y1},{search.w},{search.h})")
            return None
        frame = self.grab(search)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = build_cerebra_small_bar_mask(frame, morph_kernel=1)
        # Motion+darkness gating reduces false positives from random pink pixels.
        local_mask = mask.copy()
        dark_fixed = cv2.inRange(gray, 0, CEREBRA_SMALL_LOCAL_DARK_MAX)
        _, dark_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        local_mask = cv2.bitwise_and(local_mask, cv2.bitwise_or(dark_fixed, dark_otsu))
        if self.cerebra_prev_small_gray is not None and self.cerebra_prev_small_gray.shape == gray.shape:
            diff = cv2.absdiff(gray, self.cerebra_prev_small_gray)
            motion = cv2.threshold(diff, CEREBRA_SMALL_MOTION_DIFF_THRESH, 255, cv2.THRESH_BINARY)[1]
            motion = cv2.dilate(motion, np.ones((2, 2), dtype=np.uint8), iterations=1)
            local_mask = cv2.bitwise_and(local_mask, motion)
        k = np.ones((2, 2), dtype=np.uint8)
        local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_OPEN, k, iterations=1)
        local_mask = cv2.morphologyEx(local_mask, cv2.MORPH_CLOSE, k, iterations=1)

        col_hits = np.sum(local_mask > 0, axis=0).astype(np.float32)
        if col_hits.size > 0:
            w = int(max(1, CEREBRA_SMALL_PROJ_SMOOTH_WINDOW))
            kernel = np.ones((w,), dtype=np.float32) / float(w)
            smoothed = np.convolve(col_hits, kernel, mode="same")
            if self.cerebra_target_tracker_state.last_good_tick > 0:
                local_prev = int(round(self.cerebra_target_tracker_state.position - search.x1))
                lo = max(0, local_prev - CEREBRA_SMALL_TRACK_SEARCH_RADIUS)
                hi = min(smoothed.size, local_prev + CEREBRA_SMALL_TRACK_SEARCH_RADIUS + 1)
                gated = np.zeros_like(smoothed)
                if hi > lo:
                    gated[lo:hi] = smoothed[lo:hi]
                smoothed = gated
            peak_idx = int(np.argmax(smoothed))
            peak_val = float(smoothed[peak_idx])
            if peak_val >= CEREBRA_SMALL_PROJ_MIN_HITS:
                candidate = float(search.x1 + peak_idx)
                jump = abs(candidate - self.cerebra_target_tracker_state.position) if self.cerebra_target_tracker_state.last_good_tick > 0 else 0.0
                if self.cerebra_target_tracker_state.last_good_tick > 0 and jump > CEREBRA_TARGET_MAX_JUMP_PX_STRICT:
                    self._log_cerebra_rejection("small_target", "jump_too_large", f"jump={jump:.1f}")
                else:
                    continuity = max(0.0, 1.0 - (jump / max(1.0, CEREBRA_TARGET_LOCK_MAX_JUMP_PX))) if self.cerebra_target_tracker_state.last_good_tick > 0 else 0.42
                    conf = max(0.0, min(1.0, (0.58 * min(1.0, peak_val / 8.0)) + (0.42 * continuity)))
                    if conf >= 0.32:
                        self.cerebra_prev_small_gray = gray
                        self.cerebra_vision_debug.target_confidence = max(self.cerebra_vision_debug.target_confidence, conf)
                        self.cerebra_vision_debug.target_source = "small_bar"
                        return candidate

        found = cv2.findContours(local_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = found[0] if len(found) == 2 else found[1]
        if not contours:
            self.cerebra_prev_small_gray = gray
            return None

        prefer_x = self.cerebra_target_tracker_state.position if self.cerebra_target_tracker_state.last_good_tick > 0 else ((search.x1 + search.x2) / 2.0)
        best_center = None
        best_score = -1e9

        for c in contours:
            area = float(cv2.contourArea(c))
            if area < CEREBRA_SMALL_BAR_MIN_AREA or area > CEREBRA_SMALL_BAR_MAX_AREA:
                continue
            x, y, w, h = cv2.boundingRect(c)
            if w < CEREBRA_SMALL_BAR_MIN_W or w > CEREBRA_SMALL_BAR_MAX_W:
                continue
            if h < CEREBRA_SMALL_BAR_MIN_H or h > CEREBRA_SMALL_BAR_MAX_H:
                continue

            m = cv2.moments(c)
            if m["m00"] != 0:
                cx_local = float(m["m10"] / m["m00"])
            else:
                cx_local = float(x + (w / 2.0))
            center = search.x1 + cx_local
            dist = abs(center - prefer_x)
            compact_bonus = max(0.0, 34.0 - w) + max(0.0, 180.0 - area) * 0.08
            score = compact_bonus - (dist * 0.12)
            if score > best_score:
                best_score = score
                best_center = center

        if best_center is None:
            self.cerebra_prev_small_gray = gray
            return None
        if self.cerebra_target_tracker_state.last_good_tick > 0 and abs(best_center - self.cerebra_target_tracker_state.position) > CEREBRA_TARGET_MAX_JUMP_PX_STRICT:
            self._log_cerebra_rejection(
                "small_target",
                "jump_too_large",
                f"jump={abs(best_center - self.cerebra_target_tracker_state.position):.1f} source=contour",
            )
            self.cerebra_prev_small_gray = gray
            return None
        self.cerebra_prev_small_gray = gray
        self.cerebra_vision_debug.target_confidence = max(self.cerebra_vision_debug.target_confidence, 0.30)
        self.cerebra_vision_debug.target_source = "small_bar_contour"
        return float(best_center)

    def cerebra_detection_score(self, include_template: bool = True) -> Tuple[int, str]:
        score = 0
        signals = []
        if self.find_heartbeat_x() is not None:
            score += CEREBRA_SCORE_HEARTBEAT
            signals.append("hb")
        if self.detect_cerebra_bar_bbox() is not None:
            score += CEREBRA_SCORE_HSV_BAR
            signals.append("hsv")
        if self.is_catch_bar_displayed():
            score += CEREBRA_SCORE_UI_BAR
            signals.append("ui")
        if self.cerebra_has_active_bar_run():
            score += CEREBRA_SCORE_ACTIVE_RUN
            signals.append("run")
        if include_template and self.cerebra_by_image():
            score += CEREBRA_SCORE_TEMPLATE
            signals.append("tpl")
        return score, "+".join(signals) if signals else "none"

    def detect_cerebra_target_x(self, dt: int) -> Optional[float]:
        """
        Target = tracked waveform center inside the validated strip.
        Measured detections are preferred, but low-confidence frames only coast briefly instead of forcing a lock jump.
        """
        now = self.tick()
        lane_min = float(self.CATCH_BAR_TOP_LINE.x1)
        lane_max = float(self.CATCH_BAR_TOP_LINE.x2)
        self.cerebra_vision_debug.target_confidence = 0.0
        self.cerebra_vision_debug.target_source = "none"

        wave_x = self.detect_cerebra_black_wave_x()
        if wave_x is not None:
            conf = max(self.cerebra_vision_debug.target_confidence, 0.42)
            self._update_local_tracker(
                self.cerebra_target_tracker_state,
                wave_x,
                conf,
                self.cerebra_vision_debug.target_source or "black_wave",
                dt,
                now,
                lane_min,
                lane_max,
            )
            self.cerebra_target_x = self.cerebra_target_tracker_state.position
            self.cerebra_target_v = self.cerebra_target_tracker_state.velocity
            self.cerebra_target_has = True
            self.cerebra_target_misses = 0
            return self.cerebra_target_tracker_state.position

        small_x = self.detect_cerebra_small_bar_x()
        if small_x is not None:
            conf = max(self.cerebra_vision_debug.target_confidence, 0.34)
            self._update_local_tracker(
                self.cerebra_target_tracker_state,
                small_x,
                conf,
                self.cerebra_vision_debug.target_source or "small_bar",
                dt,
                now,
                lane_min,
                lane_max,
            )
            self.cerebra_target_x = self.cerebra_target_tracker_state.position
            self.cerebra_target_v = self.cerebra_target_tracker_state.velocity
            self.cerebra_target_has = True
            self.cerebra_target_misses = 0
            return self.cerebra_target_tracker_state.position

        self.cerebra_target_misses += 1
        if self.cerebra_target_tracker_state.last_good_tick > 0 and self.cerebra_target_tracker_state.missing_frames < CEREBRA_TARGET_MAX_MISSES_BEFORE_FALLBACK:
            self._update_local_tracker(
                self.cerebra_target_tracker_state,
                None,
                self.cerebra_target_tracker_state.confidence,
                "target_prediction",
                dt,
                now,
                lane_min,
                lane_max,
            )
            self.cerebra_target_x = self.cerebra_target_tracker_state.position
            self.cerebra_target_v = self.cerebra_target_tracker_state.velocity
            self.cerebra_target_has = self.cerebra_target_tracker_state.confidence >= 0.12
            self.cerebra_vision_debug.target_source = "target_prediction"
            self.cerebra_vision_debug.target_confidence = self.cerebra_target_tracker_state.confidence
            return self.cerebra_target_tracker_state.position

        self.cerebra_target_has = False
        return None

    def _choose_cerebra_action(
        self,
        now: int,
        report: Any,
        snapshot: Any,
        target_trust: str,
        target_conf: float,
    ) -> Tuple[int, str]:
        decision = report.decision
        if decision is None:
            self.cerebra_actuation.weak_frame_streak += 1
            return (-1, "no_decision")

        target_conf = float(report.target_state.confidence)
        bar_conf = float(report.bar_state.confidence)
        strong_target = target_conf >= CEREBRA_CONFIDENCE_ACT_MIN_TARGET and target_trust == "measured"
        strong_bar = bar_conf >= CEREBRA_CONFIDENCE_ACT_MIN_BAR
        error = float(decision.error)
        self.cerebra_err_smooth = (
            (self.cerebra_err_smooth * (1.0 - self.CEREBRA_ERR_SMOOTH_ALPHA))
            + (error * self.CEREBRA_ERR_SMOOTH_ALPHA)
        )
        smoothed_error = float(self.cerebra_err_smooth)
        keep_band = max(
            float(self.CATCH_DEADZONE_PX + self.CEREBRA_EXTRA_DEADZONE_PX),
            float(self.CEREBRA_HOLD_KEEP_BAND_PX + CEREBRA_ACTION_STICKY_OVERLAP_PX),
        )
        reverse_threshold = max(float(CEREBRA_ACTION_REVERSE_ERR_PX), keep_band * 1.25)
        control_mode = self._control_mode_from_target_state(target_trust, target_conf)
        weak_frame = (control_mode in {"weak", "invalid"}) or (not strong_bar) or snapshot.score < 0.24

        if weak_frame:
            self.cerebra_actuation.weak_frame_streak += 1
            if control_mode == "weak" and self.cerebra_actuation.weak_frame_streak <= CEREBRA_TARGET_PREDICTION_SHORT_FRAMES and self.cerebra_actuation.direction != 0:
                return self.cerebra_actuation.direction, "weak_target_coast"
            if target_trust == "bootstrap_unconfirmed" and self.cerebra_actuation.direction != 0 and self.cerebra_actuation.weak_frame_streak <= 1:
                return self.cerebra_actuation.direction, "bootstrap_wait"
            if target_trust == "predicted_stale":
                return -1, "prediction_expired"
            if target_trust == "invalid":
                return -1, "invalid_target_recovery"
            return -1, "weak_frame_release"

        self.cerebra_actuation.weak_frame_streak = 0
        desired = 1 if decision.hold else -1
        reason = decision.switch_reason or decision.reason or "controller"
        current = self.cerebra_actuation.direction

        # Once overlap is achieved, stay there briefly unless the error exits a wider hysteresis band.
        if abs(smoothed_error) <= keep_band:
            if current != 0:
                desired = current
            elif smoothed_error >= 0.0:
                desired = 1
            else:
                desired = -1
            self.cerebra_actuation.overlap_stick_until_tick = now + int(self.CEREBRA_OVERLAP_HOLD_MS)
            reason = "overlap_sticky"
        elif now < self.cerebra_actuation.overlap_stick_until_tick and current != 0 and abs(smoothed_error) < reverse_threshold:
            desired = current
            reason = "overlap_grace"

        if current != 0 and desired != current:
            if abs(smoothed_error) < reverse_threshold:
                desired = current
                reason = "hysteresis_reverse_block"
            elif (now - self.cerebra_actuation.last_switch_tick) < max(
                int(self.CEREBRA_ACTUATION_SWITCH_COOLDOWN_MS),
                CEREBRA_ACTION_SWITCH_COOLDOWN_MS,
            ):
                desired = current
                reason = "switch_cooldown"
            elif current > 0 and (now - self.cerebra_last_mouse_down_tick) < CEREBRA_ACTION_MIN_HOLD_MS:
                desired = current
                reason = "min_hold_time"
            elif current < 0 and (now - self.cerebra_last_mouse_up_tick) < CEREBRA_ACTION_MIN_RELEASE_MS:
                desired = current
                reason = "min_release_time"

        if desired != current:
            self.cerebra_actuation.last_switch_tick = now
            if desired > 0:
                self.cerebra_actuation.hold_since_tick = now
            else:
                self.cerebra_actuation.release_since_tick = now
        self.cerebra_actuation.direction = desired
        if control_mode == "medium" and desired != current and abs(smoothed_error) < (reverse_threshold * 1.15):
            desired = current if current != 0 else desired
            reason = "grace_hold"
        if target_trust == "measured":
            reason = "measured_control" if reason in {"controller", "keep_band"} else reason
        self.cerebra_actuation.last_reason = reason
        self.cerebra_vision_debug.error = smoothed_error
        self.cerebra_vision_debug.chosen_action = "hold" if desired > 0 else "release"
        self.cerebra_vision_debug.switch_reason = reason
        return desired, reason

    def debug_cerebra_overlay(self, bar_mid: float, predicted_bar: float, target_x: float, confidence: int, signals: str) -> None:
        if not DEBUG_CEREBRA:
            return
        frame = self.grab(self.CATCH_BAR)
        bbox, mask = detect_cerebra_bar_hsv(frame, min_area=CEREBRA_HSV_MIN_AREA_BBOX, morph_kernel=3)
        h, w = frame.shape[:2]
        vis = frame.copy()
        if bbox is not None:
            x, y, bw, bh = bbox
            cv2.rectangle(vis, (x, y), (x + bw, y + bh), (0, 255, 0), 2)
        if self.cerebra_last_border_bbox is not None:
            bx, by, bw, bh = self.cerebra_last_border_bbox
            lx1 = int(max(0, bx - self.CATCH_BAR.x1))
            ly1 = int(max(0, by - self.CATCH_BAR.y1))
            lx2 = int(min(max(0, w - 1), lx1 + bw))
            ly2 = int(min(max(0, h - 1), ly1 + bh))
            cv2.rectangle(vis, (lx1, ly1), (lx2, ly2), (255, 0, 255), 1)

        def to_local_x(value: float) -> int:
            return int(self.clamp(value - self.CATCH_BAR.x1, 0, max(0, w - 1)))

        x_bar = to_local_x(bar_mid)
        x_pred = to_local_x(predicted_bar)
        x_target = to_local_x(target_x)
        # Scan guide lines for easier calibration.
        cv2.rectangle(vis, (0, 0), (w - 1, h - 1), (80, 80, 80), 1)
        cv2.line(vis, (0, h // 2), (w - 1, h // 2), (80, 80, 255), 1)
        cv2.line(vis, (x_bar, 0), (x_bar, h - 1), (255, 255, 0), 1)     # actual
        cv2.line(vis, (x_pred, 0), (x_pred, h - 1), (0, 255, 255), 1)    # predicted
        cv2.line(vis, (x_target, 0), (x_target, h - 1), (0, 0, 255), 1)  # target
        cv2.putText(
            vis,
            f"score={confidence} sig={signals}",
            (4, max(12, h - 4)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        cv2.imshow("Cerebra Debug Frame", vis)
        cv2.imshow("Cerebra Debug Mask", mask)
        cv2.waitKey(1)

    def is_cerebra_minigame_active(self) -> bool:
        # Prefer HSV bar presence for Cerebra; fall back to generic catch-bar signal.
        return self.detect_cerebra_bar_bbox() is not None or self.is_catch_bar_displayed()

    def _result_region(self) -> Region:
        x1, y1, x2, y2 = CEREBRA_RESULT_REGION
        return Region(x1, y1, x2, y2)

    def _normalize_result_text(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()

    def _build_result_ocr_variants(self, frame: Any) -> list[tuple[str, Any]]:
        variants: list[tuple[str, Any]] = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        gray = cv2.convertScaleAbs(gray, alpha=1.6, beta=10)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(gray)

        white_mask = cv2.inRange(frame, np.array([180, 180, 180], dtype=np.uint8), np.array([255, 255, 255], dtype=np.uint8))
        yellow_mask = cv2.inRange(frame, np.array([0, 170, 170], dtype=np.uint8), np.array([180, 255, 255], dtype=np.uint8))
        green_mask = cv2.inRange(frame, np.array([0, 140, 0], dtype=np.uint8), np.array([180, 255, 180], dtype=np.uint8))

        for name, base in [
            ("gray", gray),
            ("clahe", clahe),
            ("otsu", cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]),
            ("otsu_inv", cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]),
            ("adaptive", cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 3)),
            ("adaptive_inv", cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 3)),
            ("white_mask", white_mask),
            ("yellow_mask", yellow_mask),
            ("green_mask", green_mask),
        ]:
            scaled = cv2.resize(
                base,
                (0, 0),
                fx=CEREBRA_RESULT_OCR_SCALE,
                fy=CEREBRA_RESULT_OCR_SCALE,
                interpolation=cv2.INTER_LINEAR,
            )
            variants.append((name, scaled))
        return variants

    def _fuzzy_contains_phrase(self, normalized: str, phrase: str, threshold: float = CEREBRA_RESULT_FUZZY_THRESHOLD) -> bool:
        if phrase in normalized:
            return True
        words = normalized.split()
        target_words = phrase.split()
        if not words or len(words) < len(target_words):
            return False
        width = len(target_words)
        for i in range(0, len(words) - width + 1):
            chunk = " ".join(words[i:i + width])
            if SequenceMatcher(None, chunk, phrase).ratio() >= threshold:
                return True
        return False

    def _match_result_keywords(self, normalized: str) -> tuple[Optional[bool], str, float, str]:
        win_phrases = [
            ("you just caught", 1.00),
            ("caught a", 0.95),
            ("just caught", 0.90),
            ("caught", 0.70),
            ("new highest weight", 0.65),
            ("highest weight", 0.55),
            ("bestiary", 0.45),
            ("weight", 0.35),
            ("kg", 0.28),
            ("lb", 0.28),
        ]
        loss_phrases = [
            ("escaped", 0.85),
            ("it got away", 0.90),
            ("you lost", 0.80),
            ("failed", 0.75),
        ]

        matched_win: list[tuple[str, float]] = []
        matched_loss: list[tuple[str, float]] = []
        for phrase, weight in win_phrases:
            if self._fuzzy_contains_phrase(normalized, phrase):
                matched_win.append((phrase, weight))
        for phrase, weight in loss_phrases:
            if self._fuzzy_contains_phrase(normalized, phrase):
                matched_loss.append((phrase, weight))

        win_score = min(1.6, sum(weight for _, weight in matched_win))
        loss_score = min(1.2, sum(weight for _, weight in matched_loss))
        best_win = matched_win[0][0] if matched_win else ""
        best_loss = matched_loss[0][0] if matched_loss else ""

        if win_score >= 0.68 and win_score >= (loss_score + 0.15):
            detail = ",".join(f"{phrase}:{weight:.2f}" for phrase, weight in matched_win[:4])
            return True, best_win, win_score, detail
        if loss_score >= 0.90 and loss_score >= (win_score + 0.20):
            detail = ",".join(f"{phrase}:{weight:.2f}" for phrase, weight in matched_loss[:4])
            return False, best_loss, loss_score, detail
        if matched_win or matched_loss:
            detail = (
                f"win={win_score:.2f}[{','.join(p for p, _ in matched_win[:4])}] "
                f"loss={loss_score:.2f}[{','.join(p for p, _ in matched_loss[:4])}]"
            )
            return None, best_win or best_loss, max(win_score, loss_score), detail
        return None, "", 0.0, "no_keywords"

    def scan_cerebra_result_text(self) -> ResultDetection:
        if pytesseract is None:
            return ResultDetection(outcome=None, reason="ocr_unavailable")
        r = self._result_region()
        frame = self.grab(r)
        if frame.size == 0:
            return ResultDetection(outcome=None, reason="empty_roi")

        best = ResultDetection(outcome=None, reason="no_match")
        for variant_name, variant in self._build_result_ocr_variants(frame):
            for psm in (6, 11):
                config = f"--oem 3 --psm {psm}"
                try:
                    raw = pytesseract.image_to_string(variant, config=config).strip()
                except Exception as exc:
                    continue
                normalized = self._normalize_result_text(raw)
                outcome, keyword, score, detail = self._match_result_keywords(normalized)
                if DEBUG_CEREBRA and raw and self.cerebra_result_window_started > 0:
                    self.log(
                        "Cerebra OCR "
                        f"roi=({r.x1},{r.y1},{r.x2},{r.y2}) variant={variant_name}/psm{psm} "
                        f"raw='{raw[:120]}' norm='{normalized[:120]}' match='{keyword or 'none'}' "
                        f"score={score:.2f} detail='{detail[:120]}'"
                    )
                if outcome is not None:
                    return ResultDetection(
                        outcome=outcome,
                        raw_text=raw,
                        normalized_text=normalized,
                        matched_keyword=keyword,
                        matched_score=score,
                        variant=f"{variant_name}/psm{psm}",
                        reason=detail or "keyword_match",
                    )
                if score > best.matched_score or len(normalized) > len(best.normalized_text):
                    best = ResultDetection(
                        outcome=None,
                        raw_text=raw,
                        normalized_text=normalized,
                        matched_keyword=keyword,
                        matched_score=score,
                        variant=f"{variant_name}/psm{psm}",
                        reason=detail or "best_effort",
                    )
        return best

    def detect_cerebra_result(self) -> ResultDetection:
        now = self.tick()
        if (now - self.cerebra_last_result_check) < CEREBRA_RESULT_CHECK_EVERY_MS:
            return ResultDetection(outcome=None, reason="rate_limited")
        self.cerebra_last_result_check = now
        result = self.scan_cerebra_result_text()
        if result.outcome is None:
            return result

        self.cerebra_result_history.append((now, result.outcome, result.matched_keyword, result.variant, result.matched_score))
        wins = sum(1 for _, outcome, _, _, _ in self.cerebra_result_history if outcome is True)
        losses = sum(1 for _, outcome, _, _, _ in self.cerebra_result_history if outcome is False)
        if result.outcome is True and wins >= CEREBRA_RESULT_CONFIRM_FRAMES:
            self.log(
                "Cerebra result confirmed by OCR "
                f"roi=({self._result_region().x1},{self._result_region().y1},{self._result_region().x2},{self._result_region().y2}) "
                f"keyword='{result.matched_keyword}' score={result.matched_score:.2f} variant={result.variant}"
            )
            return result
        if result.outcome is False and losses >= CEREBRA_RESULT_LOSS_CONFIRM_FRAMES:
            self.log(
                "Cerebra loss confirmed by OCR "
                f"roi=({self._result_region().x1},{self._result_region().y1},{self._result_region().x2},{self._result_region().y2}) "
                f"keyword='{result.matched_keyword}' score={result.matched_score:.2f} variant={result.variant}"
            )
            return result
        if DEBUG_CEREBRA and (result.raw_text or result.matched_score > 0.0):
            self.log(
                "Cerebra OCR not yet confirmed "
                f"roi=({self._result_region().x1},{self._result_region().y1},{self._result_region().x2},{self._result_region().y2}) "
                f"variant={result.variant or 'none'} keyword='{result.matched_keyword or 'none'}' "
                f"score={result.matched_score:.2f} reason={result.reason}"
            )
        return ResultDetection(
            outcome=None,
            raw_text=result.raw_text,
            normalized_text=result.normalized_text,
            matched_keyword=result.matched_keyword,
            matched_score=result.matched_score,
            variant=result.variant,
            reason=f"temporal_confirmation_pending:{result.reason}",
        )

    def apply_heartbeat_scaling(self) -> None:
        width = self.CATCH_BAR_TOP_LINE.x2 - self.CATCH_BAR_TOP_LINE.x1 + 1
        ratio = self.heartbeat_ratio()
        scaled = int(round(self.clamp(width * ratio, 12, width - 4)))
        self.control_bar_width = scaled
        self.control_bar_half_width = max(1, scaled // 2)
        self.left_arrow_off = max(1, self.control_bar_half_width - 9)
        self.right_arrow_off = max(1, self.control_bar_half_width - 9)

    def get_arrow_offsets(self) -> None:
        fish = self.find_fish_x()
        arrow = self.find_arrow_x()
        if fish is not None and arrow is not None:
            self.left_arrow_off = max(1, (fish + 1) - arrow)
            self.right_arrow_off = max(1, self.left_arrow_off - 10)
            self.control_bar_half_width = self.left_arrow_off + 9
            self.control_bar_width = self.control_bar_half_width * 2

    def estimate_bar_mid(self, arrow_x: int) -> float:
        s = self.state
        if s.bar_direction > 0:
            mid = arrow_x + self.left_arrow_off
        elif s.bar_direction < 0:
            mid = arrow_x - self.right_arrow_off
        elif s.click_down:
            mid = arrow_x + self.left_arrow_off
        else:
            mid = arrow_x - self.right_arrow_off
        return self.clamp(mid, self.CATCH_BAR_ARROW_LINE.x1, self.CATCH_BAR_ARROW_LINE.x2)

    def detect_bar_mid(self, heartbeat_mode: bool) -> Optional[float]:
        if heartbeat_mode:
            hb = self.find_heartbeat_x()
            if hb is not None:
                return float(hb)
        arrow = self.find_arrow_x()
        if arrow is not None:
            return float(self.estimate_bar_mid(arrow))
        if self.state.has_bar:
            dt = max(self.tick() - self.state.last_tick, 1)
            return float(self.state.last_bar_middle_x + (self.state.bar_velocity * dt))
        return None

    def update_fish_state(self, x: float, dt: int) -> None:
        s = self.state
        if not s.has_fish:
            s.has_fish = True
            s.last_fish_x = x
            return
        dx = x - s.last_fish_x
        if abs(dx) > self.CATCH_MAX_JUMP_PX:
            s.last_fish_x = x
            return
        inst = dx / max(dt, 1)
        s.fish_velocity = (s.fish_velocity * (1 - self.CATCH_FISH_SMOOTH)) + (inst * self.CATCH_FISH_SMOOTH)
        if abs(dx) >= 1:
            s.fish_direction = 1 if dx > 0 else -1
        s.last_fish_x = x

    def update_bar_state(self, x: float, dt: int) -> None:
        s = self.state
        if not s.has_bar:
            s.has_bar = True
            s.last_bar_middle_x = x
            return
        dx = x - s.last_bar_middle_x
        if abs(dx) > self.CATCH_MAX_JUMP_PX:
            s.last_bar_middle_x = x
            return
        inst = dx / max(dt, 1)
        s.bar_velocity = (s.bar_velocity * (1 - self.CATCH_BAR_SMOOTH)) + (inst * self.CATCH_BAR_SMOOTH)
        if abs(dx) >= 1:
            s.bar_direction = 1 if dx > 0 else -1
        s.last_bar_middle_x = x

    def set_dir(self, direction: int) -> None:
        s = self.state
        now = self.tick()
        if direction != s.commanded_direction:
            if s.last_switch_tick > 0 and (now - s.last_switch_tick) < self.CATCH_SWITCH_COOLDOWN_MS:
                return
            s.last_switch_tick = now
            s.commanded_direction = direction
        if direction > 0 and not s.click_down:
            self.mouse_down()
            s.click_down = True
        elif direction < 0 and s.click_down:
            self.mouse_up()
            s.click_down = False

    def release_control(self) -> None:
        if self.state.click_down:
            self.mouse_up()
            self.state.click_down = False

    def pulse_delay(self, pos_err: float, speed_gap: float) -> float:
        mag = abs(pos_err)
        speed = abs(speed_gap) * 5
        penalty = 0.0 if mag <= (self.CATCH_DEADZONE_PX * 2) else 0.8
        ms = self.clamp(2 + (mag * 0.05) + speed + penalty, 2, 10)
        return ms / 1000.0

    def catch_fish(self, heartbeat_mode: bool) -> bool:
        self.state = CatchState(last_tick=self.tick())
        if heartbeat_mode:
            self.apply_heartbeat_scaling()
        else:
            self.get_arrow_offsets()
        if self.control_bar_width <= 0:
            self.control_bar_half_width = 15
            self.control_bar_width = 30

        mn, mx = self.CATCH_BAR_TOP_LINE.x1, self.CATCH_BAR_TOP_LINE.x2
        stale, ui_missing, idx = 0, 0, 0
        loop_start = self.tick()
        last_strong = loop_start
        while True:
            if self.wait_if_paused():
                self.release_control()
                return False
            idx += 1
            now = self.tick()
            dt = max(now - self.state.last_tick, 1)
            self.state.last_tick = now
            elapsed = now - loop_start

            ui_missing = 0 if self.is_catch_bar_displayed() else ui_missing + 1
            fx = self.find_fish_x()
            if fx is None:
                if not self.state.has_fish:
                    break
                x_fish = float(round(self.clamp(self.state.last_fish_x + (self.state.fish_velocity * dt), mn, mx)))
            else:
                x_fish = float(fx)
            self.update_fish_state(x_fish, dt)

            bar_mid = self.detect_bar_mid(heartbeat_mode)
            if bar_mid is None:
                stale += 1
                if stale > 26:
                    break
                continue
            stale = 0
            last_strong = now
            self.update_bar_state(bar_mid, dt)

            if elapsed >= self.CATCH_MAX_DURATION_MS:
                break
            if idx > 10 and ui_missing >= 3:
                break
            if idx > 10 and (now - last_strong) >= self.NORMAL_END_NO_SIGNAL_MS:
                break

            left = mn + (self.control_bar_width * 0.70)
            right = mx - (self.control_bar_width * 0.70)
            if x_fish > right:
                self.set_dir(1)
                time.sleep(0.012)
                continue
            if x_fish < left:
                self.set_dir(-1)
                time.sleep(0.012)
                continue

            zone_half = max(4.0, self.control_bar_width * self.CATCH_CENTER_RATIO)
            in_center = (bar_mid - zone_half) <= x_fish <= (bar_mid + zone_half)
            predicted = self.clamp(x_fish + (self.state.fish_velocity * self.CATCH_LOOKAHEAD_MS), mn, mx)
            err = predicted - bar_mid
            gap = self.state.fish_velocity - self.state.bar_velocity
            speed = abs(self.state.bar_velocity)

            if in_center:
                if speed > self.CATCH_BRAKE_SPEED and self.state.bar_direction != 0:
                    self.set_dir(-self.state.bar_direction)
                elif abs(gap) > 0.12:
                    self.set_dir(1 if gap > 0 else -1)
                elif self.state.fish_direction != 0:
                    self.set_dir(self.state.fish_direction)
                time.sleep(0.002)
                continue

            if abs(err) <= self.CATCH_DEADZONE_PX:
                if self.state.fish_direction != 0:
                    self.set_dir(self.state.fish_direction)
                time.sleep(0.002)
                continue

            self.set_dir(1 if err > 0 else -1)
            time.sleep(self.pulse_delay(err, gap))

        self.release_control()
        return True

    def cast_line(self) -> bool:
        self.move_client(400, 300)
        self.mouse_down()
        try:
            for _ in range(5):
                time.sleep(0.01)
                frame = self.grab(self.CAST_BAR_SEARCH)
                target = self._color_to_bgr(self.CAST_BAR_WHITE)
                dif = np.abs(frame.astype(np.int16) - target.reshape(1, 1, 3).astype(np.int16))
                mask = np.all(dif <= 2, axis=2)
                ys, xs = np.where(mask)
                if xs.size == 0:
                    continue
                x = int(xs[0])
                y = int(ys[0])
                self.move_client(self.CAST_BAR_SEARCH.x1 + x, self.CAST_BAR_SEARCH.y1 + y)
                tx = self._color_to_bgr(self.CAST_BAR_GREEN)
                x1, x2 = max(0, x - 2), min(frame.shape[1] - 1, x + 2)
                y1, y2 = max(0, y - 5), min(frame.shape[0] - 1, y)
                patch = frame[y1 : y2 + 1, x1 : x2 + 1]
                pd = np.abs(patch.astype(np.int16) - tx.reshape(1, 1, 3).astype(np.int16))
                if np.any(np.all(pd <= 25, axis=2)):
                    break
        finally:
            self.mouse_up()
        time.sleep(0.1)
        return True

    def auto_shake(self) -> bool:
        if self.shake_template is None:
            return self.is_catch_bar_displayed()
        fast = self.lure_speed >= 100
        no_frames = 0
        for i in range(50):
            frame = self.grab(self.SHAKE_AREA)
            if self._match(frame, self.shake_template, 0.72):
                res = cv2.matchTemplate(frame, self.shake_template, cv2.TM_CCOEFF_NORMED)
                _, _, _, loc = cv2.minMaxLoc(res)
                self.click_client(self.SHAKE_AREA.x1 + loc[0], self.SHAKE_AREA.y1 + loc[1])
                no_frames = 0
            elif fast:
                no_frames += 1

            if self.is_catch_bar_displayed():
                return True
            if fast and (no_frames >= 2 or (i + 1) >= 4):
                return True
        return False

    def cerebra_has_active_bar_run(self) -> bool:
        line = self.grab(self.CATCH_BAR_TOP_LINE)
        target = self._color_to_bgr(self.CATCH_BAR_ACTIVE_COLOR)
        run = 0
        best = 0
        for x in range(line.shape[1]):
            if np.all(np.abs(line[0, x].astype(np.int16) - target.astype(np.int16)) <= max(8, self.CATCH_BAR_ACTIVE_VAR)):
                run += 1
                best = max(best, run)
            else:
                run = 0
        return best >= 48

    def cerebra_icon_hits(self) -> bool:
        r = Region(max(0, self.CATCH_BAR.x1 - 150), max(0, self.CATCH_BAR.y1 - 120), self.CATCH_BAR.x2 + 150, self.CATCH_BAR.y2 - 8)
        frame = self.grab(r)
        target = self._color_to_bgr(self.CEREBRA_ICON_COLOR)
        dif = np.abs(frame.astype(np.int16) - target.reshape(1, 1, 3).astype(np.int16))
        return int(np.all(dif <= self.CEREBRA_ICON_TOL, axis=2).sum()) >= self.CEREBRA_ICON_MIN_HITS

    def cerebra_by_image(self) -> bool:
        if not self.cerebra_templates:
            return False
        sr = Region(max(0, self.CATCH_BAR.x1 - 120), max(0, self.CATCH_BAR.y1 - 90), self.CATCH_BAR.x2 + 120, self.CATCH_BAR.y2 + 90)
        frame = self.grab_cerebra_masked(sr)
        for tmpl in self.cerebra_templates:
            if self._match(frame, tmpl, 0.84) or self._match(frame, tmpl, 0.80):
                return True
        return False

    def detect_cerebra_start(self) -> bool:
        if self.cerebra_by_image():
            return True
        score, signals = self.cerebra_detection_score(include_template=True)
        if self.find_arrow_x() is not None:
            score += 1
        if self.cerebra_icon_hits():
            score += 1

        px, py, color, tol = self.CEREBRA_START_PIXEL
        if self._similar(self.pixel(px, py), color, tol):
            score += 1
        for sx in [self.CATCH_BAR.x1 + 24, (self.CATCH_BAR.x1 + self.CATCH_BAR.x2) // 2, self.CATCH_BAR.x2 - 24]:
            if self._similar(self.pixel(sx, py), color, tol + 10):
                score += 1
                break
        if DEBUG_CEREBRA:
            self.log(f"Cerebra start score={score} signals={signals}")
        return score >= self.CEREBRA_START_SCORE_MIN

    def cerebra_control_tick(self) -> Tuple[bool, str]:
        now = self.tick()
        dt = max(now - self.state.last_tick, 1)
        self.state.last_tick = now
        lane_frame = self.grab(self.CATCH_BAR)
        border_frame = self.grab(self.CATCH_BORDER_SCAN)
        bar_measurement = self._measure_cerebra_bar(dt)
        report = self.cerebra_system.process_frame(
            now_ms=now,
            dt_ms=dt,
            border_frame=border_frame,
            lane_frame=lane_frame,
            border_scan_rect=self._cerebra_border_scan_rect(),
            lane_rect=self._cerebra_lane_rect(),
            bar_measurement=bar_measurement,
        )
        snapshot = self.cerebra_system.classify(report)
        self.cerebra_last_report = report
        self.cerebra_last_snapshot = snapshot
        self._sync_cerebra_trackers_from_report(report, now, dt)
        bootstrap_confirmed, bootstrap_reason, bootstrap_conf = self._update_bootstrap_state(report, now)
        target_trust, effective_target_conf, trust_reason = self._update_target_trust_state(report, now)
        if bootstrap_confirmed:
            target_trust = "measured"
            effective_target_conf = max(effective_target_conf, bootstrap_conf)
            trust_reason = bootstrap_reason
        if self.cerebra_system.target_phase != self.cerebra_last_target_phase:
            self.log(
                f"target state -> {self.cerebra_system.target_phase} "
                f"({self.cerebra_system.target_tracker.last_update_debug.get('reason', 'phase_change')})"
            )
            self.cerebra_last_target_phase = self.cerebra_system.target_phase

        if report.border is not None:
            self.cerebra_last_border_bbox = (report.border.x, report.border.y, report.border.w, report.border.h)
        else:
            self.cerebra_last_border_bbox = None
        if report.roi is not None:
            self.cerebra_vision_debug.strip_bbox = (report.roi.x, report.roi.y, report.roi.w, report.roi.h)
        self.cerebra_vision_debug.border_confidence = float(report.border_confidence)
        self.cerebra_vision_debug.strip_confidence = float(report.inner_confidence)
        self.cerebra_vision_debug.predicted_target_x = float(
            report.target_state.position + (report.target_state.velocity * max(dt, 1))
        )
        self.cerebra_vision_debug.predicted_bar_x = float(
            report.bar_state.position + (report.bar_state.velocity * max(dt, 1))
        )

        bar_measured = report.control_measurement.x if report.control_measurement is not None else None
        bar_measured_source = report.control_measurement.source if report.control_measurement is not None else "none"
        self.cerebra_vision_debug.control_source = bar_measured_source
        self.cerebra_vision_debug.control_confidence = float(report.control_confidence)
        bar_changed = False
        if report.control_measurement is not None and self.state.has_bar:
            bar_changed = abs(report.control_measurement.x - self.state.last_bar_middle_x) >= 0.75
        current_bar_x = bar_measured if bar_measured is not None else report.bar_state.position
        if bar_measured_source != self.cerebra_last_bar_source:
            self.log(
                "Cerebra bar source "
                f"prev={self.cerebra_last_bar_source}:{self.cerebra_last_bar_source_x:.1f} "
                f"new={bar_measured_source}:{current_bar_x:.1f} "
                f"border={report.border_confidence:.2f} activity={snapshot.score:.2f}"
            )
            self.cerebra_last_bar_source = bar_measured_source
            self.cerebra_last_bar_source_x = float(current_bar_x)
        elif bar_measured is not None:
            self.cerebra_last_bar_source_x = float(current_bar_x)
        if report.bar_state.has_lock:
            fallback_used = report.control_measurement is None or bar_measured_source == "bar_prediction"
            if fallback_used:
                self.cerebra_missing_hb_streak += 1
            else:
                self.cerebra_missing_hb_streak = 0
            self.update_bar_state(report.bar_state.position, dt)
        else:
            self.cerebra_missing_hb_streak += 1
            if self.state.has_bar and self.cerebra_missing_hb_streak <= CEREBRA_BAR_MISSING_GRACE_FRAMES:
                predicted_bar = self.state.last_bar_middle_x + (self.state.bar_velocity * max(dt, 1))
                predicted_bar = float(self.clamp(predicted_bar, self.CATCH_BAR_TOP_LINE.x1, self.CATCH_BAR_TOP_LINE.x2))
                self.update_bar_state(predicted_bar, dt)
                report.bar_state.has_lock = True
                report.bar_state.position = predicted_bar
                report.bar_state.confidence = max(0.15, report.bar_state.confidence)
                bar_measured = predicted_bar
                bar_measured_source = "bar_prediction"
                fallback_used = True
            else:
                if DEBUG_CEREBRA:
                    self.log(
                        "Cerebra bar fail "
                        f"missing_count={self.cerebra_missing_hb_streak} "
                        f"reason=bar_missing_escalated"
                    )
                return False, "bar_missing"

        if not report.target_state.has_lock or report.decision is None:
            self.cerebra_missing_target_streak += 1
            self.cerebra_vision_debug.target_confidence = effective_target_conf
            self.cerebra_vision_debug.target_source = target_trust
            if DEBUG_CEREBRA:
                tdbg = self.cerebra_system.target_tracker.last_update_debug
                mode = str(tdbg.get("mode", "unknown"))
                should_log = (
                    mode != self.cerebra_last_target_log_mode
                    or (now - self.cerebra_last_target_log_tick) >= 700
                    or mode in {"bootstrap_candidate", "bootstrap_rejected", "bootstrap_confirmed", "rebootstrap"}
                )
                if should_log:
                    stage = str(tdbg.get("stage", "track")).lower()
                    prefix = f"Cerebra target stage={stage} "
                    self.log(
                        f"{prefix}"
                        f"mode={mode} reason={tdbg.get('reason', 'none')} "
                        f"mx={float(tdbg.get('measurement_x', 0.0)):.1f} "
                        f"peak={float(tdbg.get('peak', 0.0)):.1f} second={float(tdbg.get('second_peak', 0.0)):.1f} "
                        f"residual={float(tdbg.get('residual', 0.0)):.1f} "
                        f"gate={float(tdbg.get('gate', 0.0)):.1f} jump={float(tdbg.get('jump', 0.0)):.1f} "
                        f"conf={float(tdbg.get('confidence', 0.0)):.2f}"
                    )
                    self.cerebra_last_target_log_mode = mode
                    self.cerebra_last_target_log_tick = now
            if target_trust in {"grace_held", "predicted_short"} and self.cerebra_actuation.direction != 0:
                self.log(
                    "Cerebra target degraded "
                    f"trust={target_trust} conf={effective_target_conf:.2f} reason={trust_reason}"
                )
                self.set_dir(self.cerebra_actuation.direction)
                return True, target_trust
            self.release_control()
            self.cerebra_actuation.direction = -1
            self.log(
                "Cerebra steering disabled "
                f"trust={target_trust} conf={effective_target_conf:.2f} reason={trust_reason}"
            )
            return False, "invalid_target_recovery"

        self.cerebra_missing_target_streak = 0
        self.cerebra_last_target_log_mode = ""
        decision = report.decision
        self.cerebra_vision_debug.target_confidence = effective_target_conf
        self.cerebra_vision_debug.target_source = target_trust
        new_direction, action_reason = self._choose_cerebra_action(
            now,
            report,
            snapshot,
            target_trust,
            effective_target_conf,
        )
        previous_action = "hold" if self.cerebra_last_direction > 0 else "release"
        if self.cerebra_last_direction == 0:
            previous_action = "neutral"
        if new_direction != self.cerebra_last_direction:
            self.cerebra_last_direction = new_direction
            self.cerebra_last_direction_tick = now
        switched = decision.switched or (action_reason not in {"overlap_sticky", "overlap_grace"} and new_direction != (1 if decision.hold else -1))
        if DEBUG_CEREBRA and switched:
            self.log(
                "Cerebra action switch "
                f"prev={previous_action} new={'hold' if new_direction > 0 else 'release'} "
                f"mode={decision.mode} reason={action_reason} "
                f"err={decision.error:.1f} bar_vel={report.bar_state.velocity:.3f} "
                f"target_vel={report.target_state.velocity:.3f}"
            )
        if self._should_disable_target_control(target_trust, effective_target_conf):
            self.release_control()
            self.cerebra_actuation.direction = -1
            self.log(
                "Cerebra steering disabled "
                f"trust={target_trust} conf={effective_target_conf:.2f} "
                f"pred_age={self.cerebra_target_prediction_age} reason={action_reason}/{trust_reason}"
            )
            return False, action_reason
        self.set_dir(new_direction)

        if DEBUG_CEREBRA:
            measured_target = report.target_measurement.x if report.target_measurement is not None else report.target_state.position
            target_source = report.target_measurement.source if report.target_measurement is not None else "target_prediction"
            target_real = int(report.target_measurement is not None)
            bar_real = int(report.control_measurement is not None and report.control_measurement.source != "bar_prediction")
            tdbg = self.cerebra_system.target_tracker.last_update_debug
            bdbg = self.cerebra_system.bar_tracker.last_update_debug
            self.log(
                "Cerebra ctrl "
                f"bar_meas={bar_measured if bar_measured is not None else -1:.1f} bar_src={bar_measured_source} "
                f"bar_changed={int(bar_changed)} bar_pos={report.bar_state.position:.1f} bar_vel={report.bar_state.velocity:.3f} "
                f"target_meas={measured_target:.1f} target_src={target_source} pred_target={decision.predicted_target:.1f} "
                f"action={'hold' if new_direction > 0 else 'release'} mode={decision.mode} err={self.cerebra_err_smooth:.1f} "
                f"target_vel={report.target_state.velocity:.3f} "
                f"real_bar={bar_real} real_target={target_real} "
                f"tmode={tdbg.get('mode')} tres={float(tdbg.get('residual', 0.0)):.1f} "
                f"tgate={float(tdbg.get('gate', 0.0)):.1f} tjump={float(tdbg.get('jump', 0.0)):.1f} "
                f"tconf={effective_target_conf:.2f} trust={target_trust} trust_reason={trust_reason} "
                f"bmode={bdbg.get('mode')} activity={snapshot.score:.2f} "
                f"border={report.border_confidence:.2f} strip={report.inner_confidence:.2f} "
                f"bconf={report.control_confidence:.2f} reason={action_reason}"
            )
        return True, action_reason

    def run_cerebra(self) -> bool:
        self.reset_cerebra_cycle_state()
        self._reload_live_tuning_if_needed(force=True)
        sm = {
            "state": "IDLE",
            "state_since": self.tick(),
            "start_confirm": 0,
            "active_confirm": 0,
            "missing_confirm": 0,
            "end_confirm": 0,
            "recovery_frames": 0,
            "control_miss": 0,
            "weak_confirm": 0,
            "recovery_confirm": 0,
        }
        while True:
            self._reload_live_tuning_if_needed()
            if self.wait_if_paused():
                self.release_control()
                return False
            try:
                now = self.tick()
            except Exception as exc:
                self.log(f"Cerebra loop tick error: {exc}")
                self.log(traceback.format_exc().splitlines()[-1])
                self.release_control()
                return False
            if sm["state"] == "IDLE":
                sm["state"] = "WAITING_FOR_START"
                sm["state_since"] = now

            if sm["state"] == "WAITING_FOR_START":
                try:
                    if self.cerebra_last_end > 0 and (now - self.cerebra_last_end) < self.CEREBRA_REARM_MS:
                        time.sleep(self.poll_delay())
                        continue

                    lane_frame = self.grab(self.CATCH_BAR)
                    start_detection = self.cerebra_system.detect_start_band(lane_frame)
                    if start_detection.confirmed:
                        sm["start_confirm"] += 1
                    else:
                        sm["start_confirm"] = 0

                    if DEBUG_CEREBRA:
                        now_dbg = self.tick()
                        if (now_dbg - self.cerebra_last_start_debug_tick) >= CEREBRA_DEBUG_LOG_EVERY_MS:
                            roi = start_detection.roi
                            self.log(
                                "Cerebra start "
                                f"pink_pixels={start_detection.pink_pixels} "
                                f"band_width={start_detection.band_width} "
                                f"roi=({roi.x},{roi.y},{roi.w},{roi.h}) "
                                f"confirm={sm['start_confirm']}/{self.cerebra_system.config.start_confirm_frames} "
                                f"conf={start_detection.confidence:.2f} reason={start_detection.reason}"
                            )
                            self.cerebra_last_start_debug_tick = now_dbg

                    if sm["start_confirm"] >= int(self.cerebra_system.config.start_confirm_frames):
                        sm["state"] = "ACTIVE"
                        sm["state_since"] = now
                        sm["missing_confirm"] = 0
                        sm["end_confirm"] = 0
                        sm["recovery_frames"] = 0
                        sm["control_miss"] = 0
                        sm["weak_confirm"] = 0
                        sm["recovery_confirm"] = 0
                        self.log("Cerebra state -> ACTIVE")
                    elif (now - sm["state_since"]) > self.CEREBRA_START_TIMEOUT_MS:
                        self.log(f"Cerebra timeout waiting start ({start_detection.reason})")
                        self.cerebra_last_end = self.tick()
                        self.release_control()
                        return False
                except Exception as exc:
                    self.log(f"Cerebra start-state error: {exc}")
                    self.log(traceback.format_exc().splitlines()[-1])
                    self.release_control()
                    return False

            elif sm["state"] == "ACTIVE":
                try:
                    ok, reason = self.cerebra_control_tick()
                    snapshot = self.cerebra_last_snapshot
                    report = self.cerebra_last_report

                    if self._should_scan_result_ocr("ACTIVE"):
                        result = self.detect_cerebra_result()
                        if result.outcome is True:
                            self.log("Cerebra minigame won (caught detected)")
                            self.cerebra_last_end = self.tick()
                            self.release_control()
                            return True
                        if result.outcome is False and snapshot is not None and snapshot.score < 0.25:
                            self.log("Cerebra minigame lost (loss text detected)")
                            self.cerebra_last_end = self.tick()
                            self.release_control()
                            return False

                    bar_real = (
                        report is not None
                        and report.control_measurement is not None
                        and report.control_measurement.source != "bar_prediction"
                    )
                    target_real = report is not None and report.target_measurement is not None
                    strong_visual = (
                        snapshot is not None
                        and report is not None
                        and report.border_confidence >= 0.28
                        and report.inner_confidence >= 0.18
                    )
                    target_trust = self.cerebra_vision_debug.target_source
                    strong_control = (
                        report is not None
                        and report.control_confidence >= CEREBRA_CONFIDENCE_ACT_MIN_BAR
                        and self.cerebra_vision_debug.target_confidence >= CEREBRA_TARGET_CONFIDENCE_MEDIUM
                        and target_trust == "measured"
                    )

                    if ok and snapshot is not None and (snapshot.active or strong_control or (target_real and snapshot.score >= 0.20)):
                        sm["missing_confirm"] = 0
                        sm["recovery_frames"] = 0
                        sm["control_miss"] = 0
                        sm["weak_confirm"] = 0
                        sm["recovery_confirm"] = 0
                    else:
                        sm["control_miss"] += 1
                        sm["weak_confirm"] += 1
                        if reason in {"prediction_expired", "invalid_target_recovery", "bootstrap_wait"}:
                            sm["missing_confirm"] += 1
                            self.log(
                                "Cerebra recovery continue "
                                f"reason={reason} trust={target_trust} conf={self.cerebra_vision_debug.target_confidence:.2f}"
                            )
                        if (not bar_real) and (not target_real or (snapshot is not None and snapshot.score < 0.18)):
                            sm["missing_confirm"] += 1
                        if snapshot is not None and snapshot.recovery_recommended:
                            sm["recovery_confirm"] += 1
                        else:
                            sm["recovery_confirm"] = 0

                        if reason in {"prediction_expired", "invalid_target_recovery"}:
                            sm["recovery_confirm"] += 1

                        if sm["recovery_confirm"] >= CEREBRA_RECOVERY_CONFIRM_FRAMES:
                            sm["state"] = "RECOVERY"
                            sm["state_since"] = now
                            sm["recovery_frames"] = 1
                            self.log(
                                "Cerebra state -> RECOVERY "
                                f"(reason={reason} weak={sm['weak_confirm']} score={snapshot.score if snapshot is not None else 0.0:.2f})"
                            )
                            time.sleep(self.poll_delay())
                            continue

                    if snapshot is not None and snapshot.end_candidate and not strong_visual:
                        sm["end_confirm"] += 1
                    else:
                        sm["end_confirm"] = 0

                    if sm["missing_confirm"] >= int(self.cerebra_system.config.active_missing_frames) and sm["weak_confirm"] >= CEREBRA_END_LOSS_CONFIRM_FRAMES:
                        sm["state"] = "RESULT_OR_END"
                        sm["state_since"] = now
                        self.cerebra_result_window_started = now
                        self.cerebra_result_history.clear()
                        self.log(
                            "Cerebra state -> RESULT_OR_END "
                            f"(reason={reason} missing={sm['missing_confirm']} weak={sm['weak_confirm']})"
                        )
                    elif sm["end_confirm"] >= max(int(self.cerebra_system.config.end_confirm_frames), CEREBRA_END_STRONG_CONFIRM_FRAMES):
                        sm["state"] = "RESULT_OR_END"
                        sm["state_since"] = now
                        self.cerebra_result_window_started = now
                        self.cerebra_result_history.clear()
                        self.log(
                            "Cerebra state -> RESULT_OR_END "
                            f"(ui_absent end_confirm={sm['end_confirm']} weak={sm['weak_confirm']})"
                        )
                    elif DEBUG_CEREBRA and report is not None:
                        now_dbg = self.tick()
                        if (now_dbg - self.cerebra_last_debug_tick) >= CEREBRA_DEBUG_LOG_EVERY_MS:
                            self.log(
                                "Cerebra active "
                                f"score={snapshot.score:.2f} border={report.border_confidence:.2f} "
                                f"inner={report.inner_confidence:.2f} ctrl={report.control_confidence:.2f} "
                                f"target={report.target_state.confidence:.2f}"
                            )
                            self.cerebra_last_debug_tick = now_dbg
                except Exception as exc:
                    self.log(f"Cerebra active-state error: {exc}")
                    self.log(traceback.format_exc().splitlines()[-1])
                    self.release_control()
                    return False

            elif sm["state"] == "RECOVERY":
                try:
                    result = self.detect_cerebra_result()
                    if result.outcome is True:
                        self.log("Cerebra minigame won (caught detected)")
                        self.cerebra_last_end = self.tick()
                        self.release_control()
                        return True
                    if result.outcome is False:
                        self.log("Cerebra minigame lost (loss text detected)")
                        self.cerebra_last_end = self.tick()
                        self.release_control()
                        return False

                    ok, reason = self.cerebra_control_tick()
                    snapshot = self.cerebra_last_snapshot
                    sm["recovery_frames"] += 1
                    if ok and snapshot is not None and snapshot.active:
                        sm["active_confirm"] += 1
                    else:
                        sm["active_confirm"] = 0
                    if sm["active_confirm"] >= CEREBRA_ACTIVE_RECOVER_CONFIRM_FRAMES:
                        sm["state"] = "ACTIVE"
                        sm["state_since"] = now
                        sm["missing_confirm"] = 0
                        sm["end_confirm"] = 0
                        sm["weak_confirm"] = 0
                        sm["recovery_confirm"] = 0
                        self.log("Cerebra state -> ACTIVE (recovered)")
                    elif sm["recovery_frames"] >= max(int(self.cerebra_system.config.recovery_grace_frames), CEREBRA_RECOVERY_CONFIRM_FRAMES + 2):
                        sm["state"] = "RESULT_OR_END"
                        sm["state_since"] = now
                        self.cerebra_result_window_started = now
                        self.cerebra_result_history.clear()
                        self.log(
                            "Cerebra state -> RESULT_OR_END "
                            f"(recovery_expired reason={reason} frames={sm['recovery_frames']})"
                        )
                    elif DEBUG_CEREBRA:
                        self.log(
                            "Cerebra recovery continue "
                            f"reason={reason} trust={self.cerebra_vision_debug.target_source} "
                            f"conf={self.cerebra_vision_debug.target_confidence:.2f} frames={sm['recovery_frames']}"
                        )
                except Exception as exc:
                    self.log(f"Cerebra recovery-state error: {exc}")
                    self.log(traceback.format_exc().splitlines()[-1])
                    self.release_control()
                    return False

            elif sm["state"] == "RESULT_OR_END":
                try:
                    result = self.detect_cerebra_result()
                    if result.outcome is True:
                        self.log("Cerebra minigame won (caught detected)")
                        self.cerebra_last_end = self.tick()
                        self.release_control()
                        return True
                    if result.outcome is False:
                        self.log("Cerebra minigame lost (loss text detected)")
                        self.cerebra_last_end = self.tick()
                        self.release_control()
                        return False

                    lane_frame = self.grab(self.CATCH_BAR)
                    start_detection = self.cerebra_system.detect_start_band(lane_frame)
                    if start_detection.confirmed:
                        sm["state"] = "ACTIVE"
                        sm["state_since"] = now
                        sm["missing_confirm"] = 0
                        sm["end_confirm"] = 0
                        sm["recovery_frames"] = 0
                        sm["weak_confirm"] = 0
                        sm["recovery_confirm"] = 0
                        self.log(
                            "Cerebra state -> ACTIVE (band_reappeared) "
                            f"pink_pixels={start_detection.pink_pixels} band_width={start_detection.band_width}"
                        )
                    else:
                        elapsed = now - max(1, self.cerebra_result_window_started or now)
                        if DEBUG_CEREBRA and result.reason != "rate_limited":
                            self.log(
                                "Cerebra result window "
                                f"elapsed_ms={elapsed} raw='{result.raw_text[:80]}' "
                                f"norm='{result.normalized_text[:80]}' match='{result.matched_keyword or 'none'}' "
                                f"score={result.matched_score:.2f} reason={result.reason} "
                                f"roi=({self._result_region().x1},{self._result_region().y1},{self._result_region().x2},{self._result_region().y2}) "
                                f"band_reason={start_detection.reason}"
                            )
                        if elapsed >= CEREBRA_RESULT_WINDOW_MS:
                            self.log("Cerebra minigame lost (result window expired; fallback)")
                            self.cerebra_last_end = self.tick()
                            self.release_control()
                            return False
                except Exception as exc:
                    self.log(f"Cerebra result-state error: {exc}")
                    self.log(traceback.format_exc().splitlines()[-1])
                    self.release_control()
                    return False
            time.sleep(self.poll_delay())

    def poll_delay(self) -> float:
        return random.randint(self.CEREBRA_POLL_MIN, self.CEREBRA_POLL_MAX) / 1000.0

    def detect_cerebra_rod(self) -> bool:
        return "cerebra" in self.rod_name.lower()

    def start_macro(self) -> int:
        mode = self.args.mode
        if mode == "auto":
            mode = "cerebra" if self.detect_cerebra_rod() else "normal"
        self.log(f"Start macro: mode={mode} rod='{self.rod_name}' control={self.control}")
        cycles = 0
        while True:
            if self.wait_if_paused():
                self.release_control()
                return 0
            cycles += 1
            self.log(f"Cycle {cycles}")
            self.cast_line()
            shake_ok = self.auto_shake()
            if not shake_ok:
                self.log("Shake fallback path")
            if mode == "cerebra":
                self.apply_heartbeat_scaling()
                won = self.run_cerebra()
                self.record_cerebra_result(bool(won))
            else:
                self.catch_fish(False)
            if self.exit_requested:
                self.release_control()
                return 0
            time.sleep(3.0)
            if self.args.max_cycles > 0 and cycles >= self.args.max_cycles:
                break
        return 0

    def run_once(self) -> int:
        if self.wait_if_paused():
            self.release_control()
            return 0
        mode = self.args.mode
        if mode == "auto":
            mode = "cerebra" if self.detect_cerebra_rod() else "normal"
        self.log(f"Single run mode={mode}")
        if mode == "cerebra":
            self.apply_heartbeat_scaling()
            won = self.run_cerebra()
            self.record_cerebra_result(bool(won))
        else:
            self.catch_fish(False)
        return 0


def write_startup_log(path_text: str, args: argparse.Namespace) -> None:
    path = Path(path_text)
    if not path.is_absolute():
        path = (Path(__file__).resolve().parent / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(
            f"{datetime.now().isoformat()} START mode={args.mode} run_macro={args.run_macro} rod={args.rod_name} "
            f"control={args.control} client=({args.client_x},{args.client_y})\n"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fisch Python macro (normal + cerebra)")
    p.add_argument("--run-macro", action="store_true")
    p.add_argument("--mode", choices=["auto", "normal", "cerebra"], default="auto")
    p.add_argument("--rod-name", default="")
    p.add_argument("--control", type=float, default=0.0)
    p.add_argument("--lure-speed", type=float, default=0.0)
    p.add_argument("--client-x", type=int, default=0)
    p.add_argument("--client-y", type=int, default=0)
    p.add_argument("--max-cycles", type=int, default=0)
    p.add_argument("--startup-log", default="logs/cerebra_python_start.log")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    write_startup_log(args.startup_log, args)
    if IMPORT_ERROR:
        msg = (
            "Missing Python dependency: " + IMPORT_ERROR
            + ". Install with: py -m pip install opencv-python numpy mss pyautogui"
        )
        print(msg, flush=True)
        log_path = Path(__file__).resolve().parent / "logs" / "cerebra_python_runtime.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        return 2
    runner = Runner(args)
    return runner.start_macro() if args.run_macro else runner.run_once()


if __name__ == "__main__":
    raise SystemExit(main())
