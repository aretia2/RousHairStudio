"""
Render fotorrealista (Blender Cycles) del modelo rou_studio.glb.

Uso:
  blender -b -P render_cycles.py -- <vista> <ancho> <alto> <muestras> <salida.png> [--save-blend]
Vistas: entrada, fondo, fachada, diagonal, barberia, espejos, tocador, lavado
"""
import bpy, bmesh, sys, os, math, random
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
VIEW = argv[0] if len(argv) > 0 else "entrada"
RES_X = int(argv[1]) if len(argv) > 1 else 960
RES_Y = int(argv[2]) if len(argv) > 2 else 540
SAMPLES = int(argv[3]) if len(argv) > 3 else 64
OUT = argv[4] if len(argv) > 4 else os.path.join(os.path.dirname(__file__), "renders_realistas", VIEW + ".png")
SAVE_BLEND = "--save-blend" in argv
HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(3)

# vistas en coordenadas del visor (X, Y=altura, Z=-profundidad) -> Blender (X, -Z, Y)
VIEWS = {
    "entrada":  ((3.3, 1.65, -0.9),  (3.0, 1.2, -15), 60),
    "fondo":    ((3.2, 1.6, -15.3),  (3.0, 1.2, 0), 60),
    "fachada":  ((3.2, 1.55, 8.5),   (3.0, 1.7, 0), 50),
    "diagonal": ((-3.2, 1.7, 6.0),   (3.2, 1.6, -1.0), 55),
    "barberia": ((4.6, 1.7, -6.9),   (0.6, 1.2, -1.8), 60),
    "espejos":  ((1.6, 1.6, -3.8),   (6.4, 1.2, -8.5), 60),
    "tocador":  ((5.5, 1.7, -12.5),  (0.4, 1.0, -7.5), 60),
    "lavado":   ((2.2, 1.7, -10.8),  (4.2, 1.0, -16), 60),
}
def to_bl(p): return Vector((p[0], -p[2], p[1]))

# ------------------------------------------------------------------ escena limpia + importacion
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=os.path.join(HERE, "rou_studio.glb"))
scene = bpy.context.scene

# separar cada objeto por material (para tratar plantas, focos, etc. por separado)
meshes = [o for o in scene.objects if o.type == "MESH"]
for o in meshes:
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True); bpy.context.view_layer.objects.active = o
    if len(o.data.materials) > 1:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.separate(type="MATERIAL")
        bpy.ops.object.mode_set(mode="OBJECT")
bpy.ops.object.select_all(action="DESELECT")
# tras separar, cada objeto conserva todas las ranuras: dejar solo el material realmente usado
for o in [o for o in scene.objects if o.type == "MESH"]:
    used = {p.material_index for p in o.data.polygons}
    if len(used) == 1 and len(o.data.materials) > 1:
        keep = o.data.materials[used.pop()]
        o.data.materials.clear(); o.data.materials.append(keep)
        for p in o.data.polygons: p.material_index = 0

def mat_name(o):
    return o.data.materials[0].name.split(".")[0] if o.type == "MESH" and o.data.materials else ""

# ------------------------------------------------------------------ materiales realistas
def principled(m):
    m.use_nodes = True
    for n in m.node_tree.nodes:
        if n.type == "BSDF_PRINCIPLED":
            return n
    return None

def add_bump(m, strength=0.2, distance=0.01, source="noise", scale=300.0, detail=8.0):
    nt = m.node_tree; bsdf = principled(m)
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    if source == "image":
        img = next((n for n in nt.nodes if n.type == "TEX_IMAGE"), None)
        if img is None: return
        nt.links.new(img.outputs["Color"], bump.inputs["Height"])
    else:
        nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
        nz.inputs["Detail"].default_value = detail
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

def rough_variation(m, lo, hi, scale=8.0):
    nt = m.node_tree; bsdf = principled(m)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = scale
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["To Min"].default_value = lo; mr.inputs["To Max"].default_value = hi
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])

def setv(b, name, val):
    if name in b.inputs: b.inputs[name].default_value = val

