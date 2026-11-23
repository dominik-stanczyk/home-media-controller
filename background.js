importScripts("socket.io.js");

console.log("Background starting");

const socket = io("http://192.168.1.110:5000", {
  transports: ["websocket"],
});

socket.on("connect", () => {
  console.log("WS CONNECTED");
});

socket.on("command", async (data) => {
  console.log("COMMAND:", data);

  const tabs = await chrome.tabs.query({
    url: "*://*.youtube.com/*"
  });

  for (const tab of tabs) {
    chrome.tabs.sendMessage(tab.id, data);
  }
});
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "METADATA" && socket.connected) {
    socket.emit("update_status", message); 
  }
});
socket.on("disconnect", () => {
  console.log("WS DISCONNECTED");
});
