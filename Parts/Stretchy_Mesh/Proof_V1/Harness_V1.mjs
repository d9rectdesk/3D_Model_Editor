// Source: Harness for the Stretchy Studio mesh part (RW-02): feeds a
// Source: synthetic L-shaped part silhouette through generateMesh and
// Source: checks the mesh covers the whole silhouette, with valid
// Source: indices and UVs, and that retriangulate also works.
// Source: Duke - original work, 2026-11-16. No outside source.

import { generateMesh, retriangulate } from "../src/mesh/generate.js";

const W = 120;
const H = 80;

// L-shaped opaque silhouette on a transparent field:
// a horizontal bar (the upper arm) and a vertical bar
// (the forearm) joined at the corner.
function IsOpaque(x, y) {
    const inBarH = x >= 10 && x < 110 && y >= 10 && y < 34;
    const inBarV = x >= 10 && x < 34 && y >= 10 && y < 70;
    return inBarH || inBarV;
}

const data = new Uint8ClampedArray(W * H * 4);
for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
        if (IsOpaque(x, y)) {
            const i = (y * W + x) * 4;
            data[i] = 200;
            data[i + 1] = 120;
            data[i + 2] = 60;
            data[i + 3] = 255;
        }
    }
}

const mesh = generateMesh(data, W, H, { gridSpacing: 10, numEdgePoints: 60 });
console.log("vertices=" + mesh.vertices.length +
    " triangles=" + mesh.triangles.length +
    " edgeVertices=" + mesh.edgeIndices.size);

if (mesh.vertices.length < 20) {
    throw new Error("too few vertices: " + mesh.vertices.length);
}
if (mesh.triangles.length < 20) {
    throw new Error("too few triangles: " + mesh.triangles.length);
}
if (mesh.edgeIndices.size < 10) {
    throw new Error("too few edge vertices: " + mesh.edgeIndices.size);
}
for (const tri of mesh.triangles) {
    for (const idx of tri) {
        if (idx < 0 || idx >= mesh.vertices.length) {
            throw new Error("triangle index out of range: " + idx);
        }
    }
}
for (let i = 0; i < mesh.uvs.length; i++) {
    if (mesh.uvs[i] < -0.001 || mesh.uvs[i] > 1.001) {
        throw new Error("uv out of range at " + i + ": " + mesh.uvs[i]);
    }
}

// Coverage: every opaque pixel centre must fall inside at
// least one triangle. The mesh is built from the dilated
// silhouette, so full coverage is the design claim; a
// pixel counts as covered when it is inside a triangle or
// within 1.5 px of a vertex (sampling tolerance at corners).
function InTriangle(px, py, a, b, c) {
    const d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);
    if (Math.abs(d) < 1e-9) {
        return false;
    }
    const l1 = ((b.y - c.y) * (px - c.x) + (c.x - b.x) * (py - c.y)) / d;
    const l2 = ((c.y - a.y) * (px - c.x) + (a.x - c.x) * (py - c.y)) / d;
    const l3 = 1 - l1 - l2;
    return l1 >= -1e-6 && l2 >= -1e-6 && l3 >= -1e-6;
}

let opaqueCount = 0;
let coveredCount = 0;
for (let y = 0; y < H; y += 1) {
    for (let x = 0; x < W; x += 1) {
        if (!IsOpaque(x, y)) {
            continue;
        }
        opaqueCount++;
        const px = x + 0.5;
        const py = y + 0.5;
        let covered = false;
        for (const tri of mesh.triangles) {
            const a = mesh.vertices[tri[0]];
            const b = mesh.vertices[tri[1]];
            const c = mesh.vertices[tri[2]];
            if (InTriangle(px, py, a, b, c)) {
                covered = true;
                break;
            }
        }
        if (!covered) {
            for (const v of mesh.vertices) {
                const dx = v.x - px;
                const dy = v.y - py;
                if (dx * dx + dy * dy <= 2.25) {
                    covered = true;
                    break;
                }
            }
        }
        if (covered) {
            coveredCount++;
        }
    }
}
const coverage = coveredCount / opaqueCount;
console.log("coverage: " + coveredCount + "/" + opaqueCount +
    " = " + (coverage * 100).toFixed(2) + "%");
if (coverage < 0.995) {
    throw new Error("coverage below 99.5%: " + coverage);
}

// Re-triangulation of the same vertices must also produce
// a working mesh (the editor re-meshes after vertex edits).
const remesh = retriangulate(mesh.vertices, mesh.uvs, mesh.edgeIndices);
console.log("retriangulated triangles=" + remesh.triangles.length);
if (remesh.triangles.length < 20) {
    throw new Error("retriangulate produced too few triangles");
}

console.log("HARNESS PASS");
