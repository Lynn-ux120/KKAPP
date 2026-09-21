# -*- coding: utf-8 -*-
"""
双击启动器（Windows 电脑端用）。

真正的游戏代码已经移到 kunkun_da_tao_wang.py —— 因为 Buildozer 打包 APK 时
要求源码文件名必须是纯 ASCII，中文文件名在 Android 构建链上会出问题。

以后要改游戏内容，请直接编辑 kunkun_da_tao_wang.py。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kunkun_da_tao_wang

if __name__ == "__main__":
    kunkun_da_tao_wang.main()
