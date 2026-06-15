$exit = 0
$exclude = @('.venv', 'node_modules', '.git', '__pycache__', 'dist')
Get-ChildItem -Recurse -File | Where-Object {
    $ignore = $false
    foreach ($d in $exclude) { if ($_.FullName -match [regex]::Escape($d)) { $ignore = $true; break } }
    -not $ignore -and $_.Extension -notin '.png','.jpg','.ico','.pyc'
} | ForEach-Object {
    try {
        $c = [System.IO.File]::ReadAllText($_.FullName)
        if ($c -match 'BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY') {
            Write-Host ("发现私钥: " + $_.FullName)
            $exit = 1
        }
    } catch {}
}
exit $exit
