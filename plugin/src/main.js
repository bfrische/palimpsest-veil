/* Panel logic. Plain-DOM wiring on DOMContentLoaded (same approach as the
 * Detail EQ plugin — no entrypoints.setup needed for a single panel). */
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

  function syncDecoy() {
    const row = $("decoyRow");
    if (row) row.hidden = $("mode").value !== "shade";
  }

  async function onRun() {
    const mode = $("mode").value || "cloak";
    const tier = $("tier").value || "quick";
    const strength = (Number($("strength").value) || 50) / 100;
    const decoy = ($("decoy") && $("decoy").value) || "";
    const btn = $("run");
    if (btn) btn.disabled = true;

    try {
      setProgress(0.05);
      setStatus("Reading document…");
      const px = await window.VeilPS.getActivePixels();

      let out;
      if (tier === "deep") {
        setStatus("Protecting (Deep)… this can take a while.");
        setProgress(0.15);
        out = await window.VeilBridge.deepProtect(px.data01, px.width, px.height, {
          mode: mode,
          strength: strength,
          decoy: decoy,
        });
      } else {
        setStatus("Protecting (Quick)…");
        out = window.VeilQuick.quickProtect(px.data01, px.width, px.height, 3, strength, 1);
      }

      setProgress(0.85);
      setStatus("Writing protected layer…");
      await window.VeilPS.putResultLayer(out, px.width, px.height, px.componentSize, px.colorProfile, "Veil — " + mode);

      setProgress(1);
      setStatus('Done — added "Veil — ' + mode + '" layer.');
    } catch (err) {
      setStatus("Error: " + (err && err.message ? err.message : err));
      setProgress(0);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function wire() {
    const mode = $("mode");
    if (mode) mode.addEventListener("change", syncDecoy);
    const run = $("run");
    if (run) run.addEventListener("click", onRun);

    syncDecoy();
    pollHealth();
    setInterval(pollHealth, 4000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", wire);
  } else {
    wire();
  }
})();
