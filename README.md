# Monitor Input Switch (DDC/CI) - ASUS XG27AQDMG

Switch monitor input source over DDC/CI on Windows using NirSoft `ControlMyMonitor.exe`.
You can use PowerShell, Python, or Node.js.

## 1) Download tool

- Download `ControlMyMonitor` from NirSoft: [https://www.nirsoft.net/utils/control_my_monitor.html](https://www.nirsoft.net/utils/control_my_monitor.html)
- Put `ControlMyMonitor.exe` in this folder:
  - `C:\Users\a\Documents\dev\mointer switch`

## 2) List detected monitors

```powershell
# PowerShell
powershell -ExecutionPolicy Bypass -File .\switch-input.ps1 -ListOnly

# Python
python .\switch-input.py --list-only

# Node.js
node .\switch-input.js --list-only
```

## 3) Switch from DP to HDMI

```powershell
# PowerShell
powershell -ExecutionPolicy Bypass -File .\switch-input.ps1 -Input hdmi -MonitorHint XG27AQDMG

# Python
python .\switch-input.py --input hdmi --monitor-hint XG27AQDMG

# Node.js
node .\switch-input.js --input hdmi --monitor-hint XG27AQDMG
```

## 4) Switch back to DP

```powershell
# PowerShell
powershell -ExecutionPolicy Bypass -File .\switch-input.ps1 -Input dp -MonitorHint XG27AQDMG

# Python
python .\switch-input.py --input dp --monitor-hint XG27AQDMG

# Node.js
node .\switch-input.js --input dp --monitor-hint XG27AQDMG
```

## 5) AORUS KD25F quick commands (Python)

```powershell
# Use built-in preset
python .\switch-input.py --monitor aorus --input hdmi
python .\switch-input.py --monitor aorus --input dp

# Or direct short ID target (works even when monitor list is incomplete)
python .\switch-input.py --monitor-target GBT2400 --input hdmi
python .\switch-input.py --monitor-target GBT2400 --input dp
```

## 6) One command for both monitors

```powershell
# mac profile: both -> HDMI
python .\switch-input.py --profile mac

# pc profile: both -> DP
python .\switch-input.py --profile pc
```

## 7) HTTP GET API (mac/pc switch)

Run server:

```powershell
python .\switch-input.py --serve --host 127.0.0.1 --port 8765
```

Then call with GET:

```powershell
# mac mode (both to HDMI)
curl "http://127.0.0.1:8765/mac"

# pc mode (both to DP)
curl "http://127.0.0.1:8765/pc"

# same via query format
curl "http://127.0.0.1:8765/set?profile=mac"
curl "http://127.0.0.1:8765/set?profile=pc"
```

## 8) Auto start on Windows login

Configured in this project:

- `start-monitor-api.ps1` starts the API server.
- Registry key `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\MonitorSwitchApi` launches it hidden at login.

Disable auto start:

```powershell
Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "MonitorSwitchApi"
```

## Notes

- Scripts use VCP feature `0x60` (Input Source).
- Default mapping:
  - `dp` -> `0x0F`
  - `hdmi` -> `0x11`
- Python script includes monitor presets:
  - `xg27` -> `AUSAA1D`
  - `aorus` -> `GBT2400`
  - `lg` -> `GSM59F1`
- Profile mapping in Python:
  - `mac` -> HDMI on `xg27` and `aorus`
  - `pc` -> DP on `xg27` and `aorus`
- If your unit maps HDMI differently, edit mapping in:
  - `switch-input.ps1` (`Get-TargetValue`)
  - `switch-input.py` (`get_target_value`)
  - `switch-input.js` (`getTargetValue`)
  and try another value (commonly `0x11` or `0x12`).
