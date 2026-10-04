# -*- coding: utf-8 -*-
"""
=============================================================================
《坤坤大逃亡》—— 校园大逃亡 · 无尽竖版跑酷
=============================================================================
背景故事：
    同学"坤坤"在校园里惹了麻烦，班主任"shall we"和校长"花招"穷追不舍。
    坤坤只能一路狂奔，在三条跑道上躲避课桌、黑板擦和漫天试卷，
    还要提防"班主任的凝视"。

操作方式：
    左 / 右方向键 或 A / D      —— 切换跑道（切换跑道会重置凝视倒计时）
    上方向键 / W / 空格         —— 跳跃（可跳过矮障碍物：黑板擦、试卷）
    ESC                         —— 退出游戏
    R（游戏结束后）             —— 重新开始

依赖与运行：
    pip install pygame
    python kunkun_da_tao_wang.py
=============================================================================
"""

import os
import random
import math
import sys
from collections import OrderedDict

import pygame

# 【关键】pygame.SCALED 默认按 letterbox 缩放：保持宽高比、多余部分填黑边。
# 这正是"画面撑不满全屏"的元凶。改成 overscan 后 SDL 会把逻辑画面直接
# 拉伸铺满屏幕；由于画布比例本身就等于屏幕比例，拉伸不会造成形变。
# 该 hint 必须在创建窗口之前设置。
os.environ.setdefault("SDL_RENDER_LOGICAL_SIZE_MODE", "overscan")


# ==========================================================================
# 一、全局常量
# ==========================================================================
# ---- 设计稿基准尺寸（美术与排版数值一律按这套坐标书写）----
# 【为什么要区分"设计稿尺寸"和"渲染倍率"】
# pygame 是 CPU 软件渲染，画布像素总量直接决定帧率，画布不能无限大；
# 但画布太小又会被 SDL 放大，画面发虚。折中办法是钉死"设计稿宽 720"，
# 再用一个倍率把整套美术、字号、间距一起放大到目标画布分辨率——
# 布局比例永远不变，只是像素密度变高。
#
# RENDER_SCALE 是唯一的清晰度 / 帧率旋钮：
#   1.00 → 画布 720 宽（约 115 万像素，最流畅，但在 1080 屏上要放大 1.5 倍，偏软）
#   1.25 → 画布 900 宽（约 180 万像素，1080 屏只放大 1.2 倍，锐度明显提升）
#   1.50 → 画布 1080 宽（与 1080 屏 1:1，最清晰，像素量翻到 2.6 倍）
# 真机若仍掉帧就调小，反之调大；改这一个数即可，其余代码不用动。
BASE_W = 720                      # 设计稿基准宽度
BASE_H = 820                      # 设计稿基准高度（默认画布高）
# 真机调优时可用环境变量覆盖（不必改代码重新打包）：
#   KK_RENDER_SCALE=1.0 / 1.25 / 1.5
RENDER_SCALE = float(os.environ.get("KK_RENDER_SCALE", "1.25"))

_S = RENDER_SCALE                 # 渲染缩放因子：设计稿像素 → 画布像素
DESIGN_W = int(round(BASE_W * _S))        # 画布实际宽度
DESIGN_H = int(round(BASE_H * _S))        # 画布默认高度
CANVAS_H_MIN = int(round(820 * _S))       # 画布高度下限（防宽屏把布局压扁）
CANVAS_H_MAX = int(round(1800 * _S))      # 画布高度上限（控制软件渲染像素总量）
DESIGN_PLAYER_BOTTOM_GAP = 180    # 玩家判定线距画布底部的距离（设计稿单位）
DESIGN_JUMP_HEIGHT = 150          # 跳跃最大上升高度（设计稿单位）
DESIGN_SPEEDS = (240.0, 13.0, 950.0)   # 障碍初速 / 每秒递增 / 速度上限

FPS = 60
LANE_COUNT = 3                    # 跑道数量

# 跑道与障碍尺寸（侧边栏移除后跑道铺满全宽，障碍相应加宽以免显得空旷）
OBSTACLE_W = 150                  # 障碍宽度
POWERUP_SIZE = 76                 # 道具直径
SIDE_PANEL_W = 0                  # 侧边栏宽度：已移除

# ---- 运行时尺寸（由 _apply_render_scale() 重算）----
WIDTH, HEIGHT = DESIGN_W, DESIGN_H
PLAY_W, SIDE_W = WIDTH, SIDE_PANEL_W
LANE_W = PLAY_W / LANE_COUNT      # 每条跑道宽度
# 三条跑道中心的 x 坐标
LANE_CENTERS = [PLAY_W * (2 * i + 1) / 6.0 for i in range(LANE_COUNT)]
PLAYER_Y = HEIGHT - int(round(DESIGN_PLAYER_BOTTOM_GAP * _S))   # 玩家脚底判定线
JUMP_HEIGHT = int(round(DESIGN_JUMP_HEIGHT * _S))
OBSTACLE_SPEED_BASE, OBSTACLE_SPEED_INC, OBSTACLE_SPEED_MAX = DESIGN_SPEEDS

# ---- 时间类常量：不随分辨率变化 ----
JUMP_DURATION = 0.6               # 跳跃持续时间（秒）
SPAWN_INTERVAL_BASE = 1.0         # 障碍初始生成间隔（秒）
SPAWN_INTERVAL_MIN = 0.42         # 障碍生成间隔下限


# --------------------------------------------------------------------------
# 分辨率换算
# --------------------------------------------------------------------------
def px(value):
    """设计稿像素 → 画布像素。

    整套美术与排版数值都按 720 宽的设计稿书写，这里是唯一的换算出口。
    调 RENDER_SCALE 就能整体提高 / 降低清晰度，不需要动任何布局代码。
    """
    return int(round(value * _S))


def vh(fraction):
    """按画布高度的比例取纵坐标。

    画布高度随设备屏幕比例在 820~1800 之间浮动，菜单布局若写死像素，
    矮画布上会挤成一团、高画布上会散得太开。统一用比例定位即可自适应。
    """
    return int(round(HEIGHT * fraction))


def _apply_render_scale(canvas_h):
    """按屏幕比例确定画布高度，并重算与高度相关的全局常量。

    canvas_h：画布高度。等于 画布宽 × 屏幕高/屏幕宽，使画布宽高比与屏幕
             完全一致——这样 SCALED 缩放后不留任何黑边。
    """
    global HEIGHT, PLAY_W, SIDE_W, LANE_W, LANE_CENTERS
    global PLAYER_Y, JUMP_HEIGHT
    global OBSTACLE_SPEED_BASE, OBSTACLE_SPEED_INC, OBSTACLE_SPEED_MAX

    HEIGHT = max(CANVAS_H_MIN, min(CANVAS_H_MAX, int(canvas_h)))
    PLAY_W = WIDTH                       # 跑道区 = 整个画布（侧边栏已移除）
    SIDE_W = SIDE_PANEL_W
    LANE_W = PLAY_W / LANE_COUNT
    LANE_CENTERS = [PLAY_W * (2 * i + 1) / 6.0 for i in range(LANE_COUNT)]

    # 玩家判定线贴着画布底部，角色不会飘到屏幕中间
    PLAYER_Y = HEIGHT - px(DESIGN_PLAYER_BOTTOM_GAP)
    # 跳跃高度与人物同步（只影响观感，不参与碰撞判定）
    JUMP_HEIGHT = px(DESIGN_JUMP_HEIGHT)
    # 画布越高看得越远，速度同比放大才能维持原本的反应时间。
    # 注意分母用 BASE_H（设计稿基准高 820）而不是 DESIGN_H（= BASE_H × _S）：
    # DESIGN_SPEEDS 的单位是"设计稿像素/秒"，要换算到画布像素必须乘 _S，
    # 用 DESIGN_H 会把 _S 约掉，导致提高清晰度后障碍下落同比变慢。
    r = HEIGHT / BASE_H
    OBSTACLE_SPEED_BASE, OBSTACLE_SPEED_INC, OBSTACLE_SPEED_MAX = [
        v * r for v in DESIGN_SPEEDS]

GAZE_THRESHOLD = 5.0              # 连续不切换跑道多久触发凝视（秒）
GAZE_DURATION = 3.0               # 凝视持续时长（秒）

COFFEE_DURATION = 5.0             # 咖啡（加速）持续时长
SPICY_DURATION = 5.0              # 辣条（无敌）持续时长

