const home = document.getElementById("home");
const waitingScreen = document.getElementById("waitingScreen");
const ringBtn = document.getElementById("ringBtn");
const cancelBtn = document.getElementById("cancelBtn");
const phoneNumberInput = document.getElementById("phoneNumber");
const delaySelect = document.getElementById("delaySelect");
const statusEl = document.getElementById("status");
const countdownEl = document.getElementById("countdown");
const waitingLabel = document.getElementById("waitingLabel");
const waitingSub = document.getElementById("waitingSub");

const STORAGE_KEY = "attention-seeker-real-call-v1";

let delayTimer = null;
let countdownTimer = null;
let aborted = false;

function loadSettings() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const data = JSON.parse(raw);
    if (data.phone) phoneNumberInput.value = data.phone;
    if (data.delay != null) delaySelect.value = String(data.delay);
  } catch {
    /* ignore */
  }
}

function saveSettings() {
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      phone: phoneNumberInput.value,
      delay: delaySelect.value,
    })
  );
}

function setStatus(message, kind = "") {
  statusEl.textContent = message;
  statusEl.classList.remove("is-error", "is-ok");
  if (kind) statusEl.classList.add(kind);
}

function normalizePhone(raw) {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  const keepPlus = trimmed.startsWith("+");
  const digits = trimmed.replace(/[^\d]/g, "");
  return keepPlus ? `+${digits}` : digits;
}

function showWaiting(seconds) {
  home.hidden = true;
  waitingScreen.hidden = false;
  if (seconds > 0) {
    waitingLabel.textContent = "Real call in";
    waitingSub.textContent = "Lock the phone. Look ignored.";
    countdownEl.textContent = String(seconds);
  } else {
    waitingLabel.textContent = "Calling your phone";
    waitingSub.textContent = "Your real ringtone should start any second.";
    countdownEl.textContent = "…";
  }
}

function hideWaiting() {
  waitingScreen.hidden = true;
  home.hidden = false;
}

function clearTimers() {
  if (delayTimer) {
    clearTimeout(delayTimer);
    delayTimer = null;
  }
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
}

function cancelFlow() {
  aborted = true;
  clearTimers();
  ringBtn.disabled = false;
  hideWaiting();
  setStatus("Cancelled.");
}

async function placeRealCall(phone) {
  const res = await fetch("/api/call", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to: phone }),
  });

  let payload = {};
  try {
    payload = await res.json();
  } catch {
    payload = {};
  }

  if (!res.ok) {
    const detail = payload.error || `Call failed (${res.status})`;
    throw new Error(detail);
  }

  return payload;
}

async function startRealCall() {
  aborted = false;
  saveSettings();
  setStatus("");

  const phone = normalizePhone(phoneNumberInput.value);
  if (!phone || phone.replace(/\D/g, "").length < 8) {
    setStatus("Enter a valid phone number with country code.", "is-error");
    phoneNumberInput.focus();
    return;
  }

  // Store with + if user omitted it but included country code length — still require + for clarity
  if (!phone.startsWith("+")) {
    setStatus("Add your country code with + (example: +91…).", "is-error");
    phoneNumberInput.focus();
    return;
  }

  const delaySec = Number(delaySelect.value) || 0;
  ringBtn.disabled = true;
  showWaiting(delaySec);

  if (delaySec > 0) {
    let left = delaySec;
    countdownEl.textContent = String(left);
    countdownTimer = window.setInterval(() => {
      left -= 1;
      if (left <= 0) {
        clearInterval(countdownTimer);
        countdownTimer = null;
        countdownEl.textContent = "…";
        waitingLabel.textContent = "Calling your phone";
        waitingSub.textContent = "Your real ringtone should start any second.";
        return;
      }
      countdownEl.textContent = String(left);
    }, 1000);

    await new Promise((resolve) => {
      delayTimer = window.setTimeout(resolve, delaySec * 1000);
    });
  }

  if (aborted) return;

  waitingLabel.textContent = "Calling your phone";
  waitingSub.textContent = "Your real ringtone should start any second.";
  countdownEl.textContent = "…";

  try {
    const result = await placeRealCall(phone);
    if (aborted) return;
    setStatus(
      `Real call placed${result.sid ? ` (${result.sid.slice(0, 10)}…)` : ""}. Answer when it rings.`,
      "is-ok"
    );
    hideWaiting();
  } catch (err) {
    if (aborted) return;
    hideWaiting();
    setStatus(err.message || "Could not place call.", "is-error");
  } finally {
    ringBtn.disabled = false;
    clearTimers();
  }
}

ringBtn.addEventListener("click", () => {
  startRealCall();
});

cancelBtn.addEventListener("click", cancelFlow);
phoneNumberInput.addEventListener("change", saveSettings);
phoneNumberInput.addEventListener("input", saveSettings);
delaySelect.addEventListener("change", saveSettings);

loadSettings();

fetch("/api/health")
  .then((r) => r.json())
  .then((data) => {
    if (!data.twilioConfigured) {
      setStatus(
        "Server is up, but Twilio is not configured. Add credentials to .env — see README.",
        "is-error"
      );
    }
  })
  .catch(() => {
    setStatus(
      "Start the real-call server: py server.py — fake static hosting can’t place phone calls.",
      "is-error"
    );
  });
