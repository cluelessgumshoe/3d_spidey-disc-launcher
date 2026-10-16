"""Disc launcher upgrades: stronger wrist plate with Apple Watch band rails, band fit coupon, belt disc canister.

Run:  python launcher.py
Outputs go to ./stl, ./*.3mf and ./images

The wrist plate keeps the exact launcher-side interface of the original DWS_WristMount_Body_v4 (rebuilt from
thin slices because the original mesh has a few holes) and replaces the snap-hook edges, which kept tearing off,
with solid rails that take an Apple Watch band.

Plate coordinates are the original's, in mm: x across the wrist, +y toward the launcher, -y toward the wrist,
z along the forearm. It prints standing on its z = 0 end, same as the original.
"""
from collections import defaultdict
from pathlib import Path
import zipfile

import numpy as np
import trimesh
from manifold3d import CrossSection, FillRule, Manifold, Mesh, OpType

OUT = Path(__file__).parent
SEG = 64
BED = (250, 250)   # Anycubic Kobra 3 V2
SPRINGS = 5        # printed springs, as many as the original print file had

# ---- wrist plate --------------------------------------------------------------
KEEP_X0, KEEP_X1 = 6.8, 44.3   # middle of the original plate that is kept; the hooks lived outside this
RAIL_LEN = 30.0                # along the forearm; open-ended slot so 41 mm and 45 mm bands both fit
RAIL_ANGLE = 20.0              # slot mouth tilts this far toward the wrist so the band wraps down
BOSS_DEPTH = 8.0               # rail block, measured inward from the slot mouth
BOSS_HALF = 5.0                # rail block half height across the mouth
BOSS_R = 1.5
BOSS_CENTER = (2.5, 2.0)       # left rail block centre (x, y); right rail is mirrored
BRIDGE = (5.0, 1.4, 9.0, 5.5)  # x0, y0, x1, y1 block hulled to the rail so it blends into the plate
RAMP = 9.0                     # sloped underside below each rail; the plate prints standing, so no supports

# ---- launcher body fused onto the plate ----------------------------------------
# Measured from the original files: the body's end knuckles pin between the plate's two tabs (both 2.2 mm
# filament-pin holes). Flipped end for end about that pin, the body lies along the plate with zero overlap and
# a 1.27 mm gap under its floor; that gap is filled to join them.
PLATE_PIN = (7.86, 5.0)           # (y, z) of the tab pin hole; x is the plate centre
BODY_PIN = (22.81, 2.8, 66.38)    # (x, y, z) of the knuckle pin hole in DWS_Main_Body_Short_v2
WEB_Z = (9.0, 49.0)               # gap fill runs from past the pin tabs to the end of the plate
WEB_X_SKIP = (17.5, 33.5)         # leave the plate's middle channel and end pocket open (moving parts may use them)

# ---- Apple Watch band slot (cross-section looking along the slot) --------------
# Best estimate of the band connector; print watch_fit_coupon.3mf to check before the plate.
LIP = 1.0          # lip thickness the connector hooks behind
MOUTH = 3.3        # opening the band passes through
CAV_D = 3.6        # cavity depth behind the lip
CAV_H = 4.9        # cavity height
CAV_R = 0.8
FIT = -0.15        # grows (+) or shrinks (-) the whole slot. Coupon v1: -0.15 fits but pulls out; v2 tests tighter
DETENT_D = 1.8     # latch hole width; poke a pin in it to release the band
DETENT_LEN = 4.0   # latch hole is a short slot along the rail so 41 mm and 45 mm bands both click in
LATCH_FROM_END = 11.0   # latch distance from the end of the band connector (about half its length)

# ---- belt canister -------------------------------------------------------------
DISC_D = 30.46     # measured from the original Disc.stl
DISC_T = 3.2
DISCS = 12
BORE = DISC_D + 0.6
WALL = 2.0
FLOOR = 2.0
PUSH_HOLE = 20.0   # finger hole in the floor: push the stack up to pop the top disc out
LIP_ID = DISC_D - 0.7          # top lip the discs snap past
FINGER_H = 8.0     # slit fingers at the rim flex so discs can snap past the lip
FINGER_T = 1.6
SLITS = 4
SLIT_W = 1.2
WINDOW_W = 8.0     # front window shows how many are left
BELT_W = 38.0      # TODO: measure the belt
BELT_T = 4.5       # TODO: measure the belt
BELT_CLEAR = (1.5, 1.0)  # extra (width, thickness) in the belt tunnel
LOOP_WALL = 2.5


