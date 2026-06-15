$limit = 1024KB
$exit = 0
git diff --cached --name-only --diff-filter=A | ForEach-Object {
    $p = Join-Path (Get-Location) $_
    if (Test-Path $p) {
        $s = (Get-Item $p).Length
        if ($s -gt $limit) {
            Write-Host ("文件过大 (" + [math]::Round($s/1KB) + "KB): " + $_)
            $exit = 1
        }
    }
}
exit $exit
