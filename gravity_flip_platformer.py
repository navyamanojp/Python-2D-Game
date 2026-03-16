
# =============================================================================
# GRAVITY FLIP — Neon Cyberpunk Endless Runner
# Auto-runs right. SPACE / Click flips gravity. Dodge spikes & lava.
# =============================================================================

import pygame
import sys
import random
import math
import array

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SW, SH = 900, 550
FPS    = 60

MENU      = 0
PLAYING   = 1
GAME_OVER = 2

# ---------------------------------------------------------------------------
# Deep-Space Midnight Colour Palette  (easy on the eyes)
# ---------------------------------------------------------------------------
BG_DARK       = (12,  14,   30)   # deep navy
NEON_CYAN     = (80,  210,  220)  # soft teal
NEON_PINK     = (230,  90,  130)  # dusty rose / coral
NEON_PURPLE   = (130,  90,  210)  # muted violet
NEON_YELLOW   = (240, 200,   80)  # warm amber
NEON_GREEN    = (80,  200,  140)  # seafoam
NEON_ORANGE   = (230, 130,   50)  # burnt orange
WHITE         = (235, 240,  255)  # soft white (slightly blue-tinted)
BLACK         = (0,     0,    0)

PLAT_BODY     = (20,  28,   60)   # dark indigo slab
PLAT_EDGE     = (80,  180,  200)  # teal edge strip
PLAT_GLOW     = (40,  110,  160)  # subtle blue glow

SPIKE_BASE    = (160, 140,  200)  # muted lavender
SPIKE_TIP     = (220, 215,  255)  # pale lilac tip
SPIKE_GLOW_C  = (140, 100,  200)  # soft violet halo

LAVA_DARK     = (140,  35,   20)  # deep brick
LAVA_MID      = (210,  80,   30)  # rusty orange
LAVA_BRIGHT   = (245, 145,   50)  # warm amber-orange
LAVA_WHITE    = (255, 230,  180)  # pale glow

# Speed presets  (label, pixels-per-frame)
SPEEDS = [("SLOW", 2), ("NORMAL", 4), ("FAST", 6), ("INSANE", 9)]



THEME_LIGHT = dict(
    BG_DARK      = (110, 185, 240),   # bright sky blue
    NEON_CYAN    = (30,  140, 200),   # deeper blue accent
    NEON_PINK    = (220,  70,  90),   # coral red
    NEON_PURPLE  = (100, 160, 230),   # sky blue-purple
    NEON_YELLOW  = (240, 190,  40),   # golden
    NEON_GREEN   = (60,  175,  80),   # grass green
    NEON_ORANGE  = (220, 120,  40),   # orange
    WHITE        = (255, 255, 255),
    PLAT_BODY    = (55,  130,  60),   # grass-green slab
    PLAT_EDGE    = (90,  200,  90),   # bright green top strip
    PLAT_GLOW    = (40,  150,  50),   # dark green glow
    SPIKE_BASE   = (170, 170, 185),   # steel grey
    SPIKE_TIP    = (220, 220, 230),   # light silver
    SPIKE_GLOW_C = (130, 130, 160),   # grey-purple halo
    LAVA_DARK    = (160,  35,  20),
    LAVA_MID     = (215,  85,  30),
    LAVA_BRIGHT  = (255, 150,  40),
    LAVA_WHITE   = (255, 235, 185),
)

THEME_DARK = dict(
    BG_DARK      = (12,  14,   30),
    NEON_CYAN    = (80,  210,  220),
    NEON_PINK    = (230,  90,  130),
    NEON_PURPLE  = (130,  90,  210),
    NEON_YELLOW  = (240, 200,   80),
    NEON_GREEN   = (80,  200,  140),
    NEON_ORANGE  = (230, 130,   50),
    WHITE        = (235, 240,  255),
    PLAT_BODY    = (20,  28,   60),
    PLAT_EDGE    = (80,  180,  200),
    PLAT_GLOW    = (40,  110,  160),
    SPIKE_BASE   = (160, 140,  200),
    SPIKE_TIP    = (220, 215,  255),
    SPIKE_GLOW_C = (140, 100,  200),
    LAVA_DARK    = (140,  35,   20),
    LAVA_MID     = (210,  80,   30),
    LAVA_BRIGHT  = (245, 145,   50),
    LAVA_WHITE   = (255, 230,  180),
)


def apply_theme(t):
    """Interpolate all global palette colours between LIGHT (t=0) and DARK (t=1)."""
    g = globals()
    for key in THEME_LIGHT:
        a = THEME_LIGHT[key]
        b = THEME_DARK[key]
        g[key] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))
    g["_THEME_T"] = t


# Global theme progress (0=light, 1=dark) — read by draw classes
_THEME_T = 0.0

# Initialise with light theme
apply_theme(0.0)

# ---------------------------------------------------------------------------
# Physics / World
# ---------------------------------------------------------------------------
AUTO_SPEED          = 4   # overwritten per game from speed selector
GRAVITY_STRENGTH    = 0.52
CHUNK_WIDTH         = SW
PLATFORMS_PER_CHUNK = 5
GEN_LOOKAHEAD       = SW * 2
CULL_DISTANCE       = SW * 2
SPIKES_PER_CHUNK    = 3
LAVA_PER_CHUNK      = 1


