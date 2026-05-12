$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,2)
$freeGB  = [math]::Round($os.FreePhysicalMemory/1MB,2)
$usedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB,2)
$pct     = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100,1)
Write-Output "=== Memory ==="
Write-Output "Used: ${usedGB}GB / ${totalGB}GB  (${pct}% used,  Free: ${freeGB}GB)"

Write-Output ""
$wbCount = (Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue).Count
Write-Output "=== WorkBuddy 进程数: $wbCount ==="
Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending | ForEach-Object {
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    $type = ""
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmd -match "--type=renderer") { $type = "[renderer]" }
        elseif ($cmd -match "--type=gpu-process") { $type = "[gpu]" }
        elseif ($cmd -match "--type=utility") { $type = "[utility/node]" }
        elseif ($cmd -match "jsonServerMain") { $type = "[json-server]" }
        else { $type = "[main]" }
    } catch {}
    Write-Output "  PID=$($_.Id)  ${mem}MB  $type"
}

Write-Output ""
Write-Output "=== Top 10 by Memory ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 | ForEach-Object {
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    Write-Output "  $($_.ProcessName)  PID=$($_.Id)  ${mem}MB"
}

Write-Output ""
Get-CimInstance Win32_Processor | ForEach-Object {
    Write-Output "=== CPU Load: $($_.LoadPercentage)% ==="
}
