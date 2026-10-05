param([switch]$Installer, [switch]$InstallerOnly)
if ($InstallerOnly) { $Installer = $true }
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed: $Program (exit $LASTEXITCODE)" }
}

if ($Installer) {
    $isccCommand = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue
    $compiler = if ($isccCommand) { $isccCommand.Source } else { $null }
    if (-not $compiler) {
        foreach ($candidate in @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
            "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
        )) {
            if (Test-Path -LiteralPath $candidate) { $compiler = $candidate; break }
        }
    }
    if (-not $compiler) { throw 'Install Inno Setup 6 first: winget install --id JRSoftware.InnoSetup -e' }
}

if (-not $InstallerOnly) {
    # Isolate the build from unrelated libraries on the developer machine.
    $buildPython = Join-Path $PSScriptRoot '.venv-build\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $buildPython)) {
        Invoke-Checked -Program 'python' -Arguments @('-m', 'venv', '.venv-build')
    }
    Invoke-Checked -Program $buildPython -Arguments @('-m', 'pip', 'install', '-r', 'requirements.txt', 'pyinstaller==6.19.0')
    $previousBrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
    $previousTclPath = $env:TCL_LIBRARY
    $previousTkPath = $env:TK_LIBRARY
    try {
        $tkOutput = & $buildPython 'packaging/check_tk.py'
        if ($LASTEXITCODE -ne 0) { throw 'Tkinter preflight failed. See the Python repair instructions above.' }
        $tkPaths = $tkOutput | ConvertFrom-Json
        $env:TCL_LIBRARY = $tkPaths.TCL_LIBRARY
        $env:TK_LIBRARY = $tkPaths.TK_LIBRARY
        $env:PLAYWRIGHT_BROWSERS_PATH = '0'
        Invoke-Checked -Program $buildPython -Arguments @('-m', 'playwright', 'install', 'chromium')
        Invoke-Checked -Program $buildPython -Arguments @(
            '-m', 'PyInstaller', '--noconfirm', '--clean', '--onedir', '--windowed',
            '--name', 'ZizaSeo', '--runtime-hook', 'packaging/runtime_hook.py',
            '--icon', 'assets/zizaseo.ico', '--add-data', 'assets;assets',
            '--collect-all', 'playwright', '--collect-all', 'customtkinter',
            '--collect-all', 'fake_useragent', '--collect-all', 'playwright_stealth',
            '--collect-data', 'certifi', 'ui.py'
        )
    } finally {
        $env:PLAYWRIGHT_BROWSERS_PATH = $previousBrowserPath
        $env:TCL_LIBRARY = $previousTclPath
        $env:TK_LIBRARY = $previousTkPath
    }

}

$appExe = Join-Path $PSScriptRoot 'dist\ZizaSeo\ZizaSeo.exe'
if (-not (Test-Path -LiteralPath $appExe)) { throw 'No portable app found. Run build.ps1 without -InstallerOnly first.' }
$check = Start-Process -FilePath $appExe -ArgumentList '--smoke-test' -WindowStyle Hidden -Wait -PassThru
if ($check.ExitCode -ne 0) {
    throw 'Packaged UI/Chromium check failed. See %LOCALAPPDATA%\SeoWeb\startup.log and ui_error.log'
}
Write-Host "Portable app ready: $appExe (distribute the entire dist\ZizaSeo folder)"

if ($Installer) {
    Invoke-Checked -Program $compiler -Arguments @('packaging\installer.iss')
    Write-Host 'Installer ready: dist\installer\ZizaSeo-Setup.exe'
}
exit 0
