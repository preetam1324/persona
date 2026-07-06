/**
 * Main application — wires together WebSocket, Audio, Avatar, and LipSync.
 */
(function () {
  // DOM elements
  const messagesEl = document.getElementById("messages");
  const inputEl = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const micBtn = document.getElementById("mic-btn");
  const expressionLabel = document.getElementById("expression-label");
  const canvas = document.getElementById("avatar-canvas");

  // Initialize components
  const avatar = new AvatarRenderer(canvas);
  const audioPlayer = new AudioPlayer();
  const lipSync = new LipSyncController(avatar);

  // Determine WebSocket URL from current page location
  const wsProtocol = location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${location.host}/v1/avatar/stream`;
  const ws = new AvatarWebSocket(wsUrl);

  // Start avatar rendering
  avatar.start();

  // WebSocket event handlers
  ws.on("connected", () => {
    addMessage("system", "Connected to avatar server.");
  });

  ws.on("disconnected", () => {
    addMessage("system", "Disconnected. Reconnecting...");
  });

  ws.on("state", (data) => {
    avatar.setExpression(data.expression);
    expressionLabel.textContent = data.expression;
  });

  ws.on("text", (data) => {
    addMessage("assistant", data.content);
  });

  ws.on("audio", (data) => {
    // Play audio and animate lips
    audioPlayer.enqueue(data);
    if (data.visemes && data.visemes.length > 0) {
      lipSync.play(data.visemes);
      avatar.setExpression("speaking");
      expressionLabel.textContent = "speaking";
    }
  });

  ws.on("done", (data) => {
    avatar.setExpression("idle");
    expressionLabel.textContent = "idle";
  });

  ws.on("error", () => {
    addMessage("system", "Connection error.");
  });

  // Connect
  ws.connect();

  // Send message
  function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    addMessage("user", text);
    ws.send(text);
    inputEl.value = "";
    avatar.setExpression("thinking");
    expressionLabel.textContent = "thinking";
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // Microphone (Web Speech API)
  if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    micBtn.disabled = false;
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    let isListening = false;

    micBtn.addEventListener("click", () => {
      if (isListening) {
        recognition.stop();
        micBtn.classList.remove("active");
        isListening = false;
      } else {
        recognition.start();
        micBtn.classList.add("active");
        isListening = true;
      }
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      inputEl.value = transcript;
      sendMessage();
      micBtn.classList.remove("active");
      isListening = false;
    };

    recognition.onend = () => {
      micBtn.classList.remove("active");
      isListening = false;
    };
  }

  // Utility
  function addMessage(role, text) {
    const div = document.createElement("div");
    div.className = `message ${role}`;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
})();
