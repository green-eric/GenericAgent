$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,2)
$freeGB  = [math]::Round($os.FreePhysicalMemory/1MB,2)
$usedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB,2)
$pct     = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100,1)
$wbCount = (Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue).Count
$cpuLoad = (Get-CimInstance Win32_Processor).LoadPercentage

Write-Output "=== 概览 ==="
Write-Output "Memory: ${usedGB}GB / ${totalGB}GB ($pct% used, Free: ${freeGB}GB)"
Write-Output "CPU: ${cpuLoad}%"
Write-Output "WorkBuddy: ${wbCount} 个进程"

Write-Output ""
Write-Output "=== WorkBuddy 进程 ==="
Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending | ForEach-Object {
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    $type = "main"
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmd -match "--type=renderer")      { $type = "renderer" }
        elseif ($cmd -match "--type=gpu-process") { $type = "gpu" }
        elseif ($cmd -match "--type=utility")     { $type = "utility" }
        elseif ($cmd -match "jsonServerMain")     { $type = "json-srv" }
    } catch {}
    Write-Output "  PID=$($_.Id)  Start=$($_.StartTime)  ${mem}MB  $type"
}

Write-Output ""
Write-Output "=== Top 10 内存 ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 | ForEach-Object {
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    Write-Output "  $($_.ProcessName,-25) PID=$($_.Id,-6) ${mem}MB"
}
