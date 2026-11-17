/* Paper_Doll_Pipeline_V1.JS - Model Editor V19's paper doll
   pipeline: Bits 1 through 5 of the Paper Doll Plan, run by
   the editor itself on one pick of the man's three pictures.
   Every stage is a port of the proven Python instrument that
   passed that bit, named at its section: Cut_Clean_Cutouts_V1.PY
   (Bit 1), Split_Into_Parts_V1.PY (Bit 2), Complete_And_Buffer_V1.PY
   (Bit 3), Build_Paper_Doll_GLB_V1.PY (Bit 4), and
   Build_Paper_Doll_3D_V1.PY (Bit 5). The walk page template is
   Build_Paper_Doll_Walk_V1.PY's (Bit 6), carried base64 in
   PD_WALK_TPL_B64 and filled with this run's own GLB.
   Kevin, original work apart from the ported blocks. */
// Source: Kevin, original work - the paper doll pipeline
// in page form (Model Editor V19): Bits 1 through 5 of the
// Paper Doll Plan, each stage a port of the proven Python
// instrument named at its section, as the header above
// describes in full (gate-format mark retrofitted 2026-11-17).
"use strict";
const PD_CANVAS = 2048;
const PD_VIEWS = ["Front", "Back", "SideRight", "SideLeft"];

/* ---- tables copied from Split_Into_Parts_V1.PY (Kevin) ---- */
// Source: Kevin, original work; tables copied from
// Split_Into_Parts_V1.PY (Kevin).
const PD_Front_Pins_Rel = {
  neck: [498, 238], shoulder_l: [713, 283], shoulder_r: [288, 283],
  elbow_l: [807, 396], elbow_r: [221, 397],
  wrist_l: [865, 503], wrist_r: [130, 503],
  hip_l: [608, 609], hip_r: [378, 610],
  knee_l: [656, 691], knee_r: [320, 692],
  ankle_l: [704, 856], ankle_r: [262, 857],
  head_top: [498, 120], pelvis: [493, 610], chest: [498, 302],
  hand_tip_l: [915, 590], hand_tip_r: [80, 588],
  toe_l: [898, 923], toe_r: [106, 924] };
const PD_Back_Pins_Rel = {
  neck: [500, 199], shoulder_l: [714, 254], shoulder_r: [286, 254],
  elbow_l: [763, 404], elbow_r: [237, 404],
  wrist_l: [808, 487], wrist_r: [192, 487],
  hip_l: [571, 500], hip_r: [429, 500],
  knee_l: [625, 696], knee_r: [375, 696],
  ankle_l: [656, 879], ankle_r: [344, 879],
  head_top: [500, 49], pelvis: [500, 487], chest: [500, 232],
  hand_tip_l: [821, 554], hand_tip_r: [179, 554],
  toe_l: [768, 915], toe_r: [232, 915] };
const PD_Side_Pins = {
  head_top: [1040, 200], neck: [1025, 460],
  chest: [1000, 600], pelvis: [990, 1120],
  shoulder_n: [1004, 610], elbow_n: [1255, 639],
  wrist_n: [1520, 633], hand_tip_n: [1714, 627],
  shoulder_f: [880, 685], elbow_f: [799, 795],
  wrist_f: [668, 969], hand_tip_f: [582, 1112],
  hip_n: [1050, 1120], knee_n: [1274, 1389],
  ankle_n: [1255, 1779], toe_n: [1438, 1871],
  hip_f: [930, 1140], knee_f: [774, 1444],
  ankle_f: [477, 1679], toe_f: [524, 1859],
  eye: [1133, 354] };
const PD_Front_Back_Bones = {
  Head: ["neck", "head_top"], Neck: ["chest", "neck"],
  Torso: ["pelvis", "chest"],
  Arm_Upper_Left: ["shoulder_l", "elbow_l"],
  Arm_Upper_Right: ["shoulder_r", "elbow_r"],
  Arm_Fore_Left: ["elbow_l", "wrist_l"],
  Arm_Fore_Right: ["elbow_r", "wrist_r"],
  Hand_Left: ["wrist_l", "hand_tip_l"],
  Hand_Right: ["wrist_r", "hand_tip_r"],
  Thigh_Left: ["hip_l", "knee_l"], Thigh_Right: ["hip_r", "knee_r"],
  Shin_Left: ["knee_l", "ankle_l"], Shin_Right: ["knee_r", "ankle_r"],
  Foot_Left: ["ankle_l", "toe_l"], Foot_Right: ["ankle_r", "toe_r"] };
const PD_Side_Bones = {
  Head: ["neck", "head_top"], Neck: ["chest", "neck"],
  Torso: ["pelvis", "chest"],
  Arm_Upper_Near: ["shoulder_n", "elbow_n"],
  Arm_Fore_Near: ["elbow_n", "wrist_n"],
  Hand_Near: ["wrist_n", "hand_tip_n"],
  Arm_Upper_Far: ["shoulder_f", "elbow_f"],
  Arm_Fore_Far: ["elbow_f", "wrist_f"],
  Hand_Far: ["wrist_f", "hand_tip_f"],
  Thigh_Near: ["hip_n", "knee_n"], Shin_Near: ["knee_n", "ankle_n"],
  Foot_Near: ["ankle_n", "toe_n"],
  Thigh_Far: ["hip_f", "knee_f"], Shin_Far: ["knee_f", "ankle_f"],
  Foot_Far: ["ankle_f", "toe_f"] };
const PD_Split_Line = { Front: 765, Back: 755, SideRight: 795 };
const PD_Neck_Half = { Front: 70, Back: 70, SideRight: 62 };
const PD_Face_Features = {
  Front: [["Eye_Right", [978, 344], [36, 26]],
          ["Eye_Left", [1071, 344], [36, 26]],
          ["Mouth", [1025, 431], [46, 15]]],
  Back: [],
  SideRight: [["Eye_Side", [1133, 354], [28, 20]]] };
const PD_Expected = {
  Front: ["Head", "Eye_Right", "Eye_Left", "Mouth",
    "Torso_Top", "Torso_Middle", "Pelvis",
    "Arm_Upper_Left", "Arm_Fore_Left", "Hand_Left",
    "Arm_Upper_Right", "Arm_Fore_Right", "Hand_Right",
    "Thigh_Left", "Shin_Left", "Foot_Left",
    "Thigh_Right", "Shin_Right", "Foot_Right"],
  Back: ["Head", "Torso_Top", "Torso_Middle", "Pelvis",
    "Arm_Upper_Left", "Arm_Fore_Left", "Hand_Left",
    "Arm_Upper_Right", "Arm_Fore_Right", "Hand_Right",
    "Thigh_Left", "Shin_Left", "Foot_Left",
    "Thigh_Right", "Shin_Right", "Foot_Right"],
  SideRight: ["Head", "Eye_Side", "Torso_Top", "Torso_Middle", "Pelvis",
    "Arm_Upper_Near", "Arm_Fore_Near", "Hand_Near",
    "Arm_Upper_Far", "Arm_Fore_Far", "Hand_Far",
    "Thigh_Near", "Shin_Near", "Foot_Near",
    "Thigh_Far", "Shin_Far", "Foot_Far"] };
PD_Expected.SideLeft = PD_Expected.SideRight.slice();

/* ---- tables copied from Complete_And_Buffer_V1.PY (Kevin) ---- */
// Source: Kevin, original work; tables copied from
// Complete_And_Buffer_V1.PY (Kevin).
const PD_Waist_Pin = { Front: [1022.0, 994.0], Back: [1024.0, 977.0],
  SideRight: [990.0, 994.0] };
