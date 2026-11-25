importScripts("socket.io.js");

const socket = io("http://127.0.0.1:5000", {
  transports: ["websocket"],
});

let activeTabId = null;
let isActiveTabPlaying = false;

socket.on("connect", () => console.log("WS CONNECTED"));
socket.on("disconnect", () => console.log("WS DISCONNECTED"));
socket.on("connect_error", (err) => console.error("WS ERROR:", err));

socket.on("command", async (data) => {
  console.log("BACKGROUND RECEIVED:", data);
  console.log("ACTIVE TAB:", activeTabId);

  // Najpierw próbujemy aktywną kartę
  if (activeTabId !== null) {
    try {
      console.log("SENDING TO THE TAB:", activeTabId);

      await chrome.tabs.sendMessage(activeTabId, data);
      return;

    } catch (error) {
      console.warn("Active tab unavailable:", error);

      activeTabId = null;
      isActiveTabPlaying = false;
    }
  }

  // Szukamy kart YouTube i Spotify
  const tabs = await chrome.tabs.query({
    url: [
      "https://www.youtube.com/*",
      "https://*.youtube.com/*",
      "https://open.spotify.com/*",
      "https://*.spotify.com/*"
    ]
  });


  if (!tabs.length) {
    console.warn("Player tab was not found");
    return;
  }

  // Próbujemy wysłać do każdej znalezionej karty
  for (const tab of tabs) {
    try {
      await chrome.tabs.sendMessage(tab.id, data);

      activeTabId = tab.id;
      console.log("COMMAND DELIVERED:", tab.id);
      return;

    } catch (error) {
      console.warn("NO CONTENT SCRIPT:", tab.id);
    }
  }

  console.error("COULDN'T DELIVER THE PACKAGE TO ANY TAB");
});

chrome.runtime.onMessage.addListener((message, sender) => {
  if (message.type !== "METADATA" || !sender.tab) return;

  const tabId = sender.tab.id;
  const playingNow = !message.paused;


  if (activeTabId === null) {
    activeTabId = tabId;
    isActiveTabPlaying = playingNow;
  } else if (tabId !== activeTabId && playingNow) {
    if (isActiveTabPlaying) {
      chrome.tabs.sendMessage(activeTabId, {
        action: "pause"
      }).catch(() => {});
    }

    activeTabId = tabId;
    isActiveTabPlaying = true;
  }

  if (tabId === activeTabId && socket.connected) {
    isActiveTabPlaying = playingNow;
    socket.emit("update_status", message);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === activeTabId) {
    activeTabId = null;
    isActiveTabPlaying = false;
  }
});