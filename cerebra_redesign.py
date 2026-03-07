from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class VisionConfig:
    border_hsv_low: tuple[int, int, int] = (140, 120, 100)
    border_hsv_high: tuple[int, int, int] = (179, 255, 255)
    border_min_area: int = 700
    border_aspect_range: tuple[float, float] = (4.0, 40.0)
    border_padding_x: int = 8
    border_padding_y: int = 10
    target_dark_max: int = 88
    target_pink_hsv_low: tuple[int, int, int] = (145, 110, 100)
    target_pink_hsv_high: tuple[int, int, int] = (179, 255, 255)
    target_band_top_ratio: float = 0.22
    target_band_bottom_ratio: float = 0.78
    target_edge_margin_px: int = 6
    target_min_column_hits: int = 2
    target_projection_window: int = 9
    target_min_confidence: float = 0.28
    target_gate_px: float = 70.0
    target_max_jump_px: float = 95.0
    tracker_alpha: float = 0.55
    tracker_velocity_smoothing: float = 0.35
    tracker_history_size: int = 6
    tracker_max_missing_frames: int = 8
    prediction_lead_ms: float = 75.0
    control_deadzone_px: float = 4.0
    control_hysteresis_px: float = 2.0
    control_switch_delay_ms: int = 45
    control_reengage_error_px: float = 6.0
    control_hold_bias_px: float = 2.0
    control_hold_enter_px: float = 8.0
    control_release_enter_px: float = -8.0
    control_keep_band_px: float = 4.0
    control_min_action_ms: int = 90
    control_strong_flip_px: float = 15.0
    control_brake_velocity_px_per_ms: float = 0.11
    control_brake_error_px: float = 2.5
    control_startup_neutral_ms: int = 220
    control_startup_confidence: float = 0.45
    start_confirm_frames: int = 3
    active_confirm_frames: int = 2
    active_missing_frames: int = 6
    end_confirm_frames: int = 4
    recovery_grace_frames: int = 8
    min_start_confidence: float = 0.52
    min_active_confidence: float = 0.42
    start_roi_top_ratio: float = 0.45
    start_roi_bottom_ratio: float = 1.00
    start_roi_left_ratio: float = 0.22
    start_roi_right_ratio: float = 0.78
    start_min_pink_pixels: int = 220
    start_min_band_width_ratio: float = 0.42
    start_min_band_rows: int = 3
    target_bootstrap_confirmations: int = 2
    target_bootstrap_similarity_px: float = 24.0
    target_bootstrap_edge_margin_px: int = 18
    target_rebootstrap_no_lock_frames: int = 8
    target_post_bootstrap_grace_frames: int = 2
    target_search_peak_ratio: float = 1.14
    target_track_peak_ratio: float = 1.10
    target_search_min_peak: float = 3.0
    target_track_min_peak: float = 2.5
    target_contour_min_area: float = 8.0
    target_contour_max_area: float = 220.0
    target_contour_max_width_px: int = 42


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def right(self) -> int:
        return self.x + self.w - 1

    @property
    def top(self) -> int:
        return self.y

    @property
    def bottom(self) -> int:
        return self.y + self.h - 1

    def clamp_x(self, value: float) -> float:
        return max(float(self.left), min(float(self.right), float(value)))


@dataclass
class Measurement:
    x: float
    confidence: float
    width: float = 0.0
    source: str = "unknown"


@dataclass
class TrackerState:
    has_lock: bool = False
    position: float = 0.0
    velocity: float = 0.0
    confidence: float = 0.0
    missing_frames: int = 0
    history: deque[tuple[float, float]] = field(default_factory=lambda: deque(maxlen=6))


@dataclass
class ControllerDecision:
    hold: bool
    predicted_target: float
    error: float
    reason: str
    mode: str = "neutral"
    switched: bool = False
    switch_reason: str = ""


@dataclass
class FrameReport:
    ok: bool
    border: Optional[Rect]
    roi: Optional[Rect]
    target_measurement: Optional[Measurement]
    control_measurement: Optional[Measurement]
    target_state: TrackerState
    bar_state: TrackerState
    decision: Optional[ControllerDecision]
    target_visible: bool
    border_confidence: float
    inner_confidence: float
    control_confidence: float
    active_confidence: float
    debug_mask: Optional[Any] = None


@dataclass
class SessionSnapshot:
    possible_start: bool
    strong_start: bool
    active: bool
    recovery_recommended: bool
    end_candidate: bool
    score: float


@dataclass
class StartDetection:
    confirmed: bool
    pink_pixels: int
    band_width: int
    roi: Rect
    confidence: float
    reason: str
    mask: Optional[Any] = None