const PD_Layer_Order = {
  Front: ["Foot_Left", "Foot_Right", "Shin_Left", "Shin_Right",
    "Thigh_Left", "Thigh_Right",
    "Hand_Left", "Hand_Right", "Arm_Fore_Left", "Arm_Fore_Right",
    "Pelvis", "Torso_Middle", "Torso_Top",
    "Arm_Upper_Left", "Arm_Upper_Right",
    "Head", "Eye_Right", "Eye_Left", "Mouth"],
  Back: ["Foot_Left", "Foot_Right", "Shin_Left", "Shin_Right",
    "Thigh_Left", "Thigh_Right",
    "Hand_Left", "Hand_Right", "Arm_Fore_Left", "Arm_Fore_Right",
    "Pelvis", "Torso_Middle", "Torso_Top",
    "Arm_Upper_Left", "Arm_Upper_Right", "Head"],
  SideRight: ["Foot_Far", "Shin_Far", "Thigh_Far",
    "Hand_Far", "Arm_Fore_Far", "Arm_Upper_Far",
    "Foot_Near", "Shin_Near", "Thigh_Near",
    "Pelvis", "Torso_Middle", "Torso_Top",
    "Arm_Upper_Near", "Arm_Fore_Near", "Hand_Near",
    "Head", "Eye_Side"] };
PD_Layer_Order.SideLeft = PD_Layer_Order.SideRight.slice();

/* ---- small instruments ---- */
// Source: Kevin, original work.
function PD_log(msg) {
  const el = document.getElementById("dollLog");
  if (el) el.textContent += (el.textContent ? "\n" : "") + msg;
  if (typeof status === "function") status(msg);
}
function PD_pinsOnCanvas(rel) {
  const out = {};
  for (const k of Object.keys(rel))
    out[k] = [524 + rel[k][0] / 1000 * 1000, 24 + rel[k][1] / 1000 * 2000];
  return out;
}
/* Connected components of a binary mask (4-way), the
   scipy.ndimage.label of the Python instruments. */
function PD_label(mask) {
  const N = PD_CANVAS * PD_CANVAS;
  const labels = new Int32Array(N);
  const sizes = [];
  const stack = new Int32Array(N);
  let count = 0;
  for (let s = 0; s < N; s++) {
    if (!mask[s] || labels[s]) continue;
    count += 1;
    let sp = 0, size = 0;
    stack[sp++] = s; labels[s] = count;
    while (sp > 0) {
      const p = stack[--sp]; size += 1;
      const x = p % PD_CANVAS, y = (p / PD_CANVAS) | 0;
      if (x > 0 && mask[p - 1] && !labels[p - 1]) { labels[p - 1] = count; stack[sp++] = p - 1; }
      if (x < PD_CANVAS - 1 && mask[p + 1] && !labels[p + 1]) { labels[p + 1] = count; stack[sp++] = p + 1; }
      if (y > 0 && mask[p - PD_CANVAS] && !labels[p - PD_CANVAS]) { labels[p - PD_CANVAS] = count; stack[sp++] = p - PD_CANVAS; }
      if (y < PD_CANVAS - 1 && mask[p + PD_CANVAS] && !labels[p + PD_CANVAS]) { labels[p + PD_CANVAS] = count; stack[sp++] = p + PD_CANVAS; }
    }
    sizes.push(size);
  }
  return { labels, count, sizes };
}
/* Cross erosion, matching scipy.ndimage.binary_erosion's
   default cross structure - the Python instrument's edge
   band is one cross deep, and a 3x3 band counts diagonal
   neighbours the proven check never counted. */
function PD_erode(mask) {
  const out = new Uint8Array(mask.length);
  const C = PD_CANVAS;
  for (let y = 0; y < C; y++) for (let x = 0; x < C; x++) {
    const p = y * C + x;
    if (!mask[p]) continue;
    if (x === 0 || y === 0 || x === C - 1 || y === C - 1) continue;
    if (mask[p - 1] && mask[p + 1] && mask[p - C] && mask[p + C])
      out[p] = 1;
  }
  return out;
}
function PD_fillHoles(mask) {
  const N = mask.length, C = PD_CANVAS;
  const reached = new Uint8Array(N);
  const stack = new Int32Array(N);
  let sp = 0;
  const seed = (p) => { if (!mask[p] && !reached[p]) { reached[p] = 1; stack[sp++] = p; } };
  for (let x = 0; x < C; x++) { seed(x); seed((C - 1) * C + x); }
  for (let y = 0; y < C; y++) { seed(y * C); seed(y * C + C - 1); }
  while (sp > 0) {
    const p = stack[--sp];
    const x = p % C, y = (p / C) | 0;
    if (x > 0) seed(p - 1);
    if (x < C - 1) seed(p + 1);
    if (y > 0) seed(p - C);
    if (y < C - 1) seed(p + C);
  }
  const out = new Uint8Array(N);
  for (let i = 0; i < N; i++) out[i] = (mask[i] || !reached[i]) ? 1 : 0;
  return out;
}
function PD_segDist(px, py, A, B) {
  const abx = B[0] - A[0], aby = B[1] - A[1];
  let t = ((px - A[0]) * abx + (py - A[1]) * aby) / (abx * abx + aby * aby);
  t = Math.max(0, Math.min(1, t));
  const cx = A[0] + t * abx, cy = A[1] + t * aby;
  return Math.hypot(px - cx, py - cy);
}
function PD_canvasFromRGBA(rgba) {
  const c = document.createElement("canvas");
  c.width = PD_CANVAS; c.height = PD_CANVAS;
  c.getContext("2d").putImageData(new ImageData(new Uint8ClampedArray(rgba), PD_CANVAS, PD_CANVAS), 0, 0);
  return c;
}
function PD_blobOf(canvas) {
  return new Promise(r => canvas.toBlob(r, "image/png"));
}
async function PD_rgbaOfBlob(blob) {
  const bmp = await createImageBitmap(blob);
  const c = document.createElement("canvas");
  c.width = PD_CANVAS; c.height = PD_CANVAS;
  const g = c.getContext("2d");
  g.drawImage(bmp, 0, 0);
  return g.getImageData(0, 0, PD_CANVAS, PD_CANVAS).data;
}
function PD_download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = name; a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}
function PD_b64(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 32768)
    s += String.fromCharCode.apply(null, bytes.subarray(i, i + 32768));
  return btoa(s);
}

/* ---- Bit 1: clean cutouts, ported from
   Cut_Clean_Cutouts_V1.PY (Kevin) ---- */
