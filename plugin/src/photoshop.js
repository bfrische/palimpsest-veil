/* Photoshop I/O — the only file that touches UXP APIs. Mirrors the proven
 * Imaging-API sequence from the Detail EQ plugin. Reads the composite and
 * writes the protected result into a NEW layer (original untouched). Exposes
 * window.VeilPS. */
"use strict";
(function () {
  const { app, core, imaging, action } = require("photoshop");

  function activeDoc() {
    const doc = app.activeDocument;
    if (!doc) throw new Error("Open an image first.");
    return doc;
  }

  function checkSupported(doc) {
    const mode = String(doc.mode);
    if (!/rgb/i.test(mode)) {
      throw new Error(
        "Palimpsest Veil needs an RGB document (this one is " +
          mode.replace(/^DocumentMode\./, "") + ")."
      );
    }
    const bits = String(doc.bitsPerChannel);
    if (!/eight|(^|[^1-9])8/i.test(bits)) {
      throw new Error("Please convert to 8-bit first (Image ▸ Mode ▸ 8 Bits/Channel).");
    }
  }

  // Read the flattened composite as interleaved RGB (3 components, 8-bit).
  async function getActivePixels() {
    const doc = activeDoc();
    checkSupported(doc);
    let result = null;
    await core.executeAsModal(
      async () => {
        const got = await imaging.getPixels({ documentID: doc.id });
        const imageData = got.imageData;
        const width = imageData.width;
        const height = imageData.height;
        const components = imageData.components;
        const raw = await imageData.getData({});
        const profile = imageData.colorProfile;
        imageData.dispose();

        // Normalise to exactly 3 components so the write path matches the
        // proven Detail EQ layout (drops alpha if the source had it).
        let rgb;
        if (components === 3) {
          rgb = new Uint8Array(raw);
        } else {
          const n = width * height;
          rgb = new Uint8Array(n * 3);
          for (let i = 0; i < n; i++) {
            rgb[i * 3] = raw[i * components];
            rgb[i * 3 + 1] = raw[i * components + 1];
            rgb[i * 3 + 2] = raw[i * components + 2];
          }
        }
        result = { data: rgb, width: width, height: height, components: 3, colorProfile: profile };
      },
      { commandName: "Palimpsest Veil: read pixels" }
    );
    return result;
  }

  async function putResultLayer(outData, width, height, colorProfile, name) {
    const doc = activeDoc();
    await core.executeAsModal(
      async () => {
        const opts = {
          width: width,
          height: height,
          components: 3,
          chunky: true,
          colorSpace: "RGB",
          componentSize: 8,
        };
        if (colorProfile) opts.colorProfile = colorProfile;
        const newImg = await imaging.createImageDataFromBuffer(outData, opts);

        let layer;
        if (typeof doc.createLayer === "function") {
          layer = await doc.createLayer({ name: name });
        } else {
          await action.batchPlay([{ _obj: "make", _target: [{ _ref: "layer" }] }], {});
          layer = doc.activeLayers[0];
          layer.name = name;
        }

        await imaging.putPixels({
          documentID: doc.id,
          layerID: layer.id,
          imageData: newImg,
          replace: true,
        });
        newImg.dispose();
      },
      { commandName: "Palimpsest Veil: write layer" }
    );
  }

  window.VeilPS = { getActivePixels, putResultLayer };
})();
