// Source: Stretchy Studio part-mesh generation - a part layer's
// Source: silhouette becomes a triangulated deformation mesh (RW-02).
// Source: Project MangoLion/stretchystudio, file src/mesh/worker.js, commit 24a83a27ba43e43e9d2e3de5e33994594e6199c2.
// Source: Licence MIT, Copyright (c) 2026 Nguyen Phan - see the
// Source: LICENSE staged with this part. Copied literally
// Source: 2026-11-16; only this header differs from the
// Source: original file.
/**
 * Mesh generation Web Worker entry point.
 *
 * Receives:  { imageData: {data, width, height}, opts }
 * Responds:  { vertices, uvs, triangles, edgeIndices }
 *
 * Note: Sets (edgeIndices) can't be transferred — send as plain Array.
 */
import { generateMesh } from './generate.js';

self.onmessage = function (e) {
  const { imageData, opts } = e.data;

  try {
    const result = generateMesh(
      imageData.data,
      imageData.width,
      imageData.height,
      opts
    );

    // Serialise the Set → Array for postMessage
    self.postMessage({
      ok: true,
      vertices: result.vertices,
      uvs: result.uvs,
      triangles: result.triangles,
      edgeIndices: Array.from(result.edgeIndices),
    }, [result.uvs.buffer]); // Transfer the Float32Array buffer

  } catch (err) {
    self.postMessage({ ok: false, error: err.message });
  }
};
