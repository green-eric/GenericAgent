# ============================================================
#  Windows 10 升级后一键恢复脚本
#  生成时间: 2026-05-12
#  使用方法: 右键 → 以管理员身份运行 PowerShell，执行:
#  Set-ExecutionPolicy Bypass -Scope Process -Force; .\restore.ps1
# ============================================================

$ErrorActionPreference = "Continue"
$BackupDir = "D:\GenericAgent\backup_pre_upgrade"
$LogFile = "$BackupDir\restore_log.txt"
$StartTime = Get-Date

function Write-Log($msg) {
    $ts = Get-Date -Format "HH:mm:ss"
    $line = "[$ts] $msg"
    Write-Host $line
    Add-Content $LogFile $line -ErrorAction SilentlyContinue
}

Write-Log "========== 开始恢复 =========="
$totalSteps = 8
$step = 0

# ── Step 1: Chocolatey ──
$step++; Write-Log "[$step/$totalSteps] 安装 Chocolatey..."
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    try {
        Set-ExecutionPolicy Bypass -Scope Process -Force
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
        Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
        $env:PATH = "$env:ProgramData\chocolatey\bin;$env:PATH"
        Write-Log "  ✅ Chocolatey 安装完成"
    } catch { Write-Log "  ❌ Chocolatey 安装失败: $_" }
} else { Write-Log "  ✅ Chocolatey 已存在" }

# ── Step 2: Chocolatey 批量安装 ──
$step++; Write-Log "[$step/$totalSteps] Chocolatey 批量安装软件..."
$choco_packages = @(
    "7zip", "firefox", "git", "nodejs", "notepadplusplus",
    "python3", "redis-64", "winrar", "everything", "postgresql18"
)
foreach ($pkg in $choco_packages) {
    Write-Log "  安装 $pkg ..."
    choco install $pkg -y --no-progress 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-Log "    ✅ $pkg" }
    else { Write-Log "    ⚠️ $pkg 可能已安装或失败(退出码:$LASTEXITCODE)" }
}

# ── Step 3: pip 包 ──
$step++; Write-Log "[$step/$totalSteps] 安装 pip 包..."
$pipExe = "$env:LOCALAPPDATA\Programs\Python\Python312\pip.exe"
if (-not (Test-Path $pipExe)) { $pipExe = "pip" }
$reqFile = "$BackupDir\requirements.txt"
if (Test-Path $reqFile) {
    & $pipExe install -r $reqFile --quiet 2>&1 | Out-Null
    $pkgCount = (Get-Content $reqFile | Where-Object { $_.Trim() -ne "" }).Count
    Write-Log "  ✅ pip 恢复完成 ($pkgCount 个包)"
} else { Write-Log "  ⚠️ requirements.txt 不存在" }

# ── Step 4: GA 配置恢复 ──
$step++; Write-Log "[$step/$totalSteps] 恢复 GA 配置..."
$gaDir = "D:\GenericAgent"
if (Test-Path "$BackupDir\ga_config\mykey.py") {
    Copy-Item "$BackupDir\ga_config\mykey.py" "$gaDir\mykey.py" -Force
    Write-Log "  ✅ mykey.py 已恢复"
}
if (Test-Path "$BackupDir\ga_config\memory") {
    if (Test-Path "$gaDir\memory") { Remove-Item "$gaDir\memory" -Recurse -Force }
    Copy-Item "$BackupDir\ga_config\memory" "$gaDir\memory" -Recurse -Force
    Write-Log "  ✅ memory 目录已恢复"
}
if (Test-Path "$BackupDir\ga_config\.gitconfig") {
    Copy-Item "$BackupDir\ga_config\.gitconfig" "$env:USERPROFILE\.gitconfig" -Force
    Write-Log "  ✅ git config 已恢复"
}

# ── Step 5: 环境变量 PATH ──
$step++; Write-Log "[$step/$totalSteps] 恢复 PATH..."
$pathFile = "$BackupDir\path_entries.txt"
if (Test-Path $pathFile) {
    $customPaths = Get-Content $pathFile | Where-Object { $_.Trim() -ne "" }
    $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    $added = 0
    foreach ($p in $customPaths) {
        $p = $p.Trim()
        if ($p -and $currentPath -notlike "*$p*") {
            $currentPath += ";$p"
            $added++
        }
    }
    [Environment]::SetEnvironmentVariable("PATH", $currentPath, "User")
    Write-Log "  ✅ 恢复了 $added 条用户 PATH"
}

