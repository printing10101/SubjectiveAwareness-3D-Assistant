$paths = @('backend\app', 'frontend\src')
$results = @()
foreach ($p in $paths) {
    Get-ChildItem -Path $p -Recurse -File -Include *.py,*.vue,*.js |
        Where-Object { $_.FullName -notmatch '__pycache__' } |
        ForEach-Object {
            $size = (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue).Length
            $lines = (Get-Content $_.FullName -ErrorAction SilentlyContinue).Count
            $results += [PSCustomObject]@{
                Path   = $_.FullName.Substring($pwd.Path.Length + 1).Replace('\','/')
                SizeKB = [math]::Round($size/1024, 1)
                Lines  = $lines
            }
        }
}
$results | Sort-Object SizeKB -Descending | Select-Object -First 25 | Format-Table -AutoSize
Write-Host "Total files: $($results.Count)"
Write-Host "Total KB: $([math]::Round(($results | Measure-Object -Property SizeKB -Sum).Sum, 1))"
