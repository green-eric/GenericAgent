$os = Get-CimInstance Win32_OperatingSystem
$totalGB = [math]::Round($os.TotalVisibleMemorySize/1MB,2)
$freeGB = [math]::Round($os.FreePhysicalMemory/1MB,2)
$usedGB = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB,2)
$pct = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize*100,1)
Write-Output "=== Memory ==="
Write-Output "Used: ${usedGB}GB / ${totalGB}GB (${pct}% used, ${freeGB}GB free)"

Write-Output ""
Write-Output "=== CPU ==="
Get-CimInstance Win32_Processor | ForEach-Object { Write-Output "$($_.Name) | Cores: $($_.NumberOfCores) | Logical: $($_.NumberOfLogicalProcessors) | Load: $($_.LoadPercentage)%" }

Write-Output ""
Write-Output "=== Top 15 Processes by Memory ==="
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 15 Name, Id, @{N='MemMB';E={[math]::Round($_.WorkingSet64/1MB,1)}} | Format-Table -AutoSize

Write-Output ""
Write-Output "=== Disk ==="
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    $usedPct = [math]::Round(($_.Size-$_.FreeSpace)/$_.Size*100,1)
    Write-Output "$($_.DeviceID) Free: $([math]::Round($_.FreeSpace/1GB,1))GB / $([math]::Round($_.Size/1GB,1))GB ($usedPct% used)"
}
