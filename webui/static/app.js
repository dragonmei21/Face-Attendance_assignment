const videoEl = document.getElementById("webcam");
const overlay = document.getElementById("overlay");
const statusChip = document.getElementById("statusChip");
const countdownChip = document.getElementById("countdownChip");
const nameInput = document.getElementById("visitorName");
const enrollBtn = document.getElementById("enrollBtn");
const downloadBtn = document.getElementById("downloadBtn");

const captureCanvas = document.createElement("canvas");
const captureCtx = captureCanvas.getContext("2d");
const overlayCtx = overlay.getContext("2d");

const BLUR_THRESHOLD = 150;  // Lowered from 250 for better lighting compatibility
const HOLD_STILL_SECONDS = 3;

let latestSnapshotBlob = null;
let recognitionInterval = null;
let isRecognizing = false;
let lastResults = [];
let lastSharpness = 0;
let unknownHoldStart = null;

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

async function captureFrame() {
  if (!videoEl.videoWidth || !videoEl.videoHeight) {
    throw new Error("Camera not ready");
  }
  captureCtx.drawImage(videoEl, 0, 0, captureCanvas.width, captureCanvas.height);
  const sharpness = measureSharpness(captureCtx.getImageData(0, 0, captureCanvas.width, captureCanvas.height));
  lastSharpness = sharpness;
  return new Promise((resolve) =>
    captureCanvas.toBlob((blob) => resolve({ blob, sharpness }), "image/jpeg", 0.92)
  );
}

async function recognizeFrame() {
  if (isRecognizing) return;
  try {
    isRecognizing = true;
    const { blob, sharpness } = await captureFrame();
    if (!blob) {
      throw new Error("Unable to capture frame");
    }
    if (sharpness < BLUR_THRESHOLD) {
      lastResults = [];
      renderDetections([]);
      showBlurWarning(sharpness);
      return;
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
  const now = performance.now();

  if (known.length) {
    const names = known.map((face) => face.user_id).join(", ");
    unknownHoldStart = null;
    hideCountdown();
    setStatus(`RECOGNIZED — welcome back, ${names}!`, "success");
    
    // Log to Cloud Computing course (Lambda will check time window)
    known.forEach((face) => {
      logCloudComputingAttendance(face.user_id);
    });
  } else if (unknown) {
    if (!unknownHoldStart) {
      unknownHoldStart = now;
    }
    const elapsed = (now - unknownHoldStart) / 1000;
    const remaining = Math.max(0, HOLD_STILL_SECONDS - elapsed);
    if (remaining > 0) {
      showCountdown(`Hold still ${remaining.toFixed(1)}s`);
      setStatus(`HOLD STILL ${remaining.toFixed(1)}s`, "warning");
    } else {
      showCountdown("Captured — enter your name");
      setStatus("Unknown face captured — enter your name below.", "warning");
    }
  } else if (lastResults.length === 0) {
    unknownHoldStart = null;
    hideCountdown();
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
  const originalLabel = enrollBtn.textContent;
  enrollBtn.disabled = true;
  enrollBtn.textContent = "Uploading…";
  try {
    setStatus("Uploading securely to Esade Cloud…", "warning");
    const blob = latestSnapshotBlob || (await captureFrame()).blob;
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
    setStatus(payload.message || "Enrollment stored in the cloud!", "success");
    renderDetections([]); // clear boxes to avoid stale unknown overlay
  } catch (error) {
    console.error(error);
    setStatus(error.message, "warning");
  } finally {
    enrollBtn.textContent = originalLabel;
    updateEnrollButtonState();
  }
});

function setStatus(message, state = "neutral") {
  statusChip.textContent = message;
  statusChip.classList.remove("status-chip--success", "status-chip--warning");
  if (state === "success") statusChip.classList.add("status-chip--success");
  if (state === "warning") statusChip.classList.add("status-chip--warning");
}

function showCountdown(text) {
  countdownChip.hidden = false;
  countdownChip.textContent = text;
}

function hideCountdown() {
  countdownChip.hidden = true;
  countdownChip.textContent = "";
}

function showBlurWarning(sharpness) {
  setStatus(
    `DO NOT MOVE MUCH • sharpness ${Math.round(sharpness)}/${BLUR_THRESHOLD}`,
    "warning"
  );
  hideCountdown();
}

function measureSharpness(imageData) {
  const { data, width, height } = imageData;
  const step = 6;
  let sum = 0;
  let count = 0;
  for (let y = step; y < height - step; y += step) {
    for (let x = step; x < width - step; x += step) {
      const lap = laplacianAt(data, width, x, y);
      sum += lap * lap;
      count += 1;
    }
  }
  if (!count) return 0;
  return sum / count;
}

function laplacianAt(data, width, x, y) {
  const center = getGray(data, width, x, y);
  const left = getGray(data, width, x - 1, y);
  const right = getGray(data, width, x + 1, y);
  const up = getGray(data, width, x, y - 1);
  const down = getGray(data, width, x, y + 1);
  return left + right + up + down - 4 * center;
}

function getGray(data, width, x, y) {
  const idx = (y * width + x) * 4;
  const r = data[idx];
  const g = data[idx + 1];
  const b = data[idx + 2];
  return 0.299 * r + 0.587 * g + 0.114 * b;
}

// Lambda function call for Cloud Computing course attendance
async function logCloudComputingAttendance(userId) {
  // Lambda API Gateway endpoint for Cloud Computing course time-gated attendance
  const LAMBDA_ENDPOINT = "https://8gabwdm8ta.execute-api.eu-north-1.amazonaws.com/prod/CloudComputingAttendanceGate";
  
  try {
    const response = await fetch(LAMBDA_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ face_id: userId, source: "web-ui" })
    });
    
    const result = await response.json();
    
    if (response.ok) {
      console.log("✓ Cloud Computing attendance logged:", result.message);
    } else {
      console.warn("⚠ Lambda attendance:", result.error || result.message);
    }
  } catch (err) {
    console.error("✗ Lambda attendance failed:", err);
  }
}

// Download button handler
if (downloadBtn) {
  console.log("✓ Download button found and wired up");
  downloadBtn.addEventListener("click", async () => {
    console.log("🔽 Download button clicked!");
    const today = new Date().toISOString().slice(0, 10).replace(/-/g, ""); // YYYYMMDD
    const url = `/download/cloud-computing?session_date=${today}`;
    console.log("📡 Fetching:", url);
    
    try {
      setStatus("Downloading attendance...", "warning");
      const response = await fetch(url);
      console.log("📥 Response status:", response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error("❌ Server error:", errorText);
        throw new Error(`Failed to download: ${response.statusText}`);
      }
      
      const blob = await response.blob();
      console.log("📦 Blob size:", blob.size, "bytes");
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `CloudComputing_Attendance_${today}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
      console.log("✅ CSV download triggered!");
      
      setStatus("✓ Attendance downloaded", "success");
      setTimeout(() => setStatus("Camera ready — please center yourself", "success"), 2000);
    } catch (err) {
      console.error("❌ Download failed:", err);
      setStatus("✗ Download failed: " + err.message, "warning");
      setTimeout(() => setStatus("Camera ready — please center yourself", "success"), 3000);
    }
  });
} else {
  console.error("❌ Download button not found! Check HTML id='downloadBtn'");
}

initCamera();

