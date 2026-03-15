/**
 * background-canvas.js
 * Dynamic particle-constellation background for Sentinel.
 * Nodes drift organically, connect with lines when close, and react to mouse.
 * Themed to match Sentinel's teal color scheme.
 */
(function () {
  'use strict';

  // ── Color tokens ────────────────────────────────────────────────────────────
  const DARK_RGB  = '45, 212, 191';   // #2DD4BF
  const LIGHT_RGB = '15, 150, 131';   // #0f9683

  // ── Tuning ──────────────────────────────────────────────────────────────────
  const DENSITY          = 13000;  // px² per node
  const MIN_NODES        = 55;
  const MAX_NODES        = 160;
  const BASE_SPEED       = 0.35;
  const MAX_CONNECT_DIST = 190;    // px – line drawn below this distance
  const MOUSE_RADIUS     = 160;    // px – nodes within this get nudged
  const MOUSE_STRENGTH   = 0.045;  // nudge force (gentle attract toward cursor)
  const LINE_OPACITY_MAX = 0.22;
  const NODE_OPACITY_MIN = 0.35;
  const NODE_OPACITY_MAX = 0.70;
  const ELECTRON_CHANCE  = 0.00075; // per connection per frame
  const MAX_ELECTRONS    = 30;

  // ── State ───────────────────────────────────────────────────────────────────
  let canvas, ctx, W, H;
  let nodes     = [];
  let electrons = [];
  let mouse     = null;
  let animId    = null;

  // ── Helpers ──────────────────────────────────────────────────────────────────
  function isDarkMode() {
    return !document.body.classList.contains('light-mode');
  }

  function rgb() {
    return isDarkMode() ? DARK_RGB : LIGHT_RGB;
  }

  // ── Initialise nodes ─────────────────────────────────────────────────────────
  function createNodes() {
    const count = Math.max(MIN_NODES, Math.min(MAX_NODES, Math.floor((W * H) / DENSITY)));
    nodes = Array.from({ length: count }, () => {
      const angle = Math.random() * Math.PI * 2;
      const speed = BASE_SPEED * (0.5 + Math.random() * 0.8);
      return {
        x:  Math.random() * W,
        y:  Math.random() * H,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        r:  1.8 + Math.random() * 2.2,
        op: NODE_OPACITY_MIN + Math.random() * (NODE_OPACITY_MAX - NODE_OPACITY_MIN),
      };
    });
    electrons = [];
  }

  // ── Resize ───────────────────────────────────────────────────────────────────
  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
    createNodes();
  }

  // ── Physics update ──────────────────────────────────────────────────────────
  function updateNodes() {
    for (const n of nodes) {
      // Mouse attraction
      if (mouse) {
        const dx = mouse.x - n.x;
        const dy = mouse.y - n.y;
        const d2 = dx * dx + dy * dy;
        if (d2 < MOUSE_RADIUS * MOUSE_RADIUS && d2 > 0) {
          const d = Math.sqrt(d2);
          const force = (1 - d / MOUSE_RADIUS) * MOUSE_STRENGTH;
          n.vx += (dx / d) * force;
          n.vy += (dy / d) * force;
        }
      }

      // Soft speed cap + gentle damping
      const spd = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
      const cap = BASE_SPEED * 2.8;
      if (spd > cap) { n.vx *= cap / spd; n.vy *= cap / spd; }

      // Very light damping so nodes drift back to natural pace away from mouse
      n.vx *= 0.992;
      n.vy *= 0.992;

      // Ensure minimum drift so nodes never freeze
      if (spd < BASE_SPEED * 0.3) {
        n.vx += (Math.random() - 0.5) * 0.025;
        n.vy += (Math.random() - 0.5) * 0.025;
      }

      n.x += n.vx;
      n.y += n.vy;

      // Wrap around viewport edges
      if (n.x < -25) n.x = W + 25;
      else if (n.x > W + 25) n.x = -25;
      if (n.y < -25) n.y = H + 25;
      else if (n.y > H + 25) n.y = -25;
    }
  }

  // ── Spawn electrons along a connection ──────────────────────────────────────
  function spawnElectrons() {
    if (electrons.length >= MAX_ELECTRONS) return;
    const len = nodes.length;
    for (let i = 0; i < len && electrons.length < MAX_ELECTRONS; i++) {
      for (let j = i + 1; j < len; j++) {
        if (Math.random() > ELECTRON_CHANCE) continue;
        const dx = nodes[j].x - nodes[i].x;
        const dy = nodes[j].y - nodes[i].y;
        if (dx * dx + dy * dy < MAX_CONNECT_DIST * MAX_CONNECT_DIST) {
          electrons.push({
            a:     i,
            b:     j,
            t:     0,
            speed: 0.005 + Math.random() * 0.007,
          });
        }
      }
    }
  }

  // ── Draw one frame ───────────────────────────────────────────────────────────
  function drawFrame(ts) {
    ctx.clearRect(0, 0, W, H);

    updateNodes();
    spawnElectrons();

    const color = rgb();
    const len   = nodes.length;

    // ── Connection lines ──────────────────────────────────────────────────────
    ctx.lineWidth = 0.75;
    for (let i = 0; i < len; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < len; j++) {
        const b  = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const d2 = dx * dx + dy * dy;
        if (d2 >= MAX_CONNECT_DIST * MAX_CONNECT_DIST) continue;
        const op = LINE_OPACITY_MAX * (1 - Math.sqrt(d2) / MAX_CONNECT_DIST);
        ctx.strokeStyle = `rgba(${color},${op.toFixed(3)})`;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }

    // ── Nodes ────────────────────────────────────────────────────────────────
    for (const n of nodes) {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color},${n.op.toFixed(3)})`;
      ctx.fill();
    }

    // ── Electrons ────────────────────────────────────────────────────────────
    for (let i = electrons.length - 1; i >= 0; i--) {
      const e = electrons[i];
      e.t += e.speed;
      if (e.t > 1) { electrons.splice(i, 1); continue; }

      const a = nodes[e.a];
      const b = nodes[e.b];
      if (!a || !b) { electrons.splice(i, 1); continue; }

      const x = a.x + (b.x - a.x) * e.t;
      const y = a.y + (b.y - a.y) * e.t;

      // Soft glow halo
      ctx.beginPath();
      ctx.arc(x, y, 5, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color},0.10)`;
      ctx.fill();

      // Core dot
      ctx.beginPath();
      ctx.arc(x, y, 2, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${color},0.90)`;
      ctx.fill();
    }

    animId = requestAnimationFrame(drawFrame);
  }

  // ── Pause / resume on tab visibility ─────────────────────────────────────────
  function pause()  { if (animId) { cancelAnimationFrame(animId); animId = null; } }
  function resume() { if (!animId) animId = requestAnimationFrame(drawFrame); }

  // ── Boot ─────────────────────────────────────────────────────────────────────
  function init() {
    canvas = document.getElementById('bg-canvas');
    if (!canvas) return;
    ctx = canvas.getContext('2d');

    resize();
    window.addEventListener('resize', resize);

    window.addEventListener('mousemove', (e) => { mouse = { x: e.clientX, y: e.clientY }; });
    window.addEventListener('mouseleave', ()  => { mouse = null; });

    document.addEventListener('visibilitychange', () => {
      document.hidden ? pause() : resume();
    });

    animId = requestAnimationFrame(drawFrame);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