# 配色（偏"高级质感"的暗色系 + 金色点缀）
COLOR_SKY_TOP = (20, 28, 60)
COLOR_SKY_BOT = (90, 72, 130)
COLOR_TEXT = (240, 242, 248)
COLOR_TEXT_DIM = (170, 178, 200)
COLOR_WARN = (255, 82, 82)
COLOR_GOLD = (255, 206, 70)
COLOR_PANEL = (22, 26, 46)

# 凝视时背景叠加的红色分量（用加法混合，不是半透明覆盖）。
# 只加 R 通道、略微加 B，避免变成纯粉；数值越大"被盯上"的压迫感越强。
GAZE_TINT_RGB = (36, 0, 8)


# ==========================================================================
# 二、工具函数
# ==========================================================================
def _find_asset_dir():
    """定位资源目录：优先脚本所在目录，兼容 Android 打包后的运行目录。"""
    candidates = [
        os.path.dirname(os.path.abspath(__file__)),
        os.getcwd(),
    ]
    try:
        candidates.append(os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        pass
    for c in candidates:
        if c and os.path.exists(os.path.join(c, "kk.jpg")):
            return c
    return candidates[0]


ASSET_DIR = _find_asset_dir()

_font_cache = {}


def get_font(size, bold=False):
    """获取支持中文的字体；优先使用打包进应用的中文字体文件。"""
    key = (size, bold)
    if key in _font_cache:
        return _font_cache[key]
    # 1) 优先加载打包进应用的中文字体（Android 系统通常不含中文字体，必须自带）
    for fname in ("font.ttf", "font.otf", "NotoSansSC-Regular.otf", "DroidSansFallback.ttf"):
        fp = os.path.join(ASSET_DIR, fname)
        if os.path.exists(fp):
            try:
                font = pygame.font.Font(fp, size)
                font.set_bold(bold)
                _font_cache[key] = font
                return font
            except Exception:
                pass
    # 2) 再尝试系统字体
    candidates = ["microsoftyahei", "microsoft yahei", "simhei", "simsun",
                  "msyh", "kaiti", "fangsong", "notosanscjksc"]
    # 先尝试粗体，再退回常规（保证中文正常显示）
    for b in (bold, False):
        for name in candidates:
            path = pygame.font.match_font(name, bold=b)
            if path:
                font = pygame.font.Font(path, size)
                _font_cache[key] = font
                return font
    font = pygame.font.Font(None, size)
    _font_cache[key] = font
    return font


def load_image(filename, size, fallback_color):
    """加载并缩放图片；失败时返回纯色矩形作为兜底，避免崩溃。"""
    path = os.path.join(ASSET_DIR, filename)
    try:
        image = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(image, size)
    except Exception:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        surf.fill(fallback_color)
        return surf


def make_circle_face(image, size):
    """把头像图片裁剪成圆形（带抗锯齿边缘），用于贴到人物脸部。"""
    img = pygame.transform.smoothscale(image, (size, size)).convert_alpha()
    mask = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
    img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return img


_text_cache = OrderedDict()
_TEXT_CACHE_MAX = 400


def _render_text(text, size, color, bold):
    """渲染文本并缓存 Surface。

    文字每帧都要重绘，font.render() 开销不低，所以按
    (文本, 字号, 颜色, 粗体) 缓存。

    用 LRU 淘汰而非"满了就整体清空"：得分/时间这类每帧都在变的文本会不断
    产生新条目，整体清空会让所有静态文案一起重新渲染，造成周期性的掉帧尖峰。
    """
    key = (text, size, color, bold)
    surf = _text_cache.get(key)
    if surf is not None:
        _text_cache.move_to_end(key)
        return surf
    surf = get_font(size, bold).render(text, True, color)
    _text_cache[key] = surf
    if len(_text_cache) > _TEXT_CACHE_MAX:
        _text_cache.popitem(last=False)      # 淘汰最久未使用的
    return surf


def draw_text(screen, text, size, color, pos, anchor="topleft", bold=False):
    """绘制中文文本，返回文本矩形，便于居中/对齐。"""
    img = _render_text(text, px(size), color, bold)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    screen.blit(img, rect)
    return rect


_glow_text_cache = OrderedDict()


def draw_glow_text(screen, text, size, color, glow_color, pos, anchor="center"):
    """绘制带辉光描边的文本（四周铺一圈 glow 再盖主文字），更有质感。

    描边本身要 9 次 blit。开始界面标题和凝视警告都是每帧在画，所以这里把
    "描边 + 主文字"预先合成到一张 Surface 再缓存：运行时只剩 1 次 blit。
    文案是有限的几条，缓存命中率接近 100%。
    """
    key = (text, size, color, glow_color)
    surf = _glow_text_cache.get(key)
    if surf is None:
        main = _render_text(text, px(size), color, True)
        glow = _render_text(text, px(size), glow_color, True)
        off = max(1, px(2))
        pad = off + 1
        surf = pygame.Surface(
            (main.get_width() + pad * 2, main.get_height() + pad * 2),
            pygame.SRCALPHA)
        for dx in (-off - 1, -off, off, off + 1):
            for dy in (-off - 1, -off, off, off + 1):
                surf.blit(glow, (pad + dx, pad + dy))
        surf.blit(main, (pad, pad))
        _glow_text_cache[key] = surf
        if len(_glow_text_cache) > 64:
            _glow_text_cache.popitem(last=False)      # 淘汰最久未使用的
    rect = surf.get_rect()
    setattr(rect, anchor, pos)
    screen.blit(surf, rect)
    return rect


_panel_cache = {}


def glass_panel(screen, rect, radius=18, alpha=205, border=(110, 150, 255, 90)):
    """绘制半透明玻璃质感圆角面板（按尺寸缓存，避免每帧新建 Surface）。"""
    key = (rect.w, rect.h, radius, alpha)
    panel = _panel_cache.get(key)
    if panel is None:
        if len(_panel_cache) > 32:
            _panel_cache.clear()
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (16, 20, 38, alpha), panel.get_rect(), border_radius=radius)
        pygame.draw.rect(panel, border, panel.get_rect(), 2, border_radius=radius)
        _panel_cache[key] = panel
    screen.blit(panel, rect.topleft)


def thick_line(screen, color, p1, p2, width):
    """绘制带圆头端点的粗线段（用于人物四肢）。"""
    p1 = (int(p1[0]), int(p1[1]))
    p2 = (int(p2[0]), int(p2[1]))
    pygame.draw.line(screen, color, p1, p2, int(width))
    r = int(width) // 2 + 1
    pygame.draw.circle(screen, color, p1, r)
    pygame.draw.circle(screen, color, p2, r)


_shadow_cache = {}


def get_ellipse_shadow(w, h, alpha=70):
    """按尺寸缓存椭圆阴影 Surface，避免每帧重复创建。"""
    key = (w, h, alpha)
    if key not in _shadow_cache:
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(s, (0, 0, 0, alpha), s.get_rect())
        _shadow_cache[key] = s
    return _shadow_cache[key]


