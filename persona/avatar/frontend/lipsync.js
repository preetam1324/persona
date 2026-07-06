/**
 * Lip-sync controller — maps viseme data to avatar mouth shapes.
 */
class LipSyncController {
  constructor(avatarRenderer) {
    this.avatar = avatarRenderer;
    this.visemeQueue = [];
    this.playing = false;
    this.startTime = 0;
  }

  /**
   * Feed visemes from a TTS chunk and animate.
   * @param {Array} visemes - [{id, start_ms, duration_ms}]
   */
  play(visemes) {
    this.visemeQueue = visemes;
    this.startTime = performance.now();
    if (!this.playing) {
      this.playing = true;
      this._tick();
    }
  }

  stop() {
    this.playing = false;
    this.visemeQueue = [];
    this.avatar.setMouthOpenness(0);
    this.avatar.setExpression("idle");
  }

  _tick() {
    if (!this.playing) return;

    const elapsed = performance.now() - this.startTime;
    let currentViseme = null;

    for (const v of this.visemeQueue) {
      if (elapsed >= v.start_ms && elapsed < v.start_ms + v.duration_ms) {
        currentViseme = v;
        break;
      }
    }

    if (currentViseme) {
      const openness = this._visemeToOpenness(currentViseme.id);
      this.avatar.setMouthOpenness(openness);
      this.avatar.setExpression("speaking");
    } else if (elapsed > this._totalDuration()) {
      // Done
      this.playing = false;
      this.avatar.setMouthOpenness(0);
      this.avatar.setExpression("idle");
      return;
    }

    requestAnimationFrame(() => this._tick());
  }

  _totalDuration() {
    if (this.visemeQueue.length === 0) return 0;
    const last = this.visemeQueue[this.visemeQueue.length - 1];
    return last.start_ms + last.duration_ms;
  }

  _visemeToOpenness(visemeId) {
    const map = {
      aa: 0.9,
      oh: 0.8,
      oo: 0.6,
      ee: 0.4,
      ih: 0.5,
      ss: 0.2,
      ff: 0.15,
      dd: 0.3,
      nn: 0.25,
      mm: 0.05,
      pp: 0.0,
      rr: 0.4,
      silence: 0.0,
    };
    return map[visemeId] || 0.1;
  }
}
