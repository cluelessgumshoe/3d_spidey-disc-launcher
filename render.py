"""Blender render of the new parts: one-piece launcher (as worn), watch fit coupon, belt canister with discs.

Run:  blender -b -P render.py
Needs stl/*.stl from `python launcher.py`. Writes images/render_parts.png
"""
import math
from pathlib import Path

import bpy

HERE = Path(__file__).parent
OUT = HERE / "images" / "render_parts.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, rgb, rough=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


RED = material("red", (0.75, 0.08, 0.07))
BLUE = material("blue", (0.08, 0.20, 0.65))
WHITE = material("white", (0.92, 0.92, 0.90), rough=0.3)


def load(path, mat, loc, rot=(0, 0, 0)):
    bpy.ops.wm.stl_import(filepath=str(path))
    ob = bpy.context.selected_objects[0]
    ob.data.materials.append(mat)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    ob.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.update()
    ob.location = loc
    bpy.context.view_layer.update()
    # sit it on the floor
    zmin = min((ob.matrix_world @ v.co).z for v in ob.data.vertices)
    ob.location.z -= zmin
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    return ob


# one-piece STL is in print orientation (launcher side toward -y); turn it launcher side up, as worn
load(HERE / "stl" / "launcher_one_piece.stl", RED, (-50, 0, 0), rot=(-90, 0, 90))
load(HERE / "stl" / "watch_fit_coupon.stl", BLUE, (0, 40, 0))
can = load(HERE / "stl" / "belt_canister.stl", BLUE, (45, 0, 0), rot=(0, 0, 180))
disc = load(HERE / "original" / "Disc.stl", WHITE, (45, 2.5, 0))
disc.location.z = can.dimensions.z - 2.0
disc2 = load(HERE / "original" / "Disc.stl", WHITE, (10, -30, 0))

bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.01))
bpy.context.object.data.materials.append(material("floor", (0.94, 0.94, 0.93), rough=0.8))

bpy.ops.object.camera_add(location=(0, -190, 150))
cam = bpy.context.object
cam.data.lens = 50
target = bpy.data.objects.new("target", None)
target.location = (0, 5, 10)
scene.collection.objects.link(target)
cam.constraints.new("TRACK_TO").target = target
scene.camera = cam

for loc, energy in (((-60, -80, 160), 90000), ((120, 40, 80), 25000)):
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.object
    light.data.energy = energy
    light.data.size = 120
    light.constraints.new("TRACK_TO").target = target

world = bpy.data.worlds.new("world")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.9, 0.9, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
scene.world = world

scene.render.engine = "CYCLES"
scene.cycles.samples = 96
scene.cycles.use_denoising = True
scene.render.resolution_x = 1600
scene.render.resolution_y = 900
scene.view_settings.view_transform = "Standard"
scene.render.filepath = str(OUT)
bpy.ops.render.render(write_still=True)
print("wrote", OUT)
