from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import numpy as np

from jarvis.state import event_bus
from jarvis.utils.logging import get_logger

log = get_logger("vision.gesture")

# Landmark indices (Mediapipe Hands, 21 points per hand).
WRIST = 0
THUMB_TIP = 4
INDEX_TIP, INDEX_PIP = 8, 6
MIDDLE_TIP, MIDDLE_PIP = 12, 10
RING_TIP, RING_PIP = 16, 14
PINKY_TIP, PINKY_PIP = 20, 18

CURSOR_SMOOTHING = 0.35  # lower = smoother/laggier, higher = snappier/jittery
PINCH_THRESHOLD = 0.06  # normalized hand-frame distance, thumb tip <-> index tip
CLICK_REFRACTORY_S = 0.6  # min gap between discrete clicks (fist / point) so a held
# gesture doesn't fire repeatedly
SWIPE_REFRACTORY_S = 0.8
SWIPE_TRIGGER_DIST = 0.18  # normalized frame-width fraction to count as a swipe


def _finger_curled(landmarks, tip_idx: int, pip_idx: int) -> bool:
    # A curled finger's tip sits closer to the wrist than its own PIP joint does.
    wrist = landmarks[WRIST]
    tip = landmarks[tip_idx]
    pip = landmarks[pip_idx]
    d_tip = (tip.x - wrist.x) ** 2 + (tip.y - wrist.y) ** 2
    d_pip = (pip.x - wrist.x) ** 2 + (pip.y - wrist.y) ** 2
    return d_tip < d_pip


@dataclass
class HandState:
    fist: bool
    index_only: bool
    two_finger: bool
    pinching: bool
    index_x: float
    index_y: float
    two_finger_mid_x: float
    two_finger_mid_y: float


def _classify(landmarks) -> HandState:
    index_curled = _finger_curled(landmarks, INDEX_TIP, INDEX_PIP)
    middle_curled = _finger_curled(landmarks, MIDDLE_TIP, MIDDLE_PIP)
    ring_curled = _finger_curled(landmarks, RING_TIP, RING_PIP)
    pinky_curled = _finger_curled(landmarks, PINKY_TIP, PINKY_PIP)

    fist = index_curled and middle_curled and ring_curled and pinky_curled
    index_only = (not index_curled) and middle_curled and ring_curled and pinky_curled
    two_finger = (not index_curled) and (not middle_curled) and ring_curled and pinky_curled

    thumb = landmarks[THUMB_TIP]
    index = landmarks[INDEX_TIP]
    pinch_dist = ((thumb.x - index.x) ** 2 + (thumb.y - index.y) ** 2) ** 0.5

    middle = landmarks[MIDDLE_TIP]
    return HandState(
        fist=fist,
        index_only=index_only,
        two_finger=two_finger,
        pinching=pinch_dist < PINCH_THRESHOLD,
        index_x=index.x,
        index_y=index.y,
        two_finger_mid_x=(index.x + middle.x) / 2,
        two_finger_mid_y=(index.y + middle.y) / 2,
    )