class AlphaBetaTracker:
    def __init__(self, alpha: float, velocity_smoothing: float, history_size: int, max_missing_frames: int) -> None:
        self.alpha = float(alpha)
        self.velocity_smoothing = float(velocity_smoothing)
        self.history_size = int(history_size)
        self.max_missing_frames = int(max_missing_frames)
        self.state = TrackerState(history=deque(maxlen=max(2, int(history_size))))
        self.last_update_debug: dict[str, Any] = {"mode": "init"}

    def reset(self) -> None:
        self.state = TrackerState(history=deque(maxlen=max(2, int(self.history_size))))
        self.last_update_debug = {"mode": "reset"}

    def predict_only(self, dt_ms: float, lane: Optional[Rect] = None) -> TrackerState:
        dt = max(float(dt_ms), 1.0)
        if not self.state.has_lock:
            self.last_update_debug = {"mode": "predict_no_lock"}
            return self.state
        self.state.position += self.state.velocity * dt
        if lane is not None:
            self.state.position = lane.clamp_x(self.state.position)
        self.state.missing_frames += 1
        self.state.confidence *= 0.82
        self.last_update_debug = {
            "mode": "predict_only",
            "position": float(self.state.position),
            "velocity": float(self.state.velocity),
            "missing_frames": int(self.state.missing_frames),
            "confidence": float(self.state.confidence),
        }
        if self.state.missing_frames > self.max_missing_frames:
            self.state.has_lock = False
            self.state.confidence = 0.0
        return self.state

    def update(
        self,
        measurement: Optional[Measurement],
        dt_ms: float,
        lane: Optional[Rect] = None,
        gate_px: Optional[float] = None,
        max_jump_px: Optional[float] = None,
    ) -> TrackerState:
        dt = max(float(dt_ms), 1.0)
        if not self.state.has_lock:
            if measurement is None:
                self.last_update_debug = {"mode": "no_measurement_no_lock"}
                return self.state
            self.state.has_lock = True
            self.state.position = float(measurement.x)
            self.state.velocity = 0.0
            self.state.confidence = float(measurement.confidence)
            self.state.missing_frames = 0
            self.state.history.append((0.0, self.state.position))
            self.last_update_debug = {
                "mode": "bootstrap",
                "measurement_x": float(measurement.x),
                "confidence": float(measurement.confidence),
            }
            return self.state

        predicted = self.state.position + (self.state.velocity * dt)
        if lane is not None:
            predicted = lane.clamp_x(predicted)

        if measurement is None:
            return self.predict_only(dt_ms=dt, lane=lane)

        residual = float(measurement.x) - predicted
        allowed_gate = float(gate_px if gate_px is not None else 9e9)
        allowed_jump = float(max_jump_px if max_jump_px is not None else 9e9)
        confidence = float(measurement.confidence)
        dynamic_gate = allowed_gate * (1.35 if confidence >= 0.85 else 1.0)
        dynamic_jump = allowed_jump * (1.20 if confidence >= 0.90 else 1.0)
        if abs(residual) > dynamic_gate or abs(float(measurement.x) - self.state.position) > dynamic_jump:
            self.last_update_debug = {
                "mode": "rejected",
                "stage": "track",
                "reason": "gate_or_jump",
                "measurement_x": float(measurement.x),
                "predicted_x": float(predicted),
                "residual": float(residual),
                "gate": float(dynamic_gate),
                "jump": float(dynamic_jump),
                "confidence": float(confidence),
            }
            return self.predict_only(dt_ms=dt, lane=lane)
        if confidence < 0.55 and abs(residual) > (dynamic_gate * 0.60):
            self.last_update_debug = {
                "mode": "rejected",
                "stage": "track",
                "reason": "low_confidence_residual",
                "measurement_x": float(measurement.x),
                "predicted_x": float(predicted),
                "residual": float(residual),
                "gate": float(dynamic_gate),
                "jump": float(dynamic_jump),
                "confidence": float(confidence),
            }
            return self.predict_only(dt_ms=dt, lane=lane)

        corrected = predicted + (self.alpha * residual)
        if lane is not None:
            corrected = lane.clamp_x(corrected)
        self.state.position = corrected
        self.state.history.append((0.0, corrected))
        if len(self.state.history) >= 2:
            oldest = self.state.history[0][1]
            newest = self.state.history[-1][1]
            span = dt * float(len(self.state.history) - 1)
            raw_velocity = (newest - oldest) / max(span, 1.0)
            self.state.velocity = (
                (self.state.velocity * (1.0 - self.velocity_smoothing))
                + (raw_velocity * self.velocity_smoothing)
            )
        self.state.confidence = min(1.0, max(float(measurement.confidence), self.state.confidence * 0.75))
        self.state.missing_frames = 0
        self.last_update_debug = {
            "mode": "accepted",
            "measurement_x": float(measurement.x),
            "predicted_x": float(predicted),
            "residual": float(residual),
            "gate": float(dynamic_gate),
            "jump": float(dynamic_jump),
            "confidence": float(confidence),
            "corrected_x": float(corrected),
            "velocity": float(self.state.velocity),
        }
        return self.state