def rounded_rect(x0, y0, x1, y1, r):
    sq = CrossSection.square((x1 - x0 - 2 * r, y1 - y0 - 2 * r)).translate((x0 + r, y0 + r))
    return sq.offset(r, circular_segments=SEG)


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def cyl(x, y, z0, z1, r):
    return Manifold.cylinder(z1 - z0, r, r, SEG).translate((x, y, z0))


# ---- original plate, rebuilt -------------------------------------------------
def _loops(seg, tol=1e-4):
    """Chain 2D segments from a mesh slice into closed loops."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol))
    adj = defaultdict(list)
    for i, (a, b) in enumerate(seg):
        adj[key(a)].append((i, 0))
        adj[key(b)].append((i, 1))
    used = np.zeros(len(seg), bool)
    out = []
    for s in range(len(seg)):
        if used[s]:
            continue
        used[s] = True
        poly, start, cur = [seg[s][0], seg[s][1]], key(seg[s][0]), key(seg[s][1])
        while cur != start:
            nxt = [(i, j) for i, j in adj[cur] if not used[i]]
            if not nxt:
                raise ValueError("open loop in slice")
            i, j = nxt[0]
            used[i] = True
            poly.append(seg[i][1 - j])
            cur = key(seg[i][1 - j])
        out.append(np.array(poly[:-1]))
    return out


def original_plate(dz=0.1, same=0.15):
    """The original wrist plate as a clean solid: sliced every dz and re-stacked (its mesh is not watertight).
    Runs of slices that differ by less than `same` mm2 are merged into one extrusion, so only real shape
    changes become steps."""
    m = trimesh.load(OUT / "original" / "DWS_WristMount_Body_v4.stl")
    m.apply_translation(-m.bounds[0])
    runs = []   # [profile, z_start, z_end]
    for z in np.arange(dz / 2, m.bounds[1][2], dz):
        seg = trimesh.intersections.mesh_plane(m, [0, 0, 1], [0, 0, z])
        if not len(seg):
            continue
        cs = CrossSection([p.tolist() for p in _loops(seg[:, :, :2])], FillRule.EvenOdd).simplify(0.005)
        if runs and abs(runs[-1][2] - (z - dz / 2)) < 1e-6:
            prev = runs[-1][0]
            if (prev - cs).area() + (cs - prev).area() < same:
                runs[-1][2] = z + dz / 2
                continue
        runs.append([cs, z - dz / 2, z + dz / 2])
    # runs overlap a hair so the union fuses them; runs that only touch stay separate solids
    eps, z_end = 0.01, runs[-1][2]
    parts = [Manifold.extrude(cs, min(z1 + eps, z_end) - max(z0 - eps, 0)).translate((0, 0, max(z0 - eps, 0)))
             for cs, z0, z1 in runs]
    return Manifold.batch_boolean(parts, OpType.Add), m.bounds[1]


# ---- band slot ------------------------------------------------------------------
def slot_profile(fit=FIT):
    """Slot cross-section in local (u, v): u = depth in from the mouth face, v = across the mouth."""
    mouth = CrossSection.square((LIP + 1.0 + CAV_R, MOUTH + 2 * fit)).translate((-1.0, -MOUTH / 2 - fit))
    cav = rounded_rect(LIP - fit, -CAV_H / 2 - fit, LIP + CAV_D + fit, CAV_H / 2 + fit, CAV_R)
    return mouth + cav


def boss_profile():
    return rounded_rect(0, -BOSS_HALF, BOSS_DEPTH, BOSS_HALF, BOSS_R)


def place(cs, center, angle_deg):
    """Local (u, v) -> plate (x, y). The mouth (u = 0) faces outward along -x, tilted toward -y."""
    # local u points inward (+x when angle is 0), so the boss centre sits at u = BOSS_DEPTH / 2
    return cs.translate((-BOSS_DEPTH / 2, 0)).rotate(angle_deg).translate(center)


def rail(z0, z1, fit=FIT, ramp=0.0, detent_z=None):
    """Left rail: solid block blended into the plate, with the band slot and detent hole cut through.
    ramp > 0 adds a sloped underside below z0 so the rail prints without supports.
    detent_z: where the latch hole goes (default: the middle of the rail)."""
    boss = place(boss_profile(), BOSS_CENTER, RAIL_ANGLE)
    bridge = rounded_rect(*BRIDGE, 1.0)
    body = Manifold.extrude((boss + bridge).hull(), z1 - z0).translate((0, 0, z0))
    if ramp:
        top = Manifold.extrude((boss + bridge).hull(), 0.01).translate((0, 0, z0))
        foot = Manifold.extrude(bridge, 0.01).translate((0, 0, z0 - ramp))
        body += Manifold.hull(top + foot)
    # slot runs out both ends so either band length slides in
    slot = Manifold.extrude(place(slot_profile(fit), BOSS_CENTER, RAIL_ANGLE), z1 - z0 + ramp + 2) \
        .translate((0, 0, z0 - ramp - 1))
    return body - slot - detent((z0 + z1) / 2 if detent_z is None else detent_z)


def detent(z, length=DETENT_LEN):
    """Latch hole across the slot (through both walls), a short slot along the rail centred on z."""
    a = np.radians(RAIL_ANGLE)
    v = np.array([-np.sin(a), np.cos(a)])           # local +v in plate coordinates
    u = np.array([np.cos(a), np.sin(a)])            # local +u (inward)
    c = np.array(BOSS_CENTER) + u * (LIP + CAV_D / 2 - BOSS_DEPTH / 2)
    pin = Manifold.cylinder(4 * BOSS_HALF, DETENT_D / 2, DETENT_D / 2, 24).translate((0, 0, -2 * BOSS_HALF))
    # cylinder axis is z; turn it to lie along v
    ang = np.degrees(np.arctan2(v[1], v[0]))
    pin = pin.rotate((0, 90, 0)).rotate((0, 0, ang))
    run = max(length - DETENT_D, 0) / 2
    pin = Manifold.hull(pin.translate((0, 0, -run)) + pin.translate((0, 0, run)))
    return pin.translate((c[0], c[1], z))


def wrist_plate(ramps_up=False):
    """ramps_up puts the rail ramps on the high-z end, for printing the part the other way up."""
    orig, top = original_plate()
    xc = top[0] / 2
    keep = orig ^ box(KEEP_X0, -10, -1, KEEP_X1, 20, top[2] + 1)
    z0 = top[2] / 2 - RAIL_LEN / 2
    left = rail(z0, z0 + RAIL_LEN, ramp=min(RAMP, z0))
    if ramps_up:   # rail is symmetric about its middle apart from the ramp
        left = left.mirror((0, 0, 1)).translate((0, 0, top[2]))
    right = left.mirror((1, 0, 0)).translate((2 * xc, 0, 0))
    # rounded edge along the cut where there is no rail
    bead_l = Manifold.extrude(CrossSection.circle(2.0, SEG).translate((KEEP_X0 + 0.4, 3.5)), top[2]) ^ orig.hull()
    bead_r = bead_l.mirror((1, 0, 0)).translate((2 * xc, 0, 0))
    plate = Manifold.batch_boolean([keep, left, right, bead_l, bead_r], OpType.Add)
    # re-cut the detents in case the bead or bridge filled them
    plate = plate - detent(z0 + RAIL_LEN / 2) - detent(z0 + RAIL_LEN / 2).mirror((1, 0, 0)).translate((2 * xc, 0, 0))
    return plate


def launcher_body():
    """Original launcher body, placed where it pins onto the plate."""
    m = trimesh.load(OUT / "original" / "DWS_Main_Body_Short_v2.stl")
    m.apply_translation(-m.bounds[0])
    body = Manifold(Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                         tri_verts=np.asarray(m.faces, np.uint32)))
    plate_w = trimesh.load(OUT / "original" / "DWS_WristMount_Body_v4.stl").extents[0]
    return body.translate(tuple(-np.array(BODY_PIN))).rotate((0, 180, 0)) \
        .translate((plate_w / 2, *PLATE_PIN))


def launcher_one_piece():
    """New watch-band plate and the launcher body as one part: no snap hooks, no cuff, no clip-on joint.
    Prints muzzle end down (see print_one_piece), the way the launcher body was designed to print."""
    plate = wrist_plate(ramps_up=True)
    body = launcher_body()
    sides = box(KEEP_X0, -50, WEB_Z[0], KEEP_X1, 50, WEB_Z[1]) - box(WEB_X_SKIP[0], -60, -60, WEB_X_SKIP[1], 60, 120)
    floor_y = (body ^ sides).bounding_box()[1]
    plate_top = (plate ^ sides).bounding_box()[4]
    # copy the body's floor straight down onto the plate; its windows and notches stay open
    # (the floor is not all one height, so take a 2 mm band; anything open through the band stays open)
    skin = body ^ sides ^ box(-50, floor_y, -50, 100, floor_y + 2.0, 120)
    steps = int(np.ceil((floor_y + 2.0 - plate_top) / 0.3)) + 1
    web = Manifold.batch_boolean([skin.translate((0, -0.3 * k, 0)) for k in range(steps)], OpType.Add)
    one = Manifold.batch_boolean([plate, body, web], OpType.Add)
    # the fill seals the two floor windows the old cuff hooks clipped into; keep only the outer shell so they
    # print solid instead of as hidden pockets
    return max(one.decompose(), key=lambda p: p.volume())


def print_one_piece():
    """The one-piece launcher turned muzzle end down for printing."""
    return launcher_one_piece().rotate((180, 0, 0))


# ---- fit coupon ---------------------------------------------------------------------
def watch_fit_coupon(fits=(-0.20, -0.25, -0.30), length=26.0, pitch=16.0, base_h=2.0):
    """Three short rails side by side, slot sizes from loosest to tightest; 1 / 2 / 3 notches on top mark them.
    The base closes the bottom of each slot, so push the band all the way down and it should click.
    v2 (tighter than v1's -0.15 / 0 / +0.15) has a notch in the front edge of the base."""
    parts = []
    for i, f in enumerate(fits):
        r = rail(base_h, base_h + length, f, detent_z=base_h + LATCH_FROM_END).translate((i * pitch, 0, 0))
        for k in range(i + 1):
            r -= box(i * pitch + 3.0 + k * 1.6, 5.5, base_h + length - 1.0, i * pitch + 3.8 + k * 1.6, 12,
                     base_h + length + 1)
        parts.append(r)
    base = box(-6, -4, 0, (len(fits) - 1) * pitch + 9, 7, base_h)
    base -= box(-7, 5.0, -1, -3.0, 8, base_h + 1)   # v2 marker
    return Manifold.batch_boolean(parts + [base], OpType.Add)


# ---- belt canister -------------------------------------------------------------------
def belt_canister():
    """Disc tube with slit-finger snap lip on top, finger push hole in the floor and a belt tunnel at the back.
    Prints upright, open end up; the belt tunnel ceiling is a short bridge."""
    stack = DISCS * DISC_T + 1.0
    h = FLOOR + stack + 1.2
    ro = BORE / 2 + WALL
    tube = cyl(0, 0, 0, h, ro)
    tube -= cyl(0, 0, FLOOR, h + 1, BORE / 2)
    tube -= cyl(0, 0, -1, FLOOR + 1, PUSH_HOLE / 2)
    # snap lip at the very top, ramped on both sides so discs push in from above and out from below
    lip = cyl(0, 0, h - 1.6, h, BORE / 2 + 0.1)
    below = Manifold.cylinder(0.85, BORE / 2, LIP_ID / 2 - 0.02, SEG).translate((0, 0, h - 1.65))
    above = Manifold.cylinder(0.85, LIP_ID / 2, LIP_ID / 2 + 0.64, SEG).translate((0, 0, h - 0.8))
    tube += lip - (below + above + cyl(0, 0, h - 1.7, h - 1.6, BORE / 2))
    # thin the wall around the fingers so they flex, then slit them
    tube -= cyl(0, 0, h - FINGER_H, h + 1, ro + 1) - cyl(0, 0, h - FINGER_H - 1, h + 2, BORE / 2 + FINGER_T)
    for k in range(SLITS):
        s = box(-SLIT_W / 2, 0, h - FINGER_H, SLIT_W / 2, ro + 2, h + 1)
        tube -= s.rotate((0, 0, 45 + k * 360 / SLITS))
    # front window (+y is away from the belt)
    tube -= box(-WINDOW_W / 2, 0, FLOOR + 3, WINDOW_W / 2, ro + 2, h - FINGER_H - 2)
    # belt tunnel at the back (-y), running along x
    bw, bt = BELT_W + BELT_CLEAR[0], BELT_T + BELT_CLEAR[1]
    lh = max(h, bw + 2 * LOOP_WALL)
    lw = 2 * ro
    back = -ro + 1.0
    loop = box(-lw / 2, back - bt - 2 * LOOP_WALL, 0, lw / 2, back, lh) \
        - box(-lw / 2 - 1, back - bt - LOOP_WALL, LOOP_WALL, lw / 2 + 1, back - LOOP_WALL, LOOP_WALL + bw)
    web = box(-ro * 0.6, back - 0.5, 0, ro * 0.6, -ro + 4.0, h) - cyl(0, 0, FLOOR, h + 1, BORE / 2)
    return Manifold.batch_boolean([tube, loop, web], OpType.Add)


# ---- export ---------------------------------------------------------------------
def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=False)