// Source: Kevin, original work; ported from
// Cut_Clean_Cutouts_V1.PY (Kevin).
function PD_cutOne(img) {
  const C = PD_CANVAS;
  const SW = img.naturalWidth || img.width, SH = img.naturalHeight || img.height;
  const scale = (C - 48) / SH;
  const NW = Math.trunc(SW * scale), NH = Math.trunc(SH * scale);
  const OX = Math.trunc((C - NW) / 2), OY = Math.trunc((C - NH) / 2);
  const cv = document.createElement("canvas");
  cv.width = C; cv.height = C;
  const g = cv.getContext("2d");
  g.fillStyle = "rgb(246,246,246)"; g.fillRect(0, 0, C, C);
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(img, OX, OY, NW, NH);
  const rgba = g.getImageData(0, 0, C, C).data;
  const N = C * C;
  const cand = new Uint8Array(N);
  for (let i = 0; i < N; i++) {
    const r = rgba[4 * i], gg = rgba[4 * i + 1], b = rgba[4 * i + 2];
    const lum = (r + gg + b) / 3;
    const spread = Math.max(r, gg, b) - Math.min(r, gg, b);
    if (lum >= 236 && spread <= 20) cand[i] = 1;
  }
  const lab = PD_label(cand);
  const border = new Set();
  for (let x = 0; x < C; x++) { border.add(lab.labels[x]); border.add(lab.labels[(C - 1) * C + x]); }
  for (let y = 0; y < C; y++) { border.add(lab.labels[y * C]); border.add(lab.labels[y * C + C - 1]); }
  border.delete(0);
  let figure = new Uint8Array(N);
  for (let i = 0; i < N; i++) figure[i] = border.has(lab.labels[i]) ? 0 : 1;
  const labF = PD_label(figure);
  let keep = 1;
  for (let k = 0; k < labF.count; k++) if (labF.sizes[k] > labF.sizes[keep - 1]) keep = k + 1;
  figure = new Uint8Array(N);
  const out = new Uint8ClampedArray(rgba);
  let figCount = 0;
  for (let i = 0; i < N; i++) {
    figure[i] = labF.labels[i] === keep ? 1 : 0;
    out[4 * i + 3] = figure[i] ? 255 : 0;
    figCount += figure[i];
  }
  return { rgba: out, figure, figurePixels: figCount };
}
/* The Bit 1 check, ported from Check_One in the same script. */
function PD_checkCutout(rgba) {
  const N = PD_CANVAS * PD_CANVAS;
  const sil = new Uint8Array(N);
  for (let i = 0; i < N; i++) sil[i] = rgba[4 * i + 3] > 0 ? 1 : 0;
  const filled = PD_fillHoles(sil);
  let inside = 0;
  for (let i = 0; i < N; i++) if (filled[i] && !sil[i]) inside += 1;
  const er = PD_erode(sil);
  let fringe = 0;
  for (let i = 0; i < N; i++) {
    if (sil[i] && !er[i]) {
      const mn = Math.min(rgba[4 * i], rgba[4 * i + 1], rgba[4 * i + 2]);
      if (mn >= 240 && rgba[4 * i + 3] >= 250) fringe += 1;
    }
  }
  let fig = 0;
  for (let i = 0; i < N; i++) fig += sil[i];
  return { inside, fringe, figure: fig };
}

/* ---- Bit 2: split into parts, ported from
   Split_Into_Parts_V1.PY (Kevin) ---- */
// Source: Kevin, original work; ported from
// Split_Into_Parts_V1.PY (Kevin).
function PD_unify(masks, figure) {
  const names = Object.keys(masks);
  const C = PD_CANVAS, N = C * C;
  for (let sweep = 0; sweep < 12; sweep++) {
    const owner = new Int32Array(N).fill(-1);
    names.forEach((nm, ix) => {
      const m = masks[nm];
      for (let i = 0; i < N; i++) if (m[i]) owner[i] = ix;
    });
    let changed = false;
    for (let ix = 0; ix < names.length; ix++) {
      const nm = names[ix];
      const lab = PD_label(masks[nm]);
      if (lab.count <= 1) continue;
      let keeper = 1;
      for (let k = 0; k < lab.count; k++) if (lab.sizes[k] > lab.sizes[keeper - 1]) keeper = k + 1;
      for (let piece = 1; piece <= lab.count; piece++) {
        if (piece === keeper) continue;
        const counts = new Array(names.length).fill(0);
        for (let i = 0; i < N; i++) {
          if (lab.labels[i] !== piece) continue;
          const x = i % C, y = (i / C) | 0;
          const ring = [i - 1, i + 1, i - C, i + C];
          for (const q of ring) {
            if (q < 0 || q >= N || Math.abs((q % C) - x) > 1) continue;
            if (lab.labels[q] === piece || !figure[q]) continue;
            if (owner[q] >= 0) counts[owner[q]] += 1;
          }
        }
        let target = -1, best = 0;
        counts.forEach((v, k) => { if (v > best) { best = v; target = k; } });
        if (target < 0 || target === ix) continue;
        for (let i = 0; i < N; i++) {
          if (lab.labels[i] === piece) {
            masks[nm][i] = 0; masks[names[target]][i] = 1; owner[i] = target;
          }
        }
        changed = true;
      }
    }
    if (!changed) break;
  }
  return masks;
}
function PD_splitOne(view, rgba, pins, bones) {
  const C = PD_CANVAS, N = C * C;
  const figure = new Uint8Array(N);
  const lum = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    figure[i] = rgba[4 * i + 3] === 255 ? 1 : 0;
    lum[i] = (rgba[4 * i] + rgba[4 * i + 1] + rgba[4 * i + 2]) / 3;
  }
  const boneNames = Object.keys(bones);
  const owner = new Int16Array(N).fill(-1);
  const best = new Float64Array(N).fill(1e18);
  const figIdx = [];
  for (let i = 0; i < N; i++) if (figure[i]) figIdx.push(i);
  boneNames.forEach((nm, bi) => {
    const A = pins[bones[nm][0]], B = pins[bones[nm][1]];
    for (const i of figIdx) {
      const d = PD_segDist(i % C, (i / C) | 0, A, B);
      if (d < best[i]) { best[i] = d; owner[i] = bi; }
    }
  });
  let masks = {};
  boneNames.forEach((nm, bi) => {
    const m = new Uint8Array(N);
    for (let i = 0; i < N; i++) if (owner[i] === bi) m[i] = 1;
    masks[nm] = m;
  });
  /* The shorts are the pelvis: the cloth test, largest piece. */
  let cloth = new Uint8Array(N);
  for (let i = 0; i < N; i++)
    if (figure[i] && (rgba[4 * i + 2] - rgba[4 * i]) > 12 && lum[i] < 120) cloth[i] = 1;
  const labC = PD_label(cloth);
  if (labC.count > 0) {
    let keep = 1;
    for (let k = 0; k < labC.count; k++) if (labC.sizes[k] > labC.sizes[keep - 1]) keep = k + 1;
    cloth = new Uint8Array(N);
    for (let i = 0; i < N; i++) cloth[i] = labC.labels[i] === keep ? 1 : 0;
  }
  for (const nm of Object.keys(masks))
    for (let i = 0; i < N; i++) if (cloth[i]) masks[nm][i] = 0;
  /* The head carries the whole neck, inside the neck column. */
  const neck = masks.Neck; delete masks.Neck;
  const head = masks.Head; delete masks.Head;
  const torso = masks.Torso; delete masks.Torso;
  const A = pins[bones.Neck[0]], B = pins[bones.Neck[1]];
  const newHead = new Uint8Array(head), newTorso = new Uint8Array(torso);
  for (let i = 0; i < N; i++) {
    if (!neck[i]) continue;
    if (PD_segDist(i % C, (i / C) | 0, A, B) <= PD_Neck_Half[view]) newHead[i] = 1;
    else newTorso[i] = 1;
  }
  const line = PD_Split_Line[view];
  const top = new Uint8Array(N), mid = new Uint8Array(N);
  for (let y = 0; y < C; y++) for (let x = 0; x < C; x++) {
    const i = y * C + x;
    if (!newTorso[i]) continue;
    if (y < line) top[i] = 1; else mid[i] = 1;
  }
  masks.Torso_Top = top; masks.Torso_Middle = mid;
  masks.Pelvis = cloth;
  /* Face features carved from the head. */
  let headNow = newHead;
  for (const [nm, centre, radii] of PD_Face_Features[view]) {
    let feat = new Uint8Array(N);
    const x0 = Math.max(0, centre[0] - radii[0] - 1), x1 = Math.min(C - 1, centre[0] + radii[0] + 1);
    const y0 = Math.max(0, centre[1] - radii[1] - 1), y1 = Math.min(C - 1, centre[1] + radii[1] + 1);
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const i = y * C + x;
      const z = ((x - centre[0]) / radii[0]) ** 2 + ((y - centre[1]) / radii[1]) ** 2;
      if (z <= 1 && headNow[i] && lum[i] < 110) feat[i] = 1;
    }
    const lab = PD_label(feat);
    if (lab.count > 0) {
      let keep = 1;
      for (let k = 0; k < lab.count; k++) if (lab.sizes[k] > lab.sizes[keep - 1]) keep = k + 1;
      feat = new Uint8Array(N);
      for (let i = 0; i < N; i++) feat[i] = lab.labels[i] === keep ? 1 : 0;
    }
    masks[nm] = feat;
    for (let i = 0; i < N; i++) if (feat[i]) headNow[i] = 0;
  }
  masks.Head = headNow;
  masks = PD_unify(masks, figure);
  return masks;
}
/* The Bit 2 check on one view's masks, read off the masks
   themselves (the Python check reads the saved files back;
   the stitch battery re-runs that read-back in Python). */
