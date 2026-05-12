$skillDir = "C:\Users\green\.workbuddy\skills"
$skills = Get-ChildItem $skillDir -Directory | Select-Object Name | Sort-Object Name
Write-Output "Total: $($skills.Count) skills"
foreach ($s in $skills) {
    Write-Output $s.Name
}
