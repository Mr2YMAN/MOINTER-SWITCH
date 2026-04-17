param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("hdmi", "dp", "auto")]
    [string]$Input = "hdmi",

    [Parameter(Mandatory = $false)]
    [string]$MonitorHint = "XG27AQDMG",

    [Parameter(Mandatory = $false)]
    [string]$ControlMyMonitorPath = ".\ControlMyMonitor.exe",

    [Parameter(Mandatory = $false)]
    [switch]$ListOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ControlMyMonitorPath)) {
    throw "ControlMyMonitor.exe not found at '$ControlMyMonitorPath'. Download it from NirSoft and place it next to this script."
}

function Get-TargetValue {
    param([string]$Name)

    # Common DDC/CI input source values (VCP 0x60) used by many monitors.
    # ASUS models frequently map DP=0x0F and HDMI=0x11, but this can vary.
    switch ($Name) {
        "dp" { return 0x0F }
        "hdmi" { return 0x11 }
        "auto" { return 0x00 }
        default { throw "Unsupported input '$Name'." }
    }
}

Write-Host "Enumerating monitors..."
$devicesRaw = & $ControlMyMonitorPath /smonitors
if (-not $devicesRaw) {
    throw "No monitors returned by ControlMyMonitor."
}

$deviceLines = $devicesRaw -split "`r?`n" | Where-Object { $_.Trim() -ne "" }
if ($deviceLines.Count -eq 0) {
    throw "No monitor lines parsed from /smonitors output."
}

Write-Host ""
Write-Host "Detected monitors:"
for ($i = 0; $i -lt $deviceLines.Count; $i++) {
    Write-Host ("[{0}] {1}" -f $i, $deviceLines[$i])
}
Write-Host ""

if ($ListOnly) {
    Write-Host "ListOnly set, exiting."
    exit 0
}

$targetLine = $deviceLines | Where-Object { $_ -match [regex]::Escape($MonitorHint) } | Select-Object -First 1
if (-not $targetLine) {
    Write-Warning "No monitor matched hint '$MonitorHint'. Falling back to first monitor."
    $targetLine = $deviceLines[0]
}

# /smonitors columns are tab-delimited; first column is monitor handle/name used by /SetValue.
$targetMonitor = ($targetLine -split "`t")[0]
if (-not $targetMonitor) {
    throw "Unable to parse target monitor handle from line: $targetLine"
}

$value = Get-TargetValue -Name $Input

Write-Host "Switching '$targetMonitor' to '$Input' (VCP 0x60 = $("{0:X2}" -f $value))..."
& $ControlMyMonitorPath /SetValue "$targetMonitor" 60 $value | Out-Null

Start-Sleep -Milliseconds 250

try {
    $current = & $ControlMyMonitorPath /GetValue "$targetMonitor" 60
    if ($current) {
        Write-Host "Current VCP 0x60 response: $current"
    }
}
catch {
    Write-Warning "Switched, but could not verify current value."
}

Write-Host "Done."
