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

# ---- 菜单按钮自检 ----
canvas = game.screen.get_rect()
for btn in (game.btn_start, game.btn_retry, game.btn_quit):
    inside = canvas.contains(btn.rect)
    print(f"按钮「{btn.label}」 rect={tuple(btn.rect)} 在画布内={inside}")
    assert inside, f"按钮「{btn.label}」超出画布"

# 开始界面：点「开始游戏」应进入游戏
game.state = "start"
game._handle_menu_click(game.btn_start.rect.center)
print("点击开始按钮 -> state =", game.state)
assert game.state == "playing"

# 结束界面：点「再玩一次」应重开
game.trigger_game_over()
game._handle_menu_click(game.btn_retry.rect.center)
print("点击再玩一次 -> state =", game.state)
assert game.state == "playing"

# 结束界面：点「退出游戏」应结束主循环
game.trigger_game_over()
game._handle_menu_click(game.btn_quit.rect.center)
print("点击退出游戏 -> running =", game.running)
assert game.running is False

# 按钮按下态反馈
game.running = True
game.state = "start"
game._set_buttons_pressed(game.btn_start.rect.center, True)
print("按下态 =", game.btn_start.pressed)
assert game.btn_start.pressed is True
game._set_buttons_pressed(game.btn_start.rect.center, False)

print("SMOKE OK")
