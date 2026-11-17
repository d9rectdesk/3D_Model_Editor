// Source: Stretchy Studio part-mesh generation - a part layer's
// Source: silhouette becomes a triangulated deformation mesh (RW-02).
// Source: Project MangoLion/stretchystudio, file src/mesh/delaunay.js, commit 24a83a27ba43e43e9d2e3de5e33994594e6199c2.
// Source: Licence MIT, Copyright (c) 2026 Nguyen Phan - see the
// Source: LICENSE staged with this part. Copied literally
// Source: 2026-11-16; only this header differs from the
// Source: original file.
/**
 * Delaunay triangulation using the `delaunator` library (MIT).
 *
 * Replaces the hand-rolled Bowyer-Watson from the prototype.
 * delaunator is ~3KB, numerically robust, and the de-facto standard.
 */
import Delaunator from 'delaunator';

/**
 * Triangulate a set of 2-D points.
 *
 * @param {Array<[number,number]>} points
 * @returns {Array<[number,number,number]>}  Triangles as vertex-index triplets
 */
export function triangulate(points) {
  if (points.length < 3) return [];

  // delaunator expects a flat [x0,y0, x1,y1, …] array
  const coords = new Float64Array(points.length * 2);
  for (let i = 0; i < points.length; i++) {
    coords[i * 2]     = points[i][0];
    coords[i * 2 + 1] = points[i][1];
  }

  const d = new Delaunator(coords);
  const triangles = [];

  for (let i = 0; i < d.triangles.length; i += 3) {
    triangles.push([d.triangles[i], d.triangles[i + 1], d.triangles[i + 2]]);
  }

  return triangles;
}
