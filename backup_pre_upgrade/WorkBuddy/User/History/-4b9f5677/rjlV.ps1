$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,2)
$freeGB  = [math]::Round($os.FreePhysicalMemory/1MB,2)
$usedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB,2)
$pct     = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100,1)
Write-Output "=== Memory ==="
Write-Output "Used: ${usedGB}GB / ${totalGB}GB  (${pct}% used,  Free: ${freeGB}GB)"

Write-Output ""
Write-Output "=== Top 20 Processes by Memory ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 20 |
    ForEach-Object {
        $mem = [math]::Round($_.WorkingSet64/1MB,1)
        "{0,-30} PID={1,-6} Mem={2,7} MB" -f $_.ProcessName, $_.Id, $mem
    }

Write-Output ""
Write-Output "=== CPU Load ==="
Get-CimInstance Win32_Processor | ForEach-Object {
    "CPU: $($_.Name)  Load: $($_.LoadPercentage)%"
}
