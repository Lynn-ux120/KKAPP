# 把《坤坤大逃亡》推到 GitHub（方式B：GitHub Actions 自动打包 APK）
# 用法：
#   1) 在 GitHub 新建一个【空】仓库（不要勾选 README / .gitignore / LICENSE）
#   2) 把下面 $RepoUrl 改成你的仓库地址
#   3) 在本目录运行：  .\push_to_github.ps1

$RepoUrl = "https://github.com/Lynn-ux120/KKAPP.git"   # ← 改成你的仓库地址

Set-Location $PSScriptRoot
if (-not (Test-Path ".git")) { git init }
git add .
git commit -m "坤坤大逃亡 安卓打包工程" 2>$null
git branch -M main
git remote remove origin 2>$null
git remote add origin $RepoUrl
git push -u origin main
Write-Host "推送完成：打开 GitHub 仓库的 Actions 页签，等构建结束后在 Artifacts 下载 APK。"