def draw_humanoid(screen, face, cx, feet_y, body_color, accent, phase,
                  scale=1.0, airborne=0.0):
    """
    绘制一个"人形"跑动角色：
      - face   ：圆形头像，贴到头部（脸部）
      - cx, feet_y ：人物中心底部（脚底）坐标
      - phase  ：跑步动画相位（随时间累加，驱动四肢摆动）
      - airborne：离地高度（跳跃时使用）
    腿部与手臂按正弦摆动，形成跑步/追逐动效。
    """
    scale = scale * _S                    # 换算到当前渲染分辨率
    y = feet_y - airborne
    H = 150 * scale                       # 身高
    head_d = face.get_size()[0] if face is not None else int(38 * scale)
    head_r = head_d / 2.0                 # 头半径（以头像实际尺寸为准）
    bob = 0.0 if airborne > 0 else math.sin(phase * 2) * 2.5 * scale  # 跑步起伏
    top = y - H

    # 头
    head_cx = cx
    head_cy = top + head_r + bob
    # 脖子/肩/髋
    neck_y = head_cy + head_r - 2 * scale
    shoulder_y = neck_y + 5 * scale
    hip_y = y - 56 * scale
    torso_w = 30 * scale

    # ---- 腿（画在躯干之前，位于后方）----
    leg_len = 58 * scale
    for side in (-1, 1):
        hip_x = cx + side * 8 * scale
        if airborne > 0:
            ang = side * 0.9                      # 跳跃：双腿收起
        else:
            ang = math.sin(phase + (0.0 if side < 0 else math.pi)) * 0.85
        foot = (hip_x + math.sin(ang) * leg_len * 0.6, hip_y + math.cos(ang) * leg_len)
        thick_line(screen, body_color, (hip_x, hip_y), foot, int(9 * scale))

    # ---- 躯干（圆角，双色营造立体感）----
    torso = pygame.Rect(0, 0, int(torso_w), int(hip_y - shoulder_y))
    torso.centerx = int(cx)
    torso.top = int(shoulder_y)
    pygame.draw.rect(screen, body_color, torso, border_radius=int(10 * scale))
    stripe = pygame.Rect(0, 0, int(torso_w * 0.5), int(hip_y - shoulder_y))
    stripe.centerx = int(cx)
    stripe.top = int(shoulder_y)
    pygame.draw.rect(screen, accent, stripe, border_radius=int(8 * scale))

    # ---- 手臂（与腿反向摆动）----
    arm_len = 33 * scale
    for side in (-1, 1):
        sh_x = cx + side * (torso_w / 2 - 2 * scale)
        sh_y = shoulder_y + 4 * scale
        if airborne > 0:
            ang = -side * 0.8                      # 跳跃：双臂上摆
        else:
            ang = math.sin(phase + (math.pi if side < 0 else 0.0)) * 0.9
        hand = (sh_x + math.sin(ang) * arm_len, sh_y + math.cos(ang) * arm_len)
        thick_line(screen, accent, (sh_x, sh_y), hand, int(7 * scale))

    # ---- 头部（先铺一层底色，再贴圆形头像，最后描边）----
    head_rect = pygame.Rect(0, 0, int(head_d), int(head_d))
    head_rect.center = (int(head_cx), int(head_cy))
    pygame.draw.circle(screen, body_color, head_rect.center, int(head_r * 1.08))
    if face is not None:
        screen.blit(face, head_rect)
    pygame.draw.circle(screen, accent, head_rect.center, int(head_r * 1.08), max(1, int(2 * scale)))

    # ---- 脚下阴影 ----
    sw = int(46 * scale)
    screen.blit(get_ellipse_shadow(sw, int(9 * scale)), (int(cx - sw / 2), int(y - 3 * scale)))


# ==========================================================================
# 三、粒子系统（用于道具拾取、凝视、气氛点缀，增强质感）
# ==========================================================================
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size, gravity=0.0):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.gravity = gravity

    @property
    def alive(self):
        return self.life > 0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt
        self.life -= dt

    def draw(self, screen):
        # 直接画圆并按剩余寿命缩小半径，避免每帧创建新 Surface
        k = max(0.0, self.life / self.max_life)
        r = max(1, int(self.size * k))
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), r)


# ==========================================================================
# 四、音频管理（加载工作区音效，缺失时静默降级）
# ==========================================================================
class Audio:
    """音频管理：主线程同步初始化与播放，所有调用均做异常保护，缺失时静默降级。"""

    def __init__(self):
        self.enabled = False
        self.pickup = None
        # Android 上 SDL_mixer 常以 ogg/wav 优先，mp3 兜底
        self.bgm_path = self._find("bgm.ogg", "bgm.wav", "bgm.mp3")
        self.over_path = self._find("music.ogg", "music.wav", "music.mp3")
        pickup_path = self._find("get.ogg", "get.wav", "get.mp3")
        try:
            # 显式指定较小缓冲区，降低延迟与阻塞风险
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            if pickup_path:
                self.pickup = pygame.mixer.Sound(pickup_path)
            self.enabled = True
        except Exception:
            self.enabled = False

    @staticmethod
    def _find(*names):
        for n in names:
            p = os.path.join(ASSET_DIR, n)
            if os.path.exists(p):
                return p
        return None

    def start_bgm(self):
        """游戏进行中循环播放背景音乐。"""
        if not self.enabled or not self.bgm_path:
            return
        try:
            pygame.mixer.music.load(self.bgm_path)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def play_pickup(self):
        """拾取辣条/咖啡等道具时播放音效（即时，无队列延迟）。"""
        if not self.enabled or self.pickup is None:
            return
        try:
            self.pickup.play()
        except Exception:
            pass

    def play_game_over(self):
        """游戏结束时停止 BGM，播放结束音乐。"""
        if not self.enabled or not self.over_path:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(self.over_path)
            pygame.mixer.music.play()
        except Exception:
            pass


# ==========================================================================
# 五、玩家类：同学坤坤（人形，带逃跑跑动动效）
# ==========================================================================
class Player:
    def __init__(self):
        self.lane = 1
        self.x = LANE_CENTERS[self.lane]
        self.y = PLAYER_Y                       # 脚底线
        self.scale = 1.05
        self.head_r = px(20 * self.scale)
        self.face = make_circle_face(
            load_image("kk.jpg", (px(96), px(96)), (120, 180, 255)), self.head_r * 2)
        self.body_color = (46, 116, 226)        # 校服蓝
        self.accent = (255, 200, 70)            # 金色点缀
        self.glow = pygame.Surface((px(120), px(180)), pygame.SRCALPHA)  # 无敌光晕（预渲染）
        pygame.draw.ellipse(self.glow, (255, 206, 70, 120), self.glow.get_rect())

        self.phase = 0.0                        # 跑步动画相位
        self.jumping = False
        self.jump_t = 0.0
        self.jump_offset = 0.0

        self.invincible_timer = 0.0
        self.coffee_timer = 0.0

    @property
    def invincible(self):
        return self.invincible_timer > 0

    @property
    def speed_boost(self):
        return self.coffee_timer > 0

    def move(self, direction):
        new_lane = self.lane + direction
        if 0 <= new_lane < LANE_COUNT:
            self.lane = new_lane
            self.x = LANE_CENTERS[new_lane]

    def jump(self):
        if not self.jumping:
            self.jumping = True
            self.jump_t = 0.0

    def update(self, dt):
        # 跑步相位推进（跳跃时放慢，营造腾空感）
        self.phase += dt * (7.0 if self.jumping else 13.0)

        if self.jumping:
            self.jump_t += dt
            if self.jump_t >= JUMP_DURATION:
                self.jumping = False
                self.jump_offset = 0.0
            else:
                self.jump_offset = JUMP_HEIGHT * math.sin(math.pi * self.jump_t / JUMP_DURATION)

        self.invincible_timer = max(0.0, self.invincible_timer - dt)
        self.coffee_timer = max(0.0, self.coffee_timer - dt)

    def draw(self, screen):
        # 无敌时在身后画金色光晕
        if self.invincible:
            screen.blit(self.glow, (int(self.x - px(60)), int(self.y - px(160))))
        draw_humanoid(screen, self.face, self.x, self.y,
                      self.body_color, self.accent, self.phase,
                      self.scale, airborne=self.jump_offset)


# ==========================================================================
# 六、追逐者类：班主任 shall we / 校长花招（人形，带追逐跑动动效）
# ==========================================================================
class Chaser:
    def __init__(self, filename, name, x_offset, body_color, accent, fallback, scale=1.15):
        self.name = name
        self.x_offset = px(x_offset)
        self.x = PLAY_W / 2 + self.x_offset
        self.scale = scale
        self.head_r = px(20 * scale)
        self.face = make_circle_face(
            load_image(filename, (px(96), px(96)), fallback), self.head_r * 2)
        self.body_color = body_color
        self.accent = accent

        self.phase = 0.0
        # 脚底线贴近画布底部，只露出上半身；名字挂在脚下，
        # 放到头顶会和玩家角色叠在一起（追击者就贴在玩家两侧）
        self.base_feet_y = HEIGHT - px(44)
        self.feet_y = self.base_feet_y
        self.rise = 0.0                         # 凝视时逼近玩家的距离
        self.target_rise = 0.0
        self.run_speed = 11.0

    def set_gaze(self, active):
        """凝视时追逐者加速逼近，否则退回。"""
        self.target_rise = float(px(120)) if active else 0.0
        self.run_speed = 18.0 if active else 11.0

    def update(self, dt, target_x):
        # 平滑跟随玩家所在跑道（左右跑动，不锁定在屏幕下方）
        self.x += (target_x + self.x_offset - self.x) * min(1.0, dt * 6)
        self.phase += dt * self.run_speed
        self.rise += (self.target_rise - self.rise) * min(1.0, dt * 6)
        self.feet_y = self.base_feet_y - self.rise

    def draw(self, screen, shake=0):
        amp = px(shake) if shake else 0
        sx = self.x + (random.randint(-amp, amp) if amp else 0)
        draw_humanoid(screen, self.face, sx, self.feet_y,
                      self.body_color, self.accent, self.phase, self.scale)
        # 名字挂在脚下而不是头顶：追击者与玩家挨得很近，放头顶会被玩家挡住
        draw_text(screen, self.name, 15, (255, 130, 130),
                  (int(sx), int(self.feet_y + px(5))), anchor="midtop")