function PD_checkSplit(view, masks, figure) {
  const C = PD_CANVAS, N = C * C;
  const cover = new Int32Array(N);
  let censusOk = true, partsOk = true;
  const found = Object.keys(masks).sort();
  const want = PD_Expected[view].slice().sort();
  if (JSON.stringify(found) !== JSON.stringify(want)) censusOk = false;
  for (const nm of PD_Expected[view]) {
    const m = masks[nm];
    if (!m) { partsOk = false; continue; }
    for (let i = 0; i < N; i++) cover[i] += m[i];
    if (PD_label(m).count !== 1) partsOk = false;
  }
  let overlap = 0, missing = 0, extra = 0;
  for (let i = 0; i < N; i++) {
    if (cover[i] > 1) overlap += 1;
    if (figure[i] && cover[i] === 0) missing += 1;
    if (!figure[i] && cover[i] > 0) extra += 1;
  }
  return { censusOk, partsOk, overlap, missing, extra,
           ok: censusOk && partsOk && overlap === 0 && missing === 0 && extra === 0 };
}
function PD_partRGBA(rgba, mask) {
  const N = PD_CANVAS * PD_CANVAS;
  const out = new Uint8ClampedArray(N * 4);
  for (let i = 0; i < N; i++) {
    if (!mask[i]) continue;
    out[4 * i] = rgba[4 * i]; out[4 * i + 1] = rgba[4 * i + 1];
    out[4 * i + 2] = rgba[4 * i + 2]; out[4 * i + 3] = 255;
  }
  return out;
}
function PD_flipRGBA(rgba) {
  const C = PD_CANVAS;
  const out = new Uint8ClampedArray(rgba.length);
  for (let y = 0; y < C; y++) for (let x = 0; x < C; x++) {
    const s = (y * C + (C - 1 - x)) * 4, d = (y * C + x) * 4;
    out[d] = rgba[s]; out[d + 1] = rgba[s + 1]; out[d + 2] = rgba[s + 2]; out[d + 3] = rgba[s + 3];
  }
  return out;
}

/* ---- Bit 3: completion and buffers, ported from
   Complete_And_Buffer_V1.PY (Kevin) ---- */
// Source: Kevin, original work; ported from
// Complete_And_Buffer_V1.PY (Kevin).
function PD_frontBackRig(view, pins) {
  const spine = [pins.chest[0], PD_Split_Line[view]];
  const rig = {
    Pelvis: [PD_Waist_Pin[view], null],
    Torso_Middle: [PD_Waist_Pin[view], "Pelvis"],
    Torso_Top: [spine, "Torso_Middle"],
    Head: [pins.neck, "Torso_Top"],
    Arm_Upper_Left: [pins.shoulder_l, "Torso_Top"],
    Arm_Fore_Left: [pins.elbow_l, "Arm_Upper_Left"],
    Hand_Left: [pins.wrist_l, "Arm_Fore_Left"],
    Arm_Upper_Right: [pins.shoulder_r, "Torso_Top"],
    Arm_Fore_Right: [pins.elbow_r, "Arm_Upper_Right"],
    Hand_Right: [pins.wrist_r, "Arm_Fore_Right"],
    Thigh_Left: [pins.hip_l, "Pelvis"],
    Shin_Left: [pins.knee_l, "Thigh_Left"],
    Foot_Left: [pins.ankle_l, "Shin_Left"],
    Thigh_Right: [pins.hip_r, "Pelvis"],
    Shin_Right: [pins.knee_r, "Thigh_Right"],
    Foot_Right: [pins.ankle_r, "Shin_Right"] };
  for (const [nm] of PD_Face_Features[view]) rig[nm] = [pins.neck, "Head"];
  return rig;
}
function PD_sideRig(pins) {
  return {
    Pelvis: [pins.waist, null],
    Torso_Middle: [pins.waist, "Pelvis"],
    Torso_Top: [pins.spine, "Torso_Middle"],
    Head: [pins.neck, "Torso_Top"],
    Eye_Side: [pins.neck, "Head"],
    Arm_Upper_Near: [pins.shoulder_n, "Torso_Top"],
    Arm_Fore_Near: [pins.elbow_n, "Arm_Upper_Near"],
    Hand_Near: [pins.wrist_n, "Arm_Fore_Near"],
    Arm_Upper_Far: [pins.shoulder_f, "Torso_Top"],
    Arm_Fore_Far: [pins.elbow_f, "Arm_Upper_Far"],
    Hand_Far: [pins.wrist_f, "Arm_Fore_Far"],
    Thigh_Near: [pins.hip_n, "Pelvis"],
    Shin_Near: [pins.knee_n, "Thigh_Near"],
    Foot_Near: [pins.ankle_n, "Shin_Near"],
    Thigh_Far: [pins.hip_f, "Pelvis"],
    Shin_Far: [pins.knee_f, "Thigh_Far"],
    Foot_Far: [pins.ankle_f, "Shin_Far"] };
}
function PD_frontBackJoints(view, pins, kneeRadius) {
  const spine = [pins.chest[0], PD_Split_Line[view]];
  return [
    ["waist", PD_Waist_Pin[view], 70, "Pelvis", "Torso_Middle", false],
    ["spine", spine, 70, "Torso_Middle", "Torso_Top", true],
    ["neck", pins.neck, 60, "Torso_Top", "Head", true],
    ["shoulder_l", pins.shoulder_l, 55, "Torso_Top", "Arm_Upper_Left", true],
    ["shoulder_r", pins.shoulder_r, 55, "Torso_Top", "Arm_Upper_Right", true],
    ["elbow_l", pins.elbow_l, 48, "Arm_Upper_Left", "Arm_Fore_Left", true],
    ["elbow_r", pins.elbow_r, 48, "Arm_Upper_Right", "Arm_Fore_Right", true],
    ["wrist_l", pins.wrist_l, 36, "Arm_Fore_Left", "Hand_Left", true],
    ["wrist_r", pins.wrist_r, 36, "Arm_Fore_Right", "Hand_Right", true],
    ["hip_l", pins.hip_l, 75, "Pelvis", "Thigh_Left", false],
    ["hip_r", pins.hip_r, 75, "Pelvis", "Thigh_Right", false],
    ["knee_l", pins.knee_l, kneeRadius, "Thigh_Left", "Shin_Left", true],
    ["knee_r", pins.knee_r, kneeRadius, "Thigh_Right", "Shin_Right", true],
    ["ankle_l", pins.ankle_l, 40, "Shin_Left", "Foot_Left", true],
    ["ankle_r", pins.ankle_r, 40, "Shin_Right", "Foot_Right", true] ];
}
function PD_sideJoints(pins) {
  return [
    ["waist", pins.waist, 70, "Pelvis", "Torso_Middle", false],
    ["spine", pins.spine, 70, "Torso_Middle", "Torso_Top", true],
    ["neck", pins.neck, 60, "Torso_Top", "Head", true],
    ["shoulder_n", pins.shoulder_n, 60, "Torso_Top", "Arm_Upper_Near", true],
    ["shoulder_f", pins.shoulder_f, 55, "Torso_Top", "Arm_Upper_Far", true],
    ["elbow_n", pins.elbow_n, 52, "Arm_Upper_Near", "Arm_Fore_Near", true],
    ["elbow_f", pins.elbow_f, 52, "Arm_Upper_Far", "Arm_Fore_Far", true],
    ["wrist_n", pins.wrist_n, 36, "Arm_Fore_Near", "Hand_Near", true],
    ["wrist_f", pins.wrist_f, 36, "Arm_Fore_Far", "Hand_Far", true],
    ["hip_n", pins.hip_n, 55, "Pelvis", "Thigh_Near", false],
    ["hip_f", pins.hip_f, 65, "Pelvis", "Thigh_Far", false],
    ["knee_n", pins.knee_n, 60, "Thigh_Near", "Shin_Near", true],
    ["knee_f", pins.knee_f, 60, "Thigh_Far", "Shin_Far", true],
    ["ankle_n", pins.ankle_n, 40, "Shin_Near", "Foot_Near", true],
    ["ankle_f", pins.ankle_f, 40, "Shin_Far", "Foot_Far", true] ];
}
function PD_bridges(view, pins) {
  if (view === "Front" || view === "Back")
    return [["Torso_Top", pins.neck, pins.chest, 25],
            ["Torso_Top", pins.shoulder_l, pins.chest, 22],
            ["Torso_Top", pins.shoulder_r, pins.chest, 22]];
  return [["Torso_Top", pins.neck, pins.chest, 25],
          ["Torso_Top", pins.shoulder_f, pins.chest, 22]];
}
/* The shorts cloth source test of Extend_Shorts, ported. */
function PD_clothAt(arr, i, lum) {
  return arr[4 * i + 3] >= 250 && (arr[4 * i + 2] - arr[4 * i]) > 12 && lum >= 45 && lum <= 90;
}
function PD_clothAtLoose(arr, i, lum) {
  return arr[4 * i + 3] >= 250 && (arr[4 * i + 2] - arr[4 * i]) > 12 && lum < 120;
}
/* Fill the Want pixels of one window with the part's own
   local median tone - Fill_Flat of the Python instrument. */
