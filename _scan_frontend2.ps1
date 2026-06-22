$dirs = @(
    @{Name='UI 组件'; Path='frontend\src\components\ui'},
    @{Name='布局组件'; Path='frontend\src\components\layout'},
    @{Name='Views 顶层'; Path='frontend\src\views'},
    @{Name='Stores'; Path='frontend\src\stores'},
    @{Name='API'; Path='frontend\src\api'},
    @{Name='Utils'; Path='frontend\src\utils'},
    @{Name='Styles'; Path='frontend\src\assets\styles'}
)
foreach ($d in $dirs) {
    if (Test-Path $d.Path) {
        Write-Host "=== $($d.Name) ($($d.Path)) ==="
        Get-ChildItem -Path $d.Path -Recurse -File -Include *.vue,*.js,*.css |
            ForEach-Object {
                $lines = (Get-Content $_.FullName).Count
                Write-Host ("  {0,-50} {1,5} lines" -f $_.Name, $lines)
            }
    }
}
