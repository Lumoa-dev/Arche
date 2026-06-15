$branch = git branch --show-current
if ($branch -eq 'master' -or $branch -eq 'main') {
    Write-Host "禁止直接提交到 $branch 分支"
    exit 1
}
exit 0