function PD_fillFlat(arr, mask, x0, y0, x1, y1, wantAt, clothOnly) {
  const C = PD_CANVAS;
  const srcR = [], srcG = [], srcB = [];
  let loose = false;
  const collect = (useLoose) => {
    srcR.length = 0; srcG.length = 0; srcB.length = 0;
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const i = y * C + x;
      if (!mask[i]) continue;
      const r = arr[4 * i], g = arr[4 * i + 1], b = arr[4 * i + 2];
      const lum = (r + g + b) / 3;
      let ok;
      if (clothOnly) ok = useLoose ? PD_clothAtLoose(arr, i, lum) : PD_clothAt(arr, i, lum);
      else {
        const spread = Math.max(r, g, b) - Math.min(r, g, b);
        ok = arr[4 * i + 3] >= 250 && lum >= 110 && lum <= 232 && spread > 24;
      }
      if (ok) { srcR.push(r); srcG.push(g); srcB.push(b); }
    }
  };
  collect(false);
  if (clothOnly && srcR.length < 24) { collect(true); loose = true; }
  if (srcR.length < 24) {
    srcR.length = 0; srcG.length = 0; srcB.length = 0;
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
      const i = y * C + x;
      if (mask[i]) { srcR.push(arr[4 * i]); srcG.push(arr[4 * i + 1]); srcB.push(arr[4 * i + 2]); }
    }
  }
  if (!srcR.length) return 0;
  const med = (a) => {
    const s = a.slice().sort((p, q) => p - q);
    const n = s.length;
    return n % 2 ? s[(n - 1) / 2] : Math.trunc((s[n / 2 - 1] + s[n / 2]) / 2);
  };
  const tone = [med(srcR), med(srcG), med(srcB)];
  let added = 0;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) {
    const i = y * C + x;
    if (mask[i] || !wantAt(x, y)) continue;
    arr[4 * i] = tone[0]; arr[4 * i + 1] = tone[1]; arr[4 * i + 2] = tone[2];
    arr[4 * i + 3] = 255; mask[i] = 1; added += 1;
  }
  return added;
}
function PD_fillDisc(arr, mask, centre, radius, clothOnly) {
  const C = PD_CANVAS;
  const pad = Math.trunc(radius * 2 + 8);
  const x0 = Math.max(0, Math.trunc(centre[0] - pad)), x1 = Math.min(C - 1, Math.trunc(centre[0] + pad));
  const y0 = Math.max(0, Math.trunc(centre[1] - pad)), y1 = Math.min(C - 1, Math.trunc(centre[1] + pad));
  const r2 = radius * radius;
  return PD_fillFlat(arr, mask, x0, y0, x1, y1,
    (x, y) => (x - centre[0]) ** 2 + (y - centre[1]) ** 2 <= r2, clothOnly);
}
function PD_fillCapsule(arr, mask, A, B, radius, length, clothOnly) {
  const C = PD_CANVAS;
  let Bx = B[0], By = B[1];
  if (length !== null && length !== undefined) {
    const dx = B[0] - A[0], dy = B[1] - A[1];
    const n = Math.hypot(dx, dy);
    Bx = A[0] + dx / n * length; By = A[1] + dy / n * length;
  }
  const pad = Math.trunc(radius + 70);
  const x0 = Math.max(0, Math.trunc(Math.min(A[0], Bx) - pad)), x1 = Math.min(C - 1, Math.trunc(Math.max(A[0], Bx) + pad));
  const y0 = Math.max(0, Math.trunc(Math.min(A[1], By) - pad)), y1 = Math.min(C - 1, Math.trunc(Math.max(A[1], By) + pad));
  return PD_fillFlat(arr, mask, x0, y0, x1, y1,
    (x, y) => PD_segDist(x, y, A, [Bx, By]) <= radius, clothOnly);
}
/* Complete one view in place: canvases and masks keyed by
   part name; returns the pixels added per part. */
function PD_completeView(view, pins, joints, canvases, masks) {
  const added = {};
  for (const nm of Object.keys(masks)) added[nm] = 0;
  for (const [, centre, radii] of PD_Face_Features[view] || [])
    added.Head += PD_fillDisc(canvases.Head, masks.Head, centre, Math.trunc(radii[0]), false);
  for (const [part, A, B, radius] of PD_bridges(view, pins))
    added[part] += PD_fillCapsule(canvases[part], masks[part], A, B, radius, null, false);
  for (const [, pin, radius, parent, child, childFills] of joints) {
    added[parent] += PD_fillDisc(canvases[parent], masks[parent], pin, radius + 3, parent === "Pelvis");
    if (childFills)
      added[child] += PD_fillDisc(canvases[child], masks[child], pin, radius + 3, child === "Pelvis");
  }
  if (view === "SideRight")
    added.Pelvis += PD_fillCapsule(canvases.Pelvis, masks.Pelvis,
      pins.hip_f, pins.knee_f, 58, 180, true);
  return added;
}

/* ---- Bits 4 and 5: the GLB writers, ported from
   Build_Paper_Doll_GLB_V1.PY and Build_Paper_Doll_3D_V1.PY
   (Kevin); the writer block itself descends from
   Build_Human_GLB_V1.PY (Duke, proven). ---- */
