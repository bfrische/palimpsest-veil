/* Document I/O via the modern Imaging API — reads the composite and writes the
 * result into a NEW layer so the original is never touched. All mutations run
 * inside core.executeAsModal, per UXP best practice. */
const { app, core, action, imaging } = require("photoshop");

async function getActivePixels() {
  const doc = app.activeDocument;
  if (!doc) throw new Error("Open a document first.");

  const px = await imaging.getPixels({
    documentID: doc.id,
    componentSize: 8,
    applyAlpha: false,
  });

  const { width, height, components } = px.imageData;
  const raw = await px.imageData.getData({ chunky: true });
  px.imageData.dispose();

  return { data: new Uint8Array(raw), width, height, components };
}

async function putResultLayer(data, width, height, components, name) {
  const doc = app.activeDocument;

  await core.executeAsModal(
    async () => {
      // 1. Make a new (empty) layer; it becomes the active layer.
      await action.batchPlay(
        [
          {
            _obj: "make",
            _target: [{ _ref: "layer" }],
            using: { _obj: "layer", name: name },
          },
        ],
        { synchronousExecution: true }
      );
      const layer = doc.activeLayers[0];

      // 2. Push the protected pixels into that layer.
      const imageData = await imaging.createImageDataFromBuffer(data, {
        width,
        height,
        components,
        componentSize: 8,
        colorSpace: "RGB",
        chunky: true,
      });

      await imaging.putPixels({
        documentID: doc.id,
        layerID: layer.id,
        imageData,
        targetBounds: { left: 0, top: 0, right: width, bottom: height },
        replace: true,
      });

      imageData.dispose();
    },
    { commandName: "Veil: write protected layer" }
  );
}

module.exports = { getActivePixels, putResultLayer };