class BinaryHysteresisController:
    def __init__(self, config: VisionConfig) -> None:
        self.config = config
        self.hold = False
        self.last_switch_tick = 0
        self.current_mode = "neutral"
        self.active_since_tick = 0

    def reset(self) -> None:
        self.hold = False
        self.last_switch_tick = 0
        self.current_mode = "neutral"
        self.active_since_tick = 0

    def decide(
        self,
        now_ms: int,
        target_state: TrackerState,
        bar_state: TrackerState,
        lane: Rect,
    ) -> Optional[ControllerDecision]:
        if not target_state.has_lock or not bar_state.has_lock:
            return None
        if self.active_since_tick <= 0:
            self.active_since_tick = now_ms

        lead = max(0.0, float(self.config.prediction_lead_ms))
        predicted_target = lane.clamp_x(target_state.position + (target_state.velocity * lead))
        error = predicted_target - bar_state.position
        relative_velocity = target_state.velocity - bar_state.velocity
        startup = (
            (now_ms - self.active_since_tick) < int(self.config.control_startup_neutral_ms)
            and target_state.confidence < float(self.config.control_startup_confidence)
        )

        hold_enter = float(self.config.control_hold_enter_px)
        release_enter = float(self.config.control_release_enter_px)
        keep_band = float(self.config.control_keep_band_px)
        min_action_ms = int(self.config.control_min_action_ms)
        desired = self.hold
        reason = "keep_band"
        mode = self.current_mode

        if startup:
            desired = self.hold
            reason = "startup_neutral"
            mode = "neutral"
        else:
            overshoot_hold = self.hold and error < -float(self.config.control_brake_error_px) and bar_state.velocity > float(self.config.control_brake_velocity_px_per_ms)
            overshoot_release = (not self.hold) and error > float(self.config.control_brake_error_px) and bar_state.velocity < -float(self.config.control_brake_velocity_px_per_ms)
            if overshoot_hold:
                desired = False
                reason = "brake_release"
                mode = "brake"
            elif overshoot_release:
                desired = True
                reason = "brake_hold"
                mode = "brake"
            elif self.hold:
                if error <= release_enter:
                    desired = False
                    reason = "release_hysteresis"
                    mode = "release"
                elif error >= -keep_band:
                    desired = True
                    reason = "hold_sticky"
                    mode = "hold"
            else:
                if error >= hold_enter:
                    desired = True
                    reason = "hold_hysteresis"
                    mode = "hold"
                elif error <= keep_band:
                    desired = False
                    reason = "release_sticky"
                    mode = "release"

            if abs(error) <= keep_band:
                desired = self.hold
                reason = "keep_current_band"
                mode = "hold" if self.hold else "release"

            moving_toward_target = (error > 0 and bar_state.velocity > 0 and relative_velocity >= -0.02) or (
                error < 0 and bar_state.velocity < 0 and relative_velocity <= 0.02
            )
            if moving_toward_target and abs(error) < max(keep_band * 1.5, 6.0):
                desired = self.hold
                if error < 0:
                    desired = False
                reason = "velocity_alignment"
                mode = "hold" if desired else "release"

            if (not self.hold) and error >= float(self.config.control_reengage_error_px) and relative_velocity > -0.04:
                desired = True
                reason = "reengage"
                mode = "hold"

        switched = False
        switch_reason = ""
        if desired != self.hold:
            strong_flip = abs(error) >= float(self.config.control_strong_flip_px)
            brake_flip = reason.startswith("brake_")
            if not strong_flip and not brake_flip and (now_ms - self.last_switch_tick) < min_action_ms:
                desired = self.hold
                reason = "min_action_stick"
                mode = self.current_mode
            elif not strong_flip and not brake_flip and (now_ms - self.last_switch_tick) < int(self.config.control_switch_delay_ms):
                desired = self.hold
                reason = "switch_delay"
                mode = self.current_mode
            else:
                prev_mode = self.current_mode
                self.hold = desired
                self.last_switch_tick = now_ms
                switched = True
                switch_reason = reason
                self.current_mode = mode
                if not self.current_mode:
                    self.current_mode = "hold" if self.hold else "release"
                if prev_mode == "neutral" and self.current_mode == "neutral":
                    self.current_mode = "hold" if self.hold else "release"
        else:
            if mode != "neutral":
                self.current_mode = mode

        return ControllerDecision(
            hold=self.hold,
            predicted_target=predicted_target,
            error=error,
            reason=reason,
            mode=self.current_mode,
            switched=switched,
            switch_reason=switch_reason,
        )


