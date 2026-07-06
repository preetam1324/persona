/**
 * WebSocket client for avatar streaming communication.
 */
class AvatarWebSocket {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.listeners = {};
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this._emit("connected");
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this._emit("message", data);

      // Dispatch by type
      if (data.type) {
        this._emit(data.type, data);
      }
    };

    this.ws.onclose = () => {
      this._emit("disconnected");
      this._attemptReconnect();
    };

    this.ws.onerror = (err) => {
      this._emit("error", err);
    };
  }

  send(message, conversationId = null) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({
          message: message,
          conversation_id: conversationId,
        }),
      );
    }
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  _emit(event, data = null) {
    const cbs = this.listeners[event] || [];
    cbs.forEach((cb) => cb(data));
  }

  _attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
      setTimeout(() => this.connect(), delay);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
