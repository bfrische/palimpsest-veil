/* Talks to the local engine (engine/server.py) for Poison mode. Sends and
 * receives normalised float32 RGB. Exposes window.VeilBridge. */
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
  // Destruction poison (shade mode): corrupts the training signal so a model
  // trained on the result produces degraded output. Near-invisible.
  async function poisonProtect(data01, width, height, opts) {
    const decoy = (opts && opts.decoy) || "a vintage car";
    const strength = opts && opts.strength != null ? opts.strength : 0.55;

    const qs =
      "width=" + width + "&height=" + height + "&channels=3&dtype=float32" +
      "&mode=shade&strength=" + strength + "&decoy=" + encodeURIComponent(decoy);

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

  if (typeof window !== "undefined") window.VeilBridge = { health, poisonProtect };
})();
