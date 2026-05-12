[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$skillDir = "C:\Users\green\.workbuddy\skills"
$allSkills = @(Get-ChildItem $skillDir -Directory | Select-Object Name, FullName | Sort-Object Name)

Write-Output "Total skills: $($allSkills.Count)"
Write-Output ""

# 打印所有技能列表，带编号
for ($i = 0; $i -lt $allSkills.Count; $i++) {
    Write-Output "[$i] $($allSkills[$i].Name)"
}
