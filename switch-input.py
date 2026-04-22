#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PRESET_MONITORS = {
    "xg27": "AUSAA1D",
    "aorus": "GBT2400",
    "lg": "GSM59F1",
}

PRESET_ALIASES = {
    "xg27": "AUSAA1D",
    "xg27aqdmg": "AUSAA1D",
    "xg27aqdmgr": "AUSAA1D",
    "aorus": "GBT2400",
    "kd25f": "GBT2400",
    "aorus kd25f": "GBT2400",
    "lg": "GSM59F1",
    "ultrawide": "GSM59F1",
    "gsm59f1": "GSM59F1",
    "ausaa1d": "AUSAA1D",
    "gbt2400": "GBT2400",
}


def get_target_value(name: str) -> int:
    mapping = {
        "dp": 0x0F,
        "hdmi": 0x11,
        "auto": 0x00,
    }
    if name not in mapping:
        raise ValueError(f"Unsupported input '{name}'.")
    return mapping[name]


def run_tool(control_path: str, args: list[str]) -> str:
    proc = subprocess.run(
        [control_path, *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"ControlMyMonitor failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def load_monitors(control_path: str) -> list[dict[str, str]]:
    """
    Export monitors to a temporary file and parse key/value pairs.
    This avoids Unicode stdout parsing issues on some Windows setups.
    """
    with tempfile.NamedTemporaryFile(prefix="cmm_monitors_", suffix=".txt", delete=False) as tmp:
        temp_path = tmp.name

    try:
        run_tool(control_path, ["/smonitors", temp_path])
        with open(temp_path, "rb") as f:
            raw = f.read()

        # ControlMyMonitor may write UTF-16LE (contains many NUL bytes) or ANSI/UTF-8.
        if b"\x00" in raw:
            content = raw.decode("utf-16le", errors="replace")
        else:
            try:
                content = raw.decode("utf-8-sig", errors="strict")
            except UnicodeDecodeError:
                content = raw.decode("cp1252", errors="replace")
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

    normalized = content.replace("\r\n", "\n")
    blocks = [b.strip() for b in normalized.split("\n\n") if b.strip()]
    monitors: list[dict[str, str]] = []

    for block in blocks:
        monitor: dict[str, str] = {}
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            monitor[key.strip()] = value.strip().strip('"')

        if "Monitor Device Name" in monitor:
            monitors.append(monitor)

    return monitors


def get_preset_target(text: str) -> str | None:
    return PRESET_ALIASES.get(text.strip().lower())


def resolve_monitor_handle(
    control_path: str,
    monitor_hint: str,
    monitor: str | None,
    monitor_target: str | None,
) -> str:
    if monitor_target:
        handle = monitor_target.strip()
        print(f"Using direct monitor target: {handle}")
        return handle

    if monitor:
        handle = PRESET_MONITORS[monitor]
        print(f"Using preset '{monitor}' -> {handle}")
        return handle

    preset = get_preset_target(monitor_hint)
    if preset:
        print(f"Using preset from hint '{monitor_hint}' -> {preset}")
        return preset

    print("Enumerating monitors...")
    monitors = load_monitors(control_path)
    if not monitors:
        raise RuntimeError("No monitors returned by ControlMyMonitor.")

    print("\nDetected monitors:")
    for i, monitor_info in enumerate(monitors):
        name = monitor_info.get("Monitor Name", "?")
        short_id = monitor_info.get("Short Monitor ID", "?")
        device = monitor_info.get("Monitor Device Name", "?")
        print(f"[{i}] {name} | {short_id} | {device}")
    print("")

    hint = monitor_hint.lower()
    target_monitor = next(
        (
            m
            for m in monitors
            if hint in m.get("Monitor Name", "").lower()
            or hint in m.get("Short Monitor ID", "").lower()
            or hint in m.get("Monitor ID", "").lower()
            or hint in m.get("Monitor Device Name", "").lower()
            or hint in m.get("Serial Number", "").lower()
        ),
        None,
    )
    if target_monitor is None:
        print(
            f"Warning: no monitor matched hint '{monitor_hint}', using first monitor.",
            file=sys.stderr,
        )
        target_monitor = monitors[0]

    monitor_handle = target_monitor.get("Monitor Device Name", "")
    if not monitor_handle:
        raise RuntimeError("Could not parse monitor device name from /smonitors output.")
    return monitor_handle


def switch_input(control_path: str, monitor_handle: str, input_name: str, verify: bool = True) -> dict[str, str]:
    value = get_target_value(input_name)
    print(f"Switching '{monitor_handle}' to '{input_name}' (VCP 0x60 = {value:02X})...")
    run_tool(control_path, ["/SetValue", monitor_handle, "60", str(value)])
    result = {
        "monitor": monitor_handle,
        "input": input_name,
        "status": "ok",
    }

    if verify:
        time.sleep(0.25)
        try:
            current = run_tool(control_path, ["/GetValue", monitor_handle, "60"]).strip()
            if current:
                print(f"Current VCP 0x60 response: {current}")
                result["verify"] = current
        except Exception:
            print("Switched, but could not verify current value.", file=sys.stderr)
            result["verify"] = "unavailable"

    print("Done.")
    return result


def apply_profile(control_path: str, profile: str) -> list[dict[str, str]]:
    if profile == "mac":
        input_name = "hdmi"
    elif profile == "pc":
        input_name = "dp"
    else:
        raise ValueError("Unsupported profile. Use 'mac' or 'pc'.")

    # Both gaming monitors should follow the selected profile.
    targets = [PRESET_MONITORS["xg27"], PRESET_MONITORS["aorus"]]
    results: list[dict[str, str]] = []
    for handle in targets:
        try:
            results.append(switch_input(control_path, handle, input_name, verify=False))
        except Exception as exc:
            results.append(
                {
                    "monitor": handle,
                    "input": input_name,
                    "status": "error",
                    "error": str(exc),
                }
            )
    return results


def power_monitor(
    control_path: str,
    monitor_handle: str,
    state: str,
    input_after_on: str | None = None,
    aggressive_on: bool = False,
) -> dict[str, str]:
    if state not in ("on", "off"):
        raise ValueError("Unsupported power state. Use 'on' or 'off'.")

    print(f"Power '{state}' for '{monitor_handle}'...")
    if state == "off":
        run_tool(control_path, ["/TurnOff", monitor_handle])
        print("Done.")
        return {"monitor": monitor_handle, "power": state, "status": "ok"}

    # Wake sequence: TurnOn + D6=1, with retries.
    attempts = 6 if aggressive_on else 3
    last_error: Exception | None = None
    for idx in range(attempts):
        try:
            run_tool(control_path, ["/TurnOn", monitor_handle])
            run_tool(control_path, ["/SetValue", monitor_handle, "D6", "1"])

            # Some panels wake better with a pulse in between retries.
            if aggressive_on and idx in (2, 4):
                run_tool(control_path, ["/SwitchOffOn", monitor_handle])

            last_error = None
            time.sleep(0.25)
            break
        except Exception as exc:
            last_error = exc
            time.sleep(0.35)

    if last_error is not None:
        raise last_error

    # Optional input nudge helps some panels wake fully.
    if input_after_on:
        switch_input(control_path, monitor_handle, input_after_on, verify=False)

    print("Done.")
    result = {"monitor": monitor_handle, "power": state, "status": "ok"}
    if input_after_on:
        result["input_after_on"] = input_after_on
    if aggressive_on:
        result["aggressive_on"] = "true"
    return result


def apply_power(control_path: str, state: str, input_after_on: str | None = None) -> list[dict[str, str]]:
    if state not in ("on", "off"):
        raise ValueError("Unsupported power state. Use 'on' or 'off'.")

    # Power-off should include all configured monitors.
    # Power-on is disabled at endpoint level, but keep sensible defaults here.
    if state == "off":
        targets = [PRESET_MONITORS["xg27"], PRESET_MONITORS["aorus"], PRESET_MONITORS["lg"]]
    else:
        targets = [PRESET_MONITORS["xg27"], PRESET_MONITORS["aorus"]]
    results: list[dict[str, str]] = []
    for handle in targets:
        try:
            results.append(
                power_monitor(
                    control_path,
                    handle,
                    state,
                    input_after_on=input_after_on,
                    aggressive_on=False,
                )
            )
        except Exception as exc:
            results.append(
                {
                    "monitor": handle,
                    "power": state,
                    "status": "error",
                    "error": str(exc),
                }
            )
    return results


def apply_single_power(
    control_path: str,
    monitor_key: str,
    state: str,
    input_after_on: str | None = None,
    aggressive_on: bool = False,
) -> list[dict[str, str]]:
    if monitor_key not in PRESET_MONITORS:
        raise ValueError("Unsupported monitor key.")

    handle = PRESET_MONITORS[monitor_key]
    try:
        return [
            power_monitor(
                control_path,
                handle,
                state,
                input_after_on=input_after_on,
                aggressive_on=aggressive_on,
            )
        ]
    except Exception as exc:
        return [
            {
                "monitor": handle,
                "power": state,
                "status": "error",
                "error": str(exc),
            }
        ]


def run_http_server(control_path: str, host: str, port: int) -> int:
    class SwitchHandler(BaseHTTPRequestHandler):
        def _write_json(self, status_code: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path.lower()

            if path in ("/", "/health"):
                self._write_json(
                    200,
                    {
                        "ok": True,
                        "service": "monitor-switch",
                        "routes": [
                            "/mac",
                            "/pc",
                            "/set?profile=mac|pc",
                            "/off",
                            "/power?action=off",
                            "/aorus/off",
                        ],
                    },
                )
                return

            profile = ""
            power = ""
            input_after_on: str | None = None
            single_monitor: str | None = None
            aggressive_on = False
            on_request_disabled = False
            if path == "/mac":
                profile = "mac"
            elif path == "/pc":
                profile = "pc"
            elif path == "/set":
                query = parse_qs(parsed.query)
                profile = (query.get("profile", [""])[0] or "").lower()
            elif path == "/on":
                on_request_disabled = True
            elif path == "/off":
                power = "off"
            elif path == "/power":
                query = parse_qs(parsed.query)
                power = (query.get("action", [""])[0] or "").lower()
                if power == "on":
                    on_request_disabled = True
                    power = ""
            elif path == "/aorus/on":
                on_request_disabled = True
            elif path == "/aorus/off":
                single_monitor = "aorus"
                power = "off"

            if profile in ("mac", "pc"):
                results = apply_profile(control_path, profile)
                has_error = any(item.get("status") != "ok" for item in results)
                self._write_json(
                    200 if not has_error else 500,
                    {
                        "ok": not has_error,
                        "profile": profile,
                        "results": results,
                    },
                )
                return

            if on_request_disabled:
                self._write_json(
                    501,
                    {
                        "ok": False,
                        "error": "Power-on endpoint is disabled by configuration. Use monitor button to turn on, then API can switch input/off.",
                    },
                )
                return

            if single_monitor and power in ("on", "off"):
                results = apply_single_power(
                    control_path,
                    single_monitor,
                    power,
                    input_after_on=input_after_on,
                    aggressive_on=aggressive_on,
                )
                has_error = any(item.get("status") != "ok" for item in results)
                self._write_json(
                    200 if not has_error else 500,
                    {
                        "ok": not has_error,
                        "monitor": single_monitor,
                        "power": power,
                        "input_after_on": input_after_on,
                        "aggressive_on": aggressive_on,
                        "results": results,
                    },
                )
                return

            if power in ("on", "off"):
                results = apply_power(control_path, power, input_after_on=input_after_on)
                has_error = any(item.get("status") != "ok" for item in results)
                self._write_json(
                    200 if not has_error else 500,
                    {
                        "ok": not has_error,
                        "power": power,
                        "input_after_on": input_after_on,
                        "results": results,
                    },
                )
                return

            self._write_json(
                400,
                {
                    "ok": False,
                    "error": "Use /mac, /pc, /set?profile=mac|pc, /off, /power?action=off, or /aorus/off",
                },
            )

        def log_message(self, format: str, *args: object) -> None:
            # Keep output quiet; we already print switch actions.
            return

    server = ThreadingHTTPServer((host, port), SwitchHandler)
    print(f"HTTP server running on http://{host}:{port}")
    print("GET /mac -> HDMI for both monitors")
    print("GET /pc  -> DP for both monitors")
    print("GET /set?profile=mac or /set?profile=pc")
    print("GET /off -> power off both monitors")
    print("GET /power?action=off")
    print("GET /aorus/off (single monitor)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
    finally:
        server.server_close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Switch monitor input using DDC/CI (VCP 0x60) via ControlMyMonitor."
    )
    parser.add_argument(
        "--input",
        choices=["hdmi", "dp", "auto"],
        default="hdmi",
        help="Target input source.",
    )
    parser.add_argument(
        "--monitor-hint",
        default="XG27AQDMG",
        help="Text used to match monitor name/id/device.",
    )
    parser.add_argument(
        "--monitor",
        choices=["xg27", "aorus", "lg"],
        help="Use a built-in monitor preset.",
    )
    parser.add_argument(
        "--monitor-target",
        help="Direct monitor target for ControlMyMonitor (e.g. GBT2400 or \\\\.\\DISPLAY2\\Monitor0).",
    )
    parser.add_argument(
        "--control-path",
        default=r".\ControlMyMonitor.exe",
        help="Path to ControlMyMonitor.exe",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list detected monitors and exit.",
    )
    parser.add_argument(
        "--profile",
        choices=["mac", "pc"],
        help="Switch both main monitors at once: mac=hdmi, pc=dp.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run HTTP server: GET /mac or /pc to switch both monitors.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="HTTP server bind host for --serve (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="HTTP server port for --serve (default: 8765).",
    )

    args = parser.parse_args()

    if not os.path.exists(args.control_path):
        print(
            f"ControlMyMonitor.exe not found at '{args.control_path}'.",
            file=sys.stderr,
        )
        return 1

    if args.serve:
        return run_http_server(args.control_path, args.host, args.port)

    if args.profile:
        results = apply_profile(args.control_path, args.profile)
        has_error = any(item.get("status") != "ok" for item in results)
        print(json.dumps({"profile": args.profile, "results": results}, indent=2))
        return 1 if has_error else 0

    if args.list_only:
        print("Enumerating monitors...")
        monitors = load_monitors(args.control_path)
        if not monitors:
            print("No monitors returned by ControlMyMonitor.", file=sys.stderr)
            return 1
        print("\nDetected monitors:")
        for i, monitor in enumerate(monitors):
            name = monitor.get("Monitor Name", "?")
            short_id = monitor.get("Short Monitor ID", "?")
            device = monitor.get("Monitor Device Name", "?")
            print(f"[{i}] {name} | {short_id} | {device}")
        print("")
        print("ListOnly set, exiting.")
        return 0

    try:
        monitor_handle = resolve_monitor_handle(
            args.control_path,
            args.monitor_hint,
            args.monitor,
            args.monitor_target,
        )
        switch_input(args.control_path, monitor_handle, args.input, verify=True)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
