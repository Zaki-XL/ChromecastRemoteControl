$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== Google TV Remote Build Script ===" -ForegroundColor Blue

# Kill running instance before build to prevent file lock on Copy-Item
Write-Host "Stopping any running instance of GoogleTVRemote.exe..." -ForegroundColor Cyan
Get-Process GoogleTVRemote -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

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

# Ensure custom branded Flet client exists with icon and Google TV Remote description
if (-not (Test-Path "bin\client\flet.exe")) {
    Write-Host "Preparing custom branded Flet client in bin\client..." -ForegroundColor Cyan
    python scratch/prepare_custom_client.py
}

# --- ガードレール 1: ビルド前自動テスト (構文・属性解決・実コンポーネント検証) ---
Write-Host "`n[TEST GATE] Running Pre-Build Automated Tests..." -ForegroundColor Yellow
python tests/run_tests.py --pre-build
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "Error: Pre-build test failed! Packaging aborted." -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}

# Run PyInstaller build
Write-Host "`nStarting PyInstaller single-file packaging..." -ForegroundColor Cyan
if ($runCmd -eq "pyinstaller") {
    pyinstaller --clean --onefile --noconsole --paths="src" --collect-data flet --add-data "assets;assets" --add-data "bin/client;bin/client" --version-file="version_info.txt" --icon="assets/icon.ico" --name="GoogleTVRemote" main.py
} else {
    python -m PyInstaller --clean --onefile --noconsole --paths="src" --collect-data flet --add-data "assets;assets" --add-data "bin/client;bin/client" --version-file="version_info.txt" --icon="assets/icon.ico" --name="GoogleTVRemote" main.py
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
    
    # --- ガードレール 2: ビルド後自動テスト (EXE起動 & ログエラーゼロ検査) ---
    Write-Host "`n[TEST GATE] Running Post-Build EXE & Log Error Verification..." -ForegroundColor Yellow
    python tests/run_tests.py --post-build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n========================================" -ForegroundColor Red
        Write-Host "Error: Post-build EXE verification failed! Application has runtime errors." -ForegroundColor Red
        Write-Host "========================================" -ForegroundColor Red
        exit 1
    }

    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "Build & Verification successful!" -ForegroundColor Green
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