def pack(tms, bed=BED, gap=8.0, margin=10.0):
    """Shelf-pack meshes (already in print orientation) onto the bed; returns (x, y) offsets for each min corner."""
    order = sorted(range(len(tms)), key=lambda i: -tms[i].extents[1])
    spots, x, y, row_d = [None] * len(tms), margin, margin, 0.0
    for i in order:
        w, d = tms[i].extents[:2]
        if x + w > bed[0] - margin and x > margin:
            x, y, row_d = margin, y + row_d + gap, 0.0
        if y + d > bed[1] - margin:
            raise ValueError(f"plate is full; part {i} does not fit")
        spots[i] = (x, y)
        x, row_d = x + w + gap, max(row_d, d)
    # centre the whole layout on the bed
    used = [max(s[0] + t.extents[0] for s, t in zip(spots, tms)), max(s[1] + t.extents[1] for s, t in zip(spots, tms))]
    shift = ((bed[0] - used[0] - margin) / 2, (bed[1] - used[1] - margin) / 2)
    return [(sx + shift[0], sy + shift[1]) for sx, sy in spots]


def write_3mf(path, parts, bed=BED):
    """Plain 3MF (geometry only) with the parts packed onto the bed.
    parts: list of (name, Manifold or trimesh) already in print orientation."""
    tms = [(name, m if isinstance(m, trimesh.Trimesh) else to_trimesh(m)) for name, m in parts]
    spots = pack([tm for _, tm in tms], bed)
    objects, items = [], []
    for i, ((name, tm), (sx, sy)) in enumerate(zip(tms, spots), start=1):
        (x0, y0, z0) = tm.bounds[0]
        tx, ty, tz = sx - x0, sy - y0, -z0
        verts = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in tm.vertices)
        tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tm.faces)
        objects.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{verts}</vertices>'
                       f'<triangles>{tris}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {tx:.4f} {ty:.4f} {tz:.4f}"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<resources>{"".join(objects)}</resources><build>{"".join(items)}</build></model>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def _mesh_xml(tm):
    verts = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in tm.vertices)
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tm.faces)
    return f"<mesh><vertices>{verts}</vertices><triangles>{tris}</triangles></mesh>"