EMISSION = {"led_blanco": 38.0, "led_calido": 28.0, "led_rojo": 22.0, "foco": 60.0, "neon": 14.0, "letrero": 5.0, "tv": 1.6}

for m in bpy.data.materials:
    base = m.name.split(".")[0]
    b = principled(m)
    if b is None: continue
    if base in EMISSION:
        setv(b, "Emission Strength", EMISSION[base])
        continue
    if base == "suelo":
        setv(b, "Roughness", 0.22); add_bump(m, 0.06, 0.01, "image"); rough_variation(m, 0.12, 0.32, 3.0)
    elif base == "chapa":
        setv(b, "Metallic", 1.0); setv(b, "Anisotropic", 0.6); setv(b, "Roughness", 0.32)
        add_bump(m, 1.0, 0.03, "image")
    elif base in ("pared_blanca", "techo_blanco"):
        setv(b, "Base Color", (0.82, 0.82, 0.81, 1)); setv(b, "Roughness", 0.9); add_bump(m, 0.03, 0.005, "noise", 120)
    elif base == "techo_negro":
        setv(b, "Base Color", (0.025, 0.025, 0.028, 1)); setv(b, "Roughness", 0.75)
    elif base == "espejo":
        setv(b, "Base Color", (0.92, 0.93, 0.94, 1)); setv(b, "Metallic", 1.0); setv(b, "Roughness", 0.0)
    elif base == "cristal":
        setv(b, "Base Color", (0.9, 0.95, 0.95, 1)); setv(b, "Alpha", 1.0); setv(b, "Transmission Weight", 1.0)
        setv(b, "Roughness", 0.0); setv(b, "IOR", 1.5)
        m.blend_method = "OPAQUE" if hasattr(m, "blend_method") else None
    elif base == "piel_marron":
        setv(b, "Base Color", (0.30, 0.12, 0.055, 1)); setv(b, "Roughness", 0.38); setv(b, "Coat Weight", 0.15)
        add_bump(m, 0.25, 0.004, "noise", 900, 4)
    elif base in ("mostaza", "tostado"):
        setv(b, "Roughness", 0.42); setv(b, "Sheen Weight", 0.2); add_bump(m, 0.15, 0.003, "noise", 700, 4)
    elif base == "negro_brillo":
        setv(b, "Base Color", (0.012, 0.012, 0.014, 1)); setv(b, "Roughness", 0.35); setv(b, "Coat Weight", 0.08); add_bump(m, 0.12, 0.003, "noise", 700, 4)
    elif base == "cromo":
        setv(b, "Roughness", 0.06); setv(b, "Base Color", (0.9, 0.9, 0.92, 1))
    elif base == "madera_nogal":
        setv(b, "Roughness", 0.45); add_bump(m, 0.1, 0.004, "image")
    elif base in ("acera", "piedra"):
        setv(b, "Roughness", 0.85); add_bump(m, 0.6, 0.02, "image"); add_bump(m, 0.2, 0.004, "noise", 200)
    elif base == "fascia":
        setv(b, "Metallic", 1.0); setv(b, "Roughness", 0.18); add_bump(m, 0.8, 0.03, "image")
    elif base == "aluminio_negro":
        setv(b, "Roughness", 0.35); setv(b, "Metallic", 0.8)
    elif base in ("planta", "planta_clara"):
        setv(b, "Subsurface Weight", 0.0)
    elif base == "ceramica":
        setv(b, "Roughness", 0.08); setv(b, "Coat Weight", 0.5)
    elif base == "marmol":
        setv(b, "Roughness", 0.3); add_bump(m, 0.3, 0.01, "noise", 25, 12)
    elif base == "lamas_gris":
        add_bump(m, 0.8, 0.02, "image")

