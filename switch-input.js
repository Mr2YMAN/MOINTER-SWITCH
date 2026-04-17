#!/usr/bin/env node
const { existsSync } = require("fs");
const { spawnSync } = require("child_process");

function getArgValue(flag, fallback) {
  const idx = process.argv.indexOf(flag);
  if (idx >= 0 && idx + 1 < process.argv.length) return process.argv[idx + 1];
  return fallback;
}

function hasFlag(flag) {
  return process.argv.includes(flag);
}

function getTargetValue(inputName) {
  const mapping = {
    dp: 0x0f,
    hdmi: 0x11,
    auto: 0x00,
  };
  const value = mapping[inputName];
  if (value === undefined) {
    throw new Error(`Unsupported input '${inputName}'. Use: hdmi, dp, auto.`);
  }
  return value;
}

function runTool(controlPath, args) {
  const result = spawnSync(controlPath, args, {
    encoding: "utf8",
    windowsHide: true,
  });

  if (result.error) throw result.error;
  if (result.status !== 0) {
    const details = (result.stderr || result.stdout || "").trim();
    throw new Error(`ControlMyMonitor failed (${result.status}): ${details}`);
  }
  return result.stdout || "";
}

function parseMonitorHandle(line) {
  // /smonitors is tab-delimited; first column is monitor handle/name.
  return (line.split("\t")[0] || "").trim();
}

function usage() {
  console.log("Usage:");
  console.log("  node .\\switch-input.js [--input hdmi|dp|auto] [--monitor-hint XG27AQDMG] [--control-path .\\ControlMyMonitor.exe] [--list-only]");
}

function main() {
  if (hasFlag("--help") || hasFlag("-h")) {
    usage();
    return 0;
  }

  const input = getArgValue("--input", "hdmi").toLowerCase();
  const monitorHint = getArgValue("--monitor-hint", "XG27AQDMG");
  const controlPath = getArgValue("--control-path", ".\\ControlMyMonitor.exe");
  const listOnly = hasFlag("--list-only");

  if (!existsSync(controlPath)) {
    console.error(`ControlMyMonitor.exe not found at '${controlPath}'.`);
    return 1;
  }

  console.log("Enumerating monitors...");
  const devicesRaw = runTool(controlPath, ["/smonitors"]);
  const deviceLines = devicesRaw.split(/\r?\n/).filter((line) => line.trim() !== "");
  if (deviceLines.length === 0) {
    console.error("No monitors returned by ControlMyMonitor.");
    return 1;
  }

  console.log("\nDetected monitors:");
  deviceLines.forEach((line, i) => {
    console.log(`[${i}] ${line}`);
  });
  console.log("");

  if (listOnly) {
    console.log("ListOnly set, exiting.");
    return 0;
  }

  let targetLine = deviceLines.find((line) => line.includes(monitorHint));
  if (!targetLine) {
    console.error(`Warning: no monitor matched hint '${monitorHint}', using first monitor.`);
    targetLine = deviceLines[0];
  }

  const targetMonitor = parseMonitorHandle(targetLine);
  if (!targetMonitor) {
    console.error(`Could not parse monitor handle from line: ${targetLine}`);
    return 1;
  }

  const value = getTargetValue(input);
  console.log(`Switching '${targetMonitor}' to '${input}' (VCP 0x60 = ${value.toString(16).toUpperCase().padStart(2, "0")})...`);
  runTool(controlPath, ["/SetValue", targetMonitor, "60", String(value)]);

  try {
    const current = runTool(controlPath, ["/GetValue", targetMonitor, "60"]).trim();
    if (current) {
      console.log(`Current VCP 0x60 response: ${current}`);
    }
  } catch {
    console.error("Switched, but could not verify current value.");
  }

  console.log("Done.");
  return 0;
}

process.exit(main());
