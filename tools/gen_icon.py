# -*- coding: utf-8 -*-
"""生成应用图标 icon.png（512x512），供 buildozer 使用。"""
import os
import pygame

# 本脚本位于 tools/ 下，工程根目录在上一层
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 512

pygame.init()
screen = pygame.display.set_mode((S, S))
# 显式用 24 位无 alpha 表面，避免 pygame 写出 Android 工具链不认的 tRNS 块
surf = pygame.Surface((S, S), 0, 24)

# 背景：深蓝竖向渐变
top = (20, 28, 60)
bot = (90, 72, 130)
for y in range(S):
    t = y / (S - 1)
    c = (int(top[0] + (bot[0] - top[0]) * t),
         int(top[1] + (bot[1] - top[1]) * t),
         int(top[2] + (bot[2] - top[2]) * t))
    pygame.draw.line(surf, c, (0, y), (S, y))

# 金色圆环
pygame.draw.circle(surf, (255, 206, 70), (S // 2, S // 2), 200, 14)
pygame.draw.circle(surf, (255, 255, 255, 40), (S // 2, S // 2), 168)

# 中央汉字「坤」
font_path = os.path.join(BASE, "font.otf")
ok = False
if os.path.exists(font_path):
    try:
        f = pygame.font.Font(font_path, 240)
        img = f.render("坤", True, (255, 224, 130))
        rect = img.get_rect(center=(S // 2, S // 2))
        surf.blit(img, rect)
        ok = img.get_width() > 40
    except Exception as e:
        print("font error:", e)

# 底部小字
try:
    f2 = pygame.font.Font(font_path, 52) if os.path.exists(font_path) else pygame.font.Font(None, 52)
    sub = f2.render("大逃亡", True, (240, 242, 248))
    surf.blit(sub, sub.get_rect(center=(S // 2, S - 74)))
except Exception:
    pass

out = os.path.join(BASE, "icon.png")
pygame.image.save(surf, out)
print("icon saved:", out, os.path.getsize(out), "bytes; font_ok=", ok)
