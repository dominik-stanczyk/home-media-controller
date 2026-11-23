console.log("YT Remote: Loading successful");

const DEFAULT_VOLUME = 0.15;

function getSavedVolume() {
  const v = localStorage.getItem("YT_REMOTE_VOLUME");
  return v !== null ? Number(v) : DEFAULT_VOLUME;
}

function setVolume(v) {
  const clamped = Math.max(0, Math.min(1, Number(v)));
  localStorage.setItem("YT_REMOTE_VOLUME", String(clamped));
  const video = document.querySelector("video");
  if (video) {
    video.muted = false;
    video.volume = clamped;
  }
}

function applyVolume(video) {
  if (!video) return;
  const saved = getSavedVolume();
  if (Math.abs(video.volume - saved) > 0.005) {
    video.volume = saved;
  }
}

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// Wspólny, bezpieczny selektor przycisku Shuffle w panelu playlisty
function getShuffleButton() {
  const panel = document.querySelector("ytd-playlist-panel-renderer");
  if (!panel) return null;
  return (
    panel.querySelector("#playlist-action-menu ytd-toggle-button-renderer button") ||
    [...panel.querySelectorAll("button")].find(el => {
      const label = (el.getAttribute("aria-label") || "").toLowerCase();
      return label.includes("shuffle") || label.includes("losow");
    })
  );
}

// Zamiast ciężkiego MutationObserver: pilnowanie głośności przez zdarzenia <video>
function bindVideoEvents(video) {
  if (!video || video.dataset.ytRemoteBound) return;
  video.dataset.ytRemoteBound = "true";

  applyVolume(video);

  video.addEventListener("loadedmetadata", () => applyVolume(video));
  video.addEventListener("play", () => applyVolume(video));
  video.addEventListener("volumechange", () => applyVolume(video));
}

function sendMetadata() {
  if (!chrome.runtime?.id) return; // Zatrzymaj po przeładowaniu rozszerzenia

  const video = document.querySelector("video");
  if (!video) return;

  bindVideoEvents(video);

  const urlParams = new URLSearchParams(window.location.search);
  const videoId = urlParams.get("v");

  const shuffleBtn = getShuffleButton();
  const isShuffleActive = shuffleBtn ? shuffleBtn.getAttribute("aria-pressed") === "true" : false;

  const duration = Number.isFinite(video.duration) ? video.duration : 0;
  const currentTime = Number.isFinite(video.currentTime) ? video.currentTime : 0;

  const data = {
    type: "METADATA",
    title: document.title.replace(/\s*-\s*YouTube$/, "").trim(),
    author: document.querySelector("#upload-info #channel-name a")?.innerText?.trim() || "YouTube",
    progress: duration > 0 ? (currentTime / duration) * 100 : 0,
    thumbnail: videoId ? `https://i.ytimg.com/vi/${videoId}/mqdefault.jpg` : "",
    timeStr: `${formatTime(currentTime)} / ${formatTime(duration)}`,
    paused: video.paused,
    volume: video.volume,
    shuffle: isShuffleActive,
    loop: video.loop
  };

  chrome.runtime.sendMessage(data).catch(() => {});
}

// Główna pętla aktualizacji stanu
setInterval(sendMetadata, 1000);

// Auto-klikanie "Czy nadal oglądasz?"
setInterval(() => {
  const confirmButton = document.querySelector("yt-confirm-dialog-renderer #confirm-button");
  if (confirmButton && confirmButton.offsetParent !== null) {
    confirmButton.click();
    console.log("Automatycznie kliknięto: Kontynuuj oglądanie");
  }
}, 5000);

// Odbieranie komend z background
chrome.runtime.onMessage.addListener((data) => {
  console.log("FROM BG:", data);

  const video = document.querySelector("video");
  if (!video) return;

  switch (data.action) {
    case "pause":
      video.paused ? video.play() : video.pause();
      sendMetadata();
      break;

    case "next":
      document.querySelector(".ytp-next-button")?.click();
      break;

    case "prev":
      document.querySelector(".ytp-prev-button")?.click();
      break;

    case "shuffle":
      getShuffleButton()?.click();
      setTimeout(sendMetadata, 150);
      break;

    case "volume": {
      const value = Number(data.value);
      if (!isNaN(value)) {
        setVolume(value);
        sendMetadata();
      }
      break;
    }

    case "loop":
      video.loop = !video.loop;
      sendMetadata();
      break;
  }
});

// Natychmiastowa aktualizacja po zmianie filmu w YouTube (SPA)
window.addEventListener("yt-navigate-finish", () => {
  setTimeout(sendMetadata, 300);
});
