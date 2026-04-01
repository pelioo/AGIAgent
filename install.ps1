# AGIAgent Windows Installation Script
# 自动化安装脚本 for Windows

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Color output functions
function Write-Info($msg) {
    Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
    Write-Host $msg -ForegroundColor White
}

function Write-Success($msg) {
    Write-Host "[SUCCESS] " -NoNewline -ForegroundColor Green
    Write-Host $msg -ForegroundColor White
}

function Write-Warning($msg) {
    Write-Host "[WARNING] " -NoNewline -ForegroundColor Yellow
    Write-Host $msg -ForegroundColor White
}

function Write-Err($msg) {
    Write-Host "[ERROR] " -NoNewline -ForegroundColor Red
    Write-Host $msg -ForegroundColor White
}

# Check winget availability
function Test-Winget {
    try {
        Get-Command winget -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Check Python installation
function Test-Python {
    Write-Info "Checking Python installation..."
    $pythonPath = ".\python\python.exe"
    
    if (Test-Path $pythonPath) {
        $version = & $pythonPath --version 2>&1
        Write-Success "Found local Python: $version"
        return $pythonPath
    } else {
        Write-Err "Python not found: $pythonPath"
        return $null
    }
}

# Check Python version
function Test-PythonVersion($pythonCmd) {
    Write-Info "Checking Python version..."
    try {
        $versionOutput = & $pythonCmd --version 2>&1
        $version = $versionOutput.ToString().Replace("Python ", "")
        $parts = $version.Split('.')
        $major = [int]$parts[0]
        $minor = [int]$parts[1]
        
        if ($major -ge 3 -and $minor -ge 8) {
            Write-Success "Python version OK: $version"
            return $true
        } else {
            Write-Err "Python 3.8+ required. Current: $version"
            return $false
        }
    } catch {
        Write-Err "Cannot read Python version"
        return $false
    }
}

# Create virtual environment
function New-Venv {
    Write-Info "Creating virtual environment..."
    $venvPath = ".venv"
    
    if (Test-Path $venvPath) {
        Write-Warning "Virtual environment exists: $venvPath"
        $response = Read-Host "Delete and recreate? (y/n)"
        if ($response -match "^[Yy]$") {
            Write-Info "Removing existing venv..."
            Remove-Item -Recurse -Force $venvPath
        } else {
            Write-Info "Using existing venv"
            return $true
        }
    }
    
    Write-Info "Creating venv: $venvPath"
    & python\python.exe -m venv $venvPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Virtual environment created"
        return $true
    } else {
        Write-Err "Failed to create venv"
        return $false
    }
}

# Enter virtual environment
function Enter-Venv {
    $venvScripts = ".\.venv\Scripts"
    
    if (Test-Path $venvScripts) {
        Write-Info "Venv Scripts ready: $venvScripts"
        return $venvScripts
    } else {
        Write-Err "Cannot find venv Scripts directory"
        return $null
    }
}

# Upgrade pip
function Update-Pip($venvScripts) {
    Write-Info "Upgrading pip..."
    $pipExe = "$venvScripts\pip.exe"
    
    if (Test-Path $pipExe) {
        & $pipExe install --upgrade pip | Out-Null
        Write-Success "pip upgraded"
    }
}

# Install Python dependencies
function Install-PythonDeps($venvScripts) {
    Write-Info "Installing Python dependencies..."
    $pipExe = "$venvScripts\pip.exe"
    $requirements = "requirements.txt"
    
    if (-not (Test-Path $requirements)) {
        Write-Err "requirements.txt not found"
        return $false
    }
    
    Write-Info "Installing packages from requirements.txt..."
    Write-Info "Using Aliyun mirror: https://mirrors.aliyun.com/pypi/simple/"
    & $pipExe install -r $requirements -i https://mirrors.aliyun.com/pypi/simple/
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Dependencies installed"
        return $true
    } else {
        Write-Err "Failed to install dependencies"
        return $false
    }
}

# Install Playwright
function Install-Playwright($venvScripts) {
    Write-Info "Installing Playwright..."
    $pythonExe = "$venvScripts\python.exe"
    $playwrightPath = "Extend-dependenc\playwright"
    
    # Check if local playwright browsers exist
    if (Test-Path $playwrightPath) {
        Write-Info "Found local Playwright browsers: $playwrightPath"
        $env:PLAYWRIGHT_BROWSERS_PATH = $playwrightPath
        Write-Success "Using local Playwright browsers"
        return $true
    }
    
    # Set local path for new installation
    $env:PLAYWRIGHT_BROWSERS_PATH = $playwrightPath
    
    & $pythonExe -m playwright install chromium
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Playwright Chromium installed to: $playwrightPath"
        return $true
    } else {
        Write-Err "Failed to install Playwright"
        return $false
    }
}

# Check Pandoc
function Test-Pandoc {
    try {
        $version = & pandoc --version 2>&1 | Select-Object -First 1
        if ($version) {
            Write-Success "Pandoc installed: $version"
            return $true
        }
    } catch {}
    return $false
}