_shadow_cache2 = {}


def _get_obstacle_shadow(w, h):
    """按尺寸缓存障碍物投影，避免每次生成障碍都新建 Surface。"""
    key = (w, h)
    s = _shadow_cache2.get(key)
    if s is None:
        if len(_shadow_cache2) > 64:
            _shadow_cache2.clear()
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (0, 0, 0, 90), s.get_rect(), border_radius=px(12))
        _shadow_cache2[key] = s
    return s


_glow_cache = {}


def _get_glow(color, r):
    """按颜色与半径缓存道具光晕。半径取值有限，缓存命中率很高。"""
    key = (color, r)
    s = _glow_cache.get(key)
    if s is None:
        if len(_glow_cache) > 200:
            _glow_cache.clear()
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*color, 110), (r, r), r)
        _glow_cache[key] = s
    return s


# ==========================================================================
# 七、障碍物类：课桌 / 黑板擦 / 试卷
# ==========================================================================
class Obstacle:
    SPEC = {
        "desk":   {"name": "坤桌",   "color": (150, 96, 44),   "h": 130, "jumpable": False},
        "eraser": {"name": "黑板擦", "color": (84, 116, 220),  "h": 55,  "jumpable": True},
        "paper":  {"name": "试卷",   "color": (245, 245, 245), "h": 45,  "jumpable": True},
    }

    def __init__(self, lane, kind):
        self.lane = lane
        self.kind = kind
        info = self.SPEC[kind]
        self.name = info["name"]
        self.color = info["color"]
        self.h = px(info["h"])
        self.jumpable = info["jumpable"]
        self.w = px(OBSTACLE_W)
        self.x = LANE_CENTERS[lane]
        self.y = -float(self.h)
        self.evaluated = False
        self.shadow = _get_obstacle_shadow(self.w, self.h)   # 按尺寸复用的投影

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.w / 2), int(self.y), self.w, self.h)

    def update(self, dy):
        self.y += dy

    def draw(self, screen):
        rect = self.rect
        o4, o8 = px(4), px(8)
        # 投影
        screen.blit(self.shadow, (rect.x + o4, rect.y + px(5)))
        # 主体（圆角 + 高光渐变）
        pygame.draw.rect(screen, self.color, rect, border_radius=px(12))
        light = (min(self.color[0] + 30, 255), min(self.color[1] + 30, 255), min(self.color[2] + 30, 255))
        top = pygame.Rect(rect.x + o4, rect.y + o4, rect.w - o8, rect.h // 3)
        pygame.draw.rect(screen, light, top, border_radius=px(8))
        pygame.draw.rect(screen, (25, 25, 25), rect, max(1, px(3)), border_radius=px(12))
        text_color = (30, 30, 30) if self.kind == "paper" else (255, 255, 255)
        draw_text(screen, self.name, 24, text_color, rect.center, anchor="center", bold=True)


# ==========================================================================
# 八、道具类：咖啡 / 辣条
# ==========================================================================
class PowerUp:
    SPEC = {
        "coffee": {"name": "咖啡", "color": (150, 96, 40),  "text_color": (255, 235, 200)},
        "spicy":  {"name": "辣条", "color": (205, 44, 44),  "text_color": (255, 255, 255)},
    }

    def __init__(self, lane, kind):
        self.lane = lane
        self.kind = kind
        info = self.SPEC[kind]
        self.name = info["name"]
        self.color = info["color"]
        self.text_color = info["text_color"]
        self.size = px(POWERUP_SIZE)
        self.x = LANE_CENTERS[lane]
        self.y = -float(self.size)
        self.evaluated = False

    @property
    def rect(self):
        return pygame.Rect(int(self.x - self.size / 2), int(self.y), self.size, self.size)

    def update(self, dy):
        self.y += dy

    def draw(self, screen, pulse):
        """绘制道具：脉冲光晕 + 圆形主体 + 名称。"""
        rect = self.rect
        glow_r = int(self.size / 2 + px(6) + pulse * px(4))
        glow = _get_glow(self.color, glow_r)
        screen.blit(glow, (rect.centerx - glow_r, rect.centery - glow_r))
        pygame.draw.circle(screen, self.color, rect.center, self.size // 2)
        pygame.draw.circle(screen, (255, 255, 255), rect.center, self.size // 2, max(1, px(3)))
        draw_text(screen, self.name, 19, self.text_color, rect.center, anchor="center", bold=True)


def _is_android():
    """是否运行在 Android（python-for-android 打包环境）上。"""
    return hasattr(sys, "getandroidapilevel") or "ANDROID_ARGUMENT" in os.environ


def _screen_fit_enabled():
    """是否启用手机屏幕自适应。

    真机上启用；桌面端保持设计稿尺寸（桌面窗口若被拉高，在低分屏上会溢出）。
    想在电脑上预览手机效果，可设环境变量 KK_FORCE_FIT=1。
    """
    if os.environ.get("KK_FORCE_FIT"):
        return True
    return _is_android()


def _query_screen_size():
    """读取设备真实屏幕像素尺寸；探测失败返回 (0, 0)。

    Android 上必须拿到真实屏幕分辨率，才能算出与屏幕同比例的逻辑画布
    高度，进而做到零黑边。这里按可靠性从高到低依次尝试：

    1. SDL_GetDesktopDisplayMode（get_desktop_sizes）：返回屏幕物理分辨率，
       Android 上最可靠。
    2. get_desktop_size：老版本 pygame 的同义接口。
    3. 真开一个全屏窗口去量尺寸——会创建一个临时窗口，只在前面都失败时用。
    """
    if not pygame.display.get_init():
        try:
            pygame.display.init()
        except Exception:
            pass

    try:
        getter = getattr(pygame.display, "get_desktop_sizes", None)
        if getter is not None:
            sizes = getter()
            if sizes:
                w, h = sizes[0][0], sizes[0][1]
                if w > 0 and h > 0:
                    return w, h
    except Exception:
        pass

    try:
        w, h = pygame.display.get_desktop_size()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass

    try:
        probe = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = probe.get_size()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass

    return 0, 0


# ==========================================================================
# 八点五、按钮控件（开始 / 重新开始 / 退出等菜单操作）
# ==========================================================================
class Button:
    """圆角按钮：鼠标与触摸通用，带呼吸高亮和按下反馈。

    面板与光晕都预渲染，每帧只做 blit，避免重复创建 Surface 拖慢帧率。
    """

    def __init__(self, label, cx, cy, tone="gold", w=None, h=None):
        self.label = label
        self.tone = tone                      # gold=主行动，ghost=次行动
        self.rect = pygame.Rect(0, 0, w or px(300), h or px(76))
        self.rect.center = (cx, cy)
        self.pressed = False
        self._panel = None
        self._panel_hot = None
        self._shade = None
        self._glow = None
        self._glow_r = 0

    def place(self, cx, cy):
        """重新摆放按钮中心点。"""
        self.rect.center = (cx, cy)

    def hit(self, pos):
        return self.rect.collidepoint(pos)

    def _build_panel(self, hot=False):
        r = self.rect
        radius = min(r.w, r.h) // 2
        surf = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        if self.tone == "gold":
            base = (255, 216, 96, 248) if hot else (255, 206, 70, 238)
            pygame.draw.rect(surf, base, surf.get_rect(), border_radius=radius)
            pygame.draw.rect(surf, (255, 255, 255, 150), surf.get_rect(),
                             max(1, px(2)), border_radius=radius)
        else:
            base = (48, 56, 92, 235) if hot else (32, 38, 66, 225)
            pygame.draw.rect(surf, base, surf.get_rect(), border_radius=radius)
            pygame.draw.rect(surf, (255, 206, 70, 215), surf.get_rect(),
                             max(1, px(2)), border_radius=radius)
        return surf

    def _build_shade(self):
        """按下态的压暗遮罩，预渲染一次即可。"""
        r = self.rect
        surf = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (0, 0, 0, 80), surf.get_rect(),
                         border_radius=min(r.w, r.h) // 2)
        return surf

    def _build_glow(self):
        """径向渐变光晕，只渲染一次；每帧用 set_alpha 控制强弱。"""
        gr = int(max(self.rect.w, self.rect.h) * 0.72)
        surf = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            rr = int(gr * i / 6)
            a = int(16 * (6 - i + 1) / 6)
            pygame.draw.circle(surf, (255, 206, 70, a), (gr, gr), rr)
        return surf, gr

    def draw(self, screen, pulse=0.0, hover=False):
        if self._panel is None:
            self._panel = self._build_panel()
        if hover and self._panel_hot is None:
            self._panel_hot = self._build_panel(hot=True)
        if self._glow is None:
            self._glow, self._glow_r = self._build_glow()
        r = self.rect
        if pulse > 0:
            self._glow.set_alpha(int(70 + 110 * pulse))
            screen.blit(self._glow, (r.centerx - self._glow_r, r.centery - self._glow_r))
        screen.blit(self._panel_hot if hover else self._panel, r.topleft)
        if self.pressed:
            if self._shade is None:
                self._shade = self._build_shade()
            screen.blit(self._shade, r.topleft)
        color = (28, 24, 12) if self.tone == "gold" else COLOR_GOLD
        draw_text(screen, self.label, 28, color, r.center, anchor="center", bold=True)


# ==========================================================================
# 九、游戏主控制器
# ==========================================================================
class Game:
    def __init__(self):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.running = True
        self.touch_start = None          # 触摸起点 (x, y, 时间戳)
        self.hover_pos = None            # 电脑端鼠标位置（按钮悬停高亮用）

        # --- 决定画布分辨率并建立窗口 ---
        self._setup_canvas()
        pygame.display.set_caption("坤坤大逃亡 - 校园大逃亡")

        # 加载界面背景要在动画开始前就绪，所以单独提前加载
        self.loading_bg = self._load_loading_bg()
        self.loading_dim = self._make_overlay((6, 10, 28, 120))

        # --- 分批加载资源，同时播放加载动画 ---
        self._load_with_animation()

        # --- 菜单按钮（纵坐标按画布高度比例定位，适配各种屏幕比例）---
        cx = WIDTH // 2
        self.btn_start = Button("开始游戏", cx, vh(0.53))
        self.btn_retry = Button("再玩一次", cx, vh(0.58))
        self.btn_quit = Button("退出游戏", cx, vh(0.70), tone="ghost")

        # 预渲染半透明遮罩：每帧新建整屏 Surface 会明显拖慢帧率。
        # （凝视红罩不在这里——它被烘进了背景图，见 _make_gaze_variant）
        self.overlay_start = self._make_overlay((6, 8, 22, 150))
        self.overlay_over = self._make_overlay((30, 4, 6, 185))

        self.reset_game()
        self.state = "start"

    # ------------------------------------------------------------------
    # 屏幕与分辨率
    # ------------------------------------------------------------------
    def _setup_canvas(self):
        """按屏幕比例确定逻辑画布高度并建立窗口。

        画布宽高比刻意做成与屏幕完全一致，这样 SCALED 缩放后正好铺满，
        不会留下黑边；宽度固定 720 是为了把软件渲染的像素量控制在可流畅
        运行的范围内。
        """
        canvas_h = DESIGN_H
        matched = False
        if _screen_fit_enabled():
            screen_w, screen_h = _query_screen_size()
            # 部分安卓设备会把屏幕报告成横屏(如 2400x1080)，而本游戏锁定竖屏，
            # 统一按"短边为宽、长边为高"归一，避免算出错误比例。
            if screen_w > screen_h:
                screen_w, screen_h = screen_h, screen_w
            if screen_w > 0 and screen_h > 0:
                canvas_h = int(round(DESIGN_W * screen_h / screen_w))
                matched = True
        _apply_render_scale(canvas_h)

        # 缩放模式：画布比例与屏幕一致时用 overscan 直接铺满，零黑边；
        # 尺寸探测失败时画布是设计稿比例、与屏幕对不上，此时改用 letterbox
        # 留黑边，总好过把画面硬拉变形。必须在创建窗口之前设好。
        os.environ["SDL_RENDER_LOGICAL_SIZE_MODE"] = (
            "overscan" if matched else "letterbox")

        # SCALED：把 720 宽的逻辑画布交给 SDL 缩放铺满屏幕（有 GPU 时走硬件，
        # 比"直接在屏幕物理分辨率上软件渲染"快好几倍）。
        # FULLSCREEN 隐藏状态栏。
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT),
                                                  pygame.SCALED | pygame.FULLSCREEN)
        except Exception:
            try:
                self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED)
            except Exception:
                self.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    def _make_overlay(self, rgba, size=None):
        """生成一块半透明遮罩并缓存复用。"""
        w, h = size or (WIDTH, HEIGHT)
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        s.fill(rgba)
        return s

    def _load_loading_bg(self):
        """加载启动界面背景图。

        源图是 720x1280（9:16），而手机多在 20:9 上下，画布会更高一些。
        不能按"铺满裁切"处理——那样标题会被裁掉；也不能直接填色块——
        源图底部是亮色铁轨，填出来的色带和原图对不上，会留一道明显的分界。
        这里改成把图片底部一小段纵向拉伸补齐：源图底部本来就是铁轨，
        拉长后近似运动模糊，看上去像隧道继续向远处延伸。

        背景图自带标题，所以加载界面不需要再画一遍标题。
        图片缺失或损坏时回退为深色底，游戏照常启动。
        """
        try:
            img = pygame.image.load(os.path.join(ASSET_DIR, "loading_bg.png")).convert()
            src_w, src_h = img.get_size()
            new_h = max(1, int(round(src_h * WIDTH / src_w)))
            scaled = pygame.transform.smoothscale(img, (WIDTH, new_h))
            surface = pygame.Surface((WIDTH, HEIGHT))
            if new_h >= HEIGHT:
                surface.blit(scaled, (0, 0))          # 画布更矮：保留顶部标题
            else:
                tail_h = min(px(72), new_h)
                tail = scaled.subsurface(
                    pygame.Rect(0, new_h - tail_h, WIDTH, tail_h)).copy()
                surface.blit(scaled, (0, 0))
                surface.blit(
                    pygame.transform.smoothscale(
                        tail, (WIDTH, HEIGHT - new_h + tail_h)),
                    (0, new_h - tail_h))
            self.loading_bg_ok = True
            return surface
        except Exception:
            self.loading_bg_ok = False
            fallback = pygame.Surface((WIDTH, HEIGHT))
            fallback.fill((10, 13, 26))
            return fallback

    # ------------------------------------------------------------------
    # 加载动画
    # ------------------------------------------------------------------
    def _draw_loading(self, progress, label):
        """绘制加载界面：背景图 + 进度条 + 当前步骤。"""
        pygame.event.pump()                       # 保持窗口响应，避免被系统判定卡死
        t = pygame.time.get_ticks() / 1000.0
        cx = WIDTH // 2
        progress = max(0.0, min(1.0, progress))

        self.screen.blit(self.loading_bg, (0, 0))
        self.screen.blit(self.loading_dim, (0, 0))   # 压暗背景，保证文字可读

        if not self.loading_bg_ok:
            draw_glow_text(self.screen, "坤坤大逃亡", 52, COLOR_GOLD, (255, 120, 40),
                           (cx, vh(0.34)), anchor="center")

        # 进度条固定在画面下方，避开背景图里的标题与人物
        bar_h = px(16)
        bar_w = int(WIDTH * 0.78)
        bar = pygame.Rect(cx - bar_w // 2, vh(0.80), bar_w, bar_h)
        pygame.draw.rect(self.screen, (26, 30, 54), bar, border_radius=bar_h // 2)
        fill = pygame.Rect(bar.x, bar.y, int(bar.w * progress), bar.h)
        if fill.w > 0:
            pygame.draw.rect(self.screen, COLOR_GOLD, fill, border_radius=bar_h // 2)
        pygame.draw.rect(self.screen, (150, 170, 230), bar, max(1, px(2)),
                         border_radius=bar_h // 2)

        draw_text(self.screen, label, 22, COLOR_TEXT, (cx, bar.y - px(40)),
                  anchor="center", bold=True)
        draw_text(self.screen, f"{int(progress * 100)}%", 18, COLOR_TEXT_DIM,
                  (cx, bar.bottom + px(26)), anchor="center")

        # 跑动的小人：让"正在加载"有动感，而不是一张静止的图
        draw_humanoid(self.screen, None, WIDTH - px(100), vh(0.70),
                      (46, 116, 226), (255, 200, 70), t * 13, 0.75)

        pygame.display.flip()
        self.clock.tick(30)

    def _load_with_animation(self):
        """分批加载资源：每批之间推进进度条动画，避免开场白屏或卡顿。"""
        steps = [
            ("初始化音频", self._step_audio),
            ("加载角色", self._step_player),
            ("加载班主任与校长", self._step_chasers),
            ("生成跑道", self._step_world),
        ]
        total = len(steps)
        shown = 0.0
        for i, (label, fn) in enumerate(steps):
            # 先把进度条平滑推到这一步的起始位置，让动画真的动起来
            target = i / total
            while shown < target - 0.001:
                shown = min(target, shown + 0.10)
                self._draw_loading(shown, label)
            fn()
            shown = (i + 1) / total
            self._draw_loading(shown, label)

    def _step_audio(self):
        self.audio = Audio()

    def _step_player(self):
        self.player = Player()

    def _step_chasers(self):
        self.chasers = [
            Chaser("shallwe.jpg", "班主任 shall we", -58, (196, 74, 74), (40, 30, 30), (200, 80, 80)),
            Chaser("huazhao.jpg", "校长 花招", 58, (60, 68, 120), (30, 34, 60), (80, 80, 200)),
        ]

    def _step_world(self):
        self.particles = []
        self.bg_decor = self._make_bg_decor()
        self.bg_scroll = 0.0
        self.best_score = 0.0
        # 预渲染静态内容，之后每帧只做 blit
        self.bg_surface = self._build_background()
        self.bg_gaze = self._make_gaze_variant(self.bg_surface)
        self.hud_backdrop = self._build_hud_backdrop()
        (self.road_marks, self.road_gap,
         self.road_mark_w) = self._build_road_marks()

    def _make_bg_decor(self):
        """生成背景中的漂浮光点（预渲染成 Surface，避免每帧重复创建）。"""
        decor = []
        for _ in range(10):
            size = int(random.uniform(12, 40) * _S)
            alpha = random.randint(14, 40)
            s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (255, 255, 255, alpha), (size, size), size)
            decor.append({
                "x": random.uniform(0, PLAY_W),
                "y": random.uniform(0, HEIGHT),
                "size": size,
                "surf": s,
            })
        return decor

    def reset_game(self):
        self.state = "playing"
        self.obstacles = []
        self.powerups = []
        self.particles = []
        self.speed = OBSTACLE_SPEED_BASE
        self.spawn_timer = 1.2
        self.elapsed = 0.0
        self.score = 0.0
        self.time_since_lane_change = 0.0
        self.gaze = False
        self.gaze_timer = 0.0
        self.player = Player()
        for chaser in self.chasers:
            chaser.rise = 0.0
            chaser.target_rise = 0.0
            chaser.phase = 0.0
            chaser.x = PLAY_W / 2 + chaser.x_offset
        self.audio.start_bgm()

    def spawn(self):
        lane = random.randrange(LANE_COUNT)
        if random.random() < 0.18:
            kind = random.choice(("coffee", "spicy"))
            self.powerups.append(PowerUp(lane, kind))
        else:
            kind = random.choice(("desk", "eraser", "paper"))
            self.obstacles.append(Obstacle(lane, kind))

    def spawn_burst(self, x, y, color, n=14):
        for _ in range(n):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(60, 190) * _S
            self.particles.append(Particle(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd - px(40),
                random.uniform(0.4, 0.9), color,
                random.randint(max(1, px(2)), max(1, px(5))), gravity=px(220)))

    def trigger_game_over(self):
        self.state = "gameover"
        self.best_score = max(self.best_score, self.score)
        self.audio.play_game_over()
        for chaser in self.chasers:
            chaser.set_gaze(False)

    # ------------------------------------------------------------------
    # 事件处理
    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            # ---- 触摸支持（Android 上单点触摸会映射为鼠标事件）----
            if event.type == pygame.MOUSEMOTION:
                self.hover_pos = event.pos
                continue
            if event.type == pygame.MOUSEBUTTONDOWN:
                self.touch_start = (event.pos[0], event.pos[1], pygame.time.get_ticks())
                self._set_buttons_pressed(event.pos, True)
                continue
            if event.type == pygame.MOUSEBUTTONUP:
                self._set_buttons_pressed(event.pos, False)
                if self.touch_start is not None:
                    x0, y0, _t0 = self.touch_start
                    if not self._handle_menu_click(event.pos):
                        self._handle_touch(x0, y0, event.pos[0] - x0, event.pos[1] - y0)
                    self.touch_start = None
                continue
            if event.type == pygame.FINGERDOWN:
                pos = (int(event.x * WIDTH), int(event.y * HEIGHT))
                self.touch_start = (pos[0], pos[1], pygame.time.get_ticks())
                self._set_buttons_pressed(pos, True)
                continue
            if event.type == pygame.FINGERUP:
                pos = (int(event.x * WIDTH), int(event.y * HEIGHT))
                self._set_buttons_pressed(pos, False)
                if self.touch_start is not None:
                    x0, y0, _t0 = self.touch_start
                    if not self._handle_menu_click(pos):
                        self._handle_touch(x0, y0, pos[0] - x0, pos[1] - y0)
                    self.touch_start = None
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                if self.state == "start":
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.reset_game()
                    return
                if self.state == "gameover":
                    if event.key == pygame.K_r:
                        self.reset_game()
                    return
                if self.state == "playing":
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        self.player.move(-1)
                        self.time_since_lane_change = 0.0
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.player.move(1)
                        self.time_since_lane_change = 0.0
                    elif event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                        self.player.jump()

    def _hovering(self, button):
        """电脑端鼠标是否悬停在按钮上（触摸设备没有悬停概念）。"""
        return self.hover_pos is not None and button.hit(self.hover_pos)

    def _set_buttons_pressed(self, pos, down):
        """按下/抬起时切换按钮的按压态，给用户即时的视觉反馈。"""
        if self.state == "start":
            self.btn_start.pressed = down and self.btn_start.hit(pos)
        elif self.state == "gameover":
            self.btn_retry.pressed = down and self.btn_retry.hit(pos)
            self.btn_quit.pressed = down and self.btn_quit.hit(pos)

    def _handle_menu_click(self, pos):
        """处理菜单按钮点击；已消费掉这次点击则返回 True。"""
        if self.state == "start":
            # 按钮是主要入口；点其他位置也一并开始，避免手指没点准就没反应
            self.reset_game()
            return True
        if self.state == "gameover":
            if self.btn_quit.hit(pos):
                self.running = False
            else:
                self.reset_game()      # 「再玩一次」按钮或空白处都重开
            return True
        return False

    def _handle_touch(self, x0, y0, dx, dy):
        """把一次触摸（轻点/滑动）转换成游戏动作。"""
        if self.state != "playing":
            return

        SWIPE = px(60)        # 判定为滑动的最小像素
        if abs(dx) < SWIPE and abs(dy) < SWIPE:
            # 轻点：左 1/3 左移，右 1/3 右移，中间跳跃
            if x0 < PLAY_W / 3:
                self.player.move(-1)
                self.time_since_lane_change = 0.0
            elif x0 > PLAY_W * 2 / 3:
                self.player.move(1)
                self.time_since_lane_change = 0.0
            else:
                self.player.jump()
        else:
            # 滑动：水平主导切跑道，向上主导跳跃
            if abs(dx) > abs(dy):
                self.player.move(1 if dx > 0 else -1)
                self.time_since_lane_change = 0.0
            elif dy < 0:
                self.player.jump()

    # ------------------------------------------------------------------
    # 逻辑更新
    # ------------------------------------------------------------------
    def update(self, dt):
        if self.state != "playing":
            return

        self.elapsed += dt
        self.speed = min(OBSTACLE_SPEED_MAX,
                         OBSTACLE_SPEED_BASE + self.elapsed * OBSTACLE_SPEED_INC)
        self.bg_scroll += self.speed * dt

        # ---- 班主任的凝视机制 ----
        self.time_since_lane_change += dt
        if not self.gaze and self.time_since_lane_change >= GAZE_THRESHOLD:
            self.gaze = True
            self.gaze_timer = GAZE_DURATION
            self.time_since_lane_change = 0.0
            self.spawn_burst(self.player.x, self.player.y - 80, (255, 82, 82), 18)
        if self.gaze:
            self.gaze_timer -= dt
            if self.gaze_timer <= 0.0:
                self.gaze = False
                self.time_since_lane_change = 0.0
        for chaser in self.chasers:
            chaser.set_gaze(self.gaze)

        # ---- 计分 ----
        multiplier = 2.0 if self.player.speed_boost else 1.0
        self.score += self.speed * dt * 0.02 * multiplier

        self.player.update(dt)
        dy = self.speed * dt

        # ---- 生成障碍 ----
        self.spawn_timer -= dt
        if self.spawn_timer <= 0.0:
            self.spawn()
            self.spawn_timer = max(SPAWN_INTERVAL_MIN,
                                   SPAWN_INTERVAL_BASE - self.elapsed * 0.02)

        # ---- 碰撞判定 ----
        for obs in self.obstacles:
            obs.update(dy)
            if not obs.evaluated and obs.y >= PLAYER_Y:
                obs.evaluated = True
                if obs.lane == self.player.lane:
                    if self.player.invincible:
                        continue
                    if self.player.jumping and obs.jumpable:
                        continue
                    self.trigger_game_over()
                    return
        self.obstacles = [o for o in self.obstacles if o.y < HEIGHT + 120]

        # ---- 道具拾取 ----
        for p in self.powerups:
            p.update(dy)
            if not p.evaluated and p.y >= PLAYER_Y:
                p.evaluated = True
                if p.lane == self.player.lane:
                    if p.kind == "coffee":
                        self.player.coffee_timer = COFFEE_DURATION
                        self.spawn_burst(p.x, p.y, (255, 206, 70), 16)
                    else:
                        self.player.invincible_timer = SPICY_DURATION
                        self.spawn_burst(p.x, p.y, (255, 255, 255), 16)
                    self.audio.play_pickup()          # 拾取时播放 get.mp3
        self.powerups = [p for p in self.powerups if p.y < HEIGHT + 120]

        # ---- 追逐者跟随玩家 ----
        for chaser in self.chasers:
            chaser.update(dt, self.player.x)

        # ---- 玩家奔跑扬尘粒子 ----
        if random.random() < dt * 10:
            self.particles.append(Particle(
                self.player.x + random.uniform(-14, 14) * _S, self.player.y - px(2),
                random.uniform(-20, 20) * _S, random.uniform(-30, -10) * _S,
                0.4, (200, 200, 210), random.randint(max(1, px(1)), max(1, px(3)))))

    def update_particles(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.alive]
        # 开始界面漂浮粒子
        if self.state == "start" and random.random() < dt * 16:
            self.particles.append(Particle(
                random.uniform(0, PLAY_W), HEIGHT + px(10),
                random.uniform(-8, 8) * _S, random.uniform(-50, -20) * _S,
                random.uniform(1.5, 3.0), (180, 200, 255),
                random.randint(max(1, px(1)), max(1, px(3)))))

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------
    def _build_background(self):
        """预渲染静态背景（渐变 + 跑道分隔线），之后每帧只做一次 blit。"""
        bg = pygame.Surface((PLAY_W, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = (
                int(COLOR_SKY_TOP[0] + (COLOR_SKY_BOT[0] - COLOR_SKY_TOP[0]) * t),
                int(COLOR_SKY_TOP[1] + (COLOR_SKY_BOT[1] - COLOR_SKY_TOP[1]) * t),
                int(COLOR_SKY_TOP[2] + (COLOR_SKY_BOT[2] - COLOR_SKY_TOP[2]) * t),
            )
            pygame.draw.line(bg, color, (0, y), (PLAY_W, y))

        for i in range(LANE_COUNT):
            if i % 2 == 1:
                shade = pygame.Surface((int(LANE_W), HEIGHT), pygame.SRCALPHA)
                shade.fill((0, 0, 0, 30))
                bg.blit(shade, (int(i * LANE_W), 0))
        for i in range(1, LANE_COUNT):
            x = int(i * LANE_W)
            pygame.draw.line(bg, (90, 100, 140), (x, 0), (x, HEIGHT), max(1, px(3)))
        # 判定线（跑道地面）。追击者就站在它附近，画太重会显得像一条横杠压在身上，
        # 这里用偏暗的颜色、细一点，保留"地面"层次感又不抢戏。
        py8 = PLAYER_Y + px(8)
        pygame.draw.line(bg, (100, 110, 148), (0, py8), (PLAY_W, py8), max(1, px(3)))
        return bg

    @staticmethod
    def _make_gaze_variant(surf):
        """生成"凝视"专用的偏红版本（静态资源，只做一次）。

        早先凝视是在整屏上叠一层 SRCALPHA 红罩，实测 0.65 ms/帧，是凝视态
        最贵的一步（占凝视额外开销的一半以上）。背景本身是静态的，把红调
        直接烘进另一张背景图里，"整屏 alpha 混合"就变成了"换一张图 blit"
        （0.16 ms），效果几乎不变而成本降到 1/4。
        """
        out = surf.copy()
        out.fill(GAZE_TINT_RGB, special_flags=pygame.BLEND_RGB_ADD)
        return out

    def draw_background(self):
        # 凝视时换成偏红的那张背景（省略一次整屏半透明混合）
        self.screen.blit(self.bg_gaze if self.gaze else self.bg_surface, (0, 0))
        # 漂浮装饰（缓慢下移，循环）
        span = HEIGHT + px(60)
        for d in self.bg_decor:
            dy = int((d["y"] + self.bg_scroll * 0.12) % span - px(30))
            self.screen.blit(d["surf"], (int(d["x"] - d["size"]), dy))

    def _build_road_marks(self):
        """预渲染"一条跑道的一节标线"，绘制时按间隔竖直平铺。

        标线每帧要铺 60 次左右（约 20 行 × 3 条跑道）。早先的做法是把三条
        跑道合成一张画布宽的 Surface，于是每次 blit 都得遍历整行透明像素，
        实测占 0.23 ms/帧；改成只做标线本体的窄条后，参与混合的像素不到
        原来的 1/20。
        """
        gap = px(78)
        mark_h = px(26)
        mark_w = px(8)
        surf = pygame.Surface((mark_w, mark_h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (170, 180, 210), surf.get_rect(),
                         border_radius=px(4))
        return surf, gap, mark_w

    def draw_road_marks(self):
        marks = self.road_marks
        gap = self.road_gap
        half = self.road_mark_w / 2.0
        xs = [int(c - half) for c in LANE_CENTERS]
        y = int(self.bg_scroll % gap) - gap
        while y < HEIGHT:
            for x in xs:
                self.screen.blit(marks, (x, y))
            y += gap

    def _build_hud_backdrop(self):
        """预渲染顶部渐变压暗条。

        右侧边栏移除后所有状态信息都搬到顶部，直接压在跑道上会看不清，
        加一层自上而下渐隐的暗色条来保证可读性。
        """
        h = px(136)
        surf = pygame.Surface((WIDTH, h), pygame.SRCALPHA)
        for y in range(h):
            a = int(155 * (1 - y / h) ** 1.5)
            if a > 0:
                surf.fill((6, 10, 26, a), (0, y, WIDTH, 1))
        return surf

    def draw_hud(self):
        """顶部状态条：得分 / 最高分 / 时间 + 凝视倒计时（取代原来的右侧边栏）。"""
        # 菜单界面不显示计分板，避免"得分 0 / 时间 0.0s"压在标题上
        if self.state != "playing":
            return
        self.screen.blit(self.hud_backdrop, (0, 0))

        left = px(18)
        right = WIDTH - px(18)

        draw_text(self.screen, "得分", 15, COLOR_TEXT_DIM, (left, px(10)))
        draw_text(self.screen, f"{int(self.score)}", 38, COLOR_GOLD,
                  (left, px(26)), bold=True)

        draw_text(self.screen, f"最高 {int(self.best_score)}", 16, COLOR_TEXT_DIM,
                  (right, px(12)), anchor="topright")
        draw_text(self.screen, f"{self.elapsed:.1f}s", 20, COLOR_TEXT,
                  (right, px(36)), anchor="topright")

        # 凝视倒计时：全宽细条，一眼就能看到进度
        bar = pygame.Rect(left, px(74), WIDTH - left * 2, px(12))
        pygame.draw.rect(self.screen, (46, 48, 66), bar, border_radius=px(6))
        ratio = max(0.0, min(1.0, self.time_since_lane_change / GAZE_THRESHOLD))
        if ratio > 0.0:
            fill = pygame.Rect(bar.x, bar.y, max(px(2), int(bar.w * ratio)), bar.h)
            pygame.draw.rect(self.screen,
                             (255, 160, 40) if self.gaze else COLOR_WARN,
                             fill, border_radius=px(6))
        pygame.draw.rect(self.screen, (188, 192, 208), bar, max(1, px(2)),
                         border_radius=px(6))

        if self.gaze:
            draw_text(self.screen, "班主任的凝视中！", 18, COLOR_WARN,
                      (left, px(94)), bold=True)
        else:
            draw_text(self.screen, "凝视倒计时", 14, COLOR_TEXT_DIM, (left, px(94)))

        # 增益状态（无敌 / 加速）
        y = px(118)
        if self.player.invincible:
            draw_text(self.screen, f"无敌 {self.player.invincible_timer:.1f}s",
                      17, (255, 220, 120), (left, y), bold=True)
            y += px(24)
        if self.player.speed_boost:
            draw_text(self.screen, f"加速 {self.player.coffee_timer:.1f}s",
                      17, (120, 220, 255), (left, y), bold=True)

    def draw_gaze_warning(self):
        """凝视警告：闪烁的大字提示。

        整屏红罩已经改为预烘进背景（见 _make_gaze_variant），这里不再做整屏
        半透明混合，每帧只剩一次小面积文字绘制。凝视态因此几乎不再额外掉帧。
        """
        if int(pygame.time.get_ticks() // 250) % 2 == 0:
            draw_glow_text(self.screen, "班主任的凝视！", 42, (255, 220, 220),
                           COLOR_WARN, (PLAY_W // 2, HEIGHT // 2 - px(70)),
                           anchor="center")

    def _draw_start_help(self):
        """开始前的「操作方式 + 游戏规则」提醒面板。

        这些说明原本固定在右侧边栏里，既挤占跑道又在手机上小得看不清；
        现在只在开始界面统一提醒一次，进入游戏后画面留给跑道。
        """
        panel_top = vh(0.64)
        panel_h = max(px(230), vh(0.26))
        panel = pygame.Rect(px(22), panel_top, WIDTH - px(44), panel_h)
        glass_panel(self.screen, panel, radius=px(18))

        half = panel.w // 2
        col_l = panel.x + px(26)          # 左栏正文起点
        col_r = panel.x + half + px(10)   # 右栏正文起点

        head_y = panel.y + px(24)
        draw_text(self.screen, "操作方式", 20, COLOR_GOLD,
                  (col_l + (half - px(26)) // 2, head_y), anchor="midtop", bold=True)
        draw_text(self.screen, "游戏规则", 20, COLOR_GOLD,
                  (col_r + (panel.w - half - px(10)) // 2, head_y),
                  anchor="midtop", bold=True)

        rows_top = panel.y + max(px(58), vh(0.046))
        gap = max(px(34), vh(0.047))

        keys = [
            ("← → / A D", "切换跑道"),
            ("↑ / W / 空格", "跳跃"),
            ("左右滑动", "切换跑道"),
            ("上滑 / 点中间", "跳跃"),
        ]
        rules = [
            "躲开课桌，跳过黑板擦与试卷",
            "换道可以打断班主任的凝视",
            "凝视时班主任与校长加速逼近",
            "咖啡加速得分翻倍，辣条无敌",
        ]
        for i, (key, action) in enumerate(keys):
            y = rows_top + i * gap
            draw_text(self.screen, key, 16, (150, 205, 255), (col_l, y), bold=True)
            draw_text(self.screen, action, 16, COLOR_TEXT_DIM, (col_l + px(152), y))
        for i, text in enumerate(rules):
            draw_text(self.screen, text, 16, COLOR_TEXT, (col_r, rows_top + i * gap))

    def draw_start_screen(self):
        t = pygame.time.get_ticks() / 1000.0
        self.screen.blit(self.overlay_start, (0, 0))
        cx = WIDTH // 2

        # 标题：上下弹跳 + 辉光
        bounce = int(math.sin(t * 2.0) * px(12))
        draw_glow_text(self.screen, "坤坤大逃亡", 66, COLOR_GOLD, (255, 120, 40),
                       (cx, vh(0.115) + bounce), anchor="center")
        draw_text(self.screen, "校园大逃亡", 30, COLOR_TEXT,
                  (cx, vh(0.175) + bounce), anchor="center")

        # 三个人物在开始界面预览跑动（人形 + 动效）
        preview_y = vh(0.38)
        ph = t * 13
        draw_humanoid(self.screen, self.chasers[0].face, cx - px(150), preview_y,
                      self.chasers[0].body_color, self.chasers[0].accent, ph, 0.9)
        draw_humanoid(self.screen, self.player.face, cx, preview_y,
                      self.player.body_color, self.player.accent, ph + 0.5, 1.0)
        draw_humanoid(self.screen, self.chasers[1].face, cx + px(150), preview_y,
                      self.chasers[1].body_color, self.chasers[1].accent, ph + 1.0, 0.9)
        draw_text(self.screen, "坤坤", 18, COLOR_GOLD, (cx, preview_y + px(18)),
                  anchor="midtop", bold=True)

        # 开始按钮（呼吸高亮 + 鼠标悬停）
        pulse = (math.sin(t * 3.0) + 1) / 2.0
        self.btn_start.draw(self.screen, pulse, self._hovering(self.btn_start))

        # 操作方式与游戏规则提醒
        self._draw_start_help()

    def draw_game_over(self):
        t = pygame.time.get_ticks() / 1000.0
        self.screen.blit(self.overlay_over, (0, 0))
        cx = WIDTH // 2

        draw_glow_text(self.screen, "游戏结束", 56, (255, 230, 230), COLOR_WARN,
                       (cx, vh(0.20)), anchor="center")

        panel = pygame.Rect(0, 0, min(px(470), WIDTH - px(60)), px(184))
        panel.center = (cx, vh(0.34))
        glass_panel(self.screen, panel, radius=px(20))
        draw_text(self.screen, f"存活时间  {self.elapsed:.1f} 秒", 23, COLOR_TEXT,
                  (cx, panel.y + px(42)), anchor="center")
        draw_text(self.screen, f"最终得分  {int(self.score)}", 28, COLOR_GOLD,
                  (cx, panel.y + px(92)), anchor="center", bold=True)
        draw_text(self.screen, f"历史最高  {int(self.best_score)}", 20, COLOR_TEXT_DIM,
                  (cx, panel.y + px(138)), anchor="center")

        draw_glow_text(self.screen, "坤坤没能成功逃脱", 32, COLOR_GOLD, (180, 120, 40),
                       (cx, vh(0.48)), anchor="center")

        # 两个按钮：主行动呼吸高亮，次行动保持静态
        pulse = (math.sin(t * 3.0) + 1) / 2.0
        self.btn_retry.draw(self.screen, pulse, self._hovering(self.btn_retry))
        self.btn_quit.draw(self.screen, 0.0, self._hovering(self.btn_quit))

    def draw(self):
        self.draw_background()
        self.draw_road_marks()
        for p in self.powerups:
            p.draw(self.screen, math.sin(pygame.time.get_ticks() / 250.0) * 0.5 + 0.5)
        for obs in self.obstacles:
            obs.draw(self.screen)
        # 开始界面自带人物预览，底部不再重复画待机角色（否则下缘会被切掉半截）
        if self.state != "start":
            for chaser in self.chasers:
                chaser.draw(self.screen, shake=6 if self.gaze else 0)
            self.player.draw(self.screen)
        for p in self.particles:
            p.draw(self.screen)

        self.draw_hud()
        if self.gaze:
            self.draw_gaze_warning()

        if self.state == "start":
            self.draw_start_screen()
        elif self.state == "gameover":
            self.draw_game_over()

        pygame.display.flip()

    # ------------------------------------------------------------------
    # 主循环
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self.handle_events()
            self.update(dt)
            self.update_particles(dt)
            self.draw()
        pygame.quit()
        sys.exit(0)


def main():
    Game().run()


if __name__ == "__main__":
    main()
