$services = Get-ChildItem -Path 'backend\app\services' -File -Filter *.py | Sort-Object Name
Write-Host "Backend services count: $($services.Count)"
Write-Host "---"
$services | ForEach-Object { $lines = (Get-Content $_.FullName).Count; Write-Host ("{0,-50} {1,5} lines" -f $_.Name, $lines) }