# =============================================================================
# Helpers
# =============================================================================
def lerp_color(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_glow(surface, color, arg, radius=0, blur=8, alpha=80, is_rect=True):
    """Blit an additive glow halo around a rect or a circle."""
    try:
        if is_rect:
            r  = arg
            gw = r.width  + blur * 2
            gh = r.height + blur * 2
            gx = r.x - blur
            gy = r.y - blur
        else:
            cx, cy = arg
            gw = gh = radius * 2 + blur * 2
            gx = cx - radius - blur
            gy = cy - radius - blur

        gs = pygame.Surface((max(1, gw), max(1, gh)), pygame.SRCALPHA)
        cr, cg, cb = color[0], color[1], color[2]
        for step in range(blur, 0, -2):
            a = int(alpha * (step / blur) ** 2)
            col = (cr, cg, cb, a)
            if is_rect:
                pygame.draw.rect(gs, col,
                                 pygame.Rect(blur - step, blur - step,
                                             r.width  + step * 2,
                                             r.height + step * 2),
                                 border_radius=6)
            else:
                pygame.draw.circle(gs, col, (gw // 2, gh // 2), radius + step)
        surface.blit(gs, (gx, gy), special_flags=pygame.BLEND_RGBA_ADD)
    except Exception:
        pass


def make_sound(freq_start=440, freq_end=880, duration=0.12, amp=28000):
    try:
        sr = 44100
        n  = int(sr * duration)
        buf = array.array("h")
        for i in range(n):
            t    = i / sr
            freq = freq_start + (freq_end - freq_start) * (i / n)
            a    = amp * (1 - i / n)
            v    = int(a * math.sin(2 * math.pi * freq * t))
            buf.append(v); buf.append(v)
        return pygame.mixer.Sound(buffer=buf)
    except Exception:
        return None


# =============================================================================
# CloudLayer  (fluffy parallax clouds, visible in light theme)
# =============================================================================
class CloudLayer:
    def __init__(self):
        self.clouds = [self._make_cloud(random.randint(0, SW)) for _ in range(10)]

    def _make_cloud(self, x):
        # Keep clouds in top strip or bottom strip — clear centre play area
        if random.random() < 0.5:
            y = random.randint(30, 110)
        else:
            y = random.randint(SH - 120, SH - 45)
        return {
            "x":     float(x),
            "y":     y,
            "puffs": random.randint(3, 5),
            "radii": [random.randint(14, 28) for _ in range(5)],
            "speed": random.uniform(0.3, 0.8),
        }

    def update(self):
        for c in self.clouds:
            c["x"] -= c["speed"]
            if c["x"] < -260:
                new = self._make_cloud(SW + random.randint(10, 100))
                c.update(new)

    def draw(self, surface, alpha):
        if alpha <= 0:
            return
        for c in self.clouds:
            s  = pygame.Surface((300, 100), pygame.SRCALPHA)
            ox = 28
            for i in range(c["puffs"]):
                r  = c["radii"][i]
                px = ox + i * (r + 8)
                # outer soft haze
                pygame.draw.circle(s, (160, 188, 215, int(alpha * 0.15)), (px, 52), r + 8)
                # mid layer
                pygame.draw.circle(s, (178, 202, 222, int(alpha * 0.28)), (px, 50), r + 3)
                # core — muted blue-white, not pure white
                pygame.draw.circle(s, (200, 218, 235, int(alpha * 0.48)), (px, 48), r)
            surface.blit(s, (int(c["x"]) - 28, c["y"] - 50))


# =============================================================================
# StarField
# =============================================================================
class StarField:
    def __init__(self):
        self.stars = [{"x": random.randint(0, SW),
                        "y": random.randint(0, SH),
                        "speed": random.uniform(0.15, 1.2),
                        "size":  random.choice([1, 1, 1, 2]),
                        "bright": random.randint(80, 220)}
                      for _ in range(180)]

    def update(self):
        for s in self.stars:
            s["x"] -= s["speed"]
            if s["x"] < 0:
                s["x"] = SW + 2
                s["y"] = random.randint(0, SH)

    def draw(self, surface):
        for s in self.stars:
            b  = s["bright"]
            b2 = min(255, int(b * 1.3))
            pygame.draw.circle(surface, (b, b, b2),
                               (int(s["x"]), int(s["y"])), s["size"])


# =============================================================================
# Particle
# =============================================================================
class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x, y, color):
        self.x = float(x); self.y = float(y)
        a = random.uniform(0, math.tau)
        s = random.uniform(2, 8)
        self.vx = math.cos(a) * s; self.vy = math.sin(a) * s
        self.life = self.max_life = random.randint(22, 50)
        self.color = color
        self.size  = random.randint(2, 5)

    def update(self):
        self.x += self.vx; self.y += self.vy
        self.vy += 0.15; self.life -= 1
        return self.life > 0

    def draw(self, surf):
        t = self.life / self.max_life
        col = tuple(int(c * t) for c in self.color)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)),
                           max(1, int(self.size * t)))


class ParticleSystem:
    def __init__(self):
        self.p: list = []

    def burst(self, x, y, color, n=40):
        self.p.extend(Particle(x, y, color) for _ in range(n))

    def update(self):
        self.p = [p for p in self.p if p.update()]

    def draw(self, surf):
        for p in self.p:
            p.draw(surf)


# =============================================================================
# Button  (glassmorphism + neon border)
# =============================================================================
class Button:
    def __init__(self, x, y, w, h, text, accent=NEON_CYAN):
        self.rect   = pygame.Rect(x, y, w, h)
        self.text   = text
        self.accent = accent
        self.font   = pygame.font.SysFont("consolas", 23, bold=True)
        self._t     = 0.0

    def update(self):
        hov   = self.rect.collidepoint(pygame.mouse.get_pos())
        self._t += (1.0 if hov else -1.0) * 0.14
        self._t  = max(0.0, min(1.0, self._t))

    def draw(self, surf):
        t = self._t
        # Glass fill
        gl = pygame.Surface((self.rect.w, self.rect.h), pygame.SRCALPHA)
        gl.fill((255, 255, 255, int(40 + 70 * t)))
        surf.blit(gl, self.rect.topleft)
        # Border
        col = lerp_color((70, 70, 100), self.accent, t)
        pygame.draw.rect(surf, col, self.rect, width=2, border_radius=12)
        # Glow
        if t > 0.05:
            draw_glow(surf, self.accent, self.rect, blur=12, alpha=int(55 * t))
        # Label
        lbl = self.font.render(self.text, True,
                               lerp_color((170, 170, 200), WHITE, t))
        surf.blit(lbl, lbl.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and self.rect.collidepoint(event.pos))