def plate_origin(index, count, bed=BED):
    """Where plate `index` sits in a multi-plate project: the grid Bambu Studio based slicers
    (Anycubic Slicer Next, OrcaSlicer) lay plates out on, 1/5 of a bed apart."""
    root = count ** 0.5
    cols = int(round(root)) + (1 if root > round(root) else 0)
    col, row = index % cols, index // cols
    return col * bed[0] * 1.2, -row * bed[1] * 1.2


def write_project_3mf(path, plates_by_name, bed=BED):
    """One 3MF with every plate, in the Bambu Studio project layout (3D/Objects + Metadata/model_settings.config),
    so opening it as a project in Anycubic Slicer Next / OrcaSlicer / Bambu Studio brings in all plates at once."""
    files, objects, items, settings, plate_xml = {}, [], [], [], []
    oid = 0
    for p_i, (plate_name, parts) in enumerate(plates_by_name.items()):
        tms = [(name, m if isinstance(m, trimesh.Trimesh) else to_trimesh(m)) for name, m in parts]
        ox, oy = plate_origin(p_i, len(plates_by_name), bed)
        instances = []
        for (name, tm), (sx, sy) in zip(tms, pack([tm for _, tm in tms], bed)):
            oid += 2
            sub = f"3D/Objects/object_{oid // 2}.model"
            files[sub] = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                          '<model unit="millimeter" xml:lang="en-US" '
                          'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
                          f'<resources><object id="{oid - 1}" type="model">{_mesh_xml(tm)}</object></resources>'
                          '<build/></model>')
            objects.append(f'<object id="{oid}" type="model"><components>'
                           f'<component p:path="/{sub}" objectid="{oid - 1}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>'
                           '</components></object>')
            (x0, y0, z0) = tm.bounds[0]
            t = (ox + sx - x0, oy + sy - y0, -z0)
            items.append(f'<item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 {t[0]:.4f} {t[1]:.4f} {t[2]:.4f}" printable="1"/>')
            settings.append(f'<object id="{oid}"><metadata key="name" value="{name}"/><metadata key="extruder" value="1"/>'
                            f'<part id="1" subtype="normal_part"><metadata key="name" value="{name}"/>'
                            '<metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/></part></object>')
            instances.append(f'<model_instance><metadata key="object_id" value="{oid}"/>'
                             f'<metadata key="instance_id" value="0"/><metadata key="identify_id" value="{100 + oid}"/>'
                             '</model_instance>')
        plate_xml.append(f'<plate><metadata key="plater_id" value="{p_i + 1}"/>'
                         f'<metadata key="plater_name" value="{plate_name}"/><metadata key="locked" value="false"/>'
                         f'{"".join(instances)}</plate>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
             'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
             'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">'
             '<metadata name="Application">BambuStudio-01.09.00.70</metadata>'
             '<metadata name="BambuStudio:3mfVersion">1</metadata>'
             '<metadata name="Title">Spidey disc launcher fork</metadata>'
             f'<resources>{"".join(objects)}</resources><build>{"".join(items)}</build></model>')
    model_rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                  '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                  + "".join(f'<Relationship Target="/{f}" Id="rel-{i + 1}" '
                            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
                            for i, f in enumerate(files))
                  + '</Relationships>')
    config = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>' + "".join(settings) + "".join(plate_xml) + '</config>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                     '<Default Extension="config" ContentType="text/xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
        z.writestr("3D/_rels/3dmodel.model.rels", model_rels)
        for f, xml in files.items():
            z.writestr(f, xml)
        z.writestr("Metadata/model_settings.config", config)


