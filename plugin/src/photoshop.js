/* Photoshop I/O — the only file that touches UXP APIs. Mirrors the proven
 * Imaging-API sequence and the 8/16-bit scaling from the Detail EQ plugin.
 * Works in normalised float [0,1] so 8- and 16-bit documents share one path.
 * Reads the composite and writes the result into a NEW layer (original
 * untouched). Exposes window.VeilPS. */
"use strict";
(function () {
  const { app, core, imaging, action } = require("photoshop");

  function activeDoc() {
    const doc = app.activeDocument;
    if (!doc) throw new Error("Open an image first.");
    return doc;
  }

  function requireRGB(doc) {
    const mode = String(doc.mode);
    if (!/rgb/i.test(mode)) {
      throw new Error(
        "Palimpsest Veil needs an RGB document (this one is " +
          mode.replace(/^DocumentMode\./, "") + ")."
      );
    }
  }

  // Read the flattened composite as normalised float RGB (3 channels, [0,1]).
  async function getActivePixels() {
    const doc = activeDoc();
    requireRGB(doc);
    let result = null;
    await core.executeAsModal(
      async () => {
        const got = await imaging.getPixels({ documentID: doc.id });
        const imageData = got.imageData;
        const width = imageData.width;
        const height = imageData.height;
        const components = imageData.components;
        const componentSize = imageData.componentSize; // 8, 16, or 32
        const raw = await imageData.getData({});
        const profile = imageData.colorProfile;
        imageData.dispose();

        if (componentSize !== 8 && componentSize !== 16) {
          throw new Error(
            "32-bit documents aren't supported — convert to 16-bit (Image ▸ Mode)."
          );
        }
        const scale = componentSize === 8 ? 1 / 255 : 1 / 32768;
        const n = width * height;
        const data01 = new Float32Array(n * 3);
        for (let i = 0; i < n; i++) {
          const s = i * components;
          const o = i * 3;
          data01[o] = raw[s] * scale;
          data01[o + 1] = raw[s + 1] * scale;
          data01[o + 2] = raw[s + 2] * scale;
        }
        result = {
          data01: data01,
          width: width,
          height: height,
          componentSize: componentSize,
          colorProfile: profile,
        };
      },
      { commandName: "Palimpsest Veil: read pixels" }
    );
    return result;
  }

  // data01: Float32 normalised RGB (3 channels). Written back at the document's
  // native bit depth.
  async function putResultLayer(data01, width, height, componentSize, colorProfile, name) {
    const doc = activeDoc();
    await core.executeAsModal(
      async () => {
        const max = componentSize === 8 ? 255 : 32768;
        const Buf = componentSize === 8 ? Uint8Array : Uint16Array;
        const out = new Buf(data01.length);
        for (let i = 0; i < data01.length; i++) {
          let v = data01[i] * max + 0.5;
          out[i] = v < 0 ? 0 : v > max ? max : v | 0;
        }

        const opts = {
          width: width,
          height: height,
          components: 3,
          chunky: true,
          colorSpace: "RGB",
          componentSize: componentSize,
        };
        if (colorProfile) opts.colorProfile = colorProfile;
        const newImg = await imaging.createImageDataFromBuffer(out, opts);

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
