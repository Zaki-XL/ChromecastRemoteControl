$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Google TV Remote Build Script ===" -ForegroundColor Blue

# Kill running instance before build to prevent file lock on Copy-Item
Write-Host "Stopping any running instance of GoogleTVRemote.exe..." -ForegroundColor Cyan
taskkill /F /IM GoogleTVRemote.exe 2>$null
Start-Sleep -Seconds 1

# Check PyInstaller installation
Write-Host "Checking for PyInstaller..." -ForegroundColor Cyan
$pyinstallerExists = $null -ne (Get-Command pyinstaller -ErrorAction SilentlyContinue)
$runCmd = ""

if (-not $pyinstallerExists) {
    & python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Error: PyInstaller is not installed or not in PATH."
        Write-Host "To install, run: 'pip install pyinstaller'" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "PyInstaller command not found, but Python module detected." -ForegroundColor Yellow
    $runCmd = "python -m PyInstaller"
} else {
    $runCmd = "pyinstaller"
}

# Clean old build artifacts
Write-Host "Cleaning up old build artifacts..." -ForegroundColor Cyan
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}
if (Test-Path "dist") {
    Remove-Item -Recurse -Force "dist"
}
if (Test-Path "GoogleTVRemote.spec") {
    Remove-Item -Force "GoogleTVRemote.spec"
}

# Run PyInstaller build
Write-Host "Starting PyInstaller single-file packaging..." -ForegroundColor Cyan
if ($runCmd -eq "pyinstaller") {
    pyinstaller --clean --onefile --noconsole --name="GoogleTVRemote" main.py
} else {
    python -m PyInstaller --clean --onefile --noconsole --name="GoogleTVRemote" main.py
}

$buildExitCode = $LASTEXITCODE

# Handle build result
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Get-Location }
$exePath = Join-Path $scriptDir "dist\GoogleTVRemote.exe"
if ($buildExitCode -eq 0 -and (Test-Path $exePath)) {
    $exeFile = Get-Item $exePath
    $sizeMb = [Math]::Round($exeFile.Length / 1MB, 2)
    
    # Copy build binary to the project root directory
    $rootExePath = Join-Path $scriptDir "GoogleTVRemote.exe"
    Copy-Item -Path $exePath -Destination $rootExePath -Force
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Build successful!" -ForegroundColor Green
    Write-Host "Executable: $exePath" -ForegroundColor Green
    Write-Host "Copied to: $rootExePath" -ForegroundColor Green
    Write-Host "Size: $sizeMb MB" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "Error: Build failed." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}

