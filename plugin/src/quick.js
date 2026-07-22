/* Quick tier — a faithful JS mirror of engine/veil/quick.py so the plugin
 * protects images with zero backend. Same counter-based hash, same 1-2-1
 * high-pass, same amplitude mapping. Operates on interleaved RGB(A) bytes and
 * leaves any alpha channel untouched. */

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

function quickProtect(data, width, height, components, strength, seed = 1) {
  strength = Math.max(0, Math.min(1, strength));
  const amp = 1.0 + 7.0 * strength;
  const colorChannels = Math.min(components, 3);
  const n = width * height;

  const out = new Uint8Array(data); // copy — preserves alpha bytes as-is
  const noise = new Float32Array(n);
  const low = new Float32Array(n);
  const tmp = new Float32Array(n);

  for (let ch = 0; ch < colorChannels; ch++) {
    for (let i = 0; i < n; i++) {
      noise[i] = hash01(((i * 3 + ch) >>> 0), seed) * 2 - 1;
    }
    blur3(noise, width, height, low, tmp);

    let peak = 0;
    for (let i = 0; i < n; i++) {
      const hp = noise[i] - low[i];
      noise[i] = hp; // reuse as high-pass buffer
      const a = hp < 0 ? -hp : hp;
      if (a > peak) peak = a;
    }
    const norm = peak > 1e-6 ? 1 / peak : 0;

    for (let i = 0; i < n; i++) {
      const o = i * components + ch;
      let v = data[o] + amp * noise[i] * norm;
      v = v < 0 ? 0 : v > 255 ? 255 : v;
      out[o] = (v + 0.5) | 0;
    }
  }
  return out;
}

module.exports = { quickProtect };
