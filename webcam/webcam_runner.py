from __future__ import annotations

from typing import List, Dict, Optional, Set, Tuple
import time

import cv2
import numpy as np

from core.system import ClassAttendanceSystem


FRAME_SKIP = 5  # process every Nth frame for performance
UNKNOWN_PROMPT_COOLDOWN = 5  # seconds
BLUR_THRESHOLD = 250.0  # Laplacian variance threshold
MAX_FACES = 1
STILLNESS_SECONDS = 3.0
AUTO_EXIT_DELAY = 5  # seconds after success before closing webcam


def start_webcam_recognition(frame_skip: int = FRAME_SKIP) -> None:
    print("Opening webcam…")
    system = ClassAttendanceSystem()
    cap = cv2.VideoCapture(0)
    print("cap.isOpened():", cap.isOpened())
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam")

    frame_count = 0
    logged_users: Set[str] = set()
    last_prompt_time = 0.0
    pending_face: Optional[np.ndarray] = None
    results: List[Dict] = []
    warning_message: Optional[str] = None
    is_blurry = False
    stillness_start: Optional[float] = None
    multi_face_detected = False
    success_time: Optional[float] = None
    last_sharpness: Optional[float] = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            display_frame = frame.copy()
            shutdown_eta: Optional[float] = None
            current_sharpness: Optional[float] = None
            if frame_count % frame_skip == 0:
                current_sharpness = _sharpness_score(frame)
                last_sharpness = current_sharpness
                is_blurry = current_sharpness < BLUR_THRESHOLD
                now = time.time()
                if is_blurry:
                    multi_face_detected = False
                    results = []
                    warning_message = (
                        "DO NOT MOVE MUCH"
                        if current_sharpness is None
                        else f"DO NOT MOVE MUCH (sharpness {current_sharpness:.0f})"
                    )
                    pending_face = None
                    stillness_start = None
                else:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = system.recognize_frame(rgb_frame)
                    face_count = len(results)
                    if face_count == 0:
                        multi_face_detected = False
                        warning_message = None
                        stillness_start = None
                        pending_face = None
                    elif face_count > MAX_FACES:
                        multi_face_detected = True
                        warning_message = "ONE PERSON AT A TIME"
                        pending_face = None
                        stillness_start = None
                        results = []
                    else:
                        multi_face_detected = False
                        warning_message = None
                        if _log_recognitions(system, results, logged_users):
                            success_time = now
                        if _contains_unknown(results):
                            stillness_start = stillness_start or now
                            elapsed = now - stillness_start
                            if elapsed < STILLNESS_SECONDS:
                                warning_message = f"HOLD STILL {STILLNESS_SECONDS - elapsed:.1f}s"
                            elif pending_face is None:
                                pending_face = _capture_unknown_face(frame, results)
                        else:
                            stillness_start = None
                            pending_face = None

            if success_time is not None:
                shutdown_eta = max(0.0, AUTO_EXIT_DELAY - (time.time() - success_time))

            _display_results(
                display_frame,
                results,
                warning_message,
                shutdown_eta,
                last_sharpness,
            )

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                cv2.imwrite("frame_capture.jpg", frame)

            if not is_blurry and not multi_face_detected:
                pending_face, last_prompt_time, enrolled = _maybe_prompt_for_enrollment(
                    system, pending_face, last_prompt_time
                )
                if enrolled:
                    success_time = time.time()

            if success_time is not None and time.time() - success_time >= AUTO_EXIT_DELAY:
                print("[INFO] Auto-stopping webcam after successful recognition/enrollment.")
                break
            frame_count += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()


def _capture_unknown_face(frame, results: List[Dict]) -> Optional[np.ndarray]:
    for result in results:
        if result["user_id"] != "Unknown":
            continue
        face_roi = _extract_face_roi(frame, result["bbox"])
        if face_roi is not None:
            return face_roi
    return None