# =============================================================================
# Platform  (dark neon-edged slab with circuit lines)
# =============================================================================
class Platform:
    HEIGHT = 18

    def __init__(self, x, y, width):
        self.rect = pygame.Rect(x, y, width, self.HEIGHT)

    def draw_world(self, surf, cam):
        sx = self.rect.x - cam
        if sx + self.rect.width < 0 or sx > SW:
            return
        sr = pygame.Rect(sx, self.rect.y, self.rect.width, self.HEIGHT)

        if _THEME_T < 0.5:
            # ---- LIGHT theme: plain green slab ----
            pygame.draw.rect(surf, PLAT_BODY, sr, border_radius=4)
            # bright green top edge only
            pygame.draw.rect(surf, PLAT_EDGE,
                             pygame.Rect(sr.x, sr.y, sr.width, 3), border_radius=3)
            pygame.draw.rect(surf, (0, 80, 0), sr, width=1, border_radius=4)
        else:
            # ---- DARK theme: neon slab with circuit lines ----
            pygame.draw.rect(surf, PLAT_BODY, sr, border_radius=5)
            pygame.draw.rect(surf, (0, 80, 110), sr, width=1, border_radius=5)
            pygame.draw.rect(surf, PLAT_EDGE,
                             pygame.Rect(sr.x, sr.y, sr.width, 3), border_radius=3)
            pygame.draw.rect(surf, PLAT_GLOW,
                             pygame.Rect(sr.x, sr.bottom - 3, sr.width, 3), border_radius=3)
            draw_glow(surf, PLAT_EDGE, sr, blur=6, alpha=35)
            my = sr.centery
            pygame.draw.line(surf, (0, 60, 90), (sr.x + 8, my), (sr.right - 8, my), 1)
            for dx in range(sr.x + 20, sr.right - 20, 38):
                pygame.draw.circle(surf, PLAT_EDGE, (dx, my), 2)

    @staticmethod
    def generate_chunk(chunk_x):
        ps = []
        ps.append(Platform(chunk_x, SH - Platform.HEIGHT, CHUNK_WIDTH + 2))
        ps.append(Platform(chunk_x, 0, CHUNK_WIDTH + 2))
        bh = (SH - 80) // PLATFORMS_PER_CHUNK
        for i in range(PLATFORMS_PER_CHUNK):
            w = random.randint(110, 240)
            x = chunk_x + random.randint(20, CHUNK_WIDTH - w - 20)
            y = random.randint(40 + i * bh, 40 + i * bh + bh - 20)
            ps.append(Platform(x, y, w))
        return ps