# ------------------------------------------------------------------ biselado y suavizado (aristas reales)
NO_BEVEL = {"led_blanco", "led_calido", "led_rojo", "foco", "neon", "letrero", "tv", "cartel_verde", "cristal", "planta", "planta_clara", "espejo", "chapa"}
for o in [o for o in scene.objects if o.type == "MESH"]:
    mn = mat_name(o)
    me = o.data
    try:
        me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(32))
    except Exception:
        pass
    if mn in NO_BEVEL: continue
    bev = o.modifiers.new("Bevel", "BEVEL")
    soft = mn in ("piel_marron", "mostaza", "tostado", "negro_brillo")
    bev.width = 0.03 if soft else 0.004
    bev.segments = 4 if soft else 2; bev.limit_method = "ANGLE"; bev.angle_limit = math.radians(40)
    bev.harden_normals = False

# ------------------------------------------------------------------ vegetacion: hojas reales (geometria) sobre cada mata
from mathutils import Matrix
def leaf_shape(length, width, n=6):
    pts = [(0.0, 0.0, 0.0)]
    for i in range(1, n):
        t = i / n; w = width * math.sin(math.pi * t) ** 0.8; z = 0.15 * length * math.sin(math.pi * t) * t
        pts += [(-w / 2, t * length, z), (w / 2, t * length, z)]
    pts.append((0.0, length, 0.1 * length))
    faces = [(0, 2, 1)] + [(2 * i - 1, 2 * i, 2 * i + 2, 2 * i + 1) for i in range(1, n - 1)] + [(2 * n - 3, 2 * n - 2, 2 * n - 1)]
    return pts, faces

