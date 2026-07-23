/* Quick tier — a faithful JS mirror of engine/veil/quick.py. Works in
 * normalised float [0,1] (bit-depth agnostic). Same counter-based hash, same
 * 1-2-1 high-pass, same amplitude. Exposes window.VeilQuick. */
"use strict";
(function () {
  var AMP_BASE = 1.0 / 255.0;
  var AMP_SPAN = 7.0 / 255.0;

  function hash01(idx, seed) {
    let x = (idx + Math.imul(seed, 0x9e3779b1)) >>> 0;
    x ^= x >>> 16;
    x = Math.imul(x, 0x7feb352d) >>> 0;
    x ^= x >>> 15;
    x = Math.imul(x, 0x846ca68b) >>> 0;
    x ^= x >>> 16;
    return (x >>> 0) / 4294967296;
  }

  // Separable 1-2-1 blur with edge replication (mild low-pass).
  function blur3(src, w, h, dst, tmp) {
    for (let y = 0; y < h; y++) {
      const row = y * w;
      for (let x = 0; x < w; x++) {
        const l = src[row + (x > 0 ? x - 1 : 0)];
        const c = src[row + x];
        const r = src[row + (x < w - 1 ? x + 1 : w - 1)];
        tmp[row + x] = (l + 2 * c + r) * 0.25;
      }
    }
    for (let y = 0; y < h; y++) {
      const up = (y > 0 ? y - 1 : 0) * w;
      const dn = (y < h - 1 ? y + 1 : h - 1) * w;
      const row = y * w;
      for (let x = 0; x < w; x++) {
        dst[row + x] = (tmp[up + x] + 2 * tmp[row + x] + tmp[dn + x]) * 0.25;
      }
    }
  }

  // data01: Float32 normalised, interleaved, `components` channels. Returns a
  // new Float32Array in [0,1]; color channels perturbed, alpha untouched.
  function quickProtect(data01, width, height, components, strength, seed) {
    if (seed === undefined) seed = 1;
    strength = Math.max(0, Math.min(1, strength));
    const amp = AMP_BASE + AMP_SPAN * strength;
    const colorChannels = Math.min(components, 3);
    const n = width * height;

    const out = new Float32Array(data01); // copy — preserves alpha as-is
    const noise = new Float32Array(n);
    const low = new Float32Array(n);
    const tmp = new Float32Array(n);

    for (let ch = 0; ch < colorChannels; ch++) {
      for (let i = 0; i < n; i++) {
        noise[i] = hash01((i * 3 + ch) >>> 0, seed) * 2 - 1;
      }
      blur3(noise, width, height, low, tmp);

      let peak = 0;
      for (let i = 0; i < n; i++) {
        const hp = noise[i] - low[i];
        noise[i] = hp;
        const a = hp < 0 ? -hp : hp;
        if (a > peak) peak = a;
      }
      const norm = peak > 1e-6 ? 1 / peak : 0;

      for (let i = 0; i < n; i++) {
        const o = i * components + ch;
        let v = data01[o] + amp * noise[i] * norm;
        out[o] = v < 0 ? 0 : v > 1 ? 1 : v;
      }
    }
    return out;
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { quickProtect };
  if (typeof window !== "undefined") window.VeilQuick = { quickProtect };
})();
