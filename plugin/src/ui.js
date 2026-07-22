/* Panel UI wiring + run orchestration. */
const photoshop = require("./photoshop.js");
const quick = require("./quick.js");
const bridge = require("./bridge.js");

let initialized = false;
let healthTimer = null;

const $ = (id) => document.getElementById(id);

function setStatus(msg) {
  const s = $("status");
  if (s) s.textContent = msg;
}

function setProgress(f) {
  const b = $("bar");
  if (b) b.style.width = Math.round(Math.max(0, Math.min(1, f)) * 100) + "%";
}

async function pollHealth() {
  const dot = $("dot");
  const ok = await bridge.health();
  if (dot) {
    dot.classList.toggle("on", ok);
    dot.classList.toggle("off", !ok);
  }
  return ok;
}

function init() {
  if (initialized) return;
  initialized = true;

  const modeGroup = $("mode");
  const decoyRow = $("decoyRow");
  const strength = $("strength");
  const strengthVal = $("strengthVal");
  const run = $("run");

  if (modeGroup) {
    modeGroup.addEventListener("change", () => {
      decoyRow.hidden = modeGroup.selected !== "shade";
    });
  }
  if (strength) {
    strength.addEventListener("input", () => {
      strengthVal.textContent = String(strength.value);
    });
  }
  if (run) run.addEventListener("click", onRun);

  pollHealth();
  healthTimer = setInterval(pollHealth, 4000);
}

async function onRun() {
  const mode = ($("mode") && $("mode").selected) || "cloak";
  const tier = ($("tier") && $("tier").selected) || "quick";
  const strength = Number(($("strength") && $("strength").value) || 50) / 100;
  const decoy = ($("decoy") && $("decoy").value) || "";
  const runBtn = $("run");
  if (runBtn) runBtn.disabled = true;

  try {
    setProgress(0.03);
    setStatus("Reading document…");
    const { data, width, height, components } = await photoshop.getActivePixels();

    let result;
    if (tier === "deep") {
      setStatus("Protecting (Deep)… this can take a while.");
      setProgress(0.15);
      result = await bridge.deepProtect(data, width, height, components, {
        mode,
        strength,
        decoy,
      });
    } else {
      setStatus("Protecting (Quick)…");
      result = quick.quickProtect(data, width, height, components, strength);
    }

    setProgress(0.85);
    setStatus("Writing protected layer…");
    await photoshop.putResultLayer(result, width, height, components, `Veil — ${mode}`);

    setProgress(1.0);
    setStatus(`Done — added "Veil — ${mode}" layer.`);
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    setStatus("Error: " + msg);
    setProgress(0);
  } finally {
    if (runBtn) runBtn.disabled = false;
  }
}

module.exports = { init };
