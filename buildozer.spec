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

# (list) 排除目录（dsh-deep-whale 是另一个无关工程，不要打进去）
source.exclude_dirs = .git,.github,__pycache__,.venv,.deps,.pip-tmp,bin,.buildozer,.buildozer_global,dsh-deep-whale,.workbuddy,tools

# (list) 排除文件：这两张是有水印的素材源图，只用于本地生成 icon.png /
# loading_bg.png，不需要打进 APK（省约 2.5 MB）
source.exclude_patterns = kkphoto.png,beijing.png

# (list) 依赖
# 关键：p4a 的 pygame 配方版本是 2.1.0，只支持到 Python 3.10，
# 而 p4a 默认已经是 Python 3.14，不锁版本必定编译失败。
requirements = python3==3.10.13,hostpython3==3.10.13,pygame

# (str) 使用 SDL2 引导器（pygame 必须）
android.bootstrap = sdl2

# (str) 竖屏
orientation = portrait

# (bool) 全屏（隐藏状态栏）
fullscreen = 1

# (str) 目标架构
android.archs = arm64-v8a, armeabi-v7a

# (int) SDK 版本：API 33 与 NDK 25b 是久经验证的组合
android.api = 33
android.minapi = 21
android.ndk = 25b

# (bool) CI 环境自动接受 Android SDK 许可证，避免交互卡死
android.accept_sdk_license = True

# (str) 版本号
version = 1.0

# 本游戏不需要额外权限
android.permissions =

# 图标与启动图
# icon.png       由 tools/prep_assets.py 从 kkphoto.png 生成（512x512）
# presplash 用同一张加载背景：Android 启动闪屏 → 游戏内加载动画 可以无缝衔接
icon.filename = %(source.dir)s/icon.png
presplash.filename = %(source.dir)s/loading_bg.png
presplash.color = #0A0D1A

[buildozer]

log_level = 2
warn_on_root = 1
