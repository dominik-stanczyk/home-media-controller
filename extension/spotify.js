
console.log("Spotify Remote: Loading successful");

function parseTimeToSeconds(str) {
  if (!str) return 0;
  const parts = str.trim().split(":").map(Number);

  if (parts.some(n => !Number.isFinite(n))) return 0;

  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];

  return 0;
}

// Znajdowanie przycisków Spotify
function getButton(type) {
  const selectors = {
    shuffle: [
      '[data-testid="control-button-shuffle"]',
      'button[aria-label*="Shuffle"]',
      'button[aria-label*="Losow"]'
    ],
    repeat: [
      '[data-testid="control-button-repeat"]',
      'button[aria-label*="repeat" i]',
      'button[aria-label*="powtarz" i]'
    ],
    playpause: [
      '[data-testid="control-button-playpause"]'
    ],
    next: [
      '[data-testid="control-button-skip-forward"]'
    ],
    prev: [
      '[data-testid="control-button-skip-back"]'
    ]
  };

  for (const selector of selectors[type] || []) {
    const element = document.querySelector(selector);
    if (element) return element;
  }

  return null;
}

function getButtonState(button) {
  if (!button) return false;

  const checked = button.getAttribute("aria-checked");
  const pressed = button.getAttribute("aria-pressed");

  return checked === "true" ||
         checked === "mixed" ||
         pressed === "true";
}