# ── Step 6: 磁盘信息确认 ──
$step++; Write-Log "[$step/$totalSteps] 磁盘信息..."
$c = Get-Volume -DriveLetter C -ErrorAction SilentlyContinue
$d = Get-Volume -DriveLetter D -ErrorAction SilentlyContinue
Write-Log "  C: $([math]::Round($c.SizeRemaining/1GB,1))GB free / $([math]::Round($c.Size/1GB,1))GB"
Write-Log "  D: $([math]::Round($d.SizeRemaining/1GB,1))GB free / $([math]::Round($d.Size/1GB,1))GB"

# ── Step 7: 验证 ──
$step++; Write-Log "[$step/$totalSteps] 验证..."
$checks = @(
    @{ Name="Python";  Cmd="python";  Args="--version" },
    @{ Name="pip";     Cmd="pip";     Args="--version" },
    @{ Name="Git";     Cmd="git";     Args="--version" },
    @{ Name="Node.js"; Cmd="node";    Args="--version" },
    @{ Name="npm";     Cmd="npm";     Args="--version" },
    @{ Name="Chrome";  Cmd="google-chrome"; Args="--version" },
    @{ Name="7-Zip";   Cmd="7z";      Args="--help" },
    @{ Name="Redis";   Cmd="redis-cli"; Args="--version" },
    @{ Name="Notepad++"; Cmd="notepad++"; Args="--version" }
)
foreach ($c in $checks) {
    try {
        $out = & $c.Cmd $c.Args 2>&1
        Write-Log "  ✅ $($c.Name): $($out[0])"
    } catch { Write-Log "  ⚠️ $($c.Name): 未找到" }
}

# ── Step 8: 手动安装提醒 ──
$step++; Write-Log "[$totalSteps/$totalSteps] 以下软件需手动安装 (详见 manual_install.txt):"
$manual = @(
    "Docker Desktop     → https://www.docker.com/products/docker-desktop",
    "Clash Verge        → https://github.com/clash-verge-rev/clash-verge-rev/releases",
    "微信               → https://weixin.qq.com",
    "Ollama             → https://ollama.com/download",
    "Microsoft Office   → 需要安装包/激活",
    "WezTerm            → https://github.com/wez/wezterm/releases",
    "Aegisub            → https://aegisub.org/downloads",
    "Alibaba Cloud      → https://www.aliyun.com",
    "Binance            → https://www.binance.com",
    "国元领航           → 联系券商重新安装",
    "WSL                → 控制面板 → 启用Windows功能"
)
foreach ($m in $manual) { Write-Log "  🔧 $m" }

$elapsed = (Get-Date) - $StartTime
Write-Log "========== 恢复完成 (耗时: $($elapsed.ToString('mm\:ss'))) =========="
Write-Host ""
Write-Host "⚠️  请重启电脑使环境变量生效" -ForegroundColor Yellow
Write-Host "⚠️  查看 D:\GenericAgent\backup_pre_upgrade\manual_install.txt 获取手动安装清单" -ForegroundColor Yellow


# ============================================================
# WorkBuddy 恢复 (便携版，从备份拷回)
# ============================================================
Write-Host "`n📦 [附加] 恢复 WorkBuddy..." -ForegroundColor Cyan
$wbSrc = "D:\GenericAgent\backup_pre_upgrade\WorkBuddy"
$wbDst = "C:\Users\green\AppData\Roaming\WorkBuddy"

if (Test-Path $wbSrc) {
    if (Test-Path $wbDst) {
        Write-Host "  ⚠️ 目标已存在，跳过 (避免覆盖新数据)" -ForegroundColor Yellow
    } else {
        Write-Host "  正在复制 WorkBuddy (809MB)..." -ForegroundColor Gray
        Copy-Item -Path $wbSrc -Destination $wbDst -Recurse -Force
        $wbSize = (Get-ChildItem $wbDst -Recurse | Measure-Object -Property Length -Sum).Sum
        Write-Host "  ✅ WorkBuddy 已恢复 ($($wbSize//1024//1024)MB)" -ForegroundColor Green
    }
} else {
    Write-Host "  ❌ 备份中未找到 WorkBuddy，跳过" -ForegroundColor Red
}
