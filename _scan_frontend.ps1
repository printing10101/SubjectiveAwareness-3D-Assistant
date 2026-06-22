$dirs = @('frontend\src\components\ui', 'frontend\src\components\layout', 'frontend\src\views', 'frontend\src\stores', 'frontend\src\api', 'frontend\src\utils', 'frontend\src\assets\styles')
foreach ($d in $dirs) {
    if (Test-Path $d) {
        $files = Get-ChildItem -Path $d -Recurse -File -Include *.vue,*.js,*.css
        $totalKb = 0
        foreach ($f in $files) { $totalKb += [math]::Round((Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue).Length/1024, 1) }
        Write-Host ("{0,-50} {1,4} files  ~{2} KB" -f $d, $files.Count, [math]::Round($totalKb,1))
    }
}
