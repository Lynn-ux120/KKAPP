[app]

# (str) 应用显示名称
title = 坤坤大逃亡

# (str) 包名（仅小写字母/数字/点）
package.name = kunkundaotao
package.domain = org.kunkun

# (str) 源码目录
source.dir = .

# (list) 打进 APK 的资源扩展名
source.include_exts = py,jpg,png,mp3,ogg,wav,ttf,otf

# (list) 排除目录
source.exclude_dirs = .git,__pycache__,.venv,.deps,.pip-tmp

# (list) 依赖
requirements = python3,pygame

# (str) 竖屏
orientation = portrait

# (bool) 全屏
fullscreen = 0

# (str) 目标架构
android.archs = arm64-v8a, armeabi-v7a

# (int) SDK 版本
android.api = 30
android.minapi = 21

# (str) 版本号
version = 0.1

# 本游戏不需要额外权限
android.permissions =

# 图标（可选，放入 icon.png 后取消注释）
# icon.filename = %(source.dir)s/icon.png

[buildozer]

log_level = 2
warn_on_root = 1
