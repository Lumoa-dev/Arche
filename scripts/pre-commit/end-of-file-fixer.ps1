$exit = 0
$exclude = @('.venv', 'node_modules', '.git', '__pycache__', 'dist')
Get-ChildItem -Recurse -File | Where-Object {
    $ignore = $false
    foreach ($d in $exclude) { if ($_.FullName -match [regex]::Escape($d)) { $ignore = $true; break } }
    -not $ignore -and $_.Extension -notin '.png','.jpg','.ico','.pdf','.zip','.gz','.pyc'
} | ForEach-Object {
    try {
        $c = [System.IO.File]::ReadAllText($_.FullName)
        if ($c.Length -gt 0 -and -not $c.EndsWith([Environment]::NewLine)) {
            Write-Host ("  Fixing EOF: " + $_.FullName)
            [System.IO.File]::WriteAllText($_.FullName, $c.TrimEnd() + [Environment]::NewLine)
            $exit = 1
        }
    } catch {}
}
exit $exit