// VOLUME – natywny suwak Spotify
function setSpotifyVolume(targetFraction) {
  const value = Math.max(0, Math.min(1, Number(targetFraction)));
  if (!Number.isFinite(value)) return;

  const volBar = document.querySelector('[data-testid="volume-bar"]');
  if (!volBar) return;

  const slider = volBar.querySelector('input[type="range"]');
  if (slider) {
    const min = Number(slider.min || 0);
    const max = Number(slider.max || 100);
    const target = min + value * (max - min);

    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
    if (setter) {
      setter.call(slider, String(target));
      slider.dispatchEvent(new Event("input", { bubbles: true }));
      slider.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }

  // Natychmiastowe kliknięcie w pasek przez PointerEvent (React łapie to w 0 ms)
  const progressBar = volBar.querySelector('[data-testid="progress-bar"]') || volBar;
  const rect = progressBar.getBoundingClientRect();
  if (rect.width > 0) {
    const clientX = rect.left + rect.width * value;
    const clientY = rect.top + rect.height / 2;

    ["pointerdown", "mousedown", "pointerup", "mouseup", "click"].forEach((type) => {
      progressBar.dispatchEvent(
        new PointerEvent(type, {
          bubbles: true,
          cancelable: true,
          view: window,
          clientX,
          clientY,
          pointerId: 1,
          pointerType: "mouse",
        })
      );
    });
  }
}


function getSpotifyVolume() {
  const slider = document.querySelector(
    '[data-testid="volume-bar"] input[type="range"]'
  );

  if (!slider) return 0.15;

  const min = Number(slider.min || 0);
  const max = Number(slider.max || 100);

  return max > min
    ? (Number(slider.value) - min) / (max - min)
    : 0;
}
function getSpotifyVolume() {
  const slider = document.querySelector(
    '[data-testid="volume-bar"] input[type="range"]'
  );

  if (!slider) return 0.15;

  const min = Number(slider.min || 0);
  const max = Number(slider.max || 100);
  const current = Number(slider.value);

  return max > min
    ? (current - min) / (max - min)
    : 0;
}

// SHUFFLE
// Pomocnik: szuka przycisku Shuffle wyłącznie w dolnym pasku odtwarzacza
// SHUFFLE
function findSpotifyShuffleBtn() {
  const playerBar = document.querySelector('[data-testid="now-playing-bar"], footer') || document;
  return (
    playerBar.querySelector('[data-testid="control-button-shuffle"]') ||
    playerBar.querySelector('button[aria-label*="shuffle" i]') ||
    playerBar.querySelector('button[aria-label*="losow" i]')
  );
}

function isSpotifyShuffleOn(btn) {
  if (!btn) return false;
  const checked = btn.getAttribute("aria-checked");
  const pressed = btn.getAttribute("aria-pressed");
  const label = (btn.getAttribute("aria-label") || "").toLowerCase();

  return (
    checked === "true" ||
    checked === "mixed" ||
    pressed === "true" ||
    label.includes("wyłącz") ||
    label.includes("disable")
  );
}

function toggleShuffle() {
  const btn = findSpotifyShuffleBtn();
  if (!btn) return;
  btn.click();
  setTimeout(sendMetadata, 350);
}

// LOOP: przełącza bezpośrednio OFF <-> powtarzanie jednego utworu ("mixed")
function toggleLoop() {
  const btn = getButton("repeat");
  if (!btn) return;

  const state = btn.getAttribute("aria-checked");

  if (state === "false" || state === null) {
    // 1. kliknięcie włącza powtarzanie playlisty ("true"),
    // 2. kliknięcie po 200 ms przeskakuje na powtarzanie 1 utworu ("mixed")
    btn.click();
    setTimeout(() => {
      const updated = getButton("repeat");
      if (updated?.getAttribute("aria-checked") === "true") {
        updated.click();
      }
      setTimeout(sendMetadata, 200);
    }, 200);
  } else {
    // Z trybu "mixed" (lub "true") jedno kliknięcie wyłącza całkowicie ("false")
    btn.click();
    setTimeout(sendMetadata, 250);
  }
}


// METADATA
function sendMetadata() {
  if (!chrome.runtime?.id) return;

  const ms = navigator.mediaSession;
  const meta = ms?.metadata;

  const titleEl = document.querySelector(
    '[data-testid="context-item-info-title"] a, [data-testid="context-item-link"]'
  );

  const authorEls = document.querySelectorAll(
    '[data-testid="context-item-info-subtitles"] a, [data-testid="context-item-info-artist"]'
  );

  const title = meta?.title ||
    titleEl?.innerText?.trim() ||
    "Spotify";

  const author = meta?.artist ||
    (authorEls.length
      ? [...authorEls].map(el => el.innerText.trim()).join(", ")
      : "Spotify");

  const imgEl = document.querySelector(
    '[data-testid="cover-art-image"]'
  );

  const thumbnail =
    (meta?.artwork?.length
      ? meta.artwork[meta.artwork.length - 1].src
      : "") ||
    imgEl?.src ||
    "";

    const posEl = document.querySelector(
    '[data-testid="playback-position"], [data-testid="progress-bar-playback-position"]'
  );
  const durEl = document.querySelector(
    '[data-testid="playback-duration"], [data-testid="progress-bar-playback-duration"]'
  );

  // Fallback: jeśli brak widocznych liczników, pobierz czas z suwaka postępu
  const playbackSlider = document.querySelector('[data-testid="playback-progressbar"] input[type="range"]');
  
  let currentStr = posEl?.innerText?.trim() || "";
  let durationStr = durEl?.innerText?.trim() || "";

  if ((!currentStr || !durationStr) && playbackSlider) {
    const curSec = Math.floor(Number(playbackSlider.value || 0));
    const maxSec = Math.floor(Number(playbackSlider.max || 0));
    const fmt = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    if (!currentStr) currentStr = fmt(curSec);
    if (!durationStr) durationStr = fmt(maxSec);
  }

  currentStr = currentStr || "0:00";
  durationStr = durationStr || "0:00";
  const currentSec = parseTimeToSeconds(currentStr);
  const durationSec = parseTimeToSeconds(durationStr);

  const progress = durationSec > 0
    ? currentSec / durationSec * 100
    : 0;

  const playBtn = getButton("playpause");
  const label = (playBtn?.getAttribute("aria-label") || "").toLowerCase();

  let isPaused = true;

  if (ms?.playbackState && ms.playbackState !== "none") {
    isPaused = ms.playbackState !== "playing";
  } else {
    isPaused = !(
      label.includes("pause") ||
      label.includes("wstrzymaj") ||
      label.includes("pauz")
    );
  }

  const shuffleButton = findSpotifyShuffleBtn();
  const isShuffleActive = isSpotifyShuffleOn(shuffleButton);

  const repeat = getButton("repeat");
  const repeatState = repeat?.getAttribute("aria-checked");
  // Świeci na zielono tylko wtedy, gdy aktywne jest powtarzanie jednego utworu ("mixed")
  const isLoopOneActive = repeatState === "mixed";


  const data = {
    type: "METADATA",
    source: "spotify",
    title,
    author,
    progress,
    thumbnail,
    timeStr: `${currentStr} / ${durationStr}`,
    paused: isPaused,
    volume: getSpotifyVolume(),
    shuffle: isShuffleActive,
    loop: isLoopOneActive,
    accentColor: "#1ed760"
  };

  chrome.runtime.sendMessage(data).catch(() => {});
}

// Aktualizacja stanu odtwarzacza
setInterval(sendMetadata, 1000);

// ODBIERANIE KOMEND
chrome.runtime.onMessage.addListener((data) => {
  if (!data?.action) return;

  console.log("SPOTIFY COMMAND:", data.action);

  switch (data.action) {
    case "pause":
      getButton("playpause")?.click();
      setTimeout(sendMetadata, 200);
      break;

    case "next":
      getButton("next")?.click();
      setTimeout(sendMetadata, 300);
      break;

    case "prev":
      getButton("prev")?.click();
      setTimeout(sendMetadata, 300);
      break;

    case "shuffle":
      toggleShuffle();
      setTimeout(sendMetadata, 300);
      break;

    case "loop":
      toggleLoop();
      setTimeout(sendMetadata, 400);
      break;

    case "volume": {
      const rawValue = Number(data.value);
      if (!Number.isFinite(rawValue)) break;

      let mappedVolume = rawValue;
      if (Math.abs(rawValue - 0.01) < 0.005) mappedVolume = 0.10;
      else if (Math.abs(rawValue - 0.05) < 0.005) mappedVolume = 0.25;
      else if (Math.abs(rawValue - 0.15) < 0.005) mappedVolume = 0.50;

      setSpotifyVolume(mappedVolume);
      sendMetadata(); // Natychmiastowe wysłanie nowego stanu bez czekania 300 ms
      break;
    }

    }
});