# Install Pandoc
function Install-Pandoc {
    Write-Info "Installing Pandoc..."
    $localMsi = "Extend-dependenc\pandoc.msi"
    
    # 1. Check local MSI first
    if (Test-Path $localMsi) {
        Write-Info "Found local pandoc.msi: $localMsi"
        Write-Info "Installing Pandoc from local MSI..."
        $result = Start-Process msiexec -ArgumentList "/i `"$localMsi`" /norestart /quiet" -Wait -PassThru
        
        if ($result.ExitCode -eq 0) {
            Write-Success "Pandoc installed from local MSI"
            return $true
        } else {
            Write-Warning "Local MSI installation failed, trying winget..."
        }
    }
    
    # 2. Try winget
    if (Test-Winget) {
        Write-Info "Using winget to install Pandoc..."
        winget install --id JohnMacFarlane.Pandoc -e --silent
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Pandoc installed via winget"
            return $true
        } else {
            Write-Warning "winget failed"
        }
    }
    
    # 3. Prompt manual install
    Write-Warning "Manual Pandoc installation required"
    Write-Info "Download: https://pandoc.org/installing.html"
    Write-Info "Or place pandoc.msi in Extend-dependenc folder and run again"
    
    return $false
}

# Check XeLaTeX
function Test-XeLaTeX {
    try {
        $version = & xelatex --version 2>&1 | Select-Object -First 1
        if ($version) {
            Write-Success "XeLaTeX installed: $version"
            return $true
        }
    } catch {}
    return $false
}

# Install XeLaTeX
function Install-XeLaTeX {
    Write-Info "Installing XeLaTeX..."
    
    $response = Read-Host "Install XeLaTeX? (y/n)"
    
    if ($response -notmatch "^[Yy]$") {
        Write-Warning "Skipping XeLaTeX"
        return $false
    }
    
    if (Test-Winget) {
        Write-Info "Using winget to install MiKTeX..."
        winget install --id MiKTeX.MiKTeX -e --silent
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "MiKTeX installed via winget"
            return $true
        } else {
            Write-Warning "winget failed, manual install needed"
        }
    }
    
    Write-Warning "Manual MiKTeX installation required"
    Write-Info "Download: https://miktex.org/download"
    Write-Info "Or run: winget install MiKTeX.MiKTeX"
    
    return $false
}

# Check Chinese fonts
function Test-ChineseFonts {
    Write-Info "Checking Chinese fonts..."
    $fonts = Get-ChildItem "C:\Windows\Fonts" -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "noto|cjk|simhei|simsun|msyh" }
    
    if ($fonts) {
        Write-Success "Chinese fonts found"
    } else {
        Write-Warning "No common Chinese fonts detected, but Windows usually has built-in fonts"
    }
}

# Verify installation
function Verify-Installation($venvScripts) {
    Write-Info "Verifying installation..."
    $pythonExe = "$venvScripts\python.exe"
    
    if (Test-Path ".venv") {
        Write-Success "Venv exists"
    } else {
        Write-Err "Venv missing"
    }
    
    try {
        & $pythonExe -c "import playwright" 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0 -or $?) {
            Write-Success "Playwright installed"
        }
    } catch {
        Write-Warning "Playwright not verified"
    }
    
    if (Test-Pandoc) {
        Write-Success "Pandoc installed"
    }
    
    if (Test-XeLaTeX) {
        Write-Success "XeLaTeX installed"
    }
    
    Test-ChineseFonts
}

# Print usage
function Print-Usage {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "   Installation Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Environment Variables:" -ForegroundColor Yellow
    Write-Host "  PLAYWRIGHT_BROWSERS_PATH=Extend-dependenc\playwright" -ForegroundColor White
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Activate venv:" -ForegroundColor White
    Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "2. Configure API key in config\config.txt" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Run GUI:" -ForegroundColor White
    Write-Host "   python GUI\app.py" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   Run CLI:" -ForegroundColor White
    Write-Host "   python agia.py \"write a poem\"" -ForegroundColor Cyan
    Write-Host ""
}

# Main
function Main {
    Clear-Host
    
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "   AGIAgent Windows Installation" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check Python
    $pythonCmd = Test-Python
    if (-not $pythonCmd) {
        Write-Err "Python not found"
        exit 1
    }
    
    if (-not (Test-PythonVersion $pythonCmd)) {
        Write-Err "Python version check failed"
        exit 1
    }
    
    # Create venv
    if (-not (New-Venv)) {
        Write-Err "Failed to create venv"
        exit 1
    }
    
    # Enter venv
    $venvScripts = Enter-Venv
    if (-not $venvScripts) {
        Write-Err "Failed to enter venv"
        exit 1
    }
    
    # Upgrade pip
    Update-Pip $venvScripts
    
    # Install deps
    if (-not (Install-PythonDeps $venvScripts)) {
        Write-Err "Failed to install dependencies"
        exit 1
    }
    
    # Install Playwright
    Install-Playwright $venvScripts
    
    # Install Pandoc
    if (-not (Test-Pandoc)) {
        Install-Pandoc
    }
    
    # Install XeLaTeX
    if (-not (Test-XeLaTeX)) {
        Install-XeLaTeX
    }
    
    # Check fonts
    Test-ChineseFonts
    
    # Verify
    Verify-Installation $venvScripts
    
    # Usage
    Print-Usage
    
    Write-Info "Installation script completed"
}

Main