class CerebraVisionSystem:
    def __init__(self, cv2_module: Any, np_module: Any, config: Optional[VisionConfig] = None) -> None:
        self.cv2 = cv2_module
        self.np = np_module
        self.config = config or VisionConfig()
        self.target_tracker = AlphaBetaTracker(
            alpha=self.config.tracker_alpha,
            velocity_smoothing=self.config.tracker_velocity_smoothing,
            history_size=self.config.tracker_history_size,
            max_missing_frames=self.config.tracker_max_missing_frames,
        )
        self.bar_tracker = AlphaBetaTracker(
            alpha=0.65,
            velocity_smoothing=0.30,
            history_size=4,
            max_missing_frames=4,
        )
        self.controller = BinaryHysteresisController(self.config)
        self.last_border: Optional[Rect] = None
        self.target_bootstrap_candidates: deque[Measurement] = deque(maxlen=2)
        self.target_no_lock_frames = 0
        self.last_target_detection_debug: dict[str, Any] = {"mode": "init"}
        self.target_phase = "SEARCH_TARGET"
        self.target_post_bootstrap_grace = 0

    def reset(self) -> None:
        self.target_tracker.reset()
        self.bar_tracker.reset()
        self.controller.reset()
        self.last_border = None
        self.target_bootstrap_candidates.clear()
        self.target_no_lock_frames = 0
        self.last_target_detection_debug = {"mode": "reset"}
        self.target_phase = "SEARCH_TARGET"
        self.target_post_bootstrap_grace = 0

    def update_config(self, config: VisionConfig) -> None:
        self.config = config
        self.controller.config = config
        self.target_tracker.alpha = config.tracker_alpha
        self.target_tracker.velocity_smoothing = config.tracker_velocity_smoothing
        self.target_tracker.history_size = config.tracker_history_size
        self.target_tracker.max_missing_frames = config.tracker_max_missing_frames

    def detect_border(self, frame_bgr: Any) -> Optional[Rect]:
        hsv = self.cv2.cvtColor(frame_bgr, self.cv2.COLOR_BGR2HSV)
        mask = self.cv2.inRange(
            hsv,
            self.np.array(self.config.border_hsv_low, dtype=self.np.uint8),
            self.np.array(self.config.border_hsv_high, dtype=self.np.uint8),
        )
        kernel = self.np.ones((3, 3), dtype=self.np.uint8)
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_CLOSE, kernel, iterations=1)
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_OPEN, kernel, iterations=1)
        found = self.cv2.findContours(mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
        contours = found[0] if len(found) == 2 else found[1]

        best: Optional[Rect] = None
        best_score = 0.0
        for contour in contours:
            area = float(self.cv2.contourArea(contour))
            if area < float(self.config.border_min_area):
                continue
            x, y, w, h = self.cv2.boundingRect(contour)
            if w < 40 or h < 6:
                continue
            aspect = float(w) / float(max(h, 1))
            lo, hi = self.config.border_aspect_range
            if aspect < lo or aspect > hi:
                continue
            score = area * min(2.0, max(1.0, aspect / 8.0))
            if score > best_score:
                best = Rect(x=x, y=y, w=w, h=h)
                best_score = score
        return best

    def build_start_roi(self, frame_bgr: Any) -> Rect:
        h, w = frame_bgr.shape[:2]
        x1 = int(round(w * self.config.start_roi_left_ratio))
        x2 = int(round(w * self.config.start_roi_right_ratio))
        y1 = int(round(h * self.config.start_roi_top_ratio))
        y2 = int(round(h * self.config.start_roi_bottom_ratio))
        x1 = max(0, min(w - 1, x1))
        x2 = max(x1 + 1, min(w, x2))
        y1 = max(0, min(h - 1, y1))
        y2 = max(y1 + 1, min(h, y2))
        return Rect(x=x1, y=y1, w=max(1, x2 - x1), h=max(1, y2 - y1))

    def detect_start_band(self, frame_bgr: Any) -> StartDetection:
        roi = self.build_start_roi(frame_bgr)
        roi_frame = frame_bgr[roi.top:roi.top + roi.h, roi.left:roi.left + roi.w]
        if roi_frame.size == 0:
            return StartDetection(
                confirmed=False,
                pink_pixels=0,
                band_width=0,
                roi=roi,
                confidence=0.0,
                reason="empty_roi",
            )

        hsv = self.cv2.cvtColor(roi_frame, self.cv2.COLOR_BGR2HSV)
        pink_mask = self.cv2.inRange(
            hsv,
            self.np.array(self.config.border_hsv_low, dtype=self.np.uint8),
            self.np.array(self.config.border_hsv_high, dtype=self.np.uint8),
        )
        kernel = self.np.ones((3, 3), dtype=self.np.uint8)
        pink_mask = self.cv2.morphologyEx(pink_mask, self.cv2.MORPH_CLOSE, kernel, iterations=1)
        pink_mask = self.cv2.morphologyEx(pink_mask, self.cv2.MORPH_OPEN, kernel, iterations=1)

        pink_pixels = int(self.np.count_nonzero(pink_mask))
        row_hits = self.np.sum(pink_mask > 0, axis=1).astype(self.np.int32)
        band_width = int(row_hits.max()) if row_hits.size else 0
        band_rows = int(self.np.count_nonzero(row_hits >= max(1, int(roi.w * 0.30))))
        width_ratio = (float(band_width) / float(max(1, roi.w))) if roi.w > 0 else 0.0
        pixel_score = min(1.0, pink_pixels / max(float(self.config.start_min_pink_pixels), 1.0))
        width_score = min(1.0, width_ratio / max(self.config.start_min_band_width_ratio, 0.01))
        row_score = min(1.0, band_rows / max(float(self.config.start_min_band_rows), 1.0))
        confidence = max(0.0, min(1.0, (0.45 * pixel_score) + (0.40 * width_score) + (0.15 * row_score)))

        confirmed = True
        reason = "pink_band"
        if pink_pixels < int(self.config.start_min_pink_pixels):
            confirmed = False
            reason = "pink_pixels_low"
        elif width_ratio < float(self.config.start_min_band_width_ratio):
            confirmed = False
            reason = "band_width_low"
        elif band_rows < int(self.config.start_min_band_rows):
            confirmed = False
            reason = "band_rows_low"

        return StartDetection(
            confirmed=confirmed,
            pink_pixels=pink_pixels,
            band_width=band_width,
            roi=roi,
            confidence=confidence,
            reason=reason,
            mask=pink_mask,
        )

    def build_roi(self, lane: Rect, border: Optional[Rect]) -> Rect:
        active = border or self.last_border
        if active is None:
            return lane
        x1 = max(lane.left, active.left - self.config.border_padding_x)
        y1 = max(lane.top, active.top - self.config.border_padding_y)
        x2 = min(lane.right, active.right + self.config.border_padding_x)
        y2 = min(lane.bottom, active.bottom + self.config.border_padding_y)
        return Rect(x=x1, y=y1, w=max(1, x2 - x1 + 1), h=max(1, y2 - y1 + 1))

    def _smooth_projection(self, values: Any, window: int) -> Any:
        window = max(1, int(window))
        if window <= 1 or len(values) == 0:
            return values
        kernel = self.np.ones((window,), dtype=self.np.float32) / float(window)
        return self.np.convolve(values, kernel, mode="same")

    def _build_target_band(self, frame_bgr: Any) -> tuple[Any, Any]:
        if frame_bgr.size == 0:
            return None, None
        gray = self.cv2.cvtColor(frame_bgr, self.cv2.COLOR_BGR2GRAY)
        band_top = int(round(frame_bgr.shape[0] * self.config.target_band_top_ratio))
        band_bottom = int(round(frame_bgr.shape[0] * self.config.target_band_bottom_ratio))
        band_top = max(0, min(frame_bgr.shape[0] - 1, band_top))
        band_bottom = max(band_top + 1, min(frame_bgr.shape[0], band_bottom))
        band_gray = gray[band_top:band_bottom, :]
        dark_mask = self.cv2.inRange(band_gray, 0, self.config.target_dark_max)
        kernel = self.np.ones((3, 3), dtype=self.np.uint8)
        dark_mask = self.cv2.morphologyEx(dark_mask, self.cv2.MORPH_OPEN, kernel, iterations=1)
        dark_mask = self.cv2.morphologyEx(dark_mask, self.cv2.MORPH_CLOSE, kernel, iterations=1)

        edge = max(0, int(self.config.target_edge_margin_px))
        if edge > 0 and dark_mask.shape[1] > (edge * 2):
            dark_mask[:, :edge] = 0
            dark_mask[:, -edge:] = 0
        return band_gray, dark_mask

    def _detect_target_projection(
        self,
        dark_mask: Any,
        lane: Rect,
        predicted_x: Optional[float],
        phase: str,
    ) -> Optional[Measurement]:
        if dark_mask is None or dark_mask.size == 0:
            self.last_target_detection_debug = {"mode": "miss", "stage": "small_mask", "reason": "empty_frame"}
            return None

        projection = self.np.sum(dark_mask > 0, axis=0).astype(self.np.float32)
        smooth = self._smooth_projection(projection, self.config.target_projection_window)
        if smooth.size == 0:
            self.last_target_detection_debug = {"mode": "miss", "stage": "small_mask", "reason": "empty_projection"}
            return None
        peak_index = int(self.np.argmax(smooth))
        peak_value = float(smooth[peak_index])
        min_peak = self.config.target_track_min_peak if phase == "TRACK_TARGET" else self.config.target_search_min_peak
        if peak_value < max(float(self.config.target_min_column_hits), float(min_peak)):
            self.last_target_detection_debug = {
                "mode": "miss",
                "stage": "projection",
                "reason": "weak_peak",
                "peak": float(peak_value),
            }
            return None

        smooth_for_second = smooth.copy()
        suppress = max(2, int(self.config.target_projection_window // 2))
        s1 = max(0, peak_index - suppress)
        s2 = min(smooth_for_second.shape[0], peak_index + suppress + 1)
        smooth_for_second[s1:s2] = 0
        second_peak = float(smooth_for_second.max()) if smooth_for_second.size > 0 else 0.0
        peak_ratio = peak_value / max(1.0, second_peak)
        min_ratio = self.config.target_track_peak_ratio if phase == "TRACK_TARGET" else self.config.target_search_peak_ratio
        if peak_ratio < min_ratio:
            self.last_target_detection_debug = {
                "mode": "miss",
                "stage": "projection",
                "reason": "ambiguous_projection",
                "peak": float(peak_value),
                "second_peak": float(second_peak),
                "peak_ratio": float(peak_ratio),
            }
            return None

        left = peak_index
        right = peak_index
        threshold = max(1.0, peak_value * 0.35)
        while left > 0 and smooth[left - 1] >= threshold:
            left -= 1
        while right < (smooth.shape[0] - 1) and smooth[right + 1] >= threshold:
            right += 1

        center = float(lane.left + peak_index)
        width = float(max(1, right - left + 1))
        strength = min(1.0, peak_value / max(6.0, float(dark_mask.shape[0]) * 0.9))
        continuity = min(1.0, width / 18.0)
        dominance = min(1.0, (peak_ratio - 1.0) / 0.9)
        confidence = (0.50 * strength) + (0.18 * continuity) + (0.20 * dominance)
        if predicted_x is not None:
            distance = abs(center - float(predicted_x))
            confidence += max(0.0, 0.28 * (1.0 - (distance / max(1.0, self.config.target_gate_px))))
        else:
            lane_center = (lane.left + lane.right) / 2.0
            center_bias = 1.0 - min(1.0, abs(center - lane_center) / max(1.0, lane.w * 0.5))
            confidence += max(0.0, 0.12 * center_bias)
        confidence = max(0.0, min(1.0, confidence))
        if confidence < self.config.target_min_confidence:
            self.last_target_detection_debug = {
                "mode": "miss",
                "stage": "projection",
                "reason": "weak_peak",
                "peak": float(peak_value),
                "peak_ratio": float(peak_ratio),
                "confidence": float(confidence),
            }
            return None

        self.last_target_detection_debug = {
            "mode": "candidate",
            "stage": "projection",
            "measurement_x": float(center),
            "confidence": float(confidence),
            "peak": float(peak_value),
            "second_peak": float(second_peak),
            "peak_ratio": float(peak_ratio),
        }
        return Measurement(x=center, confidence=confidence, width=width, source="projection")

    def _detect_target_contour(
        self,
        dark_mask: Any,
        lane: Rect,
        predicted_x: Optional[float],
    ) -> Optional[Measurement]:
        if dark_mask is None or dark_mask.size == 0:
            return None
        found = self.cv2.findContours(dark_mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
        contours = found[0] if len(found) == 2 else found[1]
        best: Optional[Measurement] = None
        best_score = 0.0
        lane_center = (lane.left + lane.right) / 2.0
        for contour in contours:
            area = float(self.cv2.contourArea(contour))
            if area < float(self.config.target_contour_min_area) or area > float(self.config.target_contour_max_area):
                continue
            x, y, w, h = self.cv2.boundingRect(contour)
            if w <= 0 or w > int(self.config.target_contour_max_width_px) or h < 2:
                continue
            center = float(lane.left + x + (w / 2.0))
            edge_dist = min(center - lane.left, lane.right - center)
            if edge_dist < float(self.config.target_bootstrap_edge_margin_px):
                continue
            compactness = min(1.0, area / max(1.0, w * h))
            size_score = min(1.0, area / 80.0)
            continuity = 0.4
            if predicted_x is not None:
                continuity = max(0.0, 1.0 - (abs(center - float(predicted_x)) / 50.0))
            else:
                continuity = max(0.0, 1.0 - (abs(center - lane_center) / max(1.0, lane.w * 0.5)))
            score = (0.35 * size_score) + (0.25 * compactness) + (0.40 * continuity)
            if score > best_score:
                best_score = score
                best = Measurement(x=center, confidence=max(0.0, min(1.0, score)), width=float(w), source="contour")
        if best is not None and best.confidence >= 0.34:
            self.last_target_detection_debug = {
                "mode": "candidate",
                "stage": "contour",
                "measurement_x": float(best.x),
                "confidence": float(best.confidence),
            }
            return best
        self.last_target_detection_debug = {"mode": "miss", "stage": "contour", "reason": "no_plausible_contour"}
        return None

    def detect_target(self, frame_bgr: Any, lane: Rect, predicted_x: Optional[float], phase: str) -> tuple[Optional[Measurement], Any]:
        if frame_bgr.size == 0:
            self.last_target_detection_debug = {"mode": "miss", "stage": "wave", "reason": "empty_frame"}
            return None, None
        _, dark_mask = self._build_target_band(frame_bgr)
        if dark_mask is None:
            self.last_target_detection_debug = {"mode": "miss", "stage": "wave", "reason": "empty_frame"}
            return None, None

        dark_cols = int(self.np.count_nonzero(self.np.sum(dark_mask > 0, axis=0) > 0))
        if dark_cols < 2:
            self.last_target_detection_debug = {"mode": "miss", "stage": "wave", "reason": "low_dark_cols"}
            return None, dark_mask

        measurement = self._detect_target_projection(dark_mask, lane, predicted_x, phase)
        if measurement is not None:
            return measurement, dark_mask
        if phase == "SEARCH_TARGET":
            contour_measurement = self._detect_target_contour(dark_mask, lane, predicted_x)
            if contour_measurement is not None:
                return contour_measurement, dark_mask
        return None, dark_mask

    def detect_control_marker(self, frame_bgr: Any, lane: Rect, predicted_x: Optional[float]) -> Optional[Measurement]:
        if frame_bgr.size == 0:
            return None
        gray = self.cv2.cvtColor(frame_bgr, self.cv2.COLOR_BGR2GRAY)
        max_channel = frame_bgr.max(axis=2)
        min_channel = frame_bgr.min(axis=2)
        white_mask = self.cv2.inRange(gray, 215, 255)
        neutral_mask = self.cv2.inRange((max_channel - min_channel).astype(self.np.uint8), 0, 28)
        mask = self.cv2.bitwise_and(white_mask, neutral_mask)
        kernel = self.np.ones((2, 2), dtype=self.np.uint8)
        mask = self.cv2.morphologyEx(mask, self.cv2.MORPH_OPEN, kernel, iterations=1)
        found = self.cv2.findContours(mask, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
        contours = found[0] if len(found) == 2 else found[1]
        best: Optional[Measurement] = None
        best_score = 0.0
        for contour in contours:
            x, y, w, h = self.cv2.boundingRect(contour)
            if h < max(3, int(frame_bgr.shape[0] * 0.28)) or w > 12:
                continue
            center = float(lane.left + x + (w / 2.0))
            height_score = min(1.0, h / max(4.0, float(frame_bgr.shape[0]) * 0.80))
            thin_score = min(1.0, 3.0 / max(1.0, float(w)))
            continuity = 0.4
            if predicted_x is not None:
                distance = abs(center - float(predicted_x))
                continuity = max(0.0, 1.0 - (distance / 55.0))
            score = (0.45 * height_score) + (0.20 * thin_score) + (0.35 * continuity)
            if score > best_score:
                best_score = score
                best = Measurement(x=center, confidence=max(0.0, min(1.0, score)), width=float(w), source="white_marker")
        if best is not None and best.confidence >= 0.30:
            return best
        return None

    def update_bar(self, measurement: Optional[Measurement], dt_ms: float, lane: Rect) -> TrackerState:
        return self.bar_tracker.update(measurement=measurement, dt_ms=dt_ms, lane=lane, gate_px=90.0, max_jump_px=120.0)

    def classify(self, report: FrameReport) -> SessionSnapshot:
        score = (
            (0.35 * report.border_confidence)
            + (0.20 * report.inner_confidence)
            + (0.20 * report.control_confidence)
            + (0.25 * report.target_state.confidence)
        )
        possible_start = report.border_confidence >= 0.45 and report.inner_confidence >= 0.30
        strong_start = (
            possible_start
            and report.control_confidence >= 0.25
            and score >= self.config.min_start_confidence
        )
        active = report.border_confidence >= 0.40 and score >= self.config.min_active_confidence
        recovery = active and (not report.target_visible) and report.target_state.has_lock
        end_candidate = report.border_confidence < 0.18 and report.control_confidence < 0.18 and report.inner_confidence < 0.18
        return SessionSnapshot(
            possible_start=possible_start,
            strong_start=strong_start,
            active=active,
            recovery_recommended=recovery,
            end_candidate=end_candidate,
            score=score,
        )

    def _prepare_target_measurement(self, measurement: Optional[Measurement], lane_rect: Rect) -> Optional[Measurement]:
        if self.target_tracker.state.has_lock:
            self.target_bootstrap_candidates.clear()
            self.target_no_lock_frames = 0
            self.target_phase = "TRACK_TARGET"
            return measurement

        self.target_phase = "SEARCH_TARGET"
        self.target_no_lock_frames += 1
        if self.target_no_lock_frames >= int(self.config.target_rebootstrap_no_lock_frames):
            self.target_bootstrap_candidates.clear()
            self.target_tracker.last_update_debug = {"mode": "rebootstrap", "stage": "bootstrap", "reason": "no_lock_timeout"}
            self.target_no_lock_frames = 0

        if measurement is None:
            if not self.target_tracker.state.has_lock:
                reason = str(self.last_target_detection_debug.get("reason", "no_measurement_no_lock"))
                self.target_tracker.last_update_debug = {
                    "mode": "bootstrap_rejected",
                    "stage": "bootstrap",
                    "reason": reason,
                    "confidence": float(self.last_target_detection_debug.get("confidence", 0.0)),
                    "measurement_x": float(self.last_target_detection_debug.get("measurement_x", 0.0)),
                }
            return None

        edge_margin = float(self.config.target_bootstrap_edge_margin_px)
        if measurement.x <= (lane_rect.left + edge_margin) or measurement.x >= (lane_rect.right - edge_margin):
            self.target_tracker.last_update_debug = {
                "mode": "bootstrap_rejected",
                "stage": "bootstrap",
                "reason": "edge_reject",
                "measurement_x": float(measurement.x),
                "confidence": float(measurement.confidence),
            }
            return None

        if measurement.confidence < max(self.config.target_min_confidence, 0.36):
            self.target_tracker.last_update_debug = {
                "mode": "bootstrap_rejected",
                "stage": "bootstrap",
                "reason": "weak_peak",
                "measurement_x": float(measurement.x),
                "confidence": float(measurement.confidence),
            }
            return None

        if not self.target_bootstrap_candidates:
            self.target_bootstrap_candidates.append(measurement)
            self.target_tracker.last_update_debug = {
                "mode": "bootstrap_candidate",
                "stage": "bootstrap",
                "reason": "bootstrap_not_confirmed",
                "measurement_x": float(measurement.x),
                "confidence": float(measurement.confidence),
            }
            return None

        prev = self.target_bootstrap_candidates[-1]
        if abs(prev.x - measurement.x) > float(self.config.target_bootstrap_similarity_px):
            self.target_bootstrap_candidates.clear()
            self.target_bootstrap_candidates.append(measurement)
            self.target_tracker.last_update_debug = {
                "mode": "bootstrap_rejected",
                "stage": "bootstrap",
                "reason": "bootstrap_not_confirmed",
                "measurement_x": float(measurement.x),
                "previous_x": float(prev.x),
                "confidence": float(measurement.confidence),
            }
            return None

        self.target_bootstrap_candidates.append(measurement)
        if len(self.target_bootstrap_candidates) < int(self.config.target_bootstrap_confirmations):
            self.target_tracker.last_update_debug = {
                "mode": "bootstrap_candidate",
                "stage": "bootstrap",
                "reason": "bootstrap_not_confirmed",
                "measurement_x": float(measurement.x),
                "confidence": float(measurement.confidence),
            }
            return None

        avg_x = sum(m.x for m in self.target_bootstrap_candidates) / float(len(self.target_bootstrap_candidates))
        avg_conf = max(m.confidence for m in self.target_bootstrap_candidates)
        self.target_bootstrap_candidates.clear()
        self.target_no_lock_frames = 0
        confirmed = Measurement(x=avg_x, confidence=max(avg_conf, 0.48), width=measurement.width, source=f"{measurement.source}_bootstrap")
        self.target_tracker.last_update_debug = {
            "mode": "bootstrap_confirmed",
            "stage": "bootstrap",
            "measurement_x": float(confirmed.x),
            "confidence": float(confirmed.confidence),
        }
        self.target_phase = "TRACK_TARGET"
        self.target_post_bootstrap_grace = int(self.config.target_post_bootstrap_grace_frames)
        return confirmed

    def process_frame(
        self,
        now_ms: int,
        dt_ms: float,
        border_frame: Any,
        lane_frame: Any,
        border_scan_rect: Rect,
        lane_rect: Rect,
        bar_measurement: Optional[Measurement],
    ) -> FrameReport:
        border = self.detect_border(border_frame)
        border_abs = None
        if border is not None:
            border_abs = Rect(
                x=border_scan_rect.left + border.left,
                y=border_scan_rect.top + border.top,
                w=border.w,
                h=border.h,
            )
            self.last_border = border_abs
        roi = self.build_roi(lane_rect, border_abs)

        roi_x1 = max(0, roi.left - lane_rect.left)
        roi_y1 = max(0, roi.top - lane_rect.top)
        roi_x2 = min(lane_frame.shape[1], roi.right - lane_rect.left + 1)
        roi_y2 = min(lane_frame.shape[0], roi.bottom - lane_rect.top + 1)
        roi_frame = lane_frame[roi_y1:roi_y2, roi_x1:roi_x2]
        if roi_frame.size == 0:
            roi_frame = lane_frame

        predicted_x = None
        phase = "TRACK_TARGET" if self.target_tracker.state.has_lock else "SEARCH_TARGET"
        if phase == "TRACK_TARGET":
            predicted_x = self.target_tracker.state.position + (self.target_tracker.state.velocity * max(float(dt_ms), 1.0))

        predicted_control_x = None
        if self.bar_tracker.state.has_lock:
            predicted_control_x = self.bar_tracker.state.position + (self.bar_tracker.state.velocity * max(float(dt_ms), 1.0))

        target_measurement, debug_mask = self.detect_target(roi_frame, roi, predicted_x, phase)
        target_measurement = self._prepare_target_measurement(target_measurement, lane_rect)
        if phase == "TRACK_TARGET" and target_measurement is None and self.target_post_bootstrap_grace > 0 and self.target_tracker.state.has_lock:
            target_measurement = Measurement(
                x=float(self.target_tracker.state.position),
                confidence=max(0.36, self.target_tracker.state.confidence),
                width=8.0,
                source="track_grace",
            )
            self.target_post_bootstrap_grace -= 1
            self.target_tracker.last_update_debug = {
                "mode": "track_grace",
                "stage": "track",
                "reason": "post_bootstrap_grace",
                "measurement_x": float(target_measurement.x),
                "confidence": float(target_measurement.confidence),
            }
        elif target_measurement is not None and target_measurement.source not in {"projection_bootstrap"}:
            self.target_post_bootstrap_grace = max(0, self.target_post_bootstrap_grace - 1)
        control_measurement = self.detect_control_marker(roi_frame, roi, predicted_control_x)
        target_state = self.target_tracker.update(
            measurement=target_measurement,
            dt_ms=dt_ms,
            lane=lane_rect,
            gate_px=self.config.target_gate_px,
            max_jump_px=self.config.target_max_jump_px,
        )
        if not target_state.has_lock and phase == "TRACK_TARGET":
            self.target_phase = "SEARCH_TARGET"
            self.target_bootstrap_candidates.clear()
            self.target_tracker.last_update_debug = {
                "mode": "rebootstrap",
                "stage": "bootstrap",
                "reason": "lost_lock",
            }
        if bar_measurement is not None:
            control_measurement = bar_measurement
        bar_state = self.update_bar(measurement=control_measurement, dt_ms=dt_ms, lane=lane_rect)
        decision = self.controller.decide(now_ms=now_ms, target_state=target_state, bar_state=bar_state, lane=lane_rect)
        border_conf = 0.0
        if border_abs is not None:
            aspect = float(border_abs.w) / float(max(border_abs.h, 1))
            aspect_score = min(1.0, aspect / 10.0)
            width_score = min(1.0, border_abs.w / max(60.0, float(lane_rect.w) * 0.55))
            border_conf = max(0.0, min(1.0, (0.65 * width_score) + (0.35 * aspect_score)))
        inner_conf = 0.0
        if roi_frame.size != 0:
            gray_roi = self.cv2.cvtColor(roi_frame, self.cv2.COLOR_BGR2GRAY)
            bright_ratio = float(self.np.count_nonzero(gray_roi > 120)) / float(gray_roi.size)
            dark_ratio = float(self.np.count_nonzero(gray_roi < self.config.target_dark_max)) / float(gray_roi.size)
            inner_conf = max(0.0, min(1.0, (0.75 * bright_ratio) + min(0.25, dark_ratio * 3.0)))
        control_conf = control_measurement.confidence if control_measurement is not None else 0.0
        active_conf = (
            (0.35 * border_conf)
            + (0.20 * inner_conf)
            + (0.20 * control_conf)
            + (0.25 * target_state.confidence)
        )
        return FrameReport(
            ok=decision is not None,
            border=border_abs,
            roi=roi,
            target_measurement=target_measurement,
            control_measurement=control_measurement,
            target_state=target_state,
            bar_state=bar_state,
            decision=decision,
            target_visible=target_measurement is not None,
            border_confidence=border_conf,
            inner_confidence=inner_conf,
            control_confidence=control_conf,
            active_confidence=active_conf,
            debug_mask=debug_mask,
        )
