# -*- coding: utf-8 -*-
"""无头冒烟测试：跑若干帧，确认游戏逻辑/渲染/资源加载都没有异常。"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# 本脚本位于 tools/ 下，工程根目录在上一层
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import kunkun_da_tao_wang as g

game = g.Game()
print("ASSET_DIR =", g.ASSET_DIR)
print("screen size =", game.screen.get_size())
print("audio enabled =", game.audio.enabled, "| bgm =", game.audio.bgm_path)

# 开始界面
for _ in range(20):
    game.handle_events()
    game.update_particles(1 / 60)
    game.draw()

# 正式游玩 300 帧（5 秒），并模拟换道 + 跳跃
game.reset_game()
for i in range(300):
    if i % 40 == 10:
        game.player.move(-1)
        game.time_since_lane_change = 0.0
    if i % 40 == 20:
        game.player.move(1)
        game.time_since_lane_change = 0.0
    if i % 55 == 30:
        game.player.jump()
    game.handle_events()
    game.update(1 / 60)
    game.update_particles(1 / 60)
    game.draw()

print("state after play =", game.state, "score =", round(game.score, 1))

# 结束界面
game.trigger_game_over()
game.draw()
game.state = "gameover"
for _ in range(5):
    game.update_particles(1 / 60)
    game.draw()

# 中文渲染自检：确认字体真的能画中文，而不是空/方块
font = g.get_font(40, True)
surf = font.render("坤坤大逃亡", True, (255, 255, 255))
print("cjk render width =", surf.get_width(), "height =", surf.get_height())

print("SMOKE OK")
