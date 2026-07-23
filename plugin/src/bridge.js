/* Talks to the local engine (engine/server.py) for the Deep tier. Sends and
 * receives normalised float32 RGB (bit-depth agnostic). Exposes window.VeilBridge. */
"use strict";
(function () {
  const BASE = "http://localhost:8760";

  async function health() {
    try {
      const res = await fetch(BASE + "/health", { method: "GET" });
      return res.ok;
    } catch (e) {
      return false;
    }
  }

  // data01: Float32Array normalised RGB (3 channels). Returns Float32Array.
  async function deepProtect(data01, width, height, opts) {
    const mode = (opts && opts.mode) || "cloak";
    const strength = opts && opts.strength != null ? opts.strength : 0.5;
    const decoy = (opts && opts.decoy) || "";

    const qs =
      "width=" + width + "&height=" + height + "&channels=3&dtype=float32" +
      "&mode=" + encodeURIComponent(mode) + "&strength=" + strength +
      "&tier=deep&decoy=" + encodeURIComponent(decoy);

    let res;
    try {
      res = await fetch(BASE + "/protect?" + qs, {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: data01.buffer,
      });
    } catch (e) {
      throw new Error("Engine not reachable. Double-click install.command once to set it up.");
    }
    if (!res.ok) {
      let detail = "";
      try { detail = await res.text(); } catch (_) {}
      throw new Error(("Engine error " + res.status + ". " + detail).trim());
    }
    const buf = await res.arrayBuffer();
    return new Float32Array(buf);
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { health, deepProtect };
  if (typeof window !== "undefined") window.VeilBridge = { health, deepProtect };
})();
