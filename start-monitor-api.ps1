$projectDir = "C:\Users\a\Documents\dev\mointer switch"
$scriptPath = Join-Path $projectDir "switch-input.py"
$stdoutLog = Join-Path $projectDir "monitor-api.out.log"
$stderrLog = Join-Path $projectDir "monitor-api.err.log"

# Prefer real python.exe path first, then fallback to launcher.
$pythonCandidates = @(
    "C:\Users\a\AppData\Local\Python\pythoncore-3.14-64\python.exe",
    "C:\Users\a\AppData\Local\Microsoft\WindowsApps\py.exe",
    "python",
    "py"
)

$pythonExe = $null
foreach ($candidate in $pythonCandidates) {
    if (Test-Path $candidate) {
        $pythonExe = $candidate
        break
    }
    try {
        $cmd = Get-Command $candidate -ErrorAction Stop
        if ($cmd.Source) {
            $pythonExe = $cmd.Source
            break
        }
    }
    catch {
        # Try next candidate.
    }
}

if (-not $pythonExe) {
    "[$(Get-Date -Format o)] Python executable not found." | Out-File -FilePath $stderrLog -Append -Encoding utf8
    exit 1
}

$quotedScriptPath = '"' + $scriptPath + '"'

Start-Process -FilePath $pythonExe `
    -ArgumentList @($quotedScriptPath, "--serve", "--host", "0.0.0.0", "--port", "8765") `
    -WorkingDirectory $projectDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog
