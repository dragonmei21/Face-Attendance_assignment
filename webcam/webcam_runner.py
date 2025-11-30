from __future__ import annotations

import cv2

from core.system import ClassAttendanceSystem


FRAME_SKIP = 5  # process every Nth frame for performance


def start_webcam_recognition(frame_skip: int = FRAME_SKIP) -> None:
    print("Opening webcam…")
    system = ClassAttendanceSystem()
    cap = cv2.VideoCapture(0)
    print("cap.isOpened():", cap.isOpened())
    if not cap.isOpened():
        raise RuntimeError("Cannot open webcam")

    frame_count = 0
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            display_frame = frame.copy()
            if frame_count % frame_skip == 0:
                results = _process_frame(system, frame)
                _display_results(display_frame, results)
            else:
                cv2.imshow("Attendance", display_frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("s"):
                cv2.imwrite("frame_capture.jpg", frame)
            frame_count += 1
    finally:
        cap.release()
        cv2.destroyAllWindows()


def _process_frame(system: ClassAttendanceSystem, frame):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = system.recognize_frame(rgb_frame)
    for result in results:
        if result["user_id"] != "Unknown":
            system.log_attendance(result["user_id"], source="webcam")
    return results


def _display_results(frame, results):
    for result in results:
        top, right, bottom, left = result["bbox"]
        color = (0, 255, 0) if result["user_id"] != "Unknown" else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        label = f"{result['user_id']} ({result['distance']:.2f})"
        cv2.putText(frame, label, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    cv2.imshow("Attendance", frame)
if __name__ == "__main__":
    start_webcam_recognition()