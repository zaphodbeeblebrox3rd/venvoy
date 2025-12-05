# venvoy Self-Bootstrapping Installer & Updater for Windows
# Works without requiring Python on the host system

param(
    [switch]$Force
)

Write-Host "🚀 venvoy Self-Bootstrapping Installer & Updater (Windows)" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# Check for Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker not found. Please install Docker Desktop first:" -ForegroundColor Red
    Write-Host "   Download from: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    Write-Host "   Or use winget: winget install Docker.DockerDesktop" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Docker found" -ForegroundColor Green

# Create installation directory
$InstallDir = "$env:USERPROFILE\.venvoy\bin"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Check if venvoy is already installed
$ExistingInstall = $false
if (Test-Path "$InstallDir\venvoy.bat") {
    $ExistingInstall = $true
    Write-Host "📦 Found existing venvoy installation" -ForegroundColor Yellow
    Write-Host "🔄 Updating to latest version..." -ForegroundColor Cyan
}

# Create venvoy.bat bootstrap script
$BatchScript = @"
@echo off
setlocal enabledelayedexpansion

set VENVOY_IMAGE=zaphodbeeblebrox3rd/venvoy:bootstrap
set VENVOY_DIR=%USERPROFILE%\.venvoy
set InstallDir=%USERPROFILE%\.venvoy\bin

:: Ensure venvoy directory exists
if not exist "%VENVOY_DIR%" mkdir "%VENVOY_DIR%"

:: Pull bootstrap image if it doesn't exist
docker image inspect %VENVOY_IMAGE% >nul 2>&1
if errorlevel 1 (
    echo 🔨 Pulling venvoy bootstrap image...
    docker pull %VENVOY_IMAGE%
    echo ✅ Bootstrap image pulled successfully
)

:: Convert Windows paths to Unix-style for Docker
set "HOME_UNIX=%USERPROFILE:\=/%"
set "PWD_UNIX=%CD:\=/%"

:: Handle uninstall command specially
if "%1"=="uninstall" (
    :: Run uninstall directly on host, not in container
    echo 🗑️  venvoy Uninstaller
    echo ====================
    echo.
    
    :: Parse arguments
    set FORCE=false
    set KEEP_PROJECTS=false
    set KEEP_IMAGES=false
    
    shift
    :parse_args
    if "%1"=="" goto :end_parse
    if "%1"=="--force" set FORCE=true
    if "%1"=="--keep-projects" set KEEP_PROJECTS=true
    if "%1"=="--keep-images" set KEEP_IMAGES=true
    shift
    goto :parse_args
    :end_parse
    
    :: Show what will be removed
    echo This will remove:
    echo   📁 Installation directory: !InstallDir!
    echo   📁 Configuration directory: %USERPROFILE%\.venvoy
    if "!KEEP_PROJECTS!"=="false" (
        echo   📁 Projects directory: %USERPROFILE%\venvoy-projects
    )
    echo   🔗 PATH entries from environment variables
    if "!KEEP_IMAGES!"=="false" (
        echo   🐳 Docker images (venvoy/bootstrap:latest and zaphodbeeblebrox3rd/venvoy:bootstrap)
    )
    echo.
    
    if "!FORCE!"=="false" (
        set /p CONFIRM="Are you sure you want to uninstall venvoy? (y/N): "
        if /i not "!CONFIRM!"=="y" (
            echo ❌ Uninstallation cancelled
            exit /b 0
        )
    )
    
    echo.
    echo 🗑️  Removing venvoy...
    
    :: Remove installation directory
    if exist "!InstallDir!" (
        rmdir /s /q "!InstallDir!"
        echo ✅ Removed installation directory
    )
    
    :: Remove configuration directory
    if exist "%USERPROFILE%\.venvoy" (
        rmdir /s /q "%USERPROFILE%\.venvoy"
        echo ✅ Removed configuration directory
    )
    
    :: Handle projects directory
    if exist "%USERPROFILE%\venvoy-projects" (
        if "!KEEP_PROJECTS!"=="true" (
            echo 📁 Kept projects directory: %USERPROFILE%\venvoy-projects
        ) else (
            if "!FORCE!"=="false" (
                set /p REMOVE_PROJECTS="Remove projects directory with environment exports? (y/N): "
                if /i "!REMOVE_PROJECTS!"=="y" (
                    rmdir /s /q "%USERPROFILE%\venvoy-projects"
                    echo ✅ Removed projects directory
                ) else (
                    echo 📁 Kept projects directory: %USERPROFILE%\venvoy-projects
                )
            ) else (
                rmdir /s /q "%USERPROFILE%\venvoy-projects"
                echo ✅ Removed projects directory
            )
        )
    )
    
    :: Remove from PATH
    for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set CURRENT_PATH=%%b
    if defined CURRENT_PATH (
        :: Create backup
        echo !CURRENT_PATH! > "%TEMP%\venvoy-path-backup-%RANDOM%.txt"
        
        :: Remove venvoy from PATH more thoroughly
        set NEW_PATH=!CURRENT_PATH!
        set NEW_PATH=!NEW_PATH:!InstallDir!;=!
        set NEW_PATH=!NEW_PATH:;!InstallDir!=!
        set NEW_PATH=!NEW_PATH:!InstallDir!=!
        
        :: Clean up any double semicolons
        set NEW_PATH=!NEW_PATH:;;=;!
        
        :: Remove leading/trailing semicolons
        if "!NEW_PATH:~0,1!"==";" set NEW_PATH=!NEW_PATH:~1!
        if "!NEW_PATH:~-1!"==";" set NEW_PATH=!NEW_PATH:~0,-1!
        
        reg add "HKCU\Environment" /v PATH /t REG_EXPAND_SZ /d "!NEW_PATH!" /f >nul
        echo ✅ Removed venvoy from user PATH
    )
    
    :: Remove Docker images
    if "!KEEP_IMAGES!"=="false" (
        echo.
        echo 🐳 Cleaning up Docker images...
        
        docker image inspect venvoy/bootstrap:latest >nul 2>&1
        if not errorlevel 1 (
            docker rmi venvoy/bootstrap:latest >nul 2>&1
            echo ✅ Removed bootstrap image
        )
        
        docker image inspect zaphodbeeblebrox3rd/venvoy:bootstrap >nul 2>&1
        if not errorlevel 1 (
            docker rmi zaphodbeeblebrox3rd/venvoy:bootstrap >nul 2>&1
            echo ✅ Removed venvoy bootstrap image
        )
    )
    
    echo.
    echo ✅ venvoy uninstalled successfully!
    echo 💡 You may need to restart your terminal for PATH changes to take effect.
    exit /b 0
) else (
    :: Run normal venvoy commands
    docker run --rm -it ^
        -v /var/run/docker.sock:/var/run/docker.sock ^
        -v "%USERPROFILE%:/host-home" ^
        -v "%CD%:/workspace" ^
        -w /workspace ^
        -e HOME="/host-home" ^
        -e VENVOY_HOST_RUNTIME="docker" ^
        %VENVOY_IMAGE% %*
)
"@

