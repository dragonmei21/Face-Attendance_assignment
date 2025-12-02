const videoEl = document.getElementById("webcam");
const overlay = document.getElementById("overlay");
const statusChip = document.getElementById("statusChip");
const countdownChip = document.getElementById("countdownChip");
const nameInput = document.getElementById("visitorName");
const enrollBtn = document.getElementById("enrollBtn");

const captureCanvas = document.createElement("canvas");
const captureCtx = captureCanvas.getContext("2d");
const overlayCtx = overlay.getContext("2d");

let latestSnapshotBlob = null;
let recognitionInterval = null;
let isRecognizing = false;
let lastResults = [];

async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: "user",
      },
      audio: false,
    });
    videoEl.srcObject = stream;
    await videoEl.play();
    resizeCanvases();
    videoEl.addEventListener("loadedmetadata", resizeCanvases);
    setStatus("Camera ready — please center yourself", "success");
    startRecognitionLoop();
  } catch (error) {
    console.error(error);
    setStatus("Please allow camera access to continue", "warning");
  }
}

function resizeCanvases() {
  const width = videoEl.videoWidth || 1280;
  const height = videoEl.videoHeight || 720;
  captureCanvas.width = width;
  captureCanvas.height = height;
  overlay.width = width;
  overlay.height = height;
}

function startRecognitionLoop() {
  if (recognitionInterval) {
    clearInterval(recognitionInterval);
  }
  recognitionInterval = setInterval(recognizeFrame, 2500);
  recognizeFrame(); // kick off immediately
}

async function captureFrameBlob() {
  if (!videoEl.videoWidth || !videoEl.videoHeight) {
    throw new Error("Camera not ready");
  }
  captureCtx.drawImage(videoEl, 0, 0, captureCanvas.width, captureCanvas.height);
  return new Promise((resolve) => captureCanvas.toBlob(resolve, "image/jpeg", 0.92));
}

async function recognizeFrame() {
  if (isRecognizing) return;
  try {
    isRecognizing = true;
    const blob = await captureFrameBlob();
    if (!blob) {
      throw new Error("Unable to capture frame");
    }
    latestSnapshotBlob = blob;
    const formData = new FormData();
    formData.append("image", blob, "frame.jpg");
    const response = await fetch("/recognize", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || "Recognition failed");
    }
    const payload = await response.json();
    lastResults = payload.results || [];
    renderDetections(lastResults);
    updateUIState(payload);
  } catch (error) {
    console.error(error);
    setStatus(error.message, "warning");
  } finally {
    isRecognizing = false;
  }
}

function renderDetections(results) {
  overlayCtx.clearRect(0, 0, overlay.width, overlay.height);
  results.forEach((face) => {
    const [top, right, bottom, left] = face.bbox;
    const width = right - left;
    const height = bottom - top;
    overlayCtx.strokeStyle = face.user_id === "Unknown" ? "#ff5c70" : "#2ae98d";
    overlayCtx.lineWidth = 3;
    overlayCtx.strokeRect(left, top, width, height);
    overlayCtx.font = "18px Montserrat";
    overlayCtx.fillStyle = "rgba(0, 0, 0, 0.6)";
    overlayCtx.fillRect(left, top - 28, overlayCtx.measureText(face.user_id).width + 16, 24);
    overlayCtx.fillStyle = "white";
    overlayCtx.fillText(face.user_id, left + 8, top - 10);
  });
}

function updateUIState(payload) {
  const known = lastResults.filter((result) => result.user_id !== "Unknown");
  const unknown = lastResults.some((result) => result.user_id === "Unknown");

  if (known.length) {
    const names = known.map((face) => face.user_id).join(", ");
    setStatus(`Welcome back, ${names}!`, "success");
  } else if (unknown) {
    setStatus("Not recognized yet — enter your name below.", "warning");
  } else if (lastResults.length === 0) {
    setStatus("Step closer and hold still for the camera.", "warning");
  }

  updateEnrollButtonState();
}

function updateEnrollButtonState() {
  const inputReady = nameInput.value.trim().length >= 2;
  const hasUnknownFace = lastResults.some((face) => face.user_id === "Unknown");
  enrollBtn.disabled = !(inputReady && hasUnknownFace);
}

nameInput.addEventListener("input", () => updateEnrollButtonState());

enrollBtn.addEventListener("click", async () => {
  if (enrollBtn.disabled) return;
  try {
    setStatus("Enrolling your profile…", "warning");
    const blob = latestSnapshotBlob || (await captureFrameBlob());
    const formData = new FormData();
    formData.append("name", nameInput.value.trim());
    formData.append("image", blob, "enroll.jpg");
    const response = await fetch("/enroll", {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.detail || "Enrollment failed");
    }
    const payload = await response.json();
    nameInput.value = "";
    updateEnrollButtonState();
    setStatus(payload.message || "Enrollment complete!", "success");
    renderDetections([]); // clear boxes to avoid stale unknown overlay
  } catch (error) {
    console.error(error);
    setStatus(error.message, "warning");
  }
});

function setStatus(message, state = "neutral") {
  statusChip.textContent = message;
  statusChip.classList.remove("status-chip--success", "status-chip--warning");
  if (state === "success") statusChip.classList.add("status-chip--success");
  if (state === "warning") statusChip.classList.add("status-chip--warning");
}

initCamera();