// Source: Kevin, original work; ported from
// Build_Paper_Doll_GLB_V1.PY and Build_Paper_Doll_3D_V1.PY
// (Kevin); the writer block descends from
// Build_Human_GLB_V1.PY (Duke, proven).
const PD_Joint_Words = {
  waist: "waist", spine: "spine", neck: "neck",
  shoulder_l: "left shoulder", shoulder_r: "right shoulder",
  shoulder_n: "near shoulder", shoulder_f: "far shoulder",
  elbow_l: "left elbow", elbow_r: "right elbow",
  elbow_n: "near elbow", elbow_f: "far elbow",
  wrist_l: "left wrist", wrist_r: "right wrist",
  wrist_n: "near wrist", wrist_f: "far wrist",
  hip_l: "left hip", hip_r: "right hip",
  hip_n: "near hip", hip_f: "far hip",
  knee_l: "left knee", knee_r: "right knee",
  knee_n: "near knee", knee_f: "far knee",
  ankle_l: "left ankle", ankle_r: "right ankle",
  ankle_n: "near ankle", ankle_f: "far ankle" };
function PD_pretty(part) {
  let t = part;
  if (t.startsWith("Part_")) t = t.slice(5);
  if (t.endsWith("_V1")) t = t.slice(0, -3);
  return t.replace(/_/g, " ");
}
function PD_describe(view, part, info, jointByChild) {
  const words = PD_pretty(part);
  const pinText = Math.round(info.pin[0]) + ", " + Math.round(info.pin[1]);
  if (!info.parent)
    return "Root rig point of the " + view + " view. The " + words +
      " part turns on the waist joint at " + pinText +
      " and carries every part connected under it.";
  const parentWords = PD_pretty(info.parent);
  if (jointByChild[part])
    return "Rig point for the " + words + " part in the " + view +
      " view. It turns on the " + PD_Joint_Words[jointByChild[part]] +
      " joint at " + pinText + ", connected to its parent part " +
      parentWords + ".";
  return "Rig point for the " + words + " part in the " + view +
    " view. It rides on its parent part " + parentWords +
    ", sharing that part's joint pin at " + pinText + ".";
}
function PD_glbWriter() {
  const chunks = [], views = [], accessors = [], meshes = [],
        materials = [], images = [], nodes = [];
  let offset = 0;
  const addView = (bytes, target) => {
    const pad = (4 - (bytes.byteLength % 4)) % 4;
    chunks.push(bytes);
    if (pad) chunks.push(new Uint8Array(pad));
    const v = { buffer: 0, byteOffset: offset, byteLength: bytes.byteLength };
    if (target) v.target = target;
    views.push(v); offset += bytes.byteLength + pad;
    return views.length - 1;
  };
  const quad = (name, pngBytes, pos, nor, uv, idx, low, high, dbl, extras) => {
    const iv = addView(pngBytes);
    images.push({ bufferView: iv, mimeType: "image/png", name });
    const ti = images.length - 1;
    materials.push({ name, pbrMetallicRoughness:
      { baseColorTexture: { index: ti }, metallicFactor: 0.0, roughnessFactor: 1.0 },
      alphaMode: "MASK", alphaCutoff: 0.35, doubleSided: dbl });
    const pv = addView(new Uint8Array(new Float32Array(pos).buffer), 34962);
    const nv = addView(new Uint8Array(new Float32Array(nor).buffer), 34962);
    const tv = addView(new Uint8Array(new Float32Array(uv).buffer), 34962);
    const xv = addView(new Uint8Array(new Uint16Array(idx).buffer), 34963);
    const base = accessors.length;
    accessors.push(
      { bufferView: pv, componentType: 5126, count: 4, type: "VEC3", min: low, max: high },
      { bufferView: nv, componentType: 5126, count: 4, type: "VEC3" },
      { bufferView: tv, componentType: 5126, count: 4, type: "VEC2" },
      { bufferView: xv, componentType: 5123, count: 6, type: "SCALAR" });
    meshes.push({ name, primitives: [
      { attributes: { POSITION: base, NORMAL: base + 1, TEXCOORD_0: base + 2 },
        indices: base + 3, material: materials.length - 1 }] });
    const node = { mesh: meshes.length - 1, name };
    if (extras) node.extras = extras;
    nodes.push(node);
  };
  const finish = (gltf) => {
    gltf.scenes = [{ nodes: nodes.map((_, k) => k) }];
    gltf.nodes = nodes; gltf.meshes = meshes; gltf.materials = materials;
    gltf.images = images;
    gltf.textures = images.map((_, k) => ({ source: k }));
    gltf.accessors = accessors; gltf.bufferViews = views;
    const binLen = offset;
    gltf.buffers = [{ byteLength: binLen }];
    let jsonStr = JSON.stringify(gltf);
    while (jsonStr.length % 4) jsonStr += " ";
    const jsonBytes = new TextEncoder().encode(jsonStr);
    const bin = new Uint8Array(binLen);
    let at = 0;
    for (const c of chunks) { bin.set(c, at); at += c.byteLength; }
    const total = 12 + 8 + jsonBytes.byteLength + 8 + binLen;
    const out = new Uint8Array(total);
    const dv = new DataView(out.buffer);
    dv.setUint32(0, 0x46546c67, true); dv.setUint32(4, 2, true);
    dv.setUint32(8, total, true);
    dv.setUint32(12, jsonBytes.byteLength, true); dv.setUint32(16, 0x4e4f534a, true);
    out.set(jsonBytes, 20);
    dv.setUint32(20 + jsonBytes.byteLength, binLen, true);
    dv.setUint32(24 + jsonBytes.byteLength, 0x004e4942, true);
    out.set(bin, 28 + jsonBytes.byteLength);
    return out;
  };
  return { quad, finish };
}
async function PD_partPng1024(blob) {
  const bmp = await createImageBitmap(blob);
  const c = document.createElement("canvas");
  c.width = 1024; c.height = 1024;
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
  g.drawImage(bmp, 0, 0, 1024, 1024);
  const b = await PD_blobOf(c);
  return new Uint8Array(await b.arrayBuffer());
}
function PD_rigExtras(rig) {
  /* Per view: joint-by-child map, from the rig JSON joints. */
  const out = {};
  for (const view of PD_VIEWS) {
    const m = {};
    for (const j of rig.views[view].joints) m[j.child] = j.name;
    out[view] = m;
  }
  return out;
}
async function PD_buildFlatGLB(rig, completedBlobs) {
  const W = PD_glbWriter();
  const groupX = { Front: -3.45, Back: -1.15, SideRight: 1.15, SideLeft: 3.45 };
  const jointsOut = {}, byChild = PD_rigExtras(rig);
  let total = 0;
  for (const view of PD_VIEWS) {
    const vd = rig.views[view];
    jointsOut[view] = vd.joints;
    const ox = groupX[view];
    for (let ix = 0; ix < vd.layer_order_back_to_front.length; ix++) {
      const part = vd.layer_order_back_to_front[ix];
      const info = vd.parts[part];
      const extras = { view, part, pin: [info.pin[0], info.pin[1]],
        parent: info.parent,
        label: view + " " + PD_pretty(part),
        desc: PD_describe(view, part, info, byChild[view]) };
      const png = await PD_partPng1024(completedBlobs[view][part]);
      const z = ix * 0.03;
      W.quad(view + "_" + part, png,
        [ox - 1, -1, z, ox + 1, -1, z, ox + 1, 1, z, ox - 1, 1, z],
        [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1],
        [0, 1, 1, 1, 1, 0, 0, 0], [0, 1, 2, 0, 2, 3],
        [ox - 1, -1, z], [ox + 1, 1, z], true, extras);
      total += 1;
    }
  }
  const gltf = { asset: { version: "2.0", generator: "Kevin Paper Doll GLB Builder V1" },
    scene: 0,
    extras: { character: "Human_Man", canvas: PD_CANVAS, views: PD_VIEWS,
      rig: "each part node carries extras.pin, extras.parent, " +
           "extras.label and extras.desc in the Model Editor's own form",
      joints: jointsOut } };
  return { bytes: W.finish(gltf), total };
}
async function PD_build3DGLB(rig, completedBlobs) {
  const W = PD_glbWriter();
  const byChild = PD_rigExtras(rig);
  const jointsOut = {};
  const shellGap = 0.0015, pageGap = 0.03;
  const placement = (view, ix) => {
    if (view === "Front") return ["front", shellGap + ix * pageGap];
    if (view === "Back") return ["back", -shellGap - ix * pageGap];
    if (view === "SideRight") return ["sideright", -shellGap - ix * pageGap];
    return ["sideleft", shellGap + ix * pageGap];
  };
  const kinds = {
    front: (o) => [[-1, -1, o, 1, -1, o, 1, 1, o, -1, 1, o],
      [0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1], [0, 1, 1, 1, 1, 0, 0, 0],
      [0, 1, 2, 0, 2, 3], [-1, -1, o], [1, 1, o]],
    back: (o) => [[1, 1, o, -1, 1, o, -1, -1, o, 1, -1, o],
      [0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0, -1], [0, 0, 1, 0, 1, 1, 0, 1],
      [0, 2, 1, 0, 3, 2], [-1, -1, o], [1, 1, o]],
    sideright: (o) => [[o, -1, -1, o, -1, 1, o, 1, 1, o, 1, -1],
      [-1, 0, 0, -1, 0, 0, -1, 0, 0, -1, 0, 0], [0, 1, 1, 1, 1, 0, 0, 0],
      [0, 1, 2, 0, 2, 3], [o, -1, -1], [o, 1, 1]],
    sideleft: (o) => [[o, -1, 1, o, -1, -1, o, 1, -1, o, 1, 1],
      [1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0], [0, 1, 1, 1, 1, 0, 0, 0],
      [0, 1, 2, 0, 2, 3], [o, -1, -1], [o, 1, 1]] };
  let total = 0;
  for (const view of PD_VIEWS) {
    const vd = rig.views[view];
    jointsOut[view] = vd.joints;
    for (let ix = 0; ix < vd.layer_order_back_to_front.length; ix++) {
      const part = vd.layer_order_back_to_front[ix];
      const info = vd.parts[part];
      const extras = { view, part, pin: [info.pin[0], info.pin[1]],
        parent: info.parent,
        label: view + " " + PD_pretty(part),
        desc: PD_describe(view, part, info, byChild[view]) };
      const png = await PD_partPng1024(completedBlobs[view][part]);
      const [kind, off] = placement(view, ix);
      const [pos, nor, uv, idx, low, high] = kinds[kind](off);
      W.quad(view + "_" + part, png, pos, nor, uv, idx, low, high, false, extras);
      total += 1;
    }
  }
  const gltf = { asset: { version: "2.0", generator: "Kevin Paper Doll 3D Builder V1" },
    scene: 0,
    extras: { character: "Human_Man", canvas: PD_CANVAS, views: PD_VIEWS,
      assembly: "one figure at the origin: Front pages on the " +
        "front plane facing +Z, Back pages on the back " +
        "plane facing -Z mirrored true, SideRight pages " +
        "on the profile plane facing -X, SideLeft pages " +
        "on the profile plane facing +X mirrored true",
      rig: "each part node carries extras.pin, extras.parent, " +
           "extras.label and extras.desc in the Model Editor's own form",
      joints: jointsOut } };
  return { bytes: W.finish(gltf), total };
}
function PD_rigOut(rigs) {
  const out = { canvas: PD_CANVAS, views: {} };
  for (const view of PD_VIEWS) {
    const [rig, joints] = rigs[view];
    out.views[view] = {
      layer_order_back_to_front: PD_Layer_Order[view].map(n => "Part_" + n + "_V1"),
      parts: {},
      joints: joints.map(([nm, pin, radius, parent, child, cf]) => ({
        name: nm, pin: [Math.round(pin[0] * 10) / 10, Math.round(pin[1] * 10) / 10],
        radius, parent: "Part_" + parent + "_V1",
        child: "Part_" + child + "_V1", child_fills: cf })) };
    for (const nm of Object.keys(rig)) {
      const [pin, parent] = rig[nm];
      out.views[view].parts["Part_" + nm + "_V1"] = {
        pin: [Math.round(pin[0] * 10) / 10, Math.round(pin[1] * 10) / 10],
        parent: parent ? "Part_" + parent + "_V1" : null };
    }
  }
  return out;
}

