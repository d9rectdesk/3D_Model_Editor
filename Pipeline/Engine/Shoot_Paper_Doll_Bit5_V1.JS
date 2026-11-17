// Shoot_Paper_Doll_Bit5_V1.JS - Paper Doll Plan Bit 5,
// engine half of the checks. The checker renders the model
// with its own software renderer; this harness renders the
// same GLB in a real engine (Three.js in headless Chrome)
// from the front, the back, the left, and the right, saves
// the four engine stills beside the checker's stills, and
// compares silhouettes and colours against them: a page
// whose winding culls it in a real engine, or a GLB a real
// loader rejects, fails here even if the file parses.
// The CDP scaffolding is copied from
// Check_Paper_Doll_Bit4_V1.JS (Kevin, proven in Bit 4).
// Kevin, original work apart from the copied scaffolding.
// Source: Kevin, original work (this snapshots script,
// apart from the copied CDP scaffolding named above).
// Settings: every folder path in this script comes
// from the pipeline settings file - the estate
// pattern of Bridge_Server_V1.PY carried to
// JavaScript: the settings file is the one named by
// the environment variable EDITOR_PIPELINE_SETTINGS,
// or Editor_Pipeline_Settings_V1.JSON beside this
// script. chrome_path names the Chrome binary and
// humanoid_home names the Humanoid_Rig folder; the
// render page and the stills folder are that folder's
// own Render_Paper_Doll_3D_V1.HTML and
// Paper_Doll_3D_Stills_V1, joined from humanoid_home
// the same way Pipeline_Steps_V1.PY joins its tool
// paths from humanoid_home. A needed setting that is
// absent stops the script at once with a plain line
// naming what is missing.
// Source: Bridge_Server_V1.PY settings block
// (Original work - Kevin), carried to JavaScript;
// the fail-fast checks below are new glue for this
// script. Original work - Kevin.
const fs = require("fs");
const os = require("os");
const path = require("path");

const SETTINGS_PATH = process.env.EDITOR_PIPELINE_SETTINGS ||
  path.join(__dirname, "Editor_Pipeline_Settings_V1.JSON");
let Settings = null;
try {
  Settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, "utf8"));
} catch (e) {
  console.log("shoot paper doll: cannot read pipeline settings file " +
    SETTINGS_PATH + " - set EDITOR_PIPELINE_SETTINGS to the pipeline " +
    "settings file (" + e.message + ")");
  process.exit(2);
}
function Need_Setting(Name) {
  const Value = Settings[Name];
  if (!Value) {
    console.log("shoot paper doll: " + Name + " is not set in pipeline " +
      "settings file " + SETTINGS_PATH + " - set " + Name +
      " in that file");
    process.exit(2);
  }
  return Value;
}
const CHROME = Need_Setting("chrome_path");
const HUMANOID = Need_Setting("humanoid_home");
const PORT = 9342;
const PAGE = "file://" + path.join(HUMANOID,
  "Render_Paper_Doll_3D_V1.HTML");
const STILLS = path.join(HUMANOID, "Paper_Doll_3D_Stills_V1");
const DIRS = ["Front", "Back", "Right", "Left"];

const sleep = ms => new Promise(r => setTimeout(r, ms));
let msgId = 0; const pending = new Map(); let ws;
const exceptions = [];
let passed = 0, failed = 0;
function check(name, cond, detail) {
  if (cond) { passed += 1; console.log("PASS  " + name); }
  else { failed += 1; console.log("FAIL  " + name + (detail ? "  || " + detail : "")); }
}
function send(method, params = {}) {
  const id = ++msgId;
  return new Promise((resolve, reject) => { pending.set(id, { resolve, reject }); ws.send(JSON.stringify({ id, method, params })); });
}
async function evalJs(expression) {
  const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error("EVAL: " + (r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails.text));
  return r.result.value;
}

