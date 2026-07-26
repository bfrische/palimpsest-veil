/* Panel logic — single-purpose Poison tool. */
"use strict";
(function () {
  const $ = (id) => document.getElementById(id);
  const setStatus = (t) => { const s = $("status"); if (s) s.textContent = t || ""; };
  const setProgress = (f) => {
    const b = $("bar");
    if (b) b.style.width = Math.round(Math.max(0, Math.min(1, f)) * 100) + "%";
  };

  async function pollHealth() {
    let ok = false;
    try { ok = await window.VeilBridge.health(); } catch (e) { ok = false; }
    const dot = $("dot");
    const t = $("engineText");
    if (dot) dot.classList.toggle("on", ok);
    if (t) t.textContent = ok ? "Engine: running" : "Engine: not running (run install.command)";
  }

  async function onRun() {
    const decoy = ($("decoy") && $("decoy").value || "").trim();
    const strength = (Number($("strength").value) || 60) / 100;
    if (!decoy) {
      setStatus("Enter a decoy concept first (e.g. 'a vintage car').");
      return;
    }
    const btn = $("run");
    if (btn) btn.disabled = true;

    try {
      setProgress(0.05);
      setStatus("Reading document…");
      const px = await window.VeilPS.getActivePixels();

      setStatus("Poisoning toward “" + decoy + "”… first run for a new concept can take a couple minutes.");
      setProgress(0.15);
      const out = await window.VeilBridge.poisonProtect(px.data01, px.width, px.height, {
        decoy: decoy,
        strength: strength,
      });

      setProgress(0.85);
      setStatus("Writing poisoned layer…");
      await window.VeilPS.putResultLayer(out, px.width, px.height, px.componentSize, px.colorProfile, "Veil — poison");

      setProgress(1.0);
      setStatus("Done — added a poisoned layer (decoy: " + decoy + ").");
    } catch (err) {
      setStatus("Error: " + (err && err.message ? err.message : err));
      setProgress(0);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function wire() {
    const run = $("run");
    if (run) run.addEventListener("click", onRun);
    pollHealth();
    setInterval(pollHealth, 4000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