def leaf_material(name, color):
    mat = bpy.data.materials.new(name); mat.use_nodes = True; b = principled(mat)
    setv(b, "Base Color", color); setv(b, "Roughness", 0.42); setv(b, "Coat Weight", 0.15)
    nt = mat.node_tree
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent"); tr.inputs["Color"].default_value = (color[0] * 2, color[1] * 2, color[2] * 1.5, 1)
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs["Fac"].default_value = 0.25
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(b.outputs["BSDF"], mix.inputs[1]); nt.links.new(tr.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat

MAT_LEAF = {"planta": leaf_material("Hoja_oscura", (0.03, 0.09, 0.025, 1)),
            "planta_clara": leaf_material("Hoja_clara", (0.07, 0.17, 0.035, 1))}
for o in [o for o in scene.objects if o.type == "MESH" and mat_name(o) in ("planta", "planta_clara")]:
    kind = mat_name(o)
    src = bmesh.new(); src.from_mesh(o.data); src.faces.ensure_lookup_table()
    faces = [f for f in src.faces if f.calc_area() > 1e-7]
    areas = [f.calc_area() for f in faces]
    total = sum(areas); n = int(min(7000, max(40, total * 900)))
    L = 0.11 if kind == "planta" else 0.15
    pts, fl = leaf_shape(L, L * 0.42)
    out = bmesh.new()
    picks = random.choices(range(len(faces)), weights=areas, k=n)
    for fi in picks:
        f = faces[fi]; c = f.calc_center_median(); nrm = f.normal.copy()
        # punto aleatorio dentro de la cara
        vs = [v.co for v in f.verts]; w = [random.random() for _ in vs]; sw = sum(w)
        p = sum((v * (wi / sw) for v, wi in zip(vs, w)), Vector()) * 0.85 + c * 0.15
        up = nrm.lerp(Vector((0, 0, 1)), 0.35).normalized()
        q = up.to_track_quat("Y", "Z")
        rot = q.to_matrix().to_4x4() @ Matrix.Rotation(random.uniform(-0.6, 0.6), 4, "Y") @ Matrix.Rotation(random.uniform(-0.5, 0.3), 4, "X")
        sc = random.uniform(0.6, 1.25)
        M = Matrix.Translation(p - nrm * 0.03) @ rot @ Matrix.Scale(sc, 4)
        vv = [out.verts.new(M @ Vector(pt)) for pt in pts]
        for fc in fl:
            try: out.faces.new([vv[k] for k in fc])
            except ValueError: pass
    src.free()
    me = bpy.data.meshes.new(o.name + "_hojas"); out.to_mesh(me); out.free()
    for pl in me.polygons: pl.use_smooth = True
    me.materials.append(MAT_LEAF[kind])
    lo = bpy.data.objects.new(o.name + "_hojas", me); lo.matrix_world = o.matrix_world.copy()
    scene.collection.objects.link(lo)
    o.hide_render = True  # la esfera original solo sirve de soporte

# ------------------------------------------------------------------ focos empotrados -> luces de area (spots)
def islands(o):
    bm = bmesh.new(); bm.from_mesh(o.data); bm.faces.ensure_lookup_table()
    seen = set(); res = []
    for f in bm.faces:
        if f.index in seen: continue
        stack = [f]; vs = []; seen.add(f.index)
        while stack:
            g = stack.pop(); vs.extend(v.co.copy() for v in g.verts)
            for e in g.edges:
                for h in e.link_faces:
                    if h.index not in seen: seen.add(h.index); stack.append(h)
        res.append(sum(vs, Vector()) / len(vs))
    bm.free(); return res

for o in [o for o in scene.objects if o.type == "MESH" and mat_name(o) == "foco"]:
    for c in islands(o):
        w = o.matrix_world @ c
        ld = bpy.data.lights.new("Foco", "SPOT"); ld.energy = 22; ld.spot_size = math.radians(110)
        ld.spot_blend = 0.6; ld.shadow_soft_size = 0.05; ld.color = (1.0, 0.95, 0.88)
        lo = bpy.data.objects.new("Foco", ld); lo.location = w - Vector((0, 0, 0.03)); scene.collection.objects.link(lo)

# farola de la calle (luz calida de vapor de sodio/led) y relleno exterior suave
ld = bpy.data.lights.new("Farola", "POINT"); ld.energy = 2500; ld.color = (1.0, 0.72, 0.45); ld.shadow_soft_size = 0.3
lo = bpy.data.objects.new("Farola", ld); lo.location = (-6, 6, 6.5); scene.collection.objects.link(lo)

# mundo: noche azulada tenue
world = bpy.data.worlds.new("Noche"); scene.world = world; world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
bg.inputs["Color"].default_value = (0.012, 0.016, 0.03, 1); bg.inputs["Strength"].default_value = 2.5

# ------------------------------------------------------------------ camara
pos, tgt, fov = VIEWS[VIEW]
cam_d = bpy.data.cameras.new("Camara"); cam_d.sensor_fit = "VERTICAL"; cam_d.angle_y = math.radians(fov)
cam_d.clip_start = 0.05
cam = bpy.data.objects.new("Camara", cam_d); scene.collection.objects.link(cam); scene.camera = cam
cam.location = to_bl(pos)
direction = to_bl(tgt) - to_bl(pos)
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
cam_d.dof.use_dof = True; cam_d.dof.focus_distance = direction.length if VIEW in ("fachada", "diagonal") else min(7.0, direction.length * 0.45); cam_d.dof.aperture_fstop = 5.6

# ------------------------------------------------------------------ Cycles
scene.render.engine = "CYCLES"
cy = scene.cycles
cy.device = "CPU"; cy.samples = SAMPLES; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
cy.use_denoising = True
try: cy.denoiser = "OPENIMAGEDENOISE"
except Exception: pass
cy.max_bounces = 8; cy.diffuse_bounces = 4; cy.glossy_bounces = 4; cy.transmission_bounces = 8
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.sample_clamp_indirect = 8.0; cy.light_sampling_threshold = 0.01
scene.render.resolution_x = RES_X; scene.render.resolution_y = RES_Y; scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
try: scene.view_settings.look = "AgX - Medium High Contrast"
except Exception: pass
scene.view_settings.exposure = -1.6 if VIEW not in ("fachada", "diagonal") else -0.9
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = OUT
os.makedirs(os.path.dirname(OUT), exist_ok=True)

if SAVE_BLEND:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "rou_studio_realista.blend"))
bpy.ops.render.render(write_still=True)
print("RENDER_OK", OUT)
