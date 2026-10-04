# -*- coding: utf-8 -*-
"""生成真机分辨率下的界面预览图，用于肉眼检查布局（按钮位置、文字是否重叠）。

输出四张图到 tools/preview/：
  loading.png  加载动画（beijing.png 背景 + 进度条）
  start.png    开始界面（开始游戏按钮 + 操作/规则提醒）
  playing.png  游玩中（顶部 HUD 状态条）
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

SCREEN = (1080, 2400)          # 按主流机型比例布局
g._screen_fit_enabled = lambda: True
g._query_screen_size = lambda: SCREEN

game = g.Game()
W, H = game.screen.get_size()
print(f"屏幕 {SCREEN[0]}x{SCREEN[1]} -> 画布 {W}x{H}  "
      f"({W * H / 1e6:.2f}M 像素, 缩放 {SCREEN[0] / W:.2f}x)")


def save(name):
    """按屏幕真实尺寸放大后保存，便于检查最终的清晰度观感。"""
    big = pygame.transform.smoothscale(game.screen, SCREEN)
    pygame.image.save(big, os.path.join(OUT, name))
    print("  ->", name)


game._draw_loading(0.55, "加载班主任与校长")
save("loading.png")

game.state = "start"
game.draw()
save("start.png")

game.reset_game()
game.state = "playing"
for _ in range(180):
    game.update(1 / 60)
    game.update_particles(1 / 60)
game.time_since_lane_change = 3.1          # 凝视条走到一半
game.player.invincible_timer = 3.0
game.player.coffee_timer = 2.0
game.draw()
save("playing.png")

# 凝视态：验证"红版背景"的观感（这一版把整屏红罩换成了背景换图）
game.time_since_lane_change = 5.4
game.update(1 / 60)
for _ in range(20):
    game.update(1 / 60)
game.draw()
save("gaze.png")

game.gaze = False
game.trigger_game_over()
game.draw()
save("over.png")

print("已输出到", OUT)
