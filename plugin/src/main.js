/* Entry point: register the panel and hand off UI wiring to ui.js. */
const { entrypoints } = require("uxp");
const ui = require("./ui.js");

entrypoints.setup({
  panels: {
    veilPanel: {
      show() {
        ui.init();
      },
    },
  },
});

// If the DOM is already parsed when the panel shows, init immediately too.
if (document.readyState === "complete" || document.readyState === "interactive") {
  ui.init();
} else {
  document.addEventListener("DOMContentLoaded", () => ui.init());
}