async function main() {
  const { spawn } = require("child_process");
  // The Chrome profile folder sits in the system temp
  // folder under this run's own process id, so two
  // shoots never share a profile.
  // Source: Render_Shoot_V1.JS profile pattern
  // (Original work - Kevin), carried to this script.
  const proc = spawn(CHROME, ["--headless=new", "--disable-gpu", "--enable-unsafe-swiftshader",
    "--allow-file-access-from-files", "--no-sandbox",
    `--remote-debugging-port=${PORT}`, "--window-size=1100,1100",
    "--user-data-dir=" + path.join(os.tmpdir(),
      "me_harness_profile_bit5_" + process.pid), "about:blank"], { stdio: "ignore" });
  try {
    let targets = null;
    for (let i = 0; i < 40; i++) {
      try { const res = await fetch(`http://127.0.0.1:${PORT}/json/list`); targets = await res.json(); if (targets && targets.length) break; } catch (e) {}
      await sleep(250);
    }
    const page = targets.find(t => t.type === "page");
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) { const p = pending.get(m.id); pending.delete(m.id); m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result); }
      else if (m.method === "Runtime.exceptionThrown") { const d = m.params.exceptionDetails; exceptions.push((d.exception && d.exception.description) || d.text); }
    };
    await send("Runtime.enable"); await send("Page.enable");
    await send("Page.navigate", { url: PAGE });
    let ready = false, loadErr = "";
    for (let i = 0; i < 60; i++) {
      await sleep(500);
      const st = await evalJs(`({ ready: !!window.__ready, err: window.__error || "" })`).catch(() => ({ ready: false, err: "" }));
      if (st.ready) { ready = true; break; }
      if (st.err) { loadErr = st.err; break; }
    }
    check("E1 Three.js loads the Bit 5 GLB with no loader error", ready, loadErr);
    if (!ready) throw new Error("viewer never became ready");

    for (const dir of DIRS) {
      const dataUrl = await evalJs(`window.__render(${JSON.stringify(dir)})`);
      const b64 = dataUrl.split(",")[1];
      fs.writeFileSync(`${STILLS}/Engine_${dir}_V1.PNG`, Buffer.from(b64, "base64"));
      const softUrl = "file://" + `${STILLS}/Human_Man_Paper_Doll_3D_${dir}_V1.PNG`;
      const m = await evalJs(`(async () => {
        const load = (url) => new Promise((res, rej) => {
          const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = url; });
        const eng = await load(${JSON.stringify("data:image/png;base64,")} + ${JSON.stringify(b64)});
        const soft = await load(${JSON.stringify(softUrl)});
        const cv = (im) => { const c = document.createElement("canvas");
          c.width = 1024; c.height = 1024;
          c.getContext("2d").drawImage(im, 0, 0, 1024, 1024);
          return c.getContext("2d").getImageData(0, 0, 1024, 1024).data; };
        const A = cv(eng), B = cv(soft);
        let inter = 0, union = 0, colourBad = 0, covered = 0;
        for (let i = 0; i < A.length; i += 4) {
          const a = A[i + 3] > 89, b = B[i + 3] > 89;
          if (a && b) inter += 1;
          if (a || b) union += 1;
          if (a && b) { covered += 1;
            if (Math.abs(A[i] - B[i]) > 8 || Math.abs(A[i + 1] - B[i + 1]) > 8 ||
                Math.abs(A[i + 2] - B[i + 2]) > 8) colourBad += 1; }
        }
        return { iou: inter / union, colourBadPct: 100 * colourBad / Math.max(covered, 1), covered };
      })()`);
      check(`E-${dir} engine render matches the checker's render (silhouette IoU >= 0.99, colour diff <= 1%)`,
        m.iou >= 0.99 && m.colourBadPct <= 1.0,
        `iou=${m.iou.toFixed(5)} colourBad=${m.colourBadPct.toFixed(3)}% covered=${m.covered}`);
    }
    check("Z no page exceptions across the engine run", exceptions.length === 0, exceptions.slice(0, 3).join(" | "));
    console.log(`RESULT: ${passed} passed, ${failed} failed`);
    if (failed > 0) process.exitCode = 2;
  } finally { try { proc.kill("SIGKILL"); } catch (e) {} }
}
main().then(() => process.exit(process.exitCode || 0)).catch(e => { console.error("HARNESS FAILED:", e.message); process.exit(1); });