class GestureController:
    """Camera -> Mediapipe Hands -> cursor/click/scroll/tab-switch mapping.
    Runs its own capture+inference loop on a background thread; start()/stop()
    are cheap and idempotent so tool calls can freely toggle the mode."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._stop_flag = threading.Event()
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> str:
        with self._lock:
            if self.is_running:
                return "El kontrolü zaten açık."
            self._stop_flag.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return "El kontrolüne geçildi. Kamerayı izliyorum."

    def stop(self) -> str:
        with self._lock:
            if not self.is_running:
                return "El kontrolü zaten kapalı."
            self._stop_flag.set()
            thread = self._thread
        if thread:
            thread.join(timeout=3)
        return "El kontrolü kapatıldı, fare/klavyeyi normal kullanabilirsin."

    def _run(self) -> None:
        import cv2
        import mediapipe as mp
        import pyautogui

        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        screen_w, screen_h = pyautogui.size()
        cursor_x, cursor_y = pyautogui.position()

        # Two hands tracked so the in-app skeleton overlay (see
        # gesture_landmarks events -> frontend GestureOverlay) shows both when
        # present, but only the first-detected hand ever drives the cursor/
        # clicks — two hands fighting over one pointer would be unusable.
        hands = mp.solutions.hands.Hands(
            max_num_hands=2, min_detection_confidence=0.6, min_tracking_confidence=0.5
        )

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            log.error("could not open camera for gesture control")
            return

        last_click_t = 0.0
        last_swipe_t = 0.0
        was_pinching = False
        swipe_anchor: tuple[float, float] | None = None

        log.info("gesture control loop started")
        try:
            while not self._stop_flag.is_set():
                ok, frame = cap.read()
                if not ok:
                    time.sleep(0.05)
                    continue

                frame = cv2.flip(frame, 1)  # mirror, so hand-left = cursor-left
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)

                # Skeleton lines rendered inside the Jarvis window itself (see
                # GestureOverlay.tsx) instead of a separate OS window — just the
                # 21 normalized (x, y) points per hand, cheap enough to send
                # over the websocket every frame.
                if result.multi_hand_landmarks:
                    event_bus.emit_threadsafe(
                        "gesture_landmarks",
                        {
                            "hands": [
                                [{"x": lm.x, "y": lm.y} for lm in hand.landmark]
                                for hand in result.multi_hand_landmarks
                            ]
                        },
                    )
                else:
                    event_bus.emit_threadsafe("gesture_landmarks", {"hands": []})
                    was_pinching = False
                    swipe_anchor = None
                    time.sleep(0.01)
                    continue

                state = _classify(result.multi_hand_landmarks[0].landmark)
                now = time.monotonic()

                # cursor follows the index fingertip while nothing else is happening
                target_x = state.index_x * screen_w
                target_y = state.index_y * screen_h
                cursor_x += (target_x - cursor_x) * CURSOR_SMOOTHING
                cursor_y += (target_y - cursor_y) * CURSOR_SMOOTHING

                if state.pinching:
                    if not was_pinching:
                        pyautogui.mouseDown()
                        was_pinching = True
                    pyautogui.moveTo(cursor_x, cursor_y)
                else:
                    if was_pinching:
                        pyautogui.mouseUp()
                        was_pinching = False

                    pyautogui.moveTo(cursor_x, cursor_y)

                    if state.fist and now - last_click_t > CLICK_REFRACTORY_S:
                        pyautogui.click(button="left")
                        last_click_t = now
                    elif state.index_only and now - last_click_t > CLICK_REFRACTORY_S:
                        pyautogui.click(button="right")
                        last_click_t = now
                    elif state.two_finger:
                        if swipe_anchor is None:
                            swipe_anchor = (state.two_finger_mid_x, state.two_finger_mid_y)
                        elif now - last_swipe_t > SWIPE_REFRACTORY_S:
                            dx = state.two_finger_mid_x - swipe_anchor[0]
                            dy = state.two_finger_mid_y - swipe_anchor[1]
                            if abs(dx) > SWIPE_TRIGGER_DIST and abs(dx) > abs(dy):
                                if dx < 0:
                                    pyautogui.hotkey("command", "alt", "left")  # prev tab
                                else:
                                    pyautogui.hotkey("command", "alt", "right")  # next tab
                                last_swipe_t = now
                                swipe_anchor = None
                            elif abs(dy) > SWIPE_TRIGGER_DIST:
                                pyautogui.scroll(600 if dy < 0 else -600)
                                last_swipe_t = now
                                swipe_anchor = None
                    else:
                        swipe_anchor = None

                time.sleep(0.01)
        finally:
            cap.release()
            hands.close()
            event_bus.emit_threadsafe("gesture_landmarks", {"hands": []})
            if was_pinching:
                pyautogui.mouseUp()
            log.info("gesture control loop stopped")


controller = GestureController()
