$skillDir = "C:\Users\green\.workbuddy\skills"
$skills = Get-ChildItem $skillDir -Directory | Select-Object Name

# 计算每个技能目录的大小
foreach ($s in $skills) {
    $size = 0
    try {
        $size = (Get-ChildItem (Join-Path $skillDir $s.Name) -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    } catch {}
    $sizeMB = [math]::Round($size/1MB,1)
    $fileCount = 0
    try {
        $fileCount = (Get-ChildItem (Join-Path $skillDir $s.Name) -Recurse -ErrorAction SilentlyContinue).Count
    } catch {}
    Write-Output "$sizeMB MB | $fileCount files | $($s.Name)"
}
