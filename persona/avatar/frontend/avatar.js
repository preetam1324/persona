/**
 * 2D avatar renderer — full upper-body character with smooth animations.
 */
class AvatarRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.expression = "idle";
    this.mouthOpenness = 0;
    this.targetMouthOpenness = 0;
    this.eyeBlinkTimer = 0;
    this.isBlinking = false;
    this.breathPhase = 0;
    this.headTilt = 0;
    this.targetHeadTilt = 0;
    this.idleSway = 0;
    this.running = false;
    this.time = 0;

    // Polished colour palette
    this.colors = {
      skin: "#f0c8a0",
      skinShadow: "#d4a574",
      skinHighlight: "#fce0c8",
      hair: "#3a2a1a",
      hairHighlight: "#5a4030",
      eyes: "#4a90d9",
      eyeHighlight: "#7ab8ff",
      pupil: "#1a1a2e",
      mouth: "#c0392b",
      mouthInner: "#8b1a1a",
      teeth: "#f5f0e8",
      lips: "#d4635a",
      shirt: "#2d5aa0",
      shirtShadow: "#1e3d6e",
      shirtHighlight: "#4a7ac7",
      bgTop: "#0f0f2a",
      bgBottom: "#1a1a3e",
      neckShadow: "#c89868",
    };
  }

  start() {
    this.running = true;
    this._animate();
  }

  stop() {
    this.running = false;
  }

  setExpression(expression) {
    this.expression = expression;
    // Add head tilt for expressions
    if (expression === "thinking") this.targetHeadTilt = -0.05;
    else if (expression === "happy") this.targetHeadTilt = 0.03;
    else this.targetHeadTilt = 0;
  }

  setMouthOpenness(value) {
    this.targetMouthOpenness = Math.max(0, Math.min(1, value));
  }

  _animate() {
    if (!this.running) return;
    this.time = Date.now();

    // Smooth interpolations
    this.mouthOpenness +=
      (this.targetMouthOpenness - this.mouthOpenness) * 0.25;
    this.headTilt += (this.targetHeadTilt - this.headTilt) * 0.08;

    // Breathing (chest rise + slight head bob)
    this.breathPhase = Math.sin(this.time / 2200) * 3;

    // Subtle idle sway
    this.idleSway = Math.sin(this.time / 4000) * 1.5;

    // Eye blink
    this.eyeBlinkTimer++;
    if (this.eyeBlinkTimer > 200 + Math.random() * 150) {
      this.isBlinking = true;
      this.eyeBlinkTimer = 0;
      setTimeout(() => {
        this.isBlinking = false;
      }, 120);
    }

    this._draw();
    requestAnimationFrame(() => this._animate());
  }

  _draw() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;
    const cx = w / 2;

    // --- Background gradient ---
    const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
    bgGrad.addColorStop(0, this.colors.bgTop);
    bgGrad.addColorStop(1, this.colors.bgBottom);
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    // Subtle radial glow behind avatar
    const glow = ctx.createRadialGradient(cx, h * 0.38, 50, cx, h * 0.38, 280);
    glow.addColorStop(0, "rgba(74, 144, 217, 0.08)");
    glow.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, w, h);

    const by = this.breathPhase;
    const sx = this.idleSway;

    // --- Body / Torso ---
    this._drawBody(ctx, cx, h, by, sx);

    // --- Neck ---
    this._drawNeck(ctx, cx, h, by, sx);

    // --- Head group (with tilt) ---
    ctx.save();
    ctx.translate(cx + sx, h * 0.3 + by * 0.6);
    ctx.rotate(this.headTilt);

    this._drawHair(ctx);
    this._drawFace(ctx);
    this._drawEars(ctx);
    this._drawEyes(ctx);
    this._drawNose(ctx);
    this._drawEyebrows(ctx);
    this._drawMouth(ctx);
    this._drawHairFront(ctx);

    // Thinking indicator
    if (this.expression === "thinking") {
      this._drawThinkingBubble(ctx);
    }

    ctx.restore();
  }

  _drawBody(ctx, cx, h, by, sx) {
    const bodyY = h * 0.58 + by;

    // Arms (behind torso)
    ctx.fillStyle = this.colors.shirt;
    // Left arm
    ctx.save();
    ctx.translate(cx - 95 + sx, bodyY - 10);
    ctx.rotate(-0.15 + Math.sin(this.time / 3000) * 0.03);
    this._roundRect(ctx, -25, 0, 50, 120, 20, this.colors.shirt);
    // Hand
    ctx.fillStyle = this.colors.skin;
    ctx.beginPath();
    ctx.ellipse(0, 125, 18, 16, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Right arm
    ctx.save();
    ctx.translate(cx + 95 + sx, bodyY - 10);
    ctx.rotate(0.15 - Math.sin(this.time / 3000) * 0.03);
    this._roundRect(ctx, -25, 0, 50, 120, 20, this.colors.shirt);
    ctx.fillStyle = this.colors.skin;
    ctx.beginPath();
    ctx.ellipse(0, 125, 18, 16, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    // Torso
    ctx.save();
    ctx.translate(cx + sx, bodyY);

    // Main shirt body
    const shirtGrad = ctx.createLinearGradient(-80, -30, 80, 160);
    shirtGrad.addColorStop(0, this.colors.shirtHighlight);
    shirtGrad.addColorStop(0.5, this.colors.shirt);
    shirtGrad.addColorStop(1, this.colors.shirtShadow);
    ctx.fillStyle = shirtGrad;

    ctx.beginPath();
    ctx.moveTo(-85, -20);
    ctx.quadraticCurveTo(-95, 40, -90, 200);
    ctx.lineTo(90, 200);
    ctx.quadraticCurveTo(95, 40, 85, -20);
    ctx.quadraticCurveTo(50, -40, 0, -35);
    ctx.quadraticCurveTo(-50, -40, -85, -20);
    ctx.fill();

    // Collar / neckline
    ctx.strokeStyle = this.colors.shirtShadow;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(-30, -32);
    ctx.quadraticCurveTo(0, -15, 30, -32);
    ctx.stroke();

    ctx.restore();
  }

  _drawNeck(ctx, cx, h, by, sx) {
    const neckY = h * 0.5 + by;
    ctx.save();
    ctx.translate(cx + sx, neckY);

    // Neck shadow
    ctx.fillStyle = this.colors.neckShadow;
    ctx.beginPath();
    ctx.ellipse(0, 15, 28, 10, 0, 0, Math.PI * 2);
    ctx.fill();

    // Neck
    const neckGrad = ctx.createLinearGradient(-22, -20, 22, 30);
    neckGrad.addColorStop(0, this.colors.skinHighlight);
    neckGrad.addColorStop(1, this.colors.skinShadow);
    ctx.fillStyle = neckGrad;
    ctx.beginPath();
    ctx.moveTo(-22, -20);
    ctx.lineTo(-25, 25);
    ctx.quadraticCurveTo(0, 35, 25, 25);
    ctx.lineTo(22, -20);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  _drawHair(ctx) {
    // Back hair volume
    ctx.fillStyle = this.colors.hair;
    ctx.beginPath();
    ctx.ellipse(0, -25, 95, 105, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  _drawFace(ctx) {
    // Face shape with gradient
    const faceGrad = ctx.createRadialGradient(-10, -15, 20, 0, 0, 90);
    faceGrad.addColorStop(0, this.colors.skinHighlight);
    faceGrad.addColorStop(0.7, this.colors.skin);
    faceGrad.addColorStop(1, this.colors.skinShadow);
    ctx.fillStyle = faceGrad;
    ctx.beginPath();
    ctx.ellipse(0, 0, 80, 95, 0, 0, Math.PI * 2);
    ctx.fill();

    // Jaw line (subtle shadow)
    ctx.fillStyle = "rgba(0,0,0,0.04)";
    ctx.beginPath();
    ctx.ellipse(0, 30, 75, 65, 0, 0.2, Math.PI - 0.2);
    ctx.fill();

    // Cheek blush
    if (this.expression === "happy") {
      ctx.fillStyle = "rgba(255, 140, 120, 0.2)";
      ctx.beginPath();
      ctx.ellipse(-40, 25, 18, 12, -0.2, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.ellipse(40, 25, 18, 12, 0.2, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  _drawEars(ctx) {
    // Left ear
    ctx.fillStyle = this.colors.skin;
    ctx.beginPath();
    ctx.ellipse(-78, -5, 12, 20, -0.15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = this.colors.skinShadow;
    ctx.beginPath();
    ctx.ellipse(-78, -5, 7, 13, -0.15, 0, Math.PI * 2);
    ctx.fill();

    // Right ear
    ctx.fillStyle = this.colors.skin;
    ctx.beginPath();
    ctx.ellipse(78, -5, 12, 20, 0.15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = this.colors.skinShadow;
    ctx.beginPath();
    ctx.ellipse(78, -5, 7, 13, 0.15, 0, Math.PI * 2);
    ctx.fill();
  }

  _drawEyes(ctx) {
    const eyeY = -15;
    const sp = 32;
    const blinkH = this.isBlinking ? 2 : 15;

    for (const side of [-1, 1]) {
      const ex = sp * side;

      // Eye socket shadow
      ctx.fillStyle = "rgba(0,0,0,0.05)";
      ctx.beginPath();
      ctx.ellipse(ex, eyeY, 22, 18, 0, 0, Math.PI * 2);
      ctx.fill();

      // White of eye
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.ellipse(ex, eyeY, 18, blinkH, 0, 0, Math.PI * 2);
      ctx.fill();

      // Eye outline
      ctx.strokeStyle = "rgba(0,0,0,0.15)";
      ctx.lineWidth = 1;
      ctx.stroke();

      if (!this.isBlinking) {
        // Iris
        const irisGrad = ctx.createRadialGradient(
          ex,
          eyeY + 1,
          2,
          ex,
          eyeY + 1,
          9,
        );
        irisGrad.addColorStop(0, this.colors.eyeHighlight);
        irisGrad.addColorStop(1, this.colors.eyes);
        ctx.fillStyle = irisGrad;
        ctx.beginPath();
        ctx.arc(ex, eyeY + 1, 9, 0, Math.PI * 2);
        ctx.fill();

        // Pupil
        ctx.fillStyle = this.colors.pupil;
        ctx.beginPath();
        ctx.arc(ex, eyeY + 1, 4.5, 0, Math.PI * 2);
        ctx.fill();

        // Eye highlight (specular)
        ctx.fillStyle = "rgba(255,255,255,0.85)";
        ctx.beginPath();
        ctx.arc(ex - 3, eyeY - 3, 2.5, 0, Math.PI * 2);
        ctx.fill();
        ctx.beginPath();
        ctx.arc(ex + 2, eyeY + 3, 1.2, 0, Math.PI * 2);
        ctx.fill();

        // Upper eyelid line
        ctx.strokeStyle = "rgba(60,40,20,0.4)";
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.ellipse(ex, eyeY - 1, 18, 14, 0, Math.PI + 0.3, -0.3);
        ctx.stroke();

        // Lower lashes
        ctx.strokeStyle = "rgba(60,40,20,0.2)";
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.ellipse(ex, eyeY + 2, 16, 12, 0, 0.3, Math.PI - 0.3);
        ctx.stroke();
      }
    }
  }

  _drawNose(ctx) {
    ctx.strokeStyle = this.colors.skinShadow;
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";

    // Nose bridge shadow
    ctx.beginPath();
    ctx.moveTo(-3, -2);
    ctx.quadraticCurveTo(-5, 15, -8, 22);
    ctx.stroke();

    // Nose tip
    ctx.beginPath();
    ctx.moveTo(-8, 22);
    ctx.quadraticCurveTo(0, 28, 8, 22);
    ctx.stroke();

    // Nostril hints
    ctx.fillStyle = this.colors.skinShadow;
    ctx.beginPath();
    ctx.ellipse(-5, 24, 3, 2, -0.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(5, 24, 3, 2, 0.3, 0, Math.PI * 2);
    ctx.fill();
  }

  _drawEyebrows(ctx) {
    const eyeY = -15;
    const sp = 32;
    const browY = eyeY - 22;
    const raise = this.expression === "thinking" ? -6 : 0;
    const furrow = this.expression === "error" ? 4 : 0;

    ctx.lineCap = "round";
    ctx.lineWidth = 3.5;
    ctx.strokeStyle = this.colors.hair;

    // Left eyebrow
    ctx.beginPath();
    ctx.moveTo(-sp - 16, browY + raise + furrow);
    ctx.quadraticCurveTo(-sp, browY - 6 + raise, -sp + 16, browY + raise);
    ctx.stroke();

    // Right eyebrow
    ctx.beginPath();
    ctx.moveTo(sp - 16, browY + raise);
    ctx.quadraticCurveTo(
      sp,
      browY - 6 + raise,
      sp + 16,
      browY + raise + furrow,
    );
    ctx.stroke();
  }

  _drawMouth(ctx) {
    const mouthY = 48;
    const mouthW = 24 + (this.expression === "happy" ? 10 : 0);
    const openAmt = this.mouthOpenness * 16;

    if (openAmt > 2) {
      // Open mouth with depth
      // Mouth cavity
      ctx.fillStyle = this.colors.mouthInner;
      ctx.beginPath();
      ctx.ellipse(0, mouthY, mouthW, openAmt, 0, 0, Math.PI * 2);
      ctx.fill();

      // Teeth (top row)
      ctx.fillStyle = this.colors.teeth;
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(0, mouthY, mouthW, openAmt, 0, 0, Math.PI * 2);
      ctx.clip();
      ctx.fillRect(
        -mouthW + 3,
        mouthY - openAmt,
        (mouthW - 3) * 2,
        openAmt * 0.45,
      );
      ctx.restore();

      // Tongue hint
      if (openAmt > 6) {
        ctx.fillStyle = "#d45a5a";
        ctx.beginPath();
        ctx.ellipse(
          0,
          mouthY + openAmt * 0.3,
          mouthW * 0.5,
          openAmt * 0.35,
          0,
          0,
          Math.PI,
        );
        ctx.fill();
      }

      // Lips outline
      ctx.strokeStyle = this.colors.lips;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.ellipse(0, mouthY, mouthW + 1, openAmt + 1, 0, 0, Math.PI * 2);
      ctx.stroke();
    } else {
      // Closed mouth
      const smileCurve =
        this.expression === "happy" ? 12 : this.expression === "error" ? -8 : 4;

      // Lip fill
      ctx.fillStyle = this.colors.lips;
      ctx.beginPath();
      ctx.moveTo(-mouthW, mouthY);
      ctx.quadraticCurveTo(0, mouthY + smileCurve + 3, mouthW, mouthY);
      ctx.quadraticCurveTo(0, mouthY + smileCurve - 2, -mouthW, mouthY);
      ctx.fill();

      // Lip line
      ctx.strokeStyle = this.colors.mouth;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(-mouthW, mouthY);
      ctx.quadraticCurveTo(0, mouthY + smileCurve, mouthW, mouthY);
      ctx.stroke();
    }
  }

  _drawHairFront(ctx) {
    // Front hair / bangs
    ctx.fillStyle = this.colors.hair;
    ctx.beginPath();
    ctx.moveTo(-80, -45);
    ctx.quadraticCurveTo(-85, -95, -50, -100);
    ctx.quadraticCurveTo(-20, -105, 0, -100);
    ctx.quadraticCurveTo(20, -105, 50, -100);
    ctx.quadraticCurveTo(85, -95, 80, -45);
    ctx.quadraticCurveTo(75, -70, 55, -75);
    ctx.quadraticCurveTo(30, -70, 15, -65);
    ctx.quadraticCurveTo(0, -68, -15, -65);
    ctx.quadraticCurveTo(-30, -70, -55, -75);
    ctx.quadraticCurveTo(-75, -70, -80, -45);
    ctx.fill();

    // Hair highlight
    ctx.fillStyle = this.colors.hairHighlight;
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    ctx.moveTo(-40, -95);
    ctx.quadraticCurveTo(-20, -100, 0, -95);
    ctx.quadraticCurveTo(-10, -80, -30, -75);
    ctx.quadraticCurveTo(-45, -80, -40, -95);
    ctx.fill();
    ctx.globalAlpha = 1.0;
  }

  _drawThinkingBubble(ctx) {
    const t = this.time / 500;
    const dotY = -110;

    ctx.fillStyle = "rgba(255,255,255,0.6)";
    for (let i = 0; i < 3; i++) {
      const bounce = Math.sin(t + i * 0.8) * 4;
      ctx.beginPath();
      ctx.arc(55 + i * 14, dotY + bounce, 5, 0, Math.PI * 2);
      ctx.fill();
    }
  }

  _roundRect(ctx, x, y, w, h, r, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
    ctx.fill();
  }
}