# =============================================================================
# Spike  (glowing purple crystal)
# =============================================================================
class Spike:
    SIZE = 16

    def __init__(self, x, y, count, pointing_up=True):
        self.x = x; self.y = y
        self.count = count
        self.pointing_up = pointing_up
        inset = 3
        self.rect = pygame.Rect(x + inset, y + inset,
                                count * self.SIZE - inset * 2,
                                self.SIZE - inset * 2)
        self._tick = random.randint(0, 60)

    def update(self):
        self._tick += 1

    def draw_world(self, surf, cam):
        sx = self.x - cam
        if sx + self.count * self.SIZE < 0 or sx > SW:
            return

        if _THEME_T < 0.5:
            # ---- LIGHT theme: plain grey steel triangles ----
            for i in range(self.count):
                bx = int(sx + i * self.SIZE)
                by = self.y
                s  = self.SIZE
                if self.pointing_up:
                    tip = (bx + s // 2, by);       bl = (bx, by + s);  br = (bx + s, by + s)
                else:
                    tip = (bx + s // 2, by + s);   bl = (bx, by);      br = (bx + s, by)
                pygame.draw.polygon(surf, (160, 160, 170), [tip, bl, br])
                pygame.draw.polygon(surf, (100, 100, 110), [tip, bl, br], 1)
        else:
            # ---- DARK theme: glowing crystal ----
            pulse = 0.5 + 0.5 * math.sin(self._tick * 0.09)
            for i in range(self.count):
                bx = int(sx + i * self.SIZE)
                by = self.y
                s  = self.SIZE
                if self.pointing_up:
                    tip = (bx + s // 2, by);       bl = (bx, by + s);  br = (bx + s, by + s)
                else:
                    tip = (bx + s // 2, by + s);   bl = (bx, by);      br = (bx + s, by)
                pts = [tip, bl, br]
                expand = 3
                glow_pts = []
                cx_tri = (tip[0] + bl[0] + br[0]) // 3
                cy_tri = (tip[1] + bl[1] + br[1]) // 3
                for px, py in pts:
                    dx = px - cx_tri; dy = py - cy_tri
                    dist = math.hypot(dx, dy) or 1
                    glow_pts.append((px + int(dx / dist * expand),
                                     py + int(dy / dist * expand)))
                ga   = int(100 * pulse)
                gl_s = pygame.Surface((s + 20, s + 20), pygame.SRCALPHA)
                off  = 10
                adj  = [(p[0] - bx + off, p[1] - by + off) for p in glow_pts]
                pygame.draw.polygon(gl_s, (*SPIKE_GLOW_C, ga), adj)
                surf.blit(gl_s, (bx - off, by - off),
                          special_flags=pygame.BLEND_RGBA_ADD)
                shrink = 3
                cx3 = (tip[0] + bl[0] + br[0]) // 3
                cy3 = (tip[1] + bl[1] + br[1]) // 3
                inner = []
                for px, py in pts:
                    dx = cx3 - px; dy = cy3 - py
                    dist = math.hypot(dx, dy) or 1
                    inner.append((px + int(dx / dist * shrink),
                                  py + int(dy / dist * shrink)))
                pygame.draw.polygon(surf, (35, 18, 75), inner)
                edge_col = lerp_color(SPIKE_BASE, SPIKE_TIP, pulse)
                pygame.draw.polygon(surf, edge_col, pts, 2)
                pygame.draw.circle(surf, WHITE, tip, 2)
                draw_glow(surf, SPIKE_GLOW_C, tip, radius=2,
                          blur=5, alpha=int(120 * pulse), is_rect=False)


# =============================================================================
# Lava  (animated magma pool with wave, bubbles, drips)
# =============================================================================
class Lava:
    HEIGHT = 30

    def __init__(self, x, y, width):
        self.rect    = pygame.Rect(x, y, width, self.HEIGHT)
        self._tick   = random.randint(0, 60)
        self._bubbles = [(random.randint(6, max(7, width - 6)),
                          random.randint(0, 80))
                         for _ in range(max(1, width // 16))]
        self._drips   = [(random.randint(0, max(1, width - 1)),
                          random.uniform(0, 1))
                         for _ in range(4)]

    def update(self):
        self._tick += 1

    def draw_world(self, surf, cam):
        sx = self.rect.x - cam
        if sx + self.rect.width < 0 or sx > SW:
            return
        w, h = self.rect.width, self.rect.height
        sr   = pygame.Rect(int(sx), self.rect.y, w, h)
        t    = self._tick

        if _THEME_T < 0.5:
            # ---- LIGHT theme: plain flat orange lava ----
            pygame.draw.rect(surf, (220, 80, 20), sr, border_radius=3)
            # simple bright top line
            pygame.draw.line(surf, (255, 160, 50), (sr.x, sr.y), (sr.right, sr.y), 2)
            return

        # ---- DARK theme: animated magma with wave, bubbles, drips ----

        # Bottom glow
        draw_glow(surf, LAVA_MID, sr, blur=16, alpha=65)

        # Gradient body
        for row in range(h):
            frac = row / h
            col  = lerp_color(LAVA_DARK, LAVA_MID, frac ** 0.6)
            pygame.draw.line(surf, col,
                             (sr.x, sr.y + row), (sr.right, sr.y + row))

        # Animated wave top
        wave_pts = [(sr.x + wx,
                     sr.y + 3 + int(3 * math.sin(wx * 0.09 + t * 0.11)))
                    for wx in range(w + 1)]
        if len(wave_pts) >= 2:
            pygame.draw.lines(surf, LAVA_BRIGHT, False, wave_pts, 2)
            for px, py in wave_pts[::5]:
                pygame.draw.circle(surf, LAVA_WHITE, (px, py), 1)

        # Rising bubbles
        for bx_l, phase in self._bubbles:
            prog = ((t * 0.85 + phase) % 80) / 80.0
            bx   = sr.x + bx_l
            by   = int(sr.bottom - 3 - prog * h)
            r    = max(1, int(3.5 * (1 - prog * 0.6)))
            col  = lerp_color(LAVA_MID, LAVA_WHITE, prog)
            if sr.left <= bx <= sr.right:
                pygame.draw.circle(surf, col, (bx, by), r)
                if prog > 0.80:
                    draw_glow(surf, LAVA_BRIGHT, (bx, by),
                              radius=r, blur=5, alpha=80, is_rect=False)

        # Drip effect
        for drip_xl, phase in self._drips:
            prog   = ((t * 0.55 + phase * 80) % 80) / 80.0
            drip_x = sr.x + int(drip_xl)
            drip_y = sr.bottom + int(prog * 14)
            drip_r = max(1, int(3.5 * (1 - prog)))
            col    = lerp_color(LAVA_MID, LAVA_DARK, prog)
            if 0 <= drip_x <= SW:
                pygame.draw.circle(surf, col, (drip_x, drip_y), drip_r)

        # Bright border
        pygame.draw.rect(surf, LAVA_BRIGHT, sr, width=1, border_radius=3)


# =============================================================================
# Player  (auto-runner, SPACE/click flips gravity)
# =============================================================================
class Player:
    WIDTH     = 30
    HEIGHT    = 38
    TRAIL_LEN = 14

    def __init__(self):
        self.rect         = pygame.Rect(SW // 4, SH // 2,
                                        self.WIDTH, self.HEIGHT)
        self.vel_y        = 0.0
        self.gravity_dir  = 1
        self.on_ground    = False
        self._flip_timer  = 0
        self._flip_squash = 1.0
        self._trail: list = []

    def flip_gravity(self):
        self.gravity_dir  *= -1
        self.vel_y         = 0.0
        self._flip_timer   = 12
        self.on_ground     = False

    def update(self, platforms, cam):
        self.vel_y += GRAVITY_STRENGTH * self.gravity_dir
        self.vel_y  = max(-13, min(13, self.vel_y))

        self.rect.y   += int(self.vel_y)
        self.on_ground = False

        for p in platforms:
            if self.rect.colliderect(p.rect):
                if self.gravity_dir == 1 and self.vel_y >= 0:
                    self.rect.bottom = p.rect.top
                    self.vel_y = 0; self.on_ground = True
                elif self.gravity_dir == -1 and self.vel_y <= 0:
                    self.rect.top = p.rect.bottom
                    self.vel_y = 0; self.on_ground = True

        if self._flip_timer > 0:
            prog = self._flip_timer / 12
            self._flip_squash = 0.55 + 0.45 * abs(prog - 0.5) * 2
            self._flip_timer -= 1
        else:
            self._flip_squash = 1.0

        # Trail in screen space
        self._trail.append((self.rect.centerx - cam, self.rect.centery))
        if len(self._trail) > self.TRAIL_LEN:
            self._trail.pop(0)

    def draw(self, surf, cam):
        sh = int(self.HEIGHT * self._flip_squash)
        sw = int(self.WIDTH  * (2.0 - self._flip_squash))
        oy = (self.HEIGHT - sh) // 2
        sx = self.rect.x - cam

        dr = pygame.Rect(sx - (sw - self.WIDTH) // 2,
                         self.rect.y + oy, sw, sh)

        # Body — plain white, no trail, no glow, no border
        pygame.draw.rect(surf, (255, 255, 255), dr, border_radius=6)

        # Eyes — black dots
        eye_y = dr.top + 9 if self.gravity_dir == 1 else dr.bottom - 13
        for ex in (dr.centerx - 7, dr.centerx + 7):
            pygame.draw.circle(surf, BLACK, (ex, eye_y), 4)

    def is_off_screen(self):
        return self.rect.top > SH or self.rect.bottom < 0


# =============================================================================
# Score
# =============================================================================
class ScoreTracker:
    UNITS_PER_METRE = 60

    def __init__(self):
        self.score = 0
        self.best  = 0
        self._max  = 0

    def update(self, world_x):
        if world_x > self._max:
            self._max  = world_x
            self.score = self._max // self.UNITS_PER_METRE
            if self.score > self.best:
                self.best = self.score


# =============================================================================
# UI helpers
# =============================================================================
def hud_panel(surf, rect, accent=NEON_CYAN):
    panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    panel.fill((0, 0, 20, 175))
    pygame.draw.rect(panel, (*accent, 210),
                     panel.get_rect(), width=2, border_radius=10)
    surf.blit(panel, rect.topleft)


def text_shadow(surf, font, txt, color, center, off=2):
    sh = font.render(txt, True, (0, 0, 0))
    tx = font.render(txt, True, color)
    cx, cy = center
    surf.blit(sh, sh.get_rect(center=(cx + off, cy + off)))
    surf.blit(tx, tx.get_rect(center=center))


# =============================================================================
# Game
# =============================================================================
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SW, SH))
        pygame.display.set_caption("GRAVITY FLIP  •  Neon Runner")
        self.clock  = pygame.time.Clock()
        self.state  = MENU
        self._tick  = 0

        self.f_title = pygame.font.SysFont("consolas", 66, bold=True)
        self.f_large = pygame.font.SysFont("consolas", 36, bold=True)
        self.f_med   = pygame.font.SysFont("consolas", 25, bold=True)
        self.f_small = pygame.font.SysFont("consolas", 18)

        self.stars     = StarField()
        self.clouds    = CloudLayer()
        self.particles = ParticleSystem()

        self._snd_flip = make_sound(520, 1000, 0.10, 27000)
        self._snd_die  = make_sound(220,  80, 0.20, 30000)

        cx = SW // 2
        self.btn_play    = Button(cx - 130, 305, 260, 52, "PLAY",    (20, 155,  90))
        self.btn_exit_m  = Button(cx - 130, 370, 260, 52, "EXIT",    (195,  50,  65))
        self.btn_restart = Button(cx - 130, 355, 260, 50, "RESTART", (20, 155,  90))
        self.btn_home    = Button(cx - 130, 415, 260, 50, "HOME",    (50, 120, 200))
        self.btn_exit_g  = Button(cx - 130, 475, 260, 50, "EXIT",    (195,  50,  65))
        # Speed selector left/right arrow buttons (beside speed pill at y=235)
        self.btn_spd_l   = Button(cx - 168, 237, 48, 46, "<",  (25, 120, 185))
        self.btn_spd_r   = Button(cx + 118, 237, 48, 46, ">",  (25, 120, 185))
        self._speed_idx  = 1  # default: NORMAL

        self._best        = 0
        self.player        = None
        self.platforms     = []
        self.hazards       = []
        self.tracker       = None
        self.camera_x      = 0
        self._frontier     = 0
        self._chunk_i      = 0
        self._death_cause  = ""
        self._theme_t          = 0.0   # 0.0 = light  1.0 = dark
        self._theme_dark       = False
        self._theme_going_dark = True  # direction of next crossfade
        self._next_theme_flip  = 350   # first flip at 350 m
        apply_theme(0.0)

    # ------------------------------------------------------------------
    def _new_game(self):
        global AUTO_SPEED
        AUTO_SPEED = SPEEDS[self._speed_idx][1]
        self.camera_x      = 0
        self._frontier     = 0
        self._chunk_i      = 0
        self.platforms     = []
        self.hazards       = []
        self.particles     = ParticleSystem()
        self._death_cause  = ""
        self._theme_t      = 0.0   # start light
        self._theme_dark   = False
        self._theme_going_dark = True  # direction of next transition
        self._next_theme_flip  = 350   # first flip: light->dark at 350 m
        apply_theme(0.0)
        for i in range(5):
            self._gen_chunk(i * CHUNK_WIDTH)
        self.player  = Player()
        self.tracker = ScoreTracker()
        self.tracker.best = self._best
        self.state   = PLAYING

    def _gen_chunk(self, cx):
        ps = Platform.generate_chunk(cx)
        self.platforms.extend(ps)
        if self._chunk_i >= 2:
            self._spawn_hazards(cx, ps)
        self._frontier  = cx + CHUNK_WIDTH
        self._chunk_i  += 1

    def _spawn_hazards(self, cx, platforms):
        mid = [p for p in platforms if 20 < p.rect.y < SH - 60]
        random.shuffle(mid)
        for plat in mid[:SPIKES_PER_CHUNK]:
            cnt = random.randint(2, max(2, plat.rect.width // Spike.SIZE - 1))
            sx  = plat.rect.x + (plat.rect.width - cnt * Spike.SIZE) // 2
            self.hazards.append(Spike(sx, plat.rect.top - Spike.SIZE,
                                      cnt, pointing_up=True))
            self.hazards.append(Spike(sx, plat.rect.bottom,
                                      cnt, pointing_up=False))

        for _ in range(LAVA_PER_CHUNK):
            w = random.randint(90, 220)
            x = cx + random.randint(40, CHUNK_WIDTH - w - 40)
            if random.choice([True, False]):
                y = SH - Platform.HEIGHT - Lava.HEIGHT
            else:
                y = Platform.HEIGHT
            self.hazards.append(Lava(x, y, w))

    def _cull(self):
        cull = self.camera_x - CULL_DISTANCE
        self.platforms = [p for p in self.platforms if p.rect.right > cull]
        self.hazards   = [h for h in self.hazards   if h.rect.right > cull]

    # ------------------------------------------------------------------
    def run(self):
        while True:
            self.clock.tick(FPS)
            self._tick += 1
            self._handle_events()
            self._update()
            self._draw()

    # ------------------------------------------------------------------
    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if self.state == MENU:
                if self.btn_play.is_clicked(ev):    self._new_game()
                if self.btn_exit_m.is_clicked(ev):  pygame.quit(); sys.exit()
                if self.btn_spd_l.is_clicked(ev):
                    self._speed_idx = (self._speed_idx - 1) % len(SPEEDS)
                if self.btn_spd_r.is_clicked(ev):
                    self._speed_idx = (self._speed_idx + 1) % len(SPEEDS)
            elif self.state == PLAYING:
                flip = (ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE) or \
                       (ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1)
                if flip:
                    self.player.flip_gravity()
                    if self._snd_flip: self._snd_flip.play()
            elif self.state == GAME_OVER:
                if self.btn_restart.is_clicked(ev): self._new_game()
                if self.btn_home.is_clicked(ev):     self._go_home()
                if self.btn_exit_g.is_clicked(ev):  pygame.quit(); sys.exit()

    # ------------------------------------------------------------------
    def _update(self):
        self.stars.update()
        self.clouds.update()

        if self.state == MENU:
            self.btn_play.update(); self.btn_exit_m.update()
            self.btn_spd_l.update(); self.btn_spd_r.update()

        elif self.state == PLAYING:
            self.camera_x       += AUTO_SPEED
            self.player.rect.x  += AUTO_SPEED

            self.player.update(self.platforms, self.camera_x)
            self.tracker.update(self.player.rect.centerx)
            if self.tracker.score > self._best:
                self._best = self.tracker.score

            # Alternating theme: light->dark at 350 m, then toggle every 200 m
            if self.tracker.score >= self._next_theme_flip and not self._theme_dark:
                self._theme_dark = True   # start fading toward target
            # Fade toward target (1.0 = dark, 0.0 = light)
            target_t = 1.0 if self._theme_going_dark else 0.0
            if self._theme_dark:
                step = 1 / 90  # ~1.5 s crossfade
                if self._theme_going_dark:
                    if self._theme_t < 1.0:
                        self._theme_t = min(1.0, self._theme_t + step)
                        apply_theme(self._theme_t)
                    elif self.tracker.score >= self._next_theme_flip + 200:
                        # Done fading to dark — schedule next flip back to light
                        self._next_theme_flip += 200
                        self._theme_going_dark = False
                        self._theme_dark = False  # re-arm trigger
                else:
                    if self._theme_t > 0.0:
                        self._theme_t = max(0.0, self._theme_t - step)
                        apply_theme(self._theme_t)
                    elif self.tracker.score >= self._next_theme_flip + 200:
                        # Done fading to light — schedule next flip back to dark
                        self._next_theme_flip += 200
                        self._theme_going_dark = True
                        self._theme_dark = False  # re-arm trigger

            for h in self.hazards: h.update()

            if self.camera_x + GEN_LOOKAHEAD > self._frontier:
                self._gen_chunk(self._frontier)
            self._cull()

            for h in self.hazards:
                if self.player.rect.colliderect(h.rect):
                    self._death_cause = "lava" if isinstance(h, Lava) else "spike"
                    self._die(); return

            if self.player.is_off_screen():
                self._death_cause = "void"; self._die()

        elif self.state == GAME_OVER:
            self.particles.update()
            self.btn_restart.update(); self.btn_home.update(); self.btn_exit_g.update()

    def _die(self):
        if self._snd_die: self._snd_die.play()
        col = LAVA_BRIGHT if self._death_cause == "lava" else \
              SPIKE_GLOW_C if self._death_cause == "spike" else NEON_PINK
        sx = self.player.rect.centerx - self.camera_x
        self.particles.burst(sx, self.player.rect.centery, col, n=55)
        self.state = GAME_OVER

    def _go_home(self):
        """Return to the main menu, resetting theme to light."""
        self._theme_t          = 0.0
        self._theme_dark       = False
        self._theme_going_dark = True
        self._next_theme_flip  = 350
        apply_theme(0.0)
        self.state = MENU

    # ------------------------------------------------------------------
    def _draw(self):
        self.screen.fill(BG_DARK)
        # Clouds — fully visible in light theme, fade away as night falls
        cloud_alpha = int(230 * max(0.0, 1.0 - _THEME_T * 1.5))
        self.clouds.draw(self.screen, cloud_alpha)
        # Scanlines + stars only in dark theme
        if self._theme_t > 0.05:
            for y in range(0, SH, 3):
                a = int(8 * self._theme_t * math.sin(y / SH * math.pi))
                pygame.draw.line(self.screen, (a, 0, a + 6), (0, y), (SW, y))
            self.stars.draw(self.screen)

        if   self.state == MENU:      self._draw_menu()
        elif self.state == PLAYING:   self._draw_playing()
        elif self.state == GAME_OVER: self._draw_gameover()

        pygame.display.flip()

    # ------------------------------------------------------------------
    def _draw_menu(self):
        t  = self._tick
        cx = SW // 2

        # ── Animated top & bottom accent bars ─────────────────────────────
        bar_h = 7
        for xi in range(0, SW, 3):
            frac = (math.sin(xi / SW * math.pi * 2 + t * 0.05) + 1) / 2
            col  = lerp_color((20, 110, 200), (20, 175, 115), frac)
            pygame.draw.line(self.screen, col, (xi, 0),          (xi, bar_h))
            pygame.draw.line(self.screen, col, (xi, SH - bar_h), (xi, SH))

        # ── Solid white card (always readable, any background) ────────────
        card_rect = pygame.Rect(cx - 270, 38, 540, 502)
        pygame.draw.rect(self.screen, (255, 255, 255), card_rect, border_radius=16)
        pygame.draw.rect(self.screen, (25, 120, 190),  card_rect, width=3, border_radius=16)

        # ── Wave-animated title ────────────────────────────────────────────
        title_str = "GRAVITY  FLIP"
        x_cur = cx - self.f_title.size(title_str)[0] // 2
        for i, ch in enumerate(title_str):
            wy   = int(6 * math.sin(t * 0.045 + i * 0.42))
            frac = (math.sin(t * 0.03 + i * 0.38) + 1) / 2
            col  = lerp_color((15, 125, 210), (15, 170, 110), frac)
            cs   = self.f_title.render(ch, True, col)
            self.screen.blit(cs, (x_cur, 52 + wy))
            x_cur += cs.get_width()

        # ── Sub-title ──────────────────────────────────────────────────────
        sub = self.f_med.render("ENDLESS  RUNNER", True, (70, 110, 155))
        self.screen.blit(sub, sub.get_rect(center=(cx, 148)))

        # ── Divider ────────────────────────────────────────────────────────
        pygame.draw.line(self.screen, (190, 215, 235), (cx - 220, 167), (cx + 220, 167), 2)

        # ── Controls hint ─────────────────────────────────────────────────
        tip = self.f_small.render("SPACE or CLICK  =  flip gravity", True, (80, 115, 160))
        self.screen.blit(tip, tip.get_rect(center=(cx, 187)))

        # ── Speed label ───────────────────────────────────────────────────
        slbl = self.f_small.render("SELECT SPEED", True, (50, 90, 140))
        self.screen.blit(slbl, slbl.get_rect(center=(cx, 218)))

        # ── Speed selector row ────────────────────────────────────────────
        spd_label, _ = SPEEDS[self._speed_idx]
        spd_bg_cols = {
            "SLOW":   (220, 245, 228),
            "NORMAL": (215, 238, 252),
            "FAST":   (255, 238, 200),
            "INSANE": (255, 215, 215),
        }
        spd_fg_cols = {
            "SLOW":   (15,  145,  65),
            "NORMAL": (10,  120, 190),
            "FAST":   (185, 105,   5),
            "INSANE": (185,  25,  25),
        }
        spd_bg  = spd_bg_cols.get(spd_label, (235, 235, 235))
        spd_col = spd_fg_cols.get(spd_label, (40,  40,  40))

        sel_rect = pygame.Rect(cx - 108, 235, 216, 50)
        pygame.draw.rect(self.screen, spd_bg,  sel_rect, border_radius=10)
        pygame.draw.rect(self.screen, spd_col, sel_rect, width=2, border_radius=10)
        spd_s = self.f_med.render(spd_label, True, spd_col)
        self.screen.blit(spd_s, spd_s.get_rect(center=sel_rect.center))

        self.btn_spd_l.draw(self.screen)
        self.btn_spd_r.draw(self.screen)

        # ── PLAY / EXIT buttons ───────────────────────────────────────────
        self.btn_play.draw(self.screen)
        self.btn_exit_m.draw(self.screen)

        # ── Best score badge ──────────────────────────────────────────────
        if self._best > 0:
            bs = self.f_small.render(f"BEST  {self._best} m", True, (150, 110, 10))
            bs_r = bs.get_rect(center=(cx, SH - 30))
            pygame.draw.rect(self.screen, (255, 248, 210), bs_r.inflate(22, 12), border_radius=6)
            pygame.draw.rect(self.screen, (195, 155, 15),  bs_r.inflate(22, 12), width=2, border_radius=6)
            self.screen.blit(bs, bs_r)

        # ── Bottom hint ───────────────────────────────────────────────────
        tag = self.f_small.render(
            "Dodge spikes & lava - survive as long as you can",
            True, (100, 135, 165))
        self.screen.blit(tag, tag.get_rect(center=(cx, SH - 13)))

    # ------------------------------------------------------------------
    def _draw_playing(self):
        cam = self.camera_x
        for p in self.platforms:
            p.draw_world(self.screen, cam)
        for h in self.hazards:
            h.draw_world(self.screen, cam)
        self.player.draw(self.screen, cam)

        # --- HUD ---
        # Distance — top-left (plain text in light, panel in dark)
        if _THEME_T < 0.5:
            self.screen.blit(self.f_small.render("DISTANCE", True, (20, 60, 130)), (18, 10))
            self.screen.blit(self.f_med.render(f"{self.tracker.score} m", True, (10, 40, 110)), (18, 27))
        else:
            dp = pygame.Rect(10, 10, 140, 52)
            hud_panel(self.screen, dp, NEON_CYAN)
            self.screen.blit(self.f_small.render("DISTANCE", True, (100, 190, 210)), (18, 14))
            self.screen.blit(self.f_med.render(f"{self.tracker.score} m", True, WHITE), (18, 31))

        # Best — top-right corner (plain text in light, panel in dark)
        if self._best > 0:
            if _THEME_T < 0.5:
                self.screen.blit(self.f_small.render("BEST", True, (20, 100, 20)), (SW - 140, 10))
                self.screen.blit(self.f_med.render(f"{self._best} m", True, (10, 80, 10)), (SW - 140, 27))
            else:
                bp = pygame.Rect(SW - 148, 10, 138, 52)
                hud_panel(self.screen, bp, (120, 160, 100))
                self.screen.blit(self.f_small.render("BEST", True, (130, 180, 115)), (SW - 140, 14))
                self.screen.blit(self.f_med.render(f"{self._best} m", True, (160, 210, 140)), (SW - 140, 31))

        # Gravity indicator — top-centre, plain text only, no box
        if self.player.gravity_dir == 1:
            gtxt = "▼  NORMAL GRAVITY"
            gcol = (20, 60, 150) if _THEME_T < 0.5 else (70, 200, 210)
        else:
            gtxt = "▲  GRAVITY FLIPPED"
            gcol = (160, 55, 15) if _THEME_T < 0.5 else (220, 130, 60)
        gs = self.f_med.render(gtxt, True, gcol)
        self.screen.blit(gs, gs.get_rect(center=(SW // 2, 22)))

        # Bottom hint
        hint_col = (40, 70, 160) if _THEME_T < 0.5 else (60, 60, 110)
        hint = self.f_small.render("SPACE or CLICK = flip gravity", True, hint_col)
        self.screen.blit(hint, hint.get_rect(center=(SW // 2, SH - 13)))

        # Theme-switch flash: show "NIGHT MODE" banner during transition
        if 0.01 < self._theme_t < 0.99:
            fade = math.sin(self._theme_t * math.pi)  # peaks at midpoint
            banner_col = lerp_color((30, 100, 200), (80, 210, 220), self._theme_t)
            banner = self.f_med.render("★  NIGHT MODE UNLOCKED  ★", True, banner_col)
            bs    = pygame.Surface((banner.get_width() + 28, banner.get_height() + 12),
                                   pygame.SRCALPHA)
            bs.fill((0, 0, 0, int(140 * fade)))
            bx = SW // 2 - bs.get_width() // 2
            by = SH // 2 - bs.get_height() // 2
            self.screen.blit(bs, (bx, by))
            alpha_banner = banner.copy()
            alpha_banner.set_alpha(int(255 * fade))
            self.screen.blit(alpha_banner,
                             alpha_banner.get_rect(center=(SW // 2, SH // 2)))

    # ------------------------------------------------------------------
    def _draw_gameover(self):
        cam = self.camera_x
        for p in self.platforms:
            if -p.rect.width < p.rect.x - cam < SW:
                p.draw_world(self.screen, cam)
        for h in self.hazards:
            if -h.rect.width < h.rect.x - cam < SW:
                h.draw_world(self.screen, cam)

        self.particles.draw(self.screen)

        # Dark vignette overlay
        ov = pygame.Surface((SW, SH), pygame.SRCALPHA)
        ov.fill((0, 0, 12, 170))
        self.screen.blit(ov, (0, 0))

        cx = SW // 2
        t  = self._tick

        # Death cause colour + message
        if   self._death_cause == "lava":  dc, dm = LAVA_BRIGHT,   "BURNED BY LAVA"
        elif self._death_cause == "spike": dc, dm = SPIKE_GLOW_C,  "IMPALED ON SPIKE"
        else:                              dc, dm = (170, 170, 210), "FELL INTO THE VOID"

        # ── GAME OVER title  (subtle pulse, no giant glow rect) ──────────
        pulse = 0.5 + 0.5 * math.sin(t * 0.10)
        gc    = lerp_color((200, 80, 110), (230, 120, 140), pulse)
        # thin horizontal accent lines either side (use surface for alpha)
        line_y = 148
        for lx1, lx2 in ((cx - 230, cx - 25), (cx + 25, cx + 230)):
            ls = pygame.Surface((lx2 - lx1, 2), pygame.SRCALPHA)
            ls.fill((*gc, 150))
            self.screen.blit(ls, (lx1, line_y))
        text_shadow(self.screen, self.f_title, "GAME OVER", gc, (cx, 138))

        # ── Cause subtitle ───────────────────────────────────────────────
        dm_s = self.f_med.render(dm, True, dc)
        self.screen.blit(dm_s, dm_s.get_rect(center=(cx, 193)))

        # ── Score panel ──────────────────────────────────────────────────
        sp = pygame.Rect(cx - 185, 218, 370, 100)
        hud_panel(self.screen, sp, NEON_CYAN)
        dl = self.f_small.render("DISTANCE TRAVELLED", True, (130, 190, 210))
        self.screen.blit(dl, dl.get_rect(center=(cx, 240)))
        dist_s = self.f_large.render(f"{self.tracker.score} m", True, WHITE)
        self.screen.blit(dist_s, dist_s.get_rect(center=(cx, 270)))

        # ── New best / best score row ─────────────────────────────────────
        if self.tracker.score >= self._best and self._best > 0:
            # amber text, small glow only on the text surface itself
            nb   = self.f_med.render("NEW BEST!", True, NEON_YELLOW)
            nb_r = nb.get_rect(center=(cx, 332))
            glow_s = pygame.Surface((nb_r.w + 24, nb_r.h + 12), pygame.SRCALPHA)
            pygame.draw.rect(glow_s, (*NEON_YELLOW, 40),
                             glow_s.get_rect(), border_radius=8)
            self.screen.blit(glow_s, (nb_r.x - 12, nb_r.y - 6))
            self.screen.blit(nb, nb_r)
        elif self._best > 0:
            bs = self.f_small.render(f"Best: {self._best} m", True, (180, 165, 100))
            self.screen.blit(bs, bs.get_rect(center=(cx, 332)))

        self.btn_restart.draw(self.screen)
        self.btn_home.draw(self.screen)
        self.btn_exit_g.draw(self.screen)


# =============================================================================
if __name__ == "__main__":
    Game().run()
