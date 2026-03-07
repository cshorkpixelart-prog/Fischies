param(
    [Parameter(Mandatory = $false)]
    [string]$CommitMessage = "Update Fisch macro + dashboard",

    [Parameter(Mandatory = $false)]
    [switch]$SkipRailwayDeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

git add -A
if ((git diff --cached --name-only | Measure-Object).Count -eq 0) {
    Write-Host "No staged changes. Nothing to commit."
    exit 0
}

git commit -m $CommitMessage
git push

if ($SkipRailwayDeploy) {
    Write-Host "Pushed to GitHub. Skipped Railway deploy."
    exit 0
}

$railway = Get-Command railway -ErrorAction SilentlyContinue
if (-not $railway) {
    Write-Host "Railway CLI not found. Install with: npm i -g @railway/cli"
    exit 0
}

Push-Location "server-dashboard"
try {
    railway up --detach
}
finally {
    Pop-Location
}

Write-Host "GitHub push complete and Railway deploy triggered."
