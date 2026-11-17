// Render_Shoot_V1.JS
// Model Editor V20, Half B Piece 2: headless Chrome
// shooter for the pipeline's snapshots and movement
// reference steps. The CDP scaffolding is adapted from
// Shoot_Paper_Doll_Bit5_V1.JS (Kevin, proven in Bit 5):
// spawn headless Chrome with --allow-file-access-from-files
// and --enable-unsafe-swiftshader, drive it over the
// DevTools protocol, screenshot each rendered direction.
// Usage: node Render_Shoot_V1.JS --page <template.HTML>
//   --glb <file.GLB> --out <folder> --vendor <folder>
//   --chrome <chrome binary> --dirs Front,Back,Left,Right
//   --size 1024 [--pose <json>]
// Original work apart from the copied scaffolding - Kevin.
const fs = require("fs");
const os = require("os");
const path = require("path");

function arg(name, fallback) {
  const i = process.argv.indexOf("--" + name);
  return i >= 0 ? process.argv[i + 1] : fallback;
}
const PAGE_TEMPLATE = arg("page");
const GLB = arg("glb");
const OUT = arg("out");
const VENDOR = arg("vendor");
const CHROME = arg("chrome");
const DIRS = arg("dirs", "Front").split(",");
const SIZE = parseInt(arg("size", "1024"), 10);
const POSE = arg("pose", "");
// The debugging port is picked free at run time, the
// same way the shoot's own HTTP server below takes a
// spare port with listen(0): a fixed port breaks the
// shoot whenever a leftover shooter Chrome still holds
// it - the new Chrome cannot bind, and the target poll
// would find the OLD Chrome's page instead. A probe
// socket claims an OS-assigned port, lets it go, and
// Chrome takes it a moment later.
// Source: Kevin, original work; the spare-port pattern
// is this file's own HTTP server's, carried to the
// debugging port (2026-11-16 fix).
async function freePort() {
  const net = require("net");
  const probe = net.createServer();
  await new Promise(r => probe.listen(0, "127.0.0.1", r));
  const p = probe.address().port;
  await new Promise(r => probe.close(r));
  return p;
}

const sleep = ms => new Promise(r => setTimeout(r, ms));
let msgId = 0; const pending = new Map(); let ws;
function send(method, params = {}) {
  const id = ++msgId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evalJs(expression) {
  const r = await send("Runtime.evaluate",
    { expression, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error("EVAL: " +
    (r.exceptionDetails.exception &&
     r.exceptionDetails.exception.description ||
     r.exceptionDetails.text));
  return r.result.value;
}

async function main() {
  // Chrome refuses fetch() of a file:// GLB, so the page,
  // the vendor tree, and the GLB are served over a local
  // HTTP server on a spare port for the shoot's lifetime.
  const http = require("http");
  let template = fs.readFileSync(PAGE_TEMPLATE, "utf8");
  const pageHtml = template
    .split("__VENDOR_URL__").join("/vendor")
    .split("__GLB_URL__").join("/glb")
    .split("__POSE_JSON__").join(POSE ? POSE : "null");
  const server = http.createServer((req, res) => {
    if (req.url === "/page") {
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(pageHtml);
    } else if (req.url === "/glb") {
      res.writeHead(200, { "Content-Type": "model/gltf-binary" });
      fs.createReadStream(GLB).pipe(res);
    } else if (req.url.startsWith("/vendor/")) {
      const file = path.join(VENDOR, req.url.slice("/vendor/".length));
      if (!fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { "Content-Type": "text/javascript" });
      fs.createReadStream(file).pipe(res);
    } else { res.writeHead(404); res.end(); }
  });
  await new Promise(r => server.listen(0, "127.0.0.1", r));
  const pageUrl = `http://127.0.0.1:${server.address().port}/page`;
  fs.mkdirSync(OUT, { recursive: true });
  const { spawn } = require("child_process");
  const PORT = await freePort();
  const proc = spawn(CHROME,
    ["--headless=new", "--disable-gpu",
     "--enable-unsafe-swiftshader",
     "--allow-file-access-from-files", "--no-sandbox",
     `--remote-debugging-port=${PORT}`,
     `--window-size=${SIZE},${SIZE}`,
     "--user-data-dir=" + path.join(os.tmpdir(),
       "me_shoot_profile_" + process.pid),
     "about:blank"], { stdio: "ignore" });
  try {
    let targets = null;
    for (let i = 0; i < 40; i++) {
      try {
        const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
        targets = await res.json();
        if (targets && targets.length) break;
      } catch (e) {}
      await sleep(250);
    }
    const page = targets.find(t => t.type === "page");
    ws = new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id); pending.delete(m.id);
        m.error ? p.reject(new Error(m.error.message)) : p.resolve(m.result);
      }
    };
    await send("Runtime.enable"); await send("Page.enable");
    await send("Page.navigate", { url: pageUrl });
    let ready = false;
    for (let i = 0; i < 60; i++) {
      ready = await evalJs("window.__ready === true");
      if (ready) break;
      const err = await evalJs("window.__error || ''");
      if (err) throw new Error("page load: " + err);
      await sleep(250);
    }
    if (!ready) throw new Error("page did not become ready");
    const shot = {};
    for (const dir of DIRS) {
      const b64 = await evalJs(
        `window.__render(${JSON.stringify(dir)})`);
      const file = path.join(OUT, dir + ".PNG");
      fs.writeFileSync(file, Buffer.from(b64, "base64"));
      shot[dir] = fs.statSync(file).size;
      console.log("shot " + dir + " -> " + file + " " + shot[dir] + " bytes");
    }
    console.log("SHOOT_JSON " + JSON.stringify({ shots: shot }));
  } finally {
    try { proc.kill("SIGKILL"); } catch (e) {}
    try { server.close(); } catch (e) {}
  }
}
main().then(() => process.exit(0))
  .catch(e => { console.error("SHOOT FAILED:", e.message); process.exit(1); });
