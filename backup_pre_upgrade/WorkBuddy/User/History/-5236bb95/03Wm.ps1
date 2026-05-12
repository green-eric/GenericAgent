$extDir = "C:\Users\green\AppData\Local\Programs\WorkBuddy\resources\app\extensions"
if (Test-Path $extDir) {
    Write-Output "=== Built-in Extensions ==="
    Get-ChildItem $extDir -Directory | ForEach-Object {
        $jsonFile = Join-Path $_.FullName "package.json"
        if (Test-Path $jsonFile) {
            $json = Get-Content $jsonFile -Raw | ConvertFrom-Json
            $name = $json.displayName
            if (-not $name) { $name = $json.name }
            Write-Output "  $name ($($_.Name))"
        }
    }
}

Write-Output ""
$userExtDir = "C:\Users\green\.workbuddy\extensions"
if (Test-Path $userExtDir) {
    Write-Output "=== User Extensions ==="
    Get-ChildItem $userExtDir -Directory | ForEach-Object {
        $jsonFile = Join-Path $_.FullName "package.json"
        if (Test-Path $jsonFile) {
            $json = Get-Content $jsonFile -Raw | ConvertFrom-Json
            $name = $json.displayName
            if (-not $name) { $name = $json.name }
            $enabled = ""
            Write-Output "  $name ($($_.Name))"
        }
    }
}

Write-Output ""
Write-Output "=== Settings - Enabled Extensions ==="
$settingsFile = "C:\Users\green\AppData\Roaming\WorkBuddy\User\settings.json"
if (Test-Path $settingsFile) {
    $settings = Get-Content $settingsFile -Raw | ConvertFrom-Json
    $settings.PSObject.Properties | Where-Object { $_.Name -match "ext|plugin|agent|skill" } | ForEach-Object {
        Write-Output "  $($_.Name) = $($_.Value)"
    }
}

Write-Output ""
Write-Output "=== Disabled Extensions ==="
$disabledFile = "C:\Users\green\AppData\Roaming\WorkBuddy\User\extensions\extensions.json"
if (Test-Path $disabledFile) {
    Get-Content $disabledFile -Raw | ConvertFrom-Json | Get-Member -MemberType NoteProperty | ForEach-Object {
        Write-Output "  $($_.Name)"
    }
}
