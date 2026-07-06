/**
 * Audio playback manager for avatar speech.
 */
class AudioPlayer {
  constructor() {
    this.audioContext = null;
    this.queue = [];
    this.playing = false;
    this.onChunkPlayed = null;
  }

  init() {
    if (!this.audioContext) {
      this.audioContext = new (
        window.AudioContext || window.webkitAudioContext
      )({
        sampleRate: 24000,
      });
    }
  }

  async playMP3(base64Audio) {
    this.init();
    const binary = atob(base64Audio);
    const buffer = new ArrayBuffer(binary.length);
    const view = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i++) {
      view[i] = binary.charCodeAt(i);
    }

    const audioBuffer = await this.audioContext.decodeAudioData(buffer);
    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);
    source.start(0);

    return new Promise((resolve) => {
      source.onended = resolve;
    });
  }

  async playPCMChunk(base64Audio, sampleRate = 24000) {
    this.init();
    const binary = atob(base64Audio);
    const int16Array = new Int16Array(binary.length / 2);
    for (let i = 0; i < int16Array.length; i++) {
      int16Array[i] =
        binary.charCodeAt(i * 2) | (binary.charCodeAt(i * 2 + 1) << 8);
    }

    // Convert Int16 to Float32
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    const audioBuffer = this.audioContext.createBuffer(
      1,
      float32Array.length,
      sampleRate,
    );
    audioBuffer.getChannelData(0).set(float32Array);

    const source = this.audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(this.audioContext.destination);
    source.start(0);

    return new Promise((resolve) => {
      source.onended = resolve;
    });
  }

  enqueue(chunk) {
    this.queue.push(chunk);
    if (!this.playing) {
      this._processQueue();
    }
  }

  async _processQueue() {
    this.playing = true;
    while (this.queue.length > 0) {
      const chunk = this.queue.shift();
      if (this.onChunkPlayed) {
        this.onChunkPlayed(chunk);
      }
      if (chunk.format === "mp3") {
        await this.playMP3(chunk.audio);
      } else {
        await this.playPCMChunk(chunk.audio, chunk.sample_rate || 24000);
      }
    }
    this.playing = false;
  }

  stop() {
    this.queue = [];
    this.playing = false;
  }
}
