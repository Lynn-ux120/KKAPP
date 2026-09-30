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

import pygame


# ==========================================================================
# 一、全局常量
# ==========================================================================
# ---- 设计稿基准尺寸 ----
# 所有绘制代码都按这套坐标编写。真机启动时 _apply_render_scale() 会把它们
# 整体放大到屏幕原生分辨率，从而 1:1 渲染、不再有放大模糊。
DESIGN_W = 720                    # 设计稿画布宽
DESIGN_H = 820                    # 设计稿画布高
DESIGN_PLAY_W = 520               # 设计稿跑道区宽
DESIGN_PLAYER_BOTTOM_GAP = 180    # 玩家判定线距画布底部的距离
DESIGN_JUMP_HEIGHT = 150          # 跳跃最大上升高度
DESIGN_SPEEDS = (240.0, 13.0, 950.0)   # 障碍初速 / 每秒递增 / 速度上限

FPS = 60
LANE_COUNT = 3                    # 跑道数量（与分辨率无关）

# 画布像素上限：pygame 是软件渲染，像素越多越吃力。
# 超过上限就整体降采样（略微牺牲清晰度）来保住帧率。
MAX_CANVAS_PIXELS = 3_200_000

# ---- 运行时实际尺寸（由 _apply_render_scale() 计算）----
_S = 1.0                          # 渲染缩放因子：设计稿像素 → 实际画布像素
WIDTH, HEIGHT = DESIGN_W, DESIGN_H
PLAY_W, SIDE_W = DESIGN_PLAY_W, DESIGN_W - DESIGN_PLAY_W
LANE_W = PLAY_W / LANE_COUNT      # 每条跑道宽度
# 三条跑道中心的 x 坐标
LANE_CENTERS = [PLAY_W * (2 * i + 1) / 6.0 for i in range(LANE_COUNT)]
PLAYER_Y = DESIGN_H - DESIGN_PLAYER_BOTTOM_GAP   # 玩家脚底的碰撞判定线
JUMP_HEIGHT = DESIGN_JUMP_HEIGHT
OBSTACLE_SPEED_BASE, OBSTACLE_SPEED_INC, OBSTACLE_SPEED_MAX = DESIGN_SPEEDS

# ---- 时间类常量：不随分辨率变化 ----
JUMP_DURATION = 0.6               # 跳跃持续时间（秒）
SPAWN_INTERVAL_BASE = 1.0         # 障碍初始生成间隔（秒）
SPAWN_INTERVAL_MIN = 0.42         # 障碍生成间隔下限


# --------------------------------------------------------------------------
# 分辨率换算
# --------------------------------------------------------------------------
def px(value):
    """把设计稿像素换算到当前渲染分辨率。

    所有硬编码的设计稿尺寸都必须经此换算，才能在高分屏上保持正确的物理大小。
    """
    return int(round(value * _S))


def _apply_render_scale(scale, canvas_h):
    """按渲染缩放因子重算所有尺寸相关的全局常量。

    scale    ：设计稿 → 画布的放大倍数（通常取 屏幕宽/720）
    canvas_h ：画布高度（竖屏时等于屏幕高度，保证比例一致、不留黑边）
    """
    global _S, WIDTH, HEIGHT, PLAY_W, SIDE_W, LANE_W, LANE_CENTERS
    global PLAYER_Y, JUMP_HEIGHT
    global OBSTACLE_SPEED_BASE, OBSTACLE_SPEED_INC, OBSTACLE_SPEED_MAX
    _S = scale
    WIDTH = int(round(DESIGN_W * scale))
    HEIGHT = int(canvas_h)
    PLAY_W = int(round(DESIGN_PLAY_W * scale))
    SIDE_W = WIDTH - PLAY_W
    LANE_W = PLAY_W / LANE_COUNT
    LANE_CENTERS = [PLAY_W * (2 * i + 1) / 6.0 for i in range(LANE_COUNT)]

    # 玩家判定线贴着画布底部，角色不会飘到屏幕中间
    PLAYER_Y = HEIGHT - px(DESIGN_PLAYER_BOTTOM_GAP)
    # 跳跃高度与人物同步放大（只影响观感，不参与碰撞判定）
    JUMP_HEIGHT = int(DESIGN_JUMP_HEIGHT * scale)
    # 画布越高看得越远，速度同比放大才能维持原本的反应时间
    r = HEIGHT / DESIGN_H
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