/* ---- the run: Bits 1 to 5 unattended, then the walk page
   from this run's own GLB ---- */
// Source: Kevin, original work.
function PD_flipMask(mask) {
  const C = PD_CANVAS;
  const out = new Uint8Array(mask.length);
  for (let y = 0; y < C; y++) for (let x = 0; x < C; x++)
    out[y * C + x] = mask[y * C + (C - 1 - x)];
  return out;
}
async function PD_run(files) {
  const logEl = document.getElementById("dollLog");
  if (logEl) logEl.textContent = "";
  window.__doll = { done: false };
  const pick = (word) => files.find(f => f.name.toLowerCase().includes(word));
  const fFront = pick("front"), fBack = pick("back"), fSide = pick("side");
  if (!fFront || !fBack || !fSide) {
    PD_log("The pick needs three pictures whose names carry front, back, and side.");
    window.__doll = { done: false, error: "missing picture" };
    return;
  }
  const summary = { checks: { bit1: {}, bit2: {} }, added: {} };
  try {
    /* Bit 1 */
    const cutouts = {}, cutBlobs = {};
    const jobs = [["Front", fFront], ["Back", fBack], ["SideRight", fSide]];
    for (const [view, file] of jobs) {
      PD_log("Bit 1 - cutting the " + view + " picture out clean...");
      const img = await createImageBitmap(file);
      const cut = PD_cutOne(img);
      const chk = PD_checkCutout(cut.rgba);
      summary.checks.bit1[view] = chk;
      PD_log("Bit 1 - " + view + ": figure " + chk.figure +
        " px, background inside silhouette " + chk.inside +
        " px, white fringe " + chk.fringe + " px.");
      if (chk.inside !== 0 || chk.fringe !== 0)
        throw new Error("Bit 1 check failed on " + view);
      cutouts[view] = cut;
      cutBlobs[view] = await PD_blobOf(PD_canvasFromRGBA(cut.rgba));
    }
    /* Bit 2 */
    const pinsOf = {
      Front: PD_pinsOnCanvas(PD_Front_Pins_Rel),
      Back: PD_pinsOnCanvas(PD_Back_Pins_Rel),
      SideRight: PD_Side_Pins };
    const bonesOf = { Front: PD_Front_Back_Bones, Back: PD_Front_Back_Bones,
      SideRight: PD_Side_Bones };
    const splitBlobs = { Front: {}, Back: {}, SideRight: {}, SideLeft: {} };
    for (const [view] of jobs) {
      PD_log("Bit 2 - splitting the " + view + " cutout into parts...");
      const masks = PD_splitOne(view, cutouts[view].rgba, pinsOf[view], bonesOf[view]);
      const chk = PD_checkSplit(view, masks, cutouts[view].figure);
      summary.checks.bit2[view] = chk;
      PD_log("Bit 2 - " + view + ": " + PD_Expected[view].length +
        " parts, partition overlap " + chk.overlap + ", missing " +
        chk.missing + ", extra " + chk.extra + ".");
      if (!chk.ok) throw new Error("Bit 2 check failed on " + view);
      for (const nm of PD_Expected[view]) {
        const rgba = PD_partRGBA(cutouts[view].rgba, masks[nm]);
        splitBlobs[view]["Part_" + nm + "_V1"] = await PD_blobOf(PD_canvasFromRGBA(rgba));
        if (view === "SideRight")
          splitBlobs.SideLeft["Part_" + nm + "_V1"] =
            await PD_blobOf(PD_canvasFromRGBA(PD_flipRGBA(rgba)));
      }
      if (view === "SideRight") {
        const masksL = {};
        for (const nm of PD_Expected.SideRight) masksL[nm] = PD_flipMask(masks[nm]);
        const chkL = PD_checkSplit("SideLeft", masksL, PD_flipMask(cutouts.SideRight.figure));
        summary.checks.bit2.SideLeft = chkL;
        PD_log("Bit 2 - SideLeft: " + PD_Expected.SideLeft.length +
          " parts (mirrored), partition overlap " + chkL.overlap +
          ", missing " + chkL.missing + ", extra " + chkL.extra + ".");
        if (!chkL.ok) throw new Error("Bit 2 check failed on SideLeft");
      }
    }
    /* Bit 3 */
    const sidePinsFull = {};
    for (const k of Object.keys(PD_Side_Pins))
      sidePinsFull[k] = [PD_Side_Pins[k][0], PD_Side_Pins[k][1]];
    sidePinsFull.waist = PD_Waist_Pin.SideRight;
    sidePinsFull.spine = [992.0, PD_Split_Line.SideRight];
    const sidePinsLeft = {};
    for (const k of Object.keys(sidePinsFull))
      sidePinsLeft[k] = [PD_CANVAS - 1 - sidePinsFull[k][0], sidePinsFull[k][1]];
    const rigs = {
      Front: [PD_frontBackRig("Front", pinsOf.Front),
              PD_frontBackJoints("Front", pinsOf.Front, 60)],
      Back: [PD_frontBackRig("Back", pinsOf.Back),
             PD_frontBackJoints("Back", pinsOf.Back, 80)],
      SideRight: [PD_sideRig(sidePinsFull), PD_sideJoints(sidePinsFull)],
      SideLeft: [PD_sideRig(sidePinsLeft), PD_sideJoints(sidePinsLeft)] };
    const completedBlobs = { Front: {}, Back: {}, SideRight: {}, SideLeft: {} };
    for (const [view] of jobs) {
      PD_log("Bit 3 - completing the " + view + " parts and growing their buffers...");
      const canvases = {}, masks = {};
      for (const nm of PD_Expected[view]) {
        const arr = await PD_rgbaOfBlob(splitBlobs[view]["Part_" + nm + "_V1"]);
        canvases[nm] = new Uint8ClampedArray(arr);
        const m = new Uint8Array(PD_CANVAS * PD_CANVAS);
        for (let i = 0; i < m.length; i++) m[i] = arr[4 * i + 3] > 0 ? 1 : 0;
        masks[nm] = m;
      }
      const pins = view === "SideRight" ? sidePinsFull : pinsOf[view];
      const added = PD_completeView(view, pins, rigs[view][1], canvases, masks);
      let totalAdded = 0;
      for (const nm of Object.keys(added)) totalAdded += added[nm];
      summary.added[view] = totalAdded;
      PD_log("Bit 3 - " + view + ": completed, added " + totalAdded + " px of buffers.");
      for (const nm of PD_Expected[view]) {
        const out = PD_partRGBA(canvases[nm], masks[nm]);
        completedBlobs[view]["Part_" + nm + "_V1"] = await PD_blobOf(PD_canvasFromRGBA(out));
        if (view === "SideRight")
          completedBlobs.SideLeft["Part_" + nm + "_V1"] =
            await PD_blobOf(PD_canvasFromRGBA(PD_flipRGBA(out)));
      }
    }
    const rig = PD_rigOut(rigs);
    const census = { views: {} };
    for (const view of PD_VIEWS) census.views[view] = { expected_parts: PD_Expected[view] };
    /* Bit 4 */
    PD_log("Bit 4 - writing the rig points into the paper GLB...");
    const flat = await PD_buildFlatGLB(rig, completedBlobs);
    PD_log("Bit 4 - paper GLB built: " + flat.bytes.length + " bytes, " +
      flat.total + " rigged parts.");
    /* Bit 5 */
    PD_log("Bit 5 - assembling the 3D paper model...");
    const glb3d = await PD_build3DGLB(rig, completedBlobs);
    PD_log("Bit 5 - 3D paper GLB built: " + glb3d.bytes.length + " bytes, " +
      glb3d.total + " pages at the origin.");
    /* The walk page, generated from this run's GLB. */
    PD_log("Walk - generating the walk page from the 3D GLB...");
    const tplBytes = Uint8Array.from(atob(PD_WALK_TPL_B64), c => c.charCodeAt(0));
    const tpl = new TextDecoder().decode(tplBytes);
    const walkHtml = tpl.replace("__GLB64__", PD_b64(glb3d.bytes));
    const walkBlob = new Blob([walkHtml], { type: "text/html" });
    /* The full stitch set, for the battery's read-back. */
    const entries = [];
    const cutName = { Front: "Human_Man_Front_Cutout_V1.PNG",
      Back: "Human_Man_Back_Cutout_V1.PNG", SideRight: "Human_Man_Side_Cutout_V1.PNG" };
    for (const [view] of jobs) entries.push([cutName[view], cutBlobs[view]]);
    for (const view of PD_VIEWS) {
      for (const part of Object.keys(splitBlobs[view]))
        entries.push(["Doll_Parts_V1/" + view + "/" + part + ".PNG", splitBlobs[view][part]]);
      for (const part of Object.keys(completedBlobs[view]))
        entries.push(["Doll_Parts_Completed_V1/" + view + "/" + part + ".PNG", completedBlobs[view][part]]);
    }
    entries.push(["Doll_Parts_V1/Doll_Parts_Census_V1.JSON",
      new Blob([JSON.stringify(census, null, 1)], { type: "application/json" })]);
    entries.push(["Doll_Parts_Completed_V1/Completed_Rig_V1.JSON",
      new Blob([JSON.stringify(rig, null, 1)], { type: "application/json" })]);
    entries.push(["Human_Man_Paper_Doll_V1.GLB",
      new Blob([flat.bytes], { type: "model/gltf-binary" })]);
    entries.push(["Human_Man_Paper_Doll_3D_V1.GLB",
      new Blob([glb3d.bytes], { type: "model/gltf-binary" })]);
    entries.push(["Paper_Doll_Walk_V1.HTML", walkBlob]);
    const zip = await buildZip(entries);
    PD_download(new Blob([glb3d.bytes], { type: "model/gltf-binary" }),
      "Human_Man_Paper_Doll_3D_V1.GLB");
    PD_download(walkBlob, "Paper_Doll_Walk_V1.HTML");
    PD_download(zip, "Paper_Doll_Stitch_Set_V1.zip");
    summary.glbFlatBytes = flat.bytes.length;
    summary.glb3dBytes = glb3d.bytes.length;
    summary.walkBytes = walkBlob.size;
    summary.zipBytes = zip.size;
    window.__doll = Object.assign({ done: true }, summary);
    PD_log("Done - the paper doll is built: the 3D GLB, the walk page, " +
      "and the full stitch set have been downloaded.");
  } catch (e) {
    PD_log("The build stopped: " + (e && e.message || e));
    window.__doll = { done: false, error: String(e && e.message || e) };
  }
}
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("dollRun");
  const pickEl = document.getElementById("dollPick");
  if (!btn || !pickEl) return;
  window.__dollReady = true;
  btn.addEventListener("click", () => pickEl.click());
  pickEl.addEventListener("change", async (ev) => {
    const files = [...ev.target.files];
    if (files.length) await PD_run(files);
    ev.target.value = "";
  });
});
