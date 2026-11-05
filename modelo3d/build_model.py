"""
Generador del modelo 3D de Rou's Hair Studio (LRS) - Calle Navarro Caro 72, Tomares.
Version 1 deducida de video1.mp4 (fachada) y video2.mp4 (recorrido interior).

Sistema de coordenadas de trabajo (metros):
  x = a lo ancho de la fachada (0 = pared izquierda interior mirando desde la calle)
  d = profundidad (0 = plano de fachada, positivo hacia el fondo del local, negativo = acera)
  h = altura (0 = suelo interior)
Se convierte a glTF (Y arriba) como X=x, Y=h, Z=-d.

Uso:  python build_model.py   ->  rou_studio.glb
"""
import json, math, struct, io, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rou_studio.glb")
rng = np.random.default_rng(7)

# ---------------------------------------------------------------- dimensiones
W = 6.5          # ancho interior
L = 16.0         # fondo interior
H_WHITE = 3.0    # techo blanco
H_BLACK = 2.8    # techo negro (zona delantera, falso techo)
D_BLACK = 4.0    # profundidad de la zona de techo negro
SIDEWALK = -0.15 # cota de la acera
WALL_T = 0.2

# ================================================================ texturas
def tex_floor():
    s = 1024; img = Image.new("RGB", (s, s)); dr = ImageDraw.Draw(img)
    # 1.2 m x 1.2 m  -> lamas 0.2 x 1.2 con junta escalonada
    pw = s // 6
    for i in range(6):
        off = (i % 3) * s // 3
        base = int(rng.integers(200, 226))
        for k in range(2):
            y0 = (off + k * s) % (2 * s) - s
            col = (base, base, base - 3)
            dr.rectangle([i * pw, y0, (i + 1) * pw - 1, y0 + s - 1], fill=col)
        for _ in range(55):  # vetas
            x = i * pw + int(rng.integers(4, pw - 4)); y = int(rng.integers(0, s))
            ln = int(rng.integers(60, 400)); c = int(rng.integers(120, 185))
            dr.line([x, y, x + int(rng.integers(-6, 6)), y + ln], fill=(c, c, c), width=int(rng.integers(1, 4)))
        dr.line([i * pw, 0, i * pw, s], fill=(150, 150, 150), width=2)
    for i in range(6):
        off = (i % 3) * s // 3
        dr.line([i * pw, off, (i + 1) * pw, off], fill=(150, 150, 150), width=2)
    return img.filter(ImageFilter.GaussianBlur(0.8))

def tex_corrugated():
    w, h = 512, 64
    x = np.arange(w)
    ridges = 8
    v = 0.5 + 0.5 * np.sin(x / w * ridges * 2 * np.pi)
    col = (150 + 85 * v).astype(np.uint8)
    arr = np.repeat(col[None, :], h, 0)
    arr = np.stack([arr, arr, (arr * 1.02).clip(0, 255).astype(np.uint8)], -1)
    return Image.fromarray(arr)

def tex_stone():
    s = 512; img = Image.new("RGB", (s, s), (120, 70, 40)); dr = ImageDraw.Draw(img)
    y = 0
    while y < s:
        hh = int(rng.integers(30, 70)); x = -int(rng.integers(0, 80))
        while x < s:
            ww = int(rng.integers(60, 150))
            c = rng.integers(0, 50)
            dr.rectangle([x + 3, y + 3, x + ww - 3, y + hh - 3], fill=(int(170 + c), int(105 + c * 0.7), int(60 + c * 0.4)))
            x += ww
        y += hh
    return img.filter(ImageFilter.GaussianBlur(1.0))

def tex_sidewalk():
    s = 512; img = Image.new("RGB", (s, s), (110, 60, 50)); dr = ImageDraw.Draw(img)
    n = 8; c = s // n  # baldosa de taco 0.4 m -> 8 tacos por 0.4? (5 cm)
    for i in range(n):
        for j in range(n):
            k = int(rng.integers(-12, 12))
            dr.rounded_rectangle([i * c + 5, j * c + 5, i * c + c - 5, j * c + c - 5], 6,
                                 fill=(160 + k, 95 + k, 85 + k))
    return img

def tex_fascia():
    w, h = 512, 256
    yy, xx = np.mgrid[0:h, 0:w]
    v = 0.5 + 0.5 * np.sin(xx / w * 4 * np.pi + np.sin(yy / h * 2 * np.pi) * 1.2)
    col = (70 + 70 * v ** 2).astype(np.uint8)
    return Image.fromarray(np.stack([col, col, col], -1))

def tex_fluted():
    w, h = 256, 32
    x = np.arange(w)
    v = np.abs(np.sin(x / w * 10 * np.pi))
    col = (55 + 40 * v).astype(np.uint8)
    arr = np.repeat(col[None, :], h, 0)
    return Image.fromarray(np.stack([arr, arr, arr + 3], -1))

