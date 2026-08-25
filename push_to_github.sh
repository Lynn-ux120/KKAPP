#!/usr/bin/env bash
# 把《坤坤大逃亡》推到 GitHub（方式B：GitHub Actions 自动打包 APK）
# 用法：
#   1) 在 GitHub 新建一个【空】仓库（不要勾选 README / .gitignore / LICENSE）
#   2) 把第 6 行的仓库地址改成你的仓库
#   3) 在项目目录运行：  bash push_to_github.sh
set -e

REPO_URL="https://github.com/Lynn-ux120/KKAPP.git"   # ← 改成你的仓库地址

cd "$(dirname "$0")"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init
fi
git add .
git commit -m "坤坤大逃亡 安卓打包工程" || true
git branch -M main
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git push -u origin main
echo "推送完成：打开 GitHub 仓库的 Actions 页签，等构建结束后在 Artifacts 下载 APK。"
