[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,2)
$freeGB  = [math]::Round($os.FreePhysicalMemory/1MB,2)
$usedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB,2)
$pct     = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100,1)
$wbCount = (Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue).Count
$cpuLoad = (Get-CimInstance Win32_Processor).LoadPercentage
$skillCount = (Get-ChildItem "C:\Users\green\.workbuddy\skills" -Directory -ErrorAction SilentlyContinue).Count

Write-Output "=== System ==="
Write-Output "Memory: ${usedGB}GB / ${totalGB}GB (${pct}% used, Free: ${freeGB}GB)"
Write-Output "CPU: ${cpuLoad}%"
Write-Output "Skills: ${skillCount}"
Write-Output "WorkBuddy processes: ${wbCount}"

Write-Output ""
$mainProcs = Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue | Where-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
    $cmd -notmatch "--type="
}
Write-Output "=== Main Process Start Times ==="
foreach ($p in $mainProcs) {
    Write-Output "  PID=$($p.Id)  Started=$($p.StartTime.ToString('HH:mm:ss'))  Mem=$([math]::Round($p.WorkingSet64/1MB,1))MB"
}

Write-Output ""
Write-Output "=== WorkBuddy Process Types ==="
$types = @{}
Get-Process -Name "WorkBuddy" -ErrorAction SilentlyContinue | ForEach-Object {
    $type = "main"
    try {
        $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
        if ($cmd -match "--type=([^ ]+)") { $type = $Matches[1] } else { $type = "main" }
    } catch {}
    if (-not $types.ContainsKey($type)) { $types[$type] = [PSCustomObject]@{Count=0;TotalMem=0} }
    $types[$type].Count++
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    $types[$type].TotalMem += $mem
}
foreach ($kv in $types.GetEnumerator()) {
    Write-Output "  $($kv.Key): $($kv.Value.Count) procs, $([math]::Round($kv.Value.TotalMem,0))MB"
}

Write-Output ""
Write-Output "=== Top 10 by Memory ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 | ForEach-Object {
    $mem = [math]::Round($_.WorkingSet64/1MB,1)
    Write-Output "  $($_.ProcessName) | PID=$($_.Id) | ${mem}MB"
}