def original_part(name):
    return trimesh.load(OUT / "original" / "parts" / f"{name}.stl")


def disc():
    return trimesh.load(OUT / "original" / "Disc.stl")


def plates(made):
    """Print plates, one 3MF each, grouped by filament color. made: the generated parts by name."""
    return {
        "plate1_any_color_fit_test": [("watch_fit_coupon", made["watch_fit_coupon"])],
        "plate2_red_launcher": [("launcher_one_piece", made["launcher_one_piece"]),
                                ("Link2_Cap", original_part("Link2_Cap")),
                                ("Link3_Pad", original_part("Link3_Pad"))],
        "plate3_black_mechanism": [(n, original_part(n)) for n in
                                   ("Slider", "Slider_Retainer", "Pusher_A", "Pusher_B", "Link2_Lever", "Link3",
                                    "SpringLockPin")]
                                  + [(f"Spring_{i + 1}", original_part("Spring")) for i in range(SPRINGS)],
        "plate4_red_discs": [(f"Disc_{i + 1}", disc()) for i in range(DISCS)],
        "plate5_black_belt_canister": [("belt_canister", made["belt_canister"])],
        "optional_plate_only": [("wrist_plate", made["wrist_plate"])],
    }


def main():
    (OUT / "stl").mkdir(exist_ok=True)
    designs = {"launcher_one_piece": print_one_piece, "wrist_plate": wrist_plate,
               "watch_fit_coupon": watch_fit_coupon, "belt_canister": belt_canister}
    made = {}
    for name, fn in designs.items():
        m = fn()
        assert m.status().name == "NoError", (name, m.status())
        assert len(m.decompose()) == 1, (name, "has loose pieces or hidden pockets")
        tm = to_trimesh(m)
        print(f"{name:18s} size {np.round(tm.extents, 1)} mm  volume {m.volume():.0f} mm3  watertight {tm.is_watertight}")
        made[name] = m
    every = plates(made)
    write_project_3mf(OUT / "spidey_launcher_all_plates_kobra3.3mf", every)
    print(f"all plates -> spidey_launcher_all_plates_kobra3.3mf ({len(every)} plates)")
    # the same plates one file each, as a fallback, plus an STL of every part
    (OUT / "plates").mkdir(exist_ok=True)
    for name, parts in every.items():
        write_3mf(OUT / "plates" / f"{name}_kobra3.3mf", parts)
        print(f"  {name:28s} {len(parts):2d} parts")
        for part_name, m in parts:
            tm = m if isinstance(m, trimesh.Trimesh) else to_trimesh(m)
            stem = part_name.rsplit("_", 1)[0] if part_name.rsplit("_", 1)[-1].isdigit() else part_name
            tm.export(OUT / "stl" / f"{stem}.stl")


if __name__ == "__main__":
    main()