$BatchScript | Out-File -FilePath "$InstallDir\venvoy.bat" -Encoding ASCII

# Create PowerShell wrapper
$PowerShellScript = @"
# venvoy PowerShell wrapper
param([Parameter(ValueFromRemainingArguments=`$true)]`$Arguments)

& "$InstallDir\venvoy.bat" @Arguments
"@

$PowerShellScript | Out-File -FilePath "$InstallDir\venvoy.ps1" -Encoding UTF8

# Function to manage PATH entries properly
function Add-ToPath {
    param(
        [string]$PathToAdd,
        [string]$Scope = "User"
    )
    
    $CurrentPath = [Environment]::GetEnvironmentVariable("PATH", $Scope)
    
    # Check if already in PATH
    if ($CurrentPath -like "*$PathToAdd*") {
        Write-Host "📝 $PathToAdd already in $Scope PATH" -ForegroundColor Yellow
        return $false
    }
    
    # Add to PATH
    if ([string]::IsNullOrEmpty($CurrentPath)) {
        $NewPath = $PathToAdd
    } else {
        $NewPath = "$PathToAdd;$CurrentPath"
    }
    
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, $Scope)
    Write-Host "📝 Added $PathToAdd to $Scope PATH" -ForegroundColor Green
    return $true
}

# Add to PATH with better handling
$PathUpdated = $false

# Try user PATH first
if (Add-ToPath -PathToAdd $InstallDir -Scope "User") {
    $PathUpdated = $true
}

# Also add to current session
if ($env:PATH -notlike "*$InstallDir*") {
    $env:PATH = "$InstallDir;$env:PATH"
    Write-Host "📝 Added venvoy to current session PATH" -ForegroundColor Green
    $PathUpdated = $true
}

Write-Host ""
Write-Host "🎉 venvoy installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan

# Force update the bootstrap image to ensure latest features
Write-Host "🔄 Updating venvoy bootstrap image..." -ForegroundColor Cyan
try {
    docker pull "zaphodbeeblebrox3rd/venvoy:bootstrap" 2>$null
    Write-Host "✅ Bootstrap image updated" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Could not update bootstrap image (will be updated on first use)" -ForegroundColor Yellow
}

Write-Host ""
if ($ExistingInstall) {
    Write-Host "🎉 venvoy updated successfully!" -ForegroundColor Green
    Write-Host "✨ All new features are now active" -ForegroundColor Green
} else {
    Write-Host "🎉 venvoy installed successfully!" -ForegroundColor Green
}

Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan

# Test if venvoy is immediately available
try {
    $null = Get-Command venvoy -ErrorAction Stop
    Write-Host "   ✅ venvoy is ready to use!" -ForegroundColor Green
    if ($ExistingInstall) {
        Write-Host "   🆕 New features available:" -ForegroundColor Cyan
        Write-Host "      • Improved container runtime selection and handling" -ForegroundColor White
        Write-Host "      • New export wheelhouse option for full offline support of multi-architecture image archive independent of repository availability" -ForegroundColor White
    }
    Write-Host "   1. Run: venvoy init" -ForegroundColor White
    Write-Host "   2. Start coding with AI-powered environments!" -ForegroundColor White
} catch {
    Write-Host "   1. Restart your terminal or PowerShell" -ForegroundColor White
    if ($ExistingInstall) {
        Write-Host "   🆕 New features available:" -ForegroundColor Cyan
        Write-Host "      • Improved container runtime selection and handling" -ForegroundColor White
        Write-Host "      • New export wheelhouse option for full offline support of multi-architecture image archive independent of repository availability" -ForegroundColor White
    }
    Write-Host "   2. Run: venvoy init" -ForegroundColor White
    Write-Host "   3. Start coding with AI-powered environments!" -ForegroundColor White
}

Write-Host ""
Write-Host "💡 The first run will download the venvoy bootstrap image" -ForegroundColor Yellow
Write-Host "   All subsequent operations will be containerized" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔧 Installed to: $InstallDir" -ForegroundColor Cyan
Write-Host "📝 Added to user PATH environment variable" -ForegroundColor Cyan
Write-Host ""
if ($ExistingInstall) {
    Write-Host "🚀 Test new features: venvoy --help" -ForegroundColor Green
} else {
    Write-Host "🚀 Quick test: venvoy --help" -ForegroundColor Green
} 