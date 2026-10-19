import assert from "node:assert/strict";
import { chmodSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { app, BrowserWindow } from "electron";
import log from "electron-log/main.js";

const sandbox = process.env.POND_SANDBOX!;
const evidence = process.env.POND_TEST_EVIDENCE!;
const mode = process.env.POND_TEST_LOG_MODE!;
const expectFailure = process.env.POND_TEST_EXPECT_FAILURE === "1";
const errors: string[] = [];
let windows = 0;
let completed = false;
let checking = false;
let prepared = false;
const timer = setTimeout(() => finish(false, { reason: "startup timeout", errors, windows }), 30000);

function finish(ok: boolean, result: Record<string, unknown>) {
  if (completed) return;
  completed = true;
  clearTimeout(timer);
  const report = { ok, mode, expectFailure, isPackaged: app.isPackaged, windows, errors, ...result };
  writeFileSync(join(evidence, "result.json"), JSON.stringify(report, null, 2));
  console.log("LOGGING_STARTUP_RESULT", JSON.stringify(report));
  app.exit(ok ? 0 : 1);
}

process.on("uncaughtException", error => finish(false, { reason: error.stack }));
process.on("unhandledRejection", error => {
  errors.push(error instanceof Error ? error.stack ?? error.message : String(error));
  if (!expectFailure) finish(false, { reason: "unexpected startup rejection" });
  else setTimeout(() => {
    try {
      assert.ok(prepared);
      assert.equal(windows, 0);
      assert.ok(errors.some(message => message.includes("EACCES") && /resolvePaths|ensureDir/.test(message)));
      finish(true, { observed: "permission-denied library startup rejection, zero windows" });
    } catch (cause) { finish(false, { reason: String(cause) }); }
  }, 2000);
});

app.on("browser-window-created", () => { windows += 1; });
app.on("web-contents-created", (_, contents) => {
  contents.on("did-fail-load", (_, code, description) => finish(false, { reason: `load failed: ${code} ${description}` }));
  contents.on("did-finish-load", async () => {
    if (checking || completed || !contents.getURL().includes("index.html")) return;
    checking = true;
    try {
      assert.equal(expectFailure, false, "original unexpectedly opened a window with blocked logs");
      const state = await contents.executeJavaScript(`(async () => {
        const started = Date.now();
        while (!document.querySelector('[data-slot="window"]') || !document.body.innerText.trim() || document.getElementById("boot")) {
          if (Date.now() - started > 15000) throw new Error("renderer did not show content");
          await new Promise(resolve => setTimeout(resolve, 50));
        }
        const info = await window.pond.query("library.info");
        const page = await window.pond.query("saves.listPage", { limit: 1 });
        return { info, rows: page.rows.length, text: document.body.innerText.slice(0, 300), root: !!document.getElementById("root"), bootDismissed: !document.getElementById("boot"), width: innerWidth, height: innerHeight };
      })()`);
      assert.ok(state.root);
      assert.equal(state.bootDismissed, true);
      assert.ok(state.text.trim());
      assert.ok(state.info.path.startsWith(sandbox));
      assert.equal(state.rows, 0);
      assert.equal(errors.length, 0);
      const window = BrowserWindow.fromWebContents(contents);
      assert.ok(window);
      for (let count = 0; !window.isVisible() && count < 100; count++) await new Promise(resolve => setTimeout(resolve, 50));
      assert.ok(window.isVisible(), "main window was never visible");
      assert.equal(app.isPackaged, process.env.POND_TEST_PACKAGED === "1");
      let logFile: string | null = null;
      if (mode === "both") assert.equal(log.transports.file.level, false);
      else {
        logFile = join(sandbox, mode === "denied" ? "app-data/logs/main.log" : "home/Library/Logs/Pond/main.log");
        assert.ok(readFileSync(logFile, "utf8").includes("[pond] main starting"));
        assert.equal(app.getPath("logs"), join(sandbox, mode === "denied" ? "app-data/logs" : "home/Library/Logs/Pond"));
      }
      if (mode !== "normal") assert.equal(existsSync(join(sandbox, "home/Library/Logs/Pond")), false);
      await new Promise(resolve => setTimeout(resolve, 400));
      const screenshot = await contents.capturePage();
      writeFileSync(join(evidence, "window.png"), screenshot.toPNG());
      finish(true, { observed: "visible renderer and successful real preload queries", logFile, fileLogging: log.transports.file.level, state, bounds: window.getBounds() });
    } catch (cause) { finish(false, { reason: cause instanceof Error ? cause.stack : String(cause) }); }
  });
});

export function prepareLoggingFailure() {
  assert.ok(sandbox && evidence);
  assert.equal(app.getPath("userData"), join(sandbox, "app-data"));
  const systemLogs = join(sandbox, "home/Library/Logs/Pond");
  mkdirSync(systemLogs, { recursive: true });
  app.setPath("logs", systemLogs);
  if (mode !== "normal") {
    rmSync(systemLogs, { recursive: true });
    if (mode === "both") {
      const fallback = join(sandbox, "app-data/logs");
      mkdirSync(fallback);
      chmodSync(fallback, 0o500);
      assert.throws(() => writeFileSync(join(fallback, "main.log"), "probe"), { code: "EACCES" });
    }
    chmodSync(join(sandbox, "home/Library/Logs"), 0o500);
    assert.throws(() => mkdirSync(systemLogs), { code: "EACCES" });
  }
  prepared = true;
  writeFileSync(join(evidence, "fixture.json"), JSON.stringify({ mode, sandbox, systemLogs, logsParentMode: (statSync(join(sandbox, "home/Library/Logs")).mode & 0o777).toString(8), permissionDenialConfirmed: mode !== "normal" }, null, 2));
}
