# venvoy Self-Bootstrapping Installer for Windows
# Works without requiring Python on the host system

param(
    [switch]$Force
)

Write-Host "🚀 venvoy Self-Bootstrapping Installer (Windows)" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan

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

# Create venvoy.bat bootstrap script
$BatchScript = @"
@echo off
setlocal enabledelayedexpansion

set VENVOY_IMAGE=venvoy/bootstrap:latest
set VENVOY_DIR=%USERPROFILE%\.venvoy
set InstallDir=%USERPROFILE%\.venvoy\bin

:: Ensure venvoy directory exists
if not exist "%VENVOY_DIR%" mkdir "%VENVOY_DIR%"

:: Build bootstrap image if it doesn't exist
docker image inspect %VENVOY_IMAGE% >nul 2>&1
if errorlevel 1 (
    echo 🔨 Building venvoy bootstrap image...
    
    :: Create temporary Dockerfile
    set TEMP_DIR=%TEMP%\venvoy_%RANDOM%
    mkdir "%TEMP_DIR%"
    
    echo FROM python:3.11-slim > "%TEMP_DIR%\Dockerfile"
    echo. >> "%TEMP_DIR%\Dockerfile"
    echo # Install system dependencies >> "%TEMP_DIR%\Dockerfile"
    echo RUN apt-get update ^&^& apt-get install -y \ >> "%TEMP_DIR%\Dockerfile"
    echo     git \ >> "%TEMP_DIR%\Dockerfile"
    echo     curl \ >> "%TEMP_DIR%\Dockerfile"
    echo     ^&^& rm -rf /var/lib/apt/lists/* >> "%TEMP_DIR%\Dockerfile"
    echo. >> "%TEMP_DIR%\Dockerfile"
    echo # Install venvoy from git >> "%TEMP_DIR%\Dockerfile"
    echo RUN pip install git+https://github.com/zaphodbeeblebrox3rd/venvoy.git >> "%TEMP_DIR%\Dockerfile"
    echo. >> "%TEMP_DIR%\Dockerfile"
    echo # Set up entrypoint >> "%TEMP_DIR%\Dockerfile"
    echo WORKDIR /workspace >> "%TEMP_DIR%\Dockerfile"
    echo ENTRYPOINT ["venvoy"] >> "%TEMP_DIR%\Dockerfile"
    
    :: Build the image
    docker build -t %VENVOY_IMAGE% "%TEMP_DIR%"
    rmdir /s /q "%TEMP_DIR%"
    
    echo ✅ Bootstrap image built successfully
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
        
        :: Remove venvoy from PATH
        set NEW_PATH=!CURRENT_PATH!
        set NEW_PATH=!NEW_PATH:!InstallDir!;=!
        set NEW_PATH=!NEW_PATH:;!InstallDir!=!
        set NEW_PATH=!NEW_PATH:!InstallDir!=!
        
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

# Add to PATH with better handling
$CurrentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$CurrentSystemPath = [Environment]::GetEnvironmentVariable("PATH", "Machine")

# Check if already in PATH
$InUserPath = $CurrentUserPath -like "*$InstallDir*"
$InSystemPath = $CurrentSystemPath -like "*$InstallDir*"
$InCurrentSession = $env:PATH -like "*$InstallDir*"

if (-not $InUserPath -and -not $InSystemPath) {
    # Add to user PATH
    $NewPath = "$InstallDir;$CurrentUserPath"
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    Write-Host "📝 Added venvoy to user PATH" -ForegroundColor Green
    
    # Also add to current session
    $env:PATH = "$InstallDir;$env:PATH"
    Write-Host "📝 Added venvoy to current session PATH" -ForegroundColor Green
} else {
    Write-Host "📝 venvoy already in PATH" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 venvoy installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan

# Test if venvoy is immediately available
try {
    $null = Get-Command venvoy -ErrorAction Stop
    Write-Host "   ✅ venvoy is ready to use!" -ForegroundColor Green
    Write-Host "   1. Run: venvoy init" -ForegroundColor White
    Write-Host "   2. Start coding with AI-powered environments!" -ForegroundColor White
} catch {
    Write-Host "   1. Restart your terminal or PowerShell" -ForegroundColor White
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
Write-Host "🚀 Quick test: venvoy --help" -ForegroundColor Green 