def tex_wood():
    w, h = 1024, 128
    img = Image.new("RGB", (w, h), (92, 58, 36)); dr = ImageDraw.Draw(img)
    for _ in range(140):
        y = int(rng.integers(0, h)); c = int(rng.integers(-25, 20))
        dr.line([0, y, w, y + int(rng.integers(-4, 4))], fill=(92 + c, 58 + c, 36 + c // 2), width=int(rng.integers(1, 3)))
    return img.filter(ImageFilter.GaussianBlur(0.6))

def font(name, size):
    return ImageFont.truetype(os.path.join("C:/Windows/Fonts", name), size)

def tex_signbox():
    img = Image.new("RGB", (1024, 640), (14, 14, 14)); dr = ImageDraw.Draw(img)
    dr.rectangle([40, 40, 984, 600], outline=(235, 235, 235), width=10)
    dr.text((512, 280), "Rous Studio", font=font("segoesc.ttf", 150), fill=(245, 245, 245), anchor="mm")
    dr.text((512, 470), "HAIR & ESTHETIC", font=font("segoeuib.ttf", 64), fill=(230, 230, 230), anchor="mm")
    return img

def tex_neon():
    img = Image.new("RGBA", (1024, 512), (0, 0, 0, 0)); dr = ImageDraw.Draw(img)
    dr.text((512, 200), "Rous Studio", font=font("segoesc.ttf", 170), fill=(255, 255, 255, 255), anchor="mm")
    dr.text((512, 400), "HAIR & ESTHETIC", font=font("segoeui.ttf", 64), fill=(255, 255, 255, 255), anchor="mm")
    glow = img.filter(ImageFilter.GaussianBlur(6))
    return Image.alpha_composite(glow, img)

def tex_tv():
    img = Image.new("RGB", (512, 288), (12, 14, 22)); dr = ImageDraw.Draw(img)
    dr.text((256, 144), "LRS", font=font("bahnschrift.ttf", 110), fill=(200, 200, 205), anchor="mm")
    return img

def tex_green_sign():
    img = Image.new("RGB", (256, 256), (70, 220, 40)); dr = ImageDraw.Draw(img)
    dr.text((128, 128), "LRS", font=font("arialbd.ttf", 80), fill=(20, 20, 20), anchor="mm")
    return img

TEXTURES = {
    "floor": tex_floor, "corrugated": tex_corrugated, "stone": tex_stone, "sidewalk": tex_sidewalk,
    "fascia": tex_fascia, "fluted": tex_fluted, "wood": tex_wood, "signbox": tex_signbox,
    "neon": tex_neon, "tv": tex_tv, "greensign": tex_green_sign,
}

# ================================================================ materiales
# name: color rgba, metal, rough, texture, tile(m), emissive rgb, strength, alpha
MATS = {
    "suelo":        dict(c=(1, 1, 1, 1), m=0.0, r=0.35, tex="floor", tile=1.2),
    "pared_blanca": dict(c=(0.93, 0.93, 0.92, 1), m=0, r=0.9),
    "techo_blanco": dict(c=(0.95, 0.95, 0.95, 1), m=0, r=0.95),
    "techo_negro":  dict(c=(0.05, 0.05, 0.055, 1), m=0, r=0.8),
    "negro_mate":   dict(c=(0.04, 0.04, 0.045, 1), m=0.1, r=0.6),
    "negro_brillo": dict(c=(0.03, 0.03, 0.035, 1), m=0.3, r=0.25),
    "chapa":        dict(c=(1, 1, 1, 1), m=0.85, r=0.35, tex="corrugated", tile=0.6),
    "piedra":       dict(c=(1, 1, 1, 1), m=0, r=0.9, tex="stone", tile=1.0),
    "acera":        dict(c=(1, 1, 1, 1), m=0, r=0.85, tex="sidewalk", tile=0.4),
    "asfalto":      dict(c=(0.12, 0.12, 0.13, 1), m=0, r=0.95),
    "bordillo":     dict(c=(0.7, 0.7, 0.68, 1), m=0, r=0.8),
    "fachada_sup":  dict(c=(0.55, 0.53, 0.5, 1), m=0, r=0.9),
    "zocalo_gris":  dict(c=(0.72, 0.72, 0.72, 1), m=0, r=0.7),
    "fascia":       dict(c=(1, 1, 1, 1), m=0.8, r=0.45, tex="fascia", tile=1.0),
    "aluminio_negro": dict(c=(0.06, 0.06, 0.07, 1), m=0.6, r=0.4),
    "cristal":      dict(c=(0.75, 0.85, 0.9, 0.18), m=0, r=0.05, alpha=True),
    "espejo":       dict(c=(0.95, 0.97, 1.0, 1), m=1.0, r=0.02),
    "marco_blanco": dict(c=(0.96, 0.96, 0.96, 1), m=0, r=0.4),
    "lamas_gris":   dict(c=(1, 1, 1, 1), m=0.1, r=0.6, tex="fluted", tile=0.6),
    "madera_nogal": dict(c=(1, 1, 1, 1), m=0, r=0.55, tex="wood", tile=2.0),
    "piel_marron":  dict(c=(0.42, 0.2, 0.11, 1), m=0, r=0.45),
    "mostaza":      dict(c=(0.78, 0.55, 0.25, 1), m=0, r=0.5),
    "tostado":      dict(c=(0.76, 0.56, 0.32, 1), m=0, r=0.5),
    "cromo":        dict(c=(0.85, 0.85, 0.88, 1), m=1.0, r=0.15),
    "ceramica":     dict(c=(0.97, 0.97, 0.97, 1), m=0, r=0.15),
    "mueble_blanco": dict(c=(0.95, 0.95, 0.95, 1), m=0, r=0.35),
    "puerta_gris":  dict(c=(0.35, 0.36, 0.38, 1), m=0.1, r=0.5),
    "planta":       dict(c=(0.18, 0.42, 0.16, 1), m=0, r=0.8),
    "planta_clara": dict(c=(0.35, 0.6, 0.2, 1), m=0, r=0.8),
    "maceta":       dict(c=(0.55, 0.55, 0.53, 1), m=0, r=0.8),
    "maceta_ocre":  dict(c=(0.75, 0.5, 0.2, 1), m=0, r=0.6),
    "marmol":       dict(c=(0.85, 0.85, 0.83, 1), m=0, r=0.6),
    "naranja":      dict(c=(1.0, 0.35, 0.05, 1), m=0, r=0.4),
    "producto":     dict(c=(0.15, 0.15, 0.17, 1), m=0.2, r=0.4),
    "producto_bl":  dict(c=(0.9, 0.9, 0.9, 1), m=0.0, r=0.3),
    "split_ac":     dict(c=(0.95, 0.95, 0.95, 1), m=0, r=0.4),
    "rejilla":      dict(c=(0.75, 0.75, 0.75, 1), m=0.3, r=0.6),
    "metal_rack":   dict(c=(0.92, 0.92, 0.92, 1), m=0.4, r=0.4),
    "letrero":      dict(c=(1, 1, 1, 1), m=0, r=0.6, tex="signbox", tile=None, em=(1, 1, 1), es=0.9, emtex=True),
    "neon":         dict(c=(1, 1, 1, 1), m=0, r=0.5, tex="neon", tile=None, em=(1, 1, 1), es=1.4, emtex=True, alpha=True),
    "tv":           dict(c=(1, 1, 1, 1), m=0.2, r=0.2, tex="tv", tile=None, em=(1, 1, 1), es=0.4, emtex=True),
    "cartel_verde": dict(c=(1, 1, 1, 1), m=0, r=0.6, tex="greensign", tile=None),
    "led_blanco":   dict(c=(1, 1, 1, 1), m=0, r=0.5, em=(1, 1, 1), es=2.2),
    "led_calido":   dict(c=(1, 0.8, 0.55, 1), m=0, r=0.5, em=(1.0, 0.72, 0.42), es=1.8),
    "led_rojo":     dict(c=(1, 0.1, 0.08, 1), m=0, r=0.5, em=(1.0, 0.08, 0.05), es=1.8),
    "foco":         dict(c=(1, 1, 1, 1), m=0, r=0.5, em=(1, 0.97, 0.92), es=1.8),
}

# ================================================================ geometria
class Builder:
    def __init__(self):
        self.groups = {}   # group -> material -> [pos, nrm, uv, idx]
        self.cur = "General"

    def group(self, name):
        self.cur = name
        return self

    def _add(self, mat, P, N, UV, I):
        g = self.groups.setdefault(self.cur, {})
        lst = g.setdefault(mat, [[], [], [], [], 0])
        base = lst[4]
        lst[0].append(P); lst[1].append(N); lst[2].append(UV); lst[3].append(np.asarray(I) + base)
        lst[4] += len(P)

    def tri_mesh(self, mat, P, N, UV, I, M=None):
        P = np.asarray(P, float); N = np.asarray(N, float); UV = np.asarray(UV, float)
        if M is not None:
            P = P @ M[:3, :3].T + M[:3, 3]
            N = N @ M[:3, :3].T
        tile = MATS[mat].get("tile", 1.0)
        if tile: UV = UV / tile
        self._add(mat, P, N, UV, I)

    # caja centrada en el origen local con tamanos (sx, sd, sh)
    def box(self, mat, center, size, yaw=0.0, pitch=0.0, roll=0.0, M=None, faces="all"):
        sx, sd, sh = [s / 2 for s in size]
        P, N, UV, I = [], [], [], []
        def quad(o, u, v, n, uw, vw):
            k = len(P)
            for a, b in ((0, 0), (1, 0), (1, 1), (0, 1)):
                P.append(o + a * u + b * v); N.append(n); UV.append((a * uw, b * vw))
            I.extend([k, k + 1, k + 2, k, k + 2, k + 3])
        e = np.eye(3)
        X, D, Hh = e[0], e[1], e[2]
        c = np.zeros(3)
        fs = {
            "+x": (c + [sx, -sd, -sh], D * 2 * sd, Hh * 2 * sh, X, 2 * sd, 2 * sh),
            "-x": (c + [-sx, sd, -sh], -D * 2 * sd, Hh * 2 * sh, -X, 2 * sd, 2 * sh),
            "+d": (c + [sx, sd, -sh], -X * 2 * sx, Hh * 2 * sh, D, 2 * sx, 2 * sh),
            "-d": (c + [-sx, -sd, -sh], X * 2 * sx, Hh * 2 * sh, -D, 2 * sx, 2 * sh),
            "+h": (c + [-sx, -sd, sh], X * 2 * sx, D * 2 * sd, Hh, 2 * sx, 2 * sd),
            "-h": (c + [-sx, sd, -sh], X * 2 * sx, -D * 2 * sd, -Hh, 2 * sx, 2 * sd),
        }
        for k, (o, u, v, n, uw, vw) in fs.items():
            if faces != "all" and k not in faces: continue
            quad(np.array(o, float), u, v, n, uw, vw)
        T = trs(center, yaw, pitch, roll)
        if M is not None: T = M @ T
        self.tri_mesh(mat, P, N, UV, I, T)

    def box_minmax(self, mat, x0, x1, d0, d1, h0, h1, faces="all"):
        self.box(mat, ((x0 + x1) / 2, (d0 + d1) / 2, (h0 + h1) / 2), (x1 - x0, d1 - d0, h1 - h0), faces=faces)

    # plano con textura completa (u 0..1), normal hacia 'normal'
    def panel(self, mat, center, w, h, yaw=0.0, pitch=0.0, flip_u=False, M=None):
        # en local: plano x-h, normal -d (mirando hacia la calle si yaw=0)
        P = [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2), (w / 2, 0, h / 2), (-w / 2, 0, h / 2)]
        uv = [(0, 1), (1, 1), (1, 0), (0, 0)]
        if flip_u: uv = [(1 - a, b) for a, b in uv]
        N = [(0, -1, 0)] * 4
        T = trs(center, yaw, pitch, 0)
        if M is not None: T = M @ T
        self.tri_mesh(mat, P, N, uv, [0, 1, 2, 0, 2, 3], T)

    def cylinder(self, mat, center, r, h, seg=24, yaw=0, pitch=0, roll=0, caps=True, r2=None, M=None):
        r2 = r if r2 is None else r2
        P, N, UV, I = [], [], [], []
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            slope = (r - r2) / h
            n = np.array([ca, sa, slope]); n /= np.linalg.norm(n)
            P.append((r * ca, r * sa, -h / 2)); N.append(n); UV.append((a * r, 0))
            P.append((r2 * ca, r2 * sa, h / 2)); N.append(n); UV.append((a * r, h))
        for i in range(seg):
            k = 2 * i
            I.extend([k, k + 2, k + 3, k, k + 3, k + 1])
        if caps:
            for z, rr, nz in ((-h / 2, r, -1), (h / 2, r2, 1)):
                c = len(P); P.append((0, 0, z)); N.append((0, 0, nz)); UV.append((0, 0))
                for i in range(seg + 1):
                    a = 2 * math.pi * i / seg
                    P.append((rr * math.cos(a), rr * math.sin(a), z)); N.append((0, 0, nz)); UV.append((rr * math.cos(a), rr * math.sin(a)))
                for i in range(seg):
                    if nz > 0: I.extend([c, c + 1 + i, c + 2 + i])
                    else: I.extend([c, c + 2 + i, c + 1 + i])
        T = trs(center, yaw, pitch, roll)
        if M is not None: T = M @ T
        self.tri_mesh(mat, P, N, UV, I, T)

    def sphere(self, mat, center, r, sx=1, sd=1, sh=1, seg=12, rings=8, M=None):
        P, N, UV, I = [], [], [], []
        for j in range(rings + 1):
            v = math.pi * j / rings
            for i in range(seg + 1):
                u = 2 * math.pi * i / seg
                n = np.array([math.sin(v) * math.cos(u), math.sin(v) * math.sin(u), -math.cos(v)])
                P.append(n * r * np.array([sx, sd, sh])); N.append(n); UV.append((u * r, v * r))
        for j in range(rings):
            for i in range(seg):
                a = j * (seg + 1) + i; b = a + seg + 1
                I.extend([a, a + 1, b + 1, a, b + 1, b])
        T = trs(center)
        if M is not None: T = M @ T
        self.tri_mesh(mat, P, N, UV, I, T)

    def torus(self, mat, center, R, r, seg=48, tseg=10, yaw=0, pitch=0, M=None):
        # anillo en el plano x-h (vertical, mirando a -d)
        P, N, UV, I = [], [], [], []
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            for j in range(tseg + 1):
                b = 2 * math.pi * j / tseg
                n = np.array([math.cos(a) * math.cos(b), math.sin(b), math.sin(a) * math.cos(b)])
                p = np.array([(R + r * math.cos(b)) * math.cos(a), r * math.sin(b), (R + r * math.cos(b)) * math.sin(a)])
                P.append(p); N.append(n); UV.append((a, b))
        for i in range(seg):
            for j in range(tseg):
                k = i * (tseg + 1) + j; k2 = k + tseg + 1
                I.extend([k, k2 + 1, k2, k, k + 1, k2 + 1])
        T = trs(center, yaw, pitch)
        if M is not None: T = M @ T
        self.tri_mesh(mat, P, N, UV, I, T)


def trs(pos=(0, 0, 0), yaw=0.0, pitch=0.0, roll=0.0):
    """yaw: giro sobre h (grados). pitch: giro sobre x. roll: giro sobre d."""
    y, p, r = map(math.radians, (yaw, pitch, roll))
    Rz = np.array([[math.cos(y), -math.sin(y), 0], [math.sin(y), math.cos(y), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    Ry = np.array([[math.cos(r), 0, math.sin(r)], [0, 1, 0], [-math.sin(r), 0, math.cos(r)]])
    M = np.eye(4); M[:3, :3] = Rz @ Rx @ Ry; M[:3, 3] = pos
    return M

B = Builder()

# ================================================================ mobiliario parametrico
def hex_ring(cx, cd, h, R, mat="led_blanco", w=0.045, t=0.035):
    """hexagono de 'punta plana' (lados paralelos al eje x)."""
    pts = [(cx + R * math.cos(math.radians(60 * i)), cd + R * math.sin(math.radians(60 * i))) for i in range(6)]
    for i in range(6):
        (x0, d0), (x1, d1) = pts[i], pts[(i + 1) % 6]
        ang = math.degrees(math.atan2(d1 - d0, x1 - x0))
        B.box(mat, ((x0 + x1) / 2, (d0 + d1) / 2, h - t / 2), (R + 0.02, w, t), yaw=ang)

def hex_chain(cells, h, R):
    for (cx, cd) in cells:
        hex_ring(cx, cd, h, R)

def hex_offsets(R):
    # vecinos de un hexagono de punta plana
    return {"n": (0, math.sqrt(3) * R), "ne": (1.5 * R, math.sqrt(3) / 2 * R), "se": (1.5 * R, -math.sqrt(3) / 2 * R)}

def downlight(x, d, h, r=0.07):
    B.cylinder("foco", (x, d, h - 0.004), r, 0.008, seg=20)

def barber_chair(x, d, yaw):
    """sillon de barbero negro capitone. yaw = direccion a la que mira el cliente."""
    M = trs((x, d, 0), yaw)
    B.cylinder("negro_brillo", (0, 0, 0.02), 0.32, 0.04, M=M)
    B.cylinder("cromo", (0, 0, 0.25), 0.06, 0.42, M=M)
    B.box("negro_brillo", (0, 0, 0.5), (0.55, 0.55, 0.14), M=M)
    B.box("negro_brillo", (-0.27, 0, 0.92), (0.12, 0.56, 0.75), pitch=0, roll=-10, M=M)
    B.box("negro_brillo", (-0.31, 0, 1.38), (0.1, 0.3, 0.2), M=M)  # reposacabezas
    for s in (-1, 1):
        B.box("negro_brillo", (0.0, s * 0.31, 0.72), (0.5, 0.08, 0.06), M=M)
        B.box("cromo", (0.12, s * 0.31, 0.62), (0.04, 0.04, 0.18), M=M)
    B.box("cromo", (0.42, 0, 0.28), (0.06, 0.4, 0.04), M=M)  # reposapies
    B.box("negro_brillo", (0.33, 0, 0.36), (0.08, 0.4, 0.22), roll=-30, M=M)

def styling_chair(x, d, yaw):
    """sillon de peinado mostaza con base cromada."""
    M = trs((x, d, 0), yaw)
    B.cylinder("cromo", (0, 0, 0.02), 0.28, 0.03, M=M)
    B.cylinder("cromo", (0, 0, 0.22), 0.045, 0.38, M=M)
    B.box("mostaza", (0, 0, 0.47), (0.52, 0.56, 0.14), M=M)
    B.box("mostaza", (-0.24, 0, 0.75), (0.1, 0.58, 0.48), roll=-8, M=M)
    for s in (-1, 1):
        B.box("mostaza", (-0.02, s * 0.27, 0.64), (0.5, 0.08, 0.22), M=M)

def wash_unit(x, d, yaw):
    """lavacabezas: sillon tostado + pila ceramica detras de la cabeza. yaw = mirada del cliente."""
    M = trs((x, d, 0), yaw)
    B.box("negro_mate", (0, 0, 0.2), (0.7, 0.56, 0.36), M=M)
    B.box("tostado", (0, 0, 0.47), (0.62, 0.56, 0.16), M=M)
    for s in (-1, 1):
        B.box("tostado", (0.0, s * 0.3, 0.45), (0.72, 0.1, 0.5), M=M)
    B.box("tostado", (-0.34, 0, 0.72), (0.12, 0.56, 0.62), roll=-22, M=M)
    B.box("cromo", (-0.62, 0, 0.45), (0.08, 0.08, 0.9), M=M)
    B.cylinder("ceramica", (-0.72, 0, 0.92), 0.26, 0.2, r2=0.3, M=M)
    B.box("ceramica", (-0.62, 0, 0.83), (0.22, 0.4, 0.06), M=M)

def toolchest(x, d, yaw, w=0.62, dep=0.45, h=1.0):
    M = trs((x, d, 0), yaw)
    B.box("negro_brillo", (0, 0, h / 2 + 0.06), (dep, w, h - 0.02), M=M)
    for i in range(5):
        B.box("cromo", (dep / 2 + 0.005, 0, 0.25 + i * 0.17), (0.01, w * 0.8, 0.012), M=M)
    for s in (-1, 1):
        for t in (-1, 1):
            B.cylinder("negro_mate", (s * dep * 0.35, t * w * 0.38, 0.035), 0.035, 0.05, M=M)
    # pequenos productos encima
    for i in range(4):
        B.cylinder("producto", (rng.uniform(-0.12, 0.12), -w / 2 + 0.1 + i * 0.13, h + 0.12), 0.03, 0.14, seg=10, M=M)

def framed_mirror(center, w, h, yaw, frame=0.05, mat_frame="marco_blanco", pitch=0):
    M = trs(center, yaw, pitch)
    B.box(mat_frame, (0, 0.0, 0), (w, 0.04, h), M=M)
    B.box("espejo", (0, -0.022, 0), (w - 2 * frame, 0.005, h - 2 * frame), M=M)

def plant(x, d, h0=0.0, size=1.0, pot="maceta", tall=False):
    B.cylinder(pot, (x, d, h0 + 0.16 * size), 0.16 * size, 0.32 * size, r2=0.19 * size)
    if tall:
        B.cylinder("madera_nogal", (x, d, h0 + 0.7 * size), 0.015, 0.8 * size, seg=6)
        for k in range(6):
            a = k * 1.1
            B.sphere("planta" if k % 2 else "planta_clara", (x + 0.15 * math.cos(a) * size, d + 0.15 * math.sin(a) * size, h0 + (0.9 + 0.12 * k) * size), 0.2 * size, 1, 1, 1.3, seg=8, rings=6)
    else:
        for k in range(5):
            a = k * 1.3
            B.sphere("planta" if k % 2 else "planta_clara", (x + 0.1 * math.cos(a) * size, d + 0.1 * math.sin(a) * size, h0 + (0.45 + 0.05 * k) * size), 0.17 * size, 1, 1, 1.2, seg=8, rings=6)

def sofa(x, d, yaw, length=2.0):
    """sofa de piel marron capitone. yaw: direccion a la que mira el asiento."""
    M = trs((x, d, 0), yaw)
    B.box("piel_marron", (0, 0, 0.3), (0.85, length, 0.22), M=M)
    B.box("piel_marron", (0.03, 0, 0.45), (0.78, length - 0.06, 0.1), M=M)
    B.box("piel_marron", (-0.36, 0, 0.72), (0.18, length, 0.55), roll=-14, M=M)
    for s in (-1, 1):
        B.box("piel_marron", (0, s * (length / 2 - 0.05), 0.48), (0.8, 0.12, 0.2), M=M)
        for t in (-1, 1):
            B.cylinder("cromo", (t * 0.3, s * (length / 2 - 0.12), 0.1), 0.015, 0.2, seg=8, M=M)
    for s in (-0.45, 0.45):
        B.box("piel_marron", (-0.15, s * length / 2, 0.62), (0.18, 0.55, 0.32), roll=-20, M=M)  # cojines

# ================================================================ ESCENA
# ---------------------------------------------------------------- calle
B.group("Calle_Acera")
B.box_minmax("acera", -4.0, 10.5, -4.0, 0.0, SIDEWALK - 0.2, SIDEWALK)
B.box_minmax("bordillo", -4.0, 10.5, -4.15, -4.0, SIDEWALK - 0.35, SIDEWALK)
B.box_minmax("asfalto", -4.0, 10.5, -10.0, -4.15, SIDEWALK - 0.4, SIDEWALK - 0.33)
# zocalo/escalon bajo el escaparate (gris claro) a cota de suelo interior
B.box_minmax("zocalo_gris", -1.0, 5.0, -0.32, 0.0, SIDEWALK, 0.0)
# rampa de acceso frente a la puerta: de la acera (-0.15) a 0.0 en 1.3 m
B.group("Rampa_Acceso")
ang = math.degrees(math.atan2(0.15, 1.3))
B.box("zocalo_gris", (5.75, -0.65, SIDEWALK / 2 - 0.02), (1.5, 1.32, 0.04), pitch=ang)
B.box_minmax("zocalo_gris", 5.0, 6.5, -1.3, 0.0, SIDEWALK - 0.01, SIDEWALK + 0.001, faces=["+h"])

# ---------------------------------------------------------------- fachada
B.group("Fachada")
H_GLASS = 2.75; H_FASCIA = 3.45; H_SOFFIT = 3.55
# machon de piedra izquierdo con contador y caja de luz
B.box_minmax("piedra", -1.0, 0.3, -0.06, 0.0, 0.0, H_FASCIA)
B.box_minmax("piedra", -1.0, -0.8, -0.06, 0.0, SIDEWALK, 0.0)
B.box_minmax("mueble_blanco", -0.85, -0.35, -0.1, -0.06, 0.6, 1.4)  # armario de contadores
B.group("Letrero_Caja_Luz")
B.box_minmax("negro_mate", -0.95, 0.15, -0.2, -0.06, 2.05, 2.75)
B.panel("letrero", (-0.4, -0.205, 2.4), 1.0, 0.6)
# carpinteria del escaparate
B.group("Escaparate")
B.box_minmax("aluminio_negro", 0.3, 0.38, -0.08, 0.0, 0.0, H_GLASS)
B.box_minmax("aluminio_negro", 5.12, 5.24, -0.08, 0.0, 0.0, H_GLASS)
B.box_minmax("aluminio_negro", 0.3, 5.24, -0.08, 0.0, 0.0, 0.06)
B.box_minmax("aluminio_negro", 0.3, 6.5, -0.08, 0.0, H_GLASS - 0.06, H_GLASS)
B.box_minmax("cristal", 0.38, 5.12, -0.045, -0.035, 0.06, H_GLASS - 0.06)
# puerta de cristal (abre hacia fuera, bisagra derecha, tirador a la izquierda)
B.group("Puerta_Entrada")
B.box_minmax("aluminio_negro", 5.24, 5.3, -0.08, 0.0, 0.0, H_GLASS)
B.box_minmax("aluminio_negro", 6.38, 6.5, -0.08, 0.0, 0.0, H_GLASS)
B.box_minmax("aluminio_negro", 5.3, 6.38, -0.07, -0.01, 0.0, 0.08)
B.box_minmax("aluminio_negro", 5.3, 6.38, -0.07, -0.01, 2.3, 2.38)
B.box_minmax("aluminio_negro", 5.3, 5.36, -0.07, -0.01, 0.0, 2.38)
B.box_minmax("aluminio_negro", 6.32, 6.38, -0.07, -0.01, 0.0, 2.38)
B.box_minmax("cristal", 5.36, 6.32, -0.045, -0.035, 0.08, 2.3)
B.box_minmax("cristal", 5.3, 6.38, -0.045, -0.035, 2.38, H_GLASS - 0.06)
B.box("cromo", (5.42, -0.12, 1.05), (0.025, 0.025, 0.9))  # tirador vertical
B.box("cromo", (5.42, -0.09, 0.62), (0.02, 0.06, 0.02)); B.box("cromo", (5.42, -0.09, 1.48), (0.02, 0.06, 0.02))
# machon derecho
B.group("Fachada")
B.box_minmax("pared_blanca", 6.5, 7.0, -0.05, 0.0, 0.0, H_FASCIA)
B.box_minmax("aluminio_negro", 6.5, 6.56, -0.08, 0.0, 0.0, H_GLASS)
B.box_minmax("piedra", 7.0, 8.5, -0.06, 0.0, SIDEWALK, H_FASCIA)
# banda negra + panel metalico ondulado
B.group("Rotulo_Fascia")
B.box_minmax("negro_mate", -1.0, 8.5, -0.12, 0.0, H_GLASS, H_FASCIA)
B.box_minmax("fascia", 0.3, 6.5, -0.16, -0.12, H_GLASS + 0.08, H_FASCIA - 0.06)
# voladizo del edificio y planta superior (simplificada, no se ve en los videos)
B.group("Edificio_Voladizo")
B.box_minmax("techo_blanco", -4.0, 10.5, -1.2, 0.0, H_SOFFIT, H_SOFFIT + 0.25)
B.box_minmax("negro_mate", -4.0, 10.5, -1.24, -1.2, H_SOFFIT - 0.05, H_SOFFIT + 0.3)
for x in (1.5, 4.5):
    downlight(x, -0.6, H_SOFFIT)
B.box_minmax("fachada_sup", -4.0, 10.5, 0.0, 0.25, H_FASCIA, 6.6)
B.box_minmax("piedra", -4.0, -1.0, -0.06, 0.0, SIDEWALK, H_SOFFIT)
B.box_minmax("piedra", 8.5, 10.5, -0.06, 0.0, SIDEWALK, H_SOFFIT)
for x in (0.5, 3.0, 5.5, 8.0):  # ventanas planta 1 (supuestas)
    B.box_minmax("aluminio_negro", x, x + 1.4, -0.02, 0.0, 4.4, 5.8)
    B.box_minmax("cristal", x + 0.05, x + 1.35, -0.03, -0.02, 4.45, 5.75)

# ---------------------------------------------------------------- envolvente interior
B.group("Suelo")
B.box_minmax("suelo", 0.0, W, 0.0, L, -0.05, 0.0)
B.group("Paredes")
B.box_minmax("pared_blanca", -WALL_T, 0.0, 0.0, L + WALL_T, 0.0, H_WHITE)          # izquierda
B.box_minmax("pared_blanca", W, W + WALL_T, 0.0, L + WALL_T, 0.0, H_WHITE)         # derecha
B.box_minmax("pared_blanca", 0.0, W, L, L + WALL_T, 0.0, H_WHITE)                   # fondo
B.box_minmax("pared_blanca", 0.0, 0.3, -0.0, 0.25, 0.0, H_WHITE)                    # machon interior
B.group("Techo_Blanco")
B.box_minmax("techo_blanco", -WALL_T, W + WALL_T, D_BLACK, L + WALL_T, H_WHITE, H_WHITE + 0.1)
B.group("Techo_Negro")
B.box_minmax("techo_negro", -WALL_T, W + WALL_T, 0.0, D_BLACK, H_BLACK, H_BLACK + 0.1)
B.box_minmax("techo_negro", -WALL_T, W + WALL_T, D_BLACK - 0.05, D_BLACK, H_BLACK, H_WHITE)  # tabica
B.box_minmax("techo_negro", -WALL_T, W + WALL_T, 0.0, 0.25, H_GLASS, H_BLACK)                 # dintel interior

# ---------------------------------------------------------------- iluminacion de techo
B.group("LED_Hexagonos_Zona_Negra")
R = 0.42
s3 = math.sqrt(3)
cells = []
for col in range(5):
    for row in range(3):
        cx = 1.0 + col * 1.5 * R
        cd = 0.85 + row * s3 * R + (s3 / 2 * R if col % 2 else 0)
        cells.append((cx, cd))
hex_chain(cells, H_BLACK, R)
hex_chain([(4.6, 1.0), (4.6 + 1.5 * R, 1.0 + s3 / 2 * R), (4.6, 1.0 + s3 * R)], H_BLACK, R)
for x, d in ((2.2, 3.6), (4.3, 3.5), (5.6, 2.8), (0.6, 3.5)):
    downlight(x, d, H_BLACK)

B.group("LED_Hexagonos_Zona_Blanca")
R2 = 0.4
# cadena izquierda (sobre los sillones mostaza) en zigzag hacia el fondo
cadena_izq = []
cx, cd = 2.0, 5.0
for i in range(5):
    cadena_izq.append((cx, cd)); cx += 1.5 * R2 * (1 if i % 2 == 0 else -1); cd += s3 / 2 * R2
cadena_der = []
cx, cd = 4.6, 6.4
for i in range(4):
    cadena_der.append((cx, cd)); cd += s3 * R2
hex_chain(cadena_izq, H_WHITE, R2)
hex_chain(cadena_der, H_WHITE, R2)
hex_chain([(3.0, 11.0), (3.0 + 1.5 * R2, 11.0 + s3 / 2 * R2), (3.0 + 3 * R2, 11.0), (3.0 + 4.5 * R2, 11.0 + s3 / 2 * R2)], H_WHITE, R2)
hex_chain([(4.2, 14.6), (4.2 + 1.5 * R2, 14.6 + s3 / 2 * R2)], H_WHITE, R2)
for x, d in ((1.2, 5.0), (3.4, 5.6), (1.0, 9.5), (3.3, 9.6), (5.6, 9.8), (1.5, 13.5), (3.0, 14.8), (5.5, 13.0), (2.0, 7.4), (5.7, 5.2)):
    downlight(x, d, H_WHITE)

B.group("Climatizacion")
for d in (8.0, 13.0):  # cassettes
    B.box_minmax("split_ac", 2.95, 3.65, d - 0.35, d + 0.35, H_WHITE - 0.04, H_WHITE)
    B.box_minmax("rejilla", 3.1, 3.5, d - 0.2, d + 0.2, H_WHITE - 0.045, H_WHITE - 0.04)
# split de pared sobre los puestos de barberia (pared izquierda)
B.box_minmax("split_ac", 0.0, 0.24, 3.0, 3.85, 2.25, 2.55)
# split de pared en zona negra derecha
B.box_minmax("split_ac", W - 0.24, W, 2.0, 2.85, 2.2, 2.5)

B.group("LED_Cornisa_Calida")
B.box_minmax("led_calido", W - 0.06, W, D_BLACK + 0.1, 10.0, H_WHITE - 0.05, H_WHITE - 0.01)

# ---------------------------------------------------------------- rotulo neon tras el escaparate
B.group("Neon_Rous_Studio")
B.panel("neon", (2.4, 0.35, 2.15), 2.6, 1.3)            # doble cara: se lee desde la calle
for x in (1.3, 3.5):
    B.cylinder("cromo", (x, 0.36, 2.65), 0.004, 0.3, seg=4)

# ---------------------------------------------------------------- recepcion (bloque de lamas junto a la puerta)
B.group("Recepcion")
B.box_minmax("lamas_gris", 4.35, 5.05, 0.35, 1.75, 0.0, 1.12)
B.box_minmax("negro_mate", 4.33, 5.07, 0.33, 1.77, 1.12, 1.16)
plant(4.7, 1.3, 1.16, size=0.7)
B.box("negro_brillo", (4.65, 0.75, 1.3), (0.3, 0.02, 0.25), pitch=-15)  # tablet / tpv
# planta alta junto al cristal (se ve desde la calle)
B.group("Plantas")
plant(4.1, 0.55, 0.0, size=1.0, tall=True)

# ---------------------------------------------------------------- zona espera (pared derecha, junto a la puerta)
B.group("Zona_Espera")
sofa(W - 0.48, 2.15, 180, length=2.0)
B.cylinder("negro_mate", (W - 1.2, 1.0, 0.5), 0.22, 0.02)    # mesita redonda
B.cylinder("negro_mate", (W - 1.2, 1.0, 0.25), 0.012, 0.5, seg=6)
plant(W - 1.2, 1.0, 0.51, size=0.45)
for k in range(3):
    B.cylinder("negro_mate", (W - 0.03, 2.6 + k * 0.18, 1.9), 0.02, 0.06, roll=90, seg=10)  # percheros
# pedestales de piedra con plantas
B.box_minmax("marmol", W - 0.42, W - 0.12, 3.25, 3.55, 0.0, 0.7)
B.box_minmax("marmol", W - 0.42, W - 0.12, 3.6, 3.9, 0.0, 0.55)
plant(W - 0.27, 3.4, 0.7, size=0.6, pot="maceta_ocre")
plant(W - 0.27, 3.75, 0.55, size=0.75, pot="maceta_ocre")

# ---------------------------------------------------------------- pared derecha: pilar + baldas de nogal + espejos apoyados
B.group("Pilar_Derecho")
B.box_minmax("pared_blanca", W - 0.3, W, 4.05, 4.45, 0.0, H_WHITE)
for k in range(6):
    B.sphere("planta", (W - 0.31, 4.25 + (0.05 if k % 2 else -0.05), 0.8 + k * 0.33), 0.05, 1, 1.4, 1.6, seg=6, rings=4)

B.group("Baldas_Nogal")
for hh in (1.25, 1.65, 2.05):
    B.box_minmax("madera_nogal", W - 0.26, W, 4.6, 9.6, hh, hh + 0.035)
    B.box_minmax("led_calido", W - 0.25, W - 0.02, 4.6, 9.6, hh - 0.006, hh)
    for k in range(14):
        dd = 4.8 + k * 0.34 + rng.uniform(-0.05, 0.05)
        mat = "producto_bl" if k % 3 else "producto"
        B.cylinder(mat, (W - 0.12, dd, hh + 0.035 + 0.07), 0.028, 0.14, seg=10)
plant(W - 0.13, 6.2, 2.085, size=0.35)
plant(W - 0.13, 8.6, 1.685, size=0.35)

B.group("Puestos_Espejo_Apoyado")  # espejos de pie apoyados (~8 grados) contra la pared
for dd in (5.7, 8.1):
    M = trs((W - 0.2, dd, 0.0), -90)
    Mt = M @ trs((0, 0, 1.0), 0, -8)
    B.box("marco_blanco", (0, 0, 0), (0.75, 0.04, 2.0), M=Mt)
    B.box("espejo", (0, -0.022, 0), (0.67, 0.005, 1.92), M=Mt)
    barber_chair(W - 1.35, dd, 0)
    B.box_minmax("negro_mate", W - 1.75, W - 0.95, dd - 0.45, dd + 0.45, 0.0, 0.012)  # alfombrilla
    toolchest(W - 0.45, dd + 0.75, 180, w=0.5, dep=0.4, h=0.9)

# ---------------------------------------------------------------- pared izquierda: zona barberia (techo negro)
B.group("Barberia_Aro_Luz")
B.box_minmax("negro_mate", 0.0, 0.03, 0.35, 2.05, 0.0, H_BLACK)
B.torus("led_blanco", (0.06, 1.2, 1.55), 0.32, 0.025, yaw=90)
B.box_minmax("negro_brillo", 0.03, 0.08, 1.9, 2.9, 1.85, 2.45)
B.panel("tv", (0.085, 2.4, 2.15), 0.96, 0.56, yaw=90)
barber_chair(1.1, 1.2, 180)
B.cylinder("cromo", (0.9, 0.7, 0.9), 0.015, 1.8, seg=8)   # brazo/pie de luz
B.group("Barberia_Puestos")
for dd in (2.65, 3.95):
    framed_mirror((0.04, dd, 1.55), 0.62, 1.55, yaw=90, frame=0.04)
    barber_chair(1.1, dd, 180)
    B.box_minmax("negro_mate", 0.75, 1.5, dd - 0.45, dd + 0.45, 0.0, 0.012)
for dd in (3.3, 4.6):
    toolchest(0.28, dd, 0, w=0.55, dep=0.5, h=1.0)
B.box("cromo", (0.5, 3.3, 2.35), (1.0, 0.03, 0.03))  # brazo articulado de luz

# ---------------------------------------------------------------- pared izquierda: tocador corrido con sillones mostaza
B.group("Tocador_Mostaza")
D0, D1 = 5.3, 11.6
B.box_minmax("madera_nogal", 0.0, 0.55, D0, D1, 0.76, 0.8)
B.box_minmax("chapa", 0.5, 0.52, D0, D1, 0.0, 0.76)         # faldon de chapa ondulada (girado)
B.box_minmax("negro_mate", 0.0, 0.5, D0, D1, 0.0, 0.05)
B.box_minmax("espejo", 0.0, 0.015, D0 + 0.05, D1 - 0.05, 0.95, 2.2)
B.box_minmax("aluminio_negro", 0.0, 0.02, D0, D1, 2.2, 2.23)
for i, dd in enumerate((5.95, 7.15, 8.35, 9.55, 10.75)):
    styling_chair(1.05, dd, 180)
    B.cylinder("producto", (0.25, dd - 0.3, 0.88), 0.03, 0.16, seg=10)
    B.cylinder("producto_bl", (0.3, dd - 0.2, 0.86), 0.025, 0.12, seg=10)
B.cylinder("negro_mate", (0.02, 8.4, 2.55), 0.17, 0.03, roll=90)   # reloj
B.cylinder("producto_bl", (0.035, 8.4, 2.55), 0.15, 0.005, roll=90)

# ---------------------------------------------------------------- fondo izquierdo: murete de chapa + puerta aseo
B.group("Murete_Chapa_Fondo")
B.box("chapa", (1.2, 12.6, 0.55), (2.4, 0.06, 1.1), yaw=0)
B.box_minmax("negro_mate", 0.0, 2.4, 12.55, 12.68, 1.1, 1.14)
B.box("chapa", (0.03, 13.6, 0.55), (0.06, 2.0, 1.1))
B.sphere("led_rojo", (0.4, 12.6, 1.25), 0.1)
B.cylinder("cromo", (0.9, 12.3, 0.8), 0.012, 1.6, seg=6)       # lampara de pie (vaporizador)
B.sphere("cromo", (0.9, 12.3, 1.65), 0.16)
B.group("Puerta_Aseo")
B.box_minmax("puerta_gris", 0.0, 0.05, 14.6, 15.5, 0.0, 2.1)
B.box_minmax("aluminio_negro", 0.0, 0.06, 14.55, 14.6, 0.0, 2.15)
B.box_minmax("aluminio_negro", 0.0, 0.06, 15.5, 15.55, 0.0, 2.15)
B.box_minmax("aluminio_negro", 0.0, 0.06, 14.55, 15.55, 2.1, 2.15)
B.box("cromo", (0.08, 15.4, 1.0), (0.04, 0.12, 0.02))

# ---------------------------------------------------------------- pared del fondo: chapa + estanteria + lavacabezas
B.group("Pared_Fondo_Chapa")
B.box_minmax("chapa", 0.6, 3.4, L - 0.04, L, 0.0, H_WHITE)
B.box_minmax("chapa", 3.4, 6.0, L - 0.04, L, 0.0, 2.6)
B.box_minmax("led_rojo", 3.4, 6.0, L - 0.06, L - 0.02, 2.6, 2.63)
B.group("Estanteria_Negra")
x0, x1, h0, h1 = 3.0, 5.4, 1.6, 2.25
B.box_minmax("negro_mate", x0, x1, L - 0.32, L - 0.04, h0, h0 + 0.03)
B.box_minmax("negro_mate", x0, x1, L - 0.32, L - 0.04, h1 - 0.03, h1)
for xx in (x0, (x0 + x1) / 2, x1 - 0.03):
    B.box_minmax("negro_mate", xx, xx + 0.03, L - 0.32, L - 0.04, h0, h1)
B.box_minmax("negro_mate", x0, x1, L - 0.32, L - 0.04, 1.92, 1.95)
for k in range(9):
    B.cylinder("producto" if k < 4 else "producto_bl", (x0 + 0.2 + k * 0.24, L - 0.18, h0 + 0.03 + 0.09), 0.03, 0.18, seg=10)
B.box_minmax("naranja", 4.6, 5.0, L - 0.3, L - 0.1, 1.95, 2.05)
B.box_minmax("negro_mate", 3.25, 3.55, L - 0.06, L - 0.04, 2.3, 2.7)  # cuadro
plant(3.05, L - 0.18, 2.25, size=0.35); plant(5.3, L - 0.18, 2.25, size=0.35)
B.group("Mueble_Lavacabezas")
B.box_minmax("mueble_blanco", 2.9, 5.2, L - 0.5, L - 0.04, 0.0, 0.9)
B.box_minmax("negro_mate", 2.88, 5.22, L - 0.52, L - 0.04, 0.9, 0.93)
B.group("Lavacabezas")
for xx in (3.75, 4.65):
    wash_unit(xx, L - 1.55, -90)
B.group("Estante_Metalico")
for xx in (1.75, 2.35):
    for dd in (L - 0.4, L - 0.08):
        B.box("metal_rack", (xx, dd, 0.55), (0.02, 0.02, 1.1))
for hh in (0.1, 0.5, 0.9):
    B.box_minmax("metal_rack", 1.75, 2.35, L - 0.4, L - 0.08, hh, hh + 0.02)
B.panel("cartel_verde", (2.05, L - 0.42, 1.15), 0.3, 0.3)
plant(2.65, L - 0.3, 0.0, size=1.0, tall=True)
plant(5.9, L - 0.35, 0.0, size=1.1, tall=True)

# ================================================================ escritura GLB
def write_glb(path):
    bin_parts = []; offset = 0
    bufferViews, accessors, meshes, nodes, images, textures = [], [], [], [], [], []
    def add_bv(data, target=None):
        nonlocal offset
        pad = (-len(data)) % 4
        bv = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target: bv["target"] = target
        bin_parts.append(data + b"\x00" * pad); offset += len(data) + pad
        bufferViews.append(bv); return len(bufferViews) - 1
    tex_index = {}
    def get_tex(name):
        if name in tex_index: return tex_index[name]
        img = TEXTURES[name]()
        bio = io.BytesIO(); img.save(bio, "PNG")
        bv = add_bv(bio.getvalue())
        images.append({"bufferView": bv, "mimeType": "image/png", "name": name})
        textures.append({"source": len(images) - 1, "sampler": 0})
        tex_index[name] = len(textures) - 1
        return tex_index[name]
    materials, mat_index = [], {}
    def get_mat(name):
        if name in mat_index: return mat_index[name]
        m = MATS[name]
        pbr = {"baseColorFactor": list(m["c"]), "metallicFactor": m["m"], "roughnessFactor": m["r"]}
        mat = {"name": name, "pbrMetallicRoughness": pbr}
        if m.get("tex"):
            pbr["baseColorTexture"] = {"index": get_tex(m["tex"])}
        if m.get("em"):
            mat["emissiveFactor"] = list(m["em"])
            mat["extensions"] = {"KHR_materials_emissive_strength": {"emissiveStrength": m.get("es", 1.0)}}
            if m.get("emtex"): mat["emissiveTexture"] = {"index": get_tex(m["tex"])}
        if m.get("alpha"):
            mat["alphaMode"] = "BLEND"; mat["doubleSided"] = True
        materials.append(mat); mat_index[name] = len(materials) - 1
        return mat_index[name]
    conv = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)  # (x,d,h) -> (X=x, Y=h, Z=-d)
    for gname, mats in B.groups.items():
        prims = []
        for mname, (Ps, Ns, UVs, Is, _) in mats.items():
            P = np.vstack(Ps) @ conv.T; N = np.vstack(Ns) @ conv.T
            N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
            UV = np.vstack(UVs); I = np.concatenate(Is).astype(np.uint32)
            P = P.astype(np.float32); N = N.astype(np.float32); UV = UV.astype(np.float32)
            a_p = len(accessors); accessors.append({"bufferView": add_bv(P.tobytes(), 34962), "componentType": 5126, "count": len(P), "type": "VEC3", "min": P.min(0).tolist(), "max": P.max(0).tolist()})
            a_n = len(accessors); accessors.append({"bufferView": add_bv(N.tobytes(), 34962), "componentType": 5126, "count": len(N), "type": "VEC3"})
            a_t = len(accessors); accessors.append({"bufferView": add_bv(UV.tobytes(), 34962), "componentType": 5126, "count": len(UV), "type": "VEC2"})
            a_i = len(accessors); accessors.append({"bufferView": add_bv(I.tobytes(), 34963), "componentType": 5125, "count": len(I), "type": "SCALAR"})
            prims.append({"attributes": {"POSITION": a_p, "NORMAL": a_n, "TEXCOORD_0": a_t}, "indices": a_i, "material": get_mat(mname)})
        meshes.append({"name": gname, "primitives": prims})
        nodes.append({"name": gname, "mesh": len(meshes) - 1})
    root = {"name": "Rous_Hair_Studio", "children": list(range(len(nodes)))}
    nodes.append(root)
    gltf = {
        "asset": {"version": "2.0", "generator": "build_model.py (Rou's Hair Studio v1)"},
        "extensionsUsed": ["KHR_materials_emissive_strength"],
        "scene": 0, "scenes": [{"name": "Rous_Hair_Studio", "nodes": [len(nodes) - 1]}],
        "nodes": nodes, "meshes": meshes, "materials": materials, "accessors": accessors,
        "bufferViews": bufferViews, "buffers": [{"byteLength": offset}],
        "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}],
    }
    if images: gltf["images"] = images; gltf["textures"] = textures
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    binary = b"".join(bin_parts)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A)); f.write(js)
        f.write(struct.pack("<II", len(binary), 0x004E4942)); f.write(binary)
    tris = sum(a["count"] for a in accessors if a["type"] == "SCALAR") // 3
    print(f"OK {path}  {total/1e6:.2f} MB  nodos={len(nodes)-1}  materiales={len(materials)}  triangulos={tris}")

if __name__ == "__main__":
    write_glb(OUT)
