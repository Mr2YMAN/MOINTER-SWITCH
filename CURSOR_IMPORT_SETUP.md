# Cursor Import Prompt (Other PC Setup)

Copy everything in the prompt block below and paste it into Cursor Chat on your other PC.

```text
You are helping me set up and validate my monitor input switch project on Windows.

Project path:
- C:\Users\a\Documents\dev\mointer switch

Goals:
1) Verify dependencies and files.
2) Detect monitor IDs on this PC.
3) Configure the script for this PC if IDs differ.
4) Verify switching works (DP <-> HDMI).
5) Optionally run and test the HTTP API.

Please do this in order:

Step A - Check project files
- Confirm these files exist:
  - switch-input.py
  - switch-input.ps1
  - switch-input.js
  - ControlMyMonitor.exe
- If ControlMyMonitor.exe is missing, stop and tell me to place it in the project folder.

Step B - Environment check
- Show Python version.
- If Python is missing, tell me how to install it and stop.
- If Python exists, continue.

Step C - Detect monitors
- Run:
  - python .\switch-input.py --list-only
- Parse and show:
  - Monitor Name
  - Short Monitor ID
  - Monitor Device Name

Step D - Validate current monitor mapping
- Current preset mapping expected:
  - xg27 -> AUSAA1D
  - aorus -> GBT2400
  - lg -> GSM59F1
- Compare detected IDs with this mapping.
- If different, update PRESET_MONITORS and PRESET_ALIASES in switch-input.py to match this PC.

Step E - Functional test (direct commands)
- Test HDMI:
  - python .\switch-input.py --monitor xg27 --input hdmi
  - python .\switch-input.py --monitor aorus --input hdmi
- Test DP:
  - python .\switch-input.py --monitor xg27 --input dp
  - python .\switch-input.py --monitor aorus --input dp
- If any command fails, diagnose and fix where possible.

Step F - Profile test
- Run:
  - python .\switch-input.py --profile mac
  - python .\switch-input.py --profile pc
- Confirm both complete successfully.

Step G - Optional API test
- Start server:
  - python .\switch-input.py --serve --host 127.0.0.1 --port 8765
- In another terminal, test:
  - curl "http://127.0.0.1:8765/health"
  - curl "http://127.0.0.1:8765/mac"
  - curl "http://127.0.0.1:8765/pc"
  - curl "http://127.0.0.1:8765/off"
- Summarize results and any endpoint failures.

Step H - Final output
- Give me:
  1) Final monitor ID mapping used.
  2) What was changed (if any).
  3) Commands that worked.
  4) Any remaining manual steps.

Important:
- Do not run destructive git commands.
- Do not commit unless I explicitly ask.
- Keep output concise and actionable.
```

## Quick Usage

1. Open this repo on the other PC in Cursor.
2. Open this file: `CURSOR_IMPORT_SETUP.md`.
3. Copy the prompt block.
4. Paste into Cursor Chat and run.
