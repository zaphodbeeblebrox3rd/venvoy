# venvoy Uninstaller for Windows
# Removes venvoy installation and cleans up PATH entries

param(
    [switch]$Force
)

Write-Host "🗑️  venvoy Uninstaller (Windows)" -ForegroundColor Red
Write-Host "=================================" -ForegroundColor Red

$InstallDir = "$env:USERPROFILE\.venvoy\bin"
$VenvoyDir = "$env:USERPROFILE\.venvoy"
$ProjectsDir = "$env:USERPROFILE\venvoy-projects"

# Show what will be removed
Write-Host ""
Write-Host "This will remove:" -ForegroundColor Yellow
Write-Host "  📁 Installation directory: $InstallDir" -ForegroundColor White
Write-Host "  📁 Configuration directory: $VenvoyDir" -ForegroundColor White
Write-Host "  📁 Projects directory: $ProjectsDir" -ForegroundColor White
Write-Host "  🔗 PATH entries from user environment variables" -ForegroundColor White
Write-Host "  🐳 Docker images (venvoy/bootstrap:latest and venvoy/* images)" -ForegroundColor White
Write-Host ""

if (-not $Force) {
    $Confirm = Read-Host "Are you sure you want to uninstall venvoy? (y/N)"
    if ($Confirm -notmatch '^[Yy]$') {
        Write-Host "❌ Uninstallation cancelled" -ForegroundColor Red
        exit 0
    }
}

Write-Host ""
Write-Host "🗑️  Removing venvoy..." -ForegroundColor Red

# Remove installation directory
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force
    Write-Host "✅ Removed installation directory" -ForegroundColor Green
}

# Remove configuration directory
if (Test-Path $VenvoyDir) {
    Remove-Item -Path $VenvoyDir -Recurse -Force
    Write-Host "✅ Removed configuration directory" -ForegroundColor Green
}

# Ask about projects directory
if (Test-Path $ProjectsDir) {
    Write-Host ""
    if (-not $Force) {
        $RemoveProjects = Read-Host "Remove projects directory with environment exports? (y/N)"
        if ($RemoveProjects -match '^[Yy]$') {
            Remove-Item -Path $ProjectsDir -Recurse -Force
            Write-Host "✅ Removed projects directory" -ForegroundColor Green
        } else {
            Write-Host "📁 Kept projects directory: $ProjectsDir" -ForegroundColor Yellow
        }
    } else {
        Remove-Item -Path $ProjectsDir -Recurse -Force
        Write-Host "✅ Removed projects directory" -ForegroundColor Green
    }
}

# Remove PATH entries
Write-Host ""
Write-Host "🔧 Cleaning up PATH..." -ForegroundColor Cyan

$CurrentUserPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($CurrentUserPath -like "*$InstallDir*") {
    # Create backup
    $BackupPath = "$env:TEMP\venvoy-path-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').txt"
    $CurrentUserPath | Out-File -FilePath $BackupPath -Encoding UTF8
    Write-Host "📋 PATH backup saved to: $BackupPath" -ForegroundColor Yellow
    
    # Remove venvoy from PATH
    $NewPath = ($CurrentUserPath -split ';' | Where-Object { $_ -notlike "*$InstallDir*" }) -join ';'
    [Environment]::SetEnvironmentVariable("PATH", $NewPath, "User")
    
    # Also remove from current session
    $env:PATH = ($env:PATH -split ';' | Where-Object { $_ -notlike "*$InstallDir*" }) -join ';'
    
    Write-Host "✅ Removed venvoy from user PATH" -ForegroundColor Green
}

# Remove Docker images
Write-Host ""
Write-Host "🐳 Cleaning up Docker images..." -ForegroundColor Cyan

# Check if Docker is available
if (Get-Command docker -ErrorAction SilentlyContinue) {
    # Remove bootstrap image
    try {
        $null = docker image inspect venvoy/bootstrap:latest 2>$null
        docker rmi venvoy/bootstrap:latest 2>$null
        Write-Host "✅ Removed bootstrap image" -ForegroundColor Green
    } catch {
        # Image doesn't exist, skip
    }
    
    # Remove venvoy environment images
    $VenvoyImages = docker images --format "table {{.Repository}}:{{.Tag}}" | Select-String "^venvoy/" | Where-Object { $_ -notmatch "bootstrap" }
    if ($VenvoyImages) {
        Write-Host "Found venvoy environment images:" -ForegroundColor Yellow
        $VenvoyImages | ForEach-Object { Write-Host "  $_" -ForegroundColor White }
        Write-Host ""
        
        if (-not $Force) {
            $RemoveImages = Read-Host "Remove all venvoy environment images? (y/N)"
            if ($RemoveImages -match '^[Yy]$') {
                $VenvoyImages | ForEach-Object {
                    $image = $_.ToString().Trim()
                    if ($image -and $image -ne "REPOSITORY:TAG") {
                        try {
                            docker rmi $image 2>$null
                        } catch {
                            # Ignore errors
                        }
                    }
                }
                Write-Host "✅ Removed venvoy environment images" -ForegroundColor Green
            }
        } else {
            $VenvoyImages | ForEach-Object {
                $image = $_.ToString().Trim()
                if ($image -and $image -ne "REPOSITORY:TAG") {
                    try {
                        docker rmi $image 2>$null
                    } catch {
                        # Ignore errors
                    }
                }
            }
            Write-Host "✅ Removed venvoy environment images" -ForegroundColor Green
        }
    }
    
    # Remove stopped containers
    $VenvoyContainers = docker ps -a --format "table {{.Names}}" | Select-String "venvoy|bootstrap"
    if ($VenvoyContainers) {
        $VenvoyContainers | ForEach-Object {
            $container = $_.ToString().Trim()
            if ($container -and $container -ne "NAMES") {
                try {
                    docker rm $container 2>$null
                } catch {
                    # Ignore errors
                }
            }
        }
        Write-Host "✅ Removed venvoy containers" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  Docker not available, skipping image cleanup" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 venvoy uninstalled successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Restart your terminal/PowerShell to update PATH" -ForegroundColor White
Write-Host "   2. Remove any remaining Docker volumes manually if needed:" -ForegroundColor White
Write-Host "      docker volume ls | Select-String venvoy" -ForegroundColor Gray
Write-Host ""
Write-Host "💡 To reinstall venvoy later, run the installer again" -ForegroundColor Yellow 