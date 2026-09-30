# -*- coding: utf-8 -*-
"""生成真机分辨率下的界面预览图，用于肉眼检查布局（按钮位置、文字是否重叠）。

输出三张图到 tools/preview/：
  loading.png  加载动画
  start.png    开始界面（开始游戏按钮）
  over.png     结束界面（再玩一次 / 退出游戏按钮）
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
OUT = os.path.join(BASE, "tools", "preview")
os.makedirs(OUT, exist_ok=True)

import pygame  # noqa: E402
import kunkun_da_tao_wang as g  # noqa: E402

g._screen_fit_enabled = lambda: True
g._query_screen_size = lambda: (1080, 2400)

game = g.Game()
print("画布 =", game.screen.get_size())

game._draw_loading(0.55, "加载班主任与校长")
pygame.image.save(game.screen, os.path.join(OUT, "loading.png"))

game.state = "start"
game.draw()
pygame.image.save(game.screen, os.path.join(OUT, "start.png"))

game.trigger_game_over()
game.draw()
pygame.image.save(game.screen, os.path.join(OUT, "over.png"))

print("已输出到", OUT)