_text_cache = {}
_TEXT_CACHE_MAX = 600


def _render_text(text, size, color, bold):
    """渲染文本并缓存 Surface。

    文字每帧都要重绘，而 font.render() 开销不低（尤其高分屏下字号变大后）。
    这里按 (文本, 字号, 颜色, 粗体) 缓存，静态文案只需渲染一次。
    """
    key = (text, size, color, bold)
    surf = _text_cache.get(key)
    if surf is None:
        if len(_text_cache) >= _TEXT_CACHE_MAX:
            _text_cache.clear()
        surf = get_font(size, bold).render(text, True, color)
        _text_cache[key] = surf
    return surf


def draw_text(screen, text, size, color, pos, anchor="topleft", bold=False):
    """绘制中文文本，返回文本矩形，便于居中/对齐。"""
    img = _render_text(text, px(size), color, bold)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    screen.blit(img, rect)
    return rect


def draw_glow_text(screen, text, size, color, glow_color, pos, anchor="center"):
    """绘制带辉光描边的文本（四周铺一圈 glow 再盖主文字），更有质感。"""
    main = _render_text(text, px(size), color, True)
    glow = _render_text(text, px(size), glow_color, True)
    rect = main.get_rect()
    setattr(rect, anchor, pos)
    off = max(1, px(2))
    for dx in (-off - 1, -off, off, off + 1):
        for dy in (-off - 1, -off, off, off + 1):
            screen.blit(glow, (rect.x + dx, rect.y + dy))
    screen.blit(main, rect)
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
        self.base_feet_y = HEIGHT - px(24)      # 平时只露出上半身
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
        label_y = self.feet_y - px(150 * self.scale) - px(6)
        draw_text(screen, self.name, 15, (255, 130, 130),
                  (int(sx), int(label_y)), anchor="midbottom")


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
        self.w = px(104)
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
        self.size = px(52)
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
    """读取设备真实屏幕像素尺寸。

    Android 上 pygame.SCALED 需要知道屏幕比例才能算出正确的逻辑画布高度。
    取不到就回退到设计稿尺寸（此时游戏表现与电脑端一致）。
    """
    if not pygame.display.get_init():
        try:
            pygame.display.init()
        except Exception:
            pass
    try:
        info = pygame.display.Info()
        if info.current_w > 0 and info.current_h > 0:
            return info.current_w, info.current_h
    except Exception:
        pass
    try:
        w, h = pygame.display.get_desktop_size()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    # 最后兜底：真的开一个全屏窗口去量它的尺寸
    try:
        probe = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        w, h = probe.get_size()
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return DESIGN_W, DESIGN_H


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

        # --- 分批加载资源，同时播放加载动画 ---
        self._load_with_animation()

        # --- 菜单按钮 ---
        cx = PLAY_W // 2
        self.btn_start = Button("开始游戏", cx, HEIGHT // 2 + px(240))
        self.btn_retry = Button("再玩一次", cx, HEIGHT // 2 + px(140))
        self.btn_quit = Button("退出游戏", cx, HEIGHT // 2 + px(232), tone="ghost")

        # 预渲染半透明遮罩：每帧新建整屏 Surface 会明显拖慢帧率
        self.overlay_start = self._make_overlay((6, 8, 22, 150))
        self.overlay_over = self._make_overlay((30, 4, 6, 185))
        self.overlay_gaze = self._make_overlay((255, 0, 0, 26), (PLAY_W, HEIGHT))

        self.reset_game()
        self.state = "start"

    # ------------------------------------------------------------------
    # 屏幕与分辨率
    # ------------------------------------------------------------------
    def _setup_canvas(self):
        """按屏幕分辨率确定逻辑画布尺寸并建立窗口。

        画布宽度对齐屏幕宽度，配合 SCALED 就是 1:1 原生渲染，
        画面不再被整体放大，清晰度比"小画布放大铺满"高一档。
        """
        screen_w, screen_h = DESIGN_W, DESIGN_H
        if _screen_fit_enabled():
            screen_w, screen_h = _query_screen_size()
            # 部分安卓设备会把屏幕报告成横屏(如 2400x1080)，而本游戏锁定竖屏，
            # 统一按"短边为宽、长边为高"归一，避免算出错误比例。
            if screen_w > screen_h:
                screen_w, screen_h = screen_h, screen_w

        scale = screen_w / DESIGN_W
        canvas_h = screen_h
        # 软件渲染下像素越多越吃力：超过上限就整体降采样，宁可略糊也要保住帧率
        if scale * DESIGN_W * canvas_h > MAX_CANVAS_PIXELS:
            k = math.sqrt(MAX_CANVAS_PIXELS / (scale * DESIGN_W * canvas_h))
            scale *= k
            canvas_h *= k
        _apply_render_scale(scale, canvas_h)

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

    # ------------------------------------------------------------------
    # 加载动画
    # ------------------------------------------------------------------
    def _draw_loading(self, progress, label):
        """绘制加载界面：标题 + 进度条 + 当前步骤 + 跑动小人。"""
        pygame.event.pump()                       # 保持窗口响应，避免被系统判定卡死
        t = pygame.time.get_ticks() / 1000.0
        self.screen.fill((8, 10, 24))
        cx, cy = WIDTH // 2, HEIGHT // 2

        draw_glow_text(self.screen, "坤坤大逃亡", 52, COLOR_GOLD, (255, 120, 40),
                       (cx, cy - px(150)), anchor="center")
        draw_text(self.screen, "校园大逃亡", 24, COLOR_TEXT_DIM,
                  (cx, cy - px(88)), anchor="center")

        # 进度条
        bar_h = px(14)
        bar = pygame.Rect(0, 0, px(360), bar_h)
        bar.center = (cx, cy + px(30))
        pygame.draw.rect(self.screen, (30, 34, 58), bar, border_radius=bar_h // 2)
        fill = pygame.Rect(bar.x, bar.y, int(bar.w * progress), bar.h)
        if fill.w > 0:
            pygame.draw.rect(self.screen, COLOR_GOLD, fill, border_radius=bar_h // 2)
        pygame.draw.rect(self.screen, (120, 140, 210), bar, max(1, px(2)),
                         border_radius=bar_h // 2)

        draw_text(self.screen, label, 18, COLOR_TEXT, (cx, cy + px(78)), anchor="center")
        draw_text(self.screen, f"{int(progress * 100)}%", 16, COLOR_TEXT_DIM,
                  (cx, cy + px(110)), anchor="center")

        # 跑动的小人：让"正在加载"有动感，而不是一张静止的图
        # 放在画面下方，与进度条拉开距离，避免和文字叠在一起
        draw_humanoid(self.screen, None, cx, cy + px(430),
                      (46, 116, 226), (255, 200, 70), t * 13, 0.85)

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
        self.side_panel_static = self._build_side_panel_static()
        self.road_marks, self.road_gap = self._build_road_marks()

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
        if x0 >= PLAY_W:      # 忽略侧边栏区域的触摸
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
        py8 = PLAYER_Y + px(8)
        pygame.draw.line(bg, (140, 150, 190), (0, py8), (PLAY_W, py8), max(1, px(4)))
        return bg

    def draw_background(self):
        self.screen.blit(self.bg_surface, (0, 0))
        # 漂浮装饰（缓慢下移，循环）
        span = HEIGHT + px(60)
        for d in self.bg_decor:
            dy = int((d["y"] + self.bg_scroll * 0.12) % span - px(30))
            self.screen.blit(d["surf"], (int(d["x"] - d["size"]), dy))

    def _build_road_marks(self):
        """预渲染一格路面标线，绘制时垂直平铺即可，省掉每帧几十次 draw.rect。"""
        gap = px(78)
        surf = pygame.Surface((PLAY_W, gap), pygame.SRCALPHA)
        for lane in range(LANE_COUNT):
            x = int(LANE_CENTERS[lane])
            pygame.draw.rect(surf, (170, 180, 210),
                             (x - px(4), 0, px(8), px(26)), border_radius=px(4))
        return surf, gap

    def draw_road_marks(self):
        gap = self.road_gap
        offset = int(self.bg_scroll % gap)
        y = -gap + offset
        while y < HEIGHT:
            self.screen.blit(self.road_marks, (0, y))
            y += gap

    def draw_hud(self):
        # 菜单界面不显示计分板，避免"得分 0 / 时间 0.0s"压在标题上
        if self.state != "playing":
            return
        x = px(18)
        draw_text(self.screen, f"得分 {int(self.score)}", 26, COLOR_GOLD, (x, px(16)), bold=True)
        draw_text(self.screen, f"时间 {self.elapsed:.1f}s", 19, COLOR_TEXT, (x, px(52)))
        draw_text(self.screen, f"最高分 {int(self.best_score)}", 17, COLOR_TEXT_DIM, (x, px(80)))

    def _build_side_panel_static(self):
        """预渲染侧边栏静态部分（面板 + 键位说明 + 实时状态标题）。"""
        surf = pygame.Surface((SIDE_W, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(surf, (16, 20, 38, 200), surf.get_rect())
        pygame.draw.rect(surf, (110, 150, 255, 90), surf.get_rect(), 2)

        cx = SIDE_W // 2
        draw_glow_text(surf, "键位说明", 24, COLOR_GOLD, (80, 90, 140),
                       (cx, px(30)), anchor="midtop")
        hints = [
            ("← / →  或  A / D", "切换跑道"),
            ("↑ / W / 空格", "跳跃"),
            ("ESC", "退出游戏"),
            ("R（结束后）", "重新开始"),
        ]
        y = px(76)
        for keys, action in hints:
            draw_text(surf, keys, 16, (150, 205, 255), (px(16), y), bold=True)
            draw_text(surf, action, 14, COLOR_TEXT_DIM, (px(16), y + px(21)))
            y += px(48)

        pygame.draw.line(surf, (70, 80, 110), (px(12), y), (SIDE_W - px(12), y), max(1, px(2)))
        y += px(14)
        draw_glow_text(surf, "实时状态", 20, COLOR_GOLD, (80, 90, 140),
                       (cx, y), anchor="midtop")
        return surf

    def draw_side_panel(self):
        self.screen.blit(self.side_panel_static, (PLAY_W, 0))

        # 动态状态（与静态区底部对齐后向下绘制）
        tx = PLAY_W + px(16)
        y = px(314)
        draw_text(self.screen, f"得分  {int(self.score)}", 16, COLOR_TEXT, (tx, y)); y += px(25)
        draw_text(self.screen, f"时间  {self.elapsed:.1f}s", 16, COLOR_TEXT, (tx, y)); y += px(25)
        draw_text(self.screen, f"速度  {int(self.speed)}", 16, COLOR_TEXT, (tx, y)); y += px(30)

        # 凝视倒计时
        # 字号 15 实际渲染高度约 20，步进必须留够，否则进度条会压住文字
        draw_text(self.screen, "凝视倒计时", 15, COLOR_WARN, (tx, y), bold=True); y += px(26)
        bar = pygame.Rect(tx, y, SIDE_W - px(32), px(13))
        pygame.draw.rect(self.screen, (50, 50, 60), bar, border_radius=px(7))
        ratio = max(0.0, min(1.0, self.time_since_lane_change / GAZE_THRESHOLD))
        fill = pygame.Rect(bar.x, bar.y, int(bar.w * ratio), bar.h)
        pygame.draw.rect(self.screen, (255, 160, 40) if self.gaze else COLOR_WARN, fill, border_radius=px(7))
        pygame.draw.rect(self.screen, (190, 190, 200), bar, max(1, px(2)), border_radius=px(7))
        y += px(30)

        if self.player.invincible:
            draw_text(self.screen, f"无敌 {self.player.invincible_timer:.1f}s", 16, (255, 220, 120), (tx, y), bold=True); y += px(24)
        if self.player.speed_boost:
            draw_text(self.screen, f"加速 {self.player.coffee_timer:.1f}s", 16, (120, 220, 255), (tx, y), bold=True); y += px(24)

    def draw_gaze_warning(self):
        if int(pygame.time.get_ticks() // 250) % 2 == 0:
            draw_glow_text(self.screen, "班主任的凝视！", 42, (255, 220, 220), COLOR_WARN,
                           (PLAY_W // 2, HEIGHT // 2 - px(70)), anchor="center")
        self.screen.blit(self.overlay_gaze, (0, 0))

    def draw_start_screen(self):
        t = pygame.time.get_ticks() / 1000.0
        self.screen.blit(self.overlay_start, (0, 0))
        cx, cy = PLAY_W // 2, HEIGHT // 2

        # 标题：上下弹跳 + 辉光
        bounce = int(math.sin(t * 2.0) * px(12))
        draw_glow_text(self.screen, "坤坤大逃亡", 66, COLOR_GOLD, (255, 120, 40),
                       (cx, cy - px(200) + bounce), anchor="center")
        draw_text(self.screen, "校园大逃亡", 30, COLOR_TEXT,
                  (cx, cy - px(140) + bounce), anchor="center")

        # 三个人物在开始界面预览跑动（人形 + 动效）
        # 脚底下移到 cy+80，给副标题留出空间，避免人物头顶压住文字
        preview_y = cy + px(80)
        ph = t * 13
        draw_humanoid(self.screen, self.chasers[0].face, cx - px(150), preview_y,
                      self.chasers[0].body_color, self.chasers[0].accent, ph, 0.9)
        draw_humanoid(self.screen, self.player.face, cx, preview_y,
                      self.player.body_color, self.player.accent, ph + 0.5, 1.0)
        draw_humanoid(self.screen, self.chasers[1].face, cx + px(150), preview_y,
                      self.chasers[1].body_color, self.chasers[1].accent, ph + 1.0, 0.9)
        draw_text(self.screen, "坤坤", 18, COLOR_GOLD, (cx, preview_y + px(70)),
                  anchor="midtop", bold=True)

        # 开始按钮（呼吸高亮 + 鼠标悬停）
        pulse = (math.sin(t * 3.0) + 1) / 2.0
        self.btn_start.draw(self.screen, pulse, self._hovering(self.btn_start))

        draw_text(self.screen, "空格 / 点击按钮 开始", 20, COLOR_TEXT_DIM,
                  (cx, cy + px(310)), anchor="center")
        draw_text(self.screen, "切换跑道可躲避班主任的凝视", 18, COLOR_TEXT_DIM,
                  (cx, cy + px(345)), anchor="center")
        draw_text(self.screen, "手机：左右滑换道，上滑/点按跳跃", 18, COLOR_TEXT_DIM,
                  (cx, cy + px(373)), anchor="center")

    def draw_game_over(self):
        t = pygame.time.get_ticks() / 1000.0
        self.screen.blit(self.overlay_over, (0, 0))
        cx, cy = PLAY_W // 2, HEIGHT // 2

        draw_glow_text(self.screen, "游戏结束", 56, (255, 230, 230), COLOR_WARN,
                       (cx, cy - px(170)), anchor="center")

        panel = pygame.Rect(cx - px(150), cy - px(120), px(300), px(152))
        glass_panel(self.screen, panel, radius=px(20))
        draw_text(self.screen, f"存活时间  {self.elapsed:.1f} 秒", 24, COLOR_TEXT,
                  (cx, cy - px(92)), anchor="center")
        draw_text(self.screen, f"最终得分  {int(self.score)}", 24, COLOR_TEXT,
                  (cx, cy - px(56)), anchor="center")
        draw_text(self.screen, f"历史最高  {int(self.best_score)}", 20, COLOR_TEXT_DIM,
                  (cx, cy - px(22)), anchor="center")

        draw_glow_text(self.screen, "坤坤没能成功逃脱", 32, COLOR_GOLD, (180, 120, 40),
                       (cx, cy + px(60)), anchor="center")

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
        self.draw_side_panel()
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