def _maybe_prompt_for_enrollment(
    system: ClassAttendanceSystem,
    pending_face: Optional[np.ndarray],
    last_prompt_time: float,
) -> Tuple[Optional[np.ndarray], float, bool]:
    if pending_face is None:
        return None, last_prompt_time, False

    now = time.time()
    if now - last_prompt_time < UNKNOWN_PROMPT_COOLDOWN:
        return pending_face, last_prompt_time, False

    user_id = input("Unknown face detected. Enter a name to enroll (blank to skip): ").strip()
    if not user_id:
        print("[INFO] Skipped enrollment; no name entered.")
        return pending_face, now, False

    try:
        system.enroll_user(user_id, pending_face)
        print(f"[INFO] Enrolled new user '{user_id}'.")
        return None, now, True
    except Exception as exc:
        print(f"[ERROR] Failed to enroll user: {exc}")
        return pending_face, now, False


def _extract_face_roi(frame, bbox, padding: int = 20) -> Optional:
    top, right, bottom, left = bbox
    height, width = frame.shape[:2]
    top = max(0, top - padding)
    bottom = min(height, bottom + padding)
    left = max(0, left - padding)
    right = min(width, right + padding)
    if top >= bottom or left >= right:
        return None
    return frame[top:bottom, left:right]


def _sharpness_score(frame: np.ndarray) -> float:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(variance)


def _contains_unknown(results: List[Dict]) -> bool:
    return any(result["user_id"] == "Unknown" for result in results)


def _contains_multiple_faces(results: List[Dict]) -> bool:
    return len(results) > MAX_FACES


def _log_recognitions(system: ClassAttendanceSystem, results: List[Dict], logged_users: Set[str]) -> bool:
    logged_any = False
    for result in results:
        user_id = result["user_id"]
        if user_id == "Unknown":
            continue
        if user_id in logged_users:
            continue
        if system.log_attendance(user_id, source="webcam"):
            logged_users.add(user_id)
            print(f"[INFO] Logged attendance for {user_id}")
            logged_any = True
    return logged_any


def _display_results(
    frame,
    results,
    warning_message: Optional[str] = None,
    shutdown_eta: Optional[float] = None,
    sharpness_value: Optional[float] = None,
):
    recognized = any(result["user_id"] != "Unknown" for result in results)
    for result in results:
        top, right, bottom, left = result["bbox"]
        color = (0, 255, 0) if result["user_id"] != "Unknown" else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        label = f"{result['user_id']} ({result['distance']:.2f})"
        cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    if recognized:
        cv2.putText(
            frame,
            "RECOGNIZED",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
    if warning_message:
        _draw_warning(frame, warning_message)
    if shutdown_eta is not None:
        _draw_shutdown_countdown(frame, shutdown_eta)
    if sharpness_value is not None:
        _draw_sharpness(frame, sharpness_value)
    cv2.imshow("Attendance", frame)


def _draw_warning(frame, message: str) -> None:
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.9
    thickness = 2
    padding = 10
    x, y = 20, 70
    text_size, baseline = cv2.getTextSize(message, font, scale, thickness)
    top_left = (x - padding, y - text_size[1] - padding)
    bottom_right = (x + text_size[0] + padding, y + baseline + padding)
    cv2.rectangle(frame, top_left, bottom_right, (0, 0, 255), thickness=-1)
    cv2.putText(frame, message, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)


def _draw_shutdown_countdown(frame, eta: float) -> None:
    remaining = max(0.0, eta)
    message = f"Closing in {remaining:.1f}s"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.7
    thickness = 2
    x, y = 20, 110
    cv2.putText(frame, message, (x, y), font, scale, (0, 255, 255), thickness, cv2.LINE_AA)


def _draw_sharpness(frame, value: float) -> None:
    message = f"Sharpness {value:.0f} / {BLUR_THRESHOLD:.0f}"
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.6
    thickness = 2
    text_size, _ = cv2.getTextSize(message, font, scale, thickness)
    x = frame.shape[1] - text_size[0] - 20
    y = 35
    cv2.putText(frame, message, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)


if __name__ == "__main__":
    start_webcam_recognition()