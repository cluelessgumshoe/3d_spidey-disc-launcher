"""Mark III upgrades: MechBrick's Spidey Disc Launcher Mark III (4-disc cartridge) on an Apple Watch band.

Run:  python mk3/mk3.py
Outputs go to mk3/stl and mk3/*.3mf

The wrist base keeps MechBrick's launcher-side shape exactly (the body snaps between its two end walls).
Only the outside of the end walls changes: the strap slots are filled and each wall gets a band rail with the
slot opening facing straight down, so the base still prints flat and the band drops down the sides of the wrist.

Base coordinates are the original's, in mm: x along the forearm, y across the wrist, z up (wrist side at z = 0).
"""
import sys
from pathlib import Path

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, Mesh, OpType

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "mk1"))
import launcher as L   # noqa: E402  shared slot shape, latch settings and 3MF writers from the MK-I fork (mk1/)

# ---- band rails on the wrist base ------------------------------------------------
FIT = -0.10        # flat-printed slot; the standing MK-I coupon liked -0.20. Set from coupon v3
RAIL_LEN = 30.0    # along the forearm, centred on the base
RAIL_WALL = 2.6    # material either side of the band cavity
RAIL_TOP = 8.6     # rail block height above the bed
SLOT_Y = -4.2      # slot centre, measured out from the base's outer face (y = 0)
HULL_INTO = (0.0, 6.5, 0.0, 9.6)   # y0, y1, z0, z1: outer part of the end wall (the strap bars) the rail is
                                   # hulled into; down to the bed so the joint has no overhang. The launcher snaps
                                   # onto the inner legs of the walls, from y = 8 in, which stay untouched


def load(name):
    m = trimesh.load(HERE / "original" / name)
    m.apply_translation(-m.bounds[0])
    solid = Manifold(Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
    # some originals are several overlapping shells (the base's raised lettering); fuse them into one solid
    return Manifold.batch_boolean(solid.decompose(), OpType.Add), m.extents


def yz_prism(cs, x0, x1):
    """Extrude a 2D profile drawn in (y, z) along x from x0 to x1."""
    m = Manifold.extrude(cs, x1 - x0)                      # (a, b, c) = (y, z, along)
    return m.transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], float))


def slot_yz(fit):
    """MK-I band slot turned so the mouth faces straight down (-z) at the bed, centred on y = SLOT_Y."""
    return L.slot_profile(fit).rotate(90).translate((SLOT_Y, 0))


def rail_block(x0, x1):
    half = L.CAV_H / 2 + RAIL_WALL
    boss = L.rounded_rect(SLOT_Y - half, 0, SLOT_Y + half, RAIL_TOP, 1.2)
    y0, y1, z0, z1 = HULL_INTO
    wall = L.rounded_rect(y0, z0, y1, z1, 1.0)
    return yz_prism((boss + wall).hull(), x0, x1)


def latch_hole(x):
    """Latch slot across the band cavity (along y, through the outer wall), centred at x."""
    d, run = L.DETENT_D, max(L.DETENT_LEN - L.DETENT_D, 0) / 2
    z = L.LIP + L.CAV_D / 2
    pin = Manifold.cylinder(14, d / 2, d / 2, 24).rotate((90, 0, 0)).translate((0, SLOT_Y + 7, z))
    return Manifold.hull(pin.translate((x - run, 0, 0)) + pin.translate((x + run, 0, 0)))


STOP = 1.5         # solid end that closes the slot, like the base of the MK-I coupon


def rail(x0, x1, fit=FIT):
    """One side's rail at the y = 0 face: slot closed by a STOP-thick end at x0, open at x1,
    latch slot LATCH_FROM_END in from the stop (same as the coupons)."""
    body = rail_block(x0, x1)
    slot = yz_prism(slot_yz(fit), x0 + STOP, x1 + 1)
    return body - slot - latch_hole(x0 + STOP + L.LATCH_FROM_END)


def watch_base():
    base, ext = load("WristBase.stl")
    xc, w = ext[0] / 2, ext[1]
    x0 = xc - RAIL_LEN / 2
    near = rail(x0, x0 + RAIL_LEN)
    far = near.mirror((0, 1, 0)).translate((0, w, 0))
    return Manifold.batch_boolean([base, near, far], OpType.Add)


# ---- fit coupon v3 (prints flat, like the base) -----------------------------------
def watch_fit_coupon_v3(fits=(-0.20, -0.10, 0.0), length=26.0, pitch=24.0):
    """Three short rails lying flat, slot mouths down on the bed, closed at one end with the latch slot 11 mm in.
    1 / 2 / 3 notches on top = tightest (-0.20) to loosest (0.0). Two notches in the spine mark it as v3."""
    parts = []
    for i, f in enumerate(fits):
        r = rail(0, length, f).translate((0, i * pitch, 0))
        for k in range(i + 1):
            r -= L.box(length - 3.0 - k * 1.8, i * pitch + 3.0, RAIL_TOP - 0.8, length - 2.2 - k * 1.8, i * pitch + 10, RAIL_TOP + 1)
        parts.append(r)
    spine = L.box(0, -1.0, 0, 4.0, (len(fits) - 1) * pitch + 7.0, 3.0)
    spine -= L.box(1.0, -2, 1.8, 1.6, 1.0, 4) + L.box(2.4, -2, 1.8, 3.0, 1.0, 4)   # v3 marker
    return Manifold.batch_boolean(parts + [spine], OpType.Add)


def original(name):
    return trimesh.load(HERE / "original" / f"{name}.stl")


DISCS = 12   # three cartridge loads


def plates(made):
    """Print plates grouped by filament color, in MechBrick's print orientations. Everything in plain PLA."""
    pair = lambda n: [(f"{n}_{i + 1}", original(n)) for i in range(2)]
    return {
        "plate1_any_color_fit_test_v3": [("watch_fit_coupon_v3", made["watch_fit_coupon_v3"])],
        "plate2_red_launcher": [(n, original(n)) for n in
                                ("Body", "Pusher", "Trigger_Lever", "Trigger_PalmPad", "Trigger_Button")],
        "plate3_black_cartridges": pair("Cartridge_Body") + pair("Cartridge_Clip_C") + pair("Cartridge_Clip_D")
                                   + pair("Cartridge_LoadingCover"),
        "plate4_black_springs_and_pins": pair("Launch_Spring_Y") + [("Return_Spring_printed", original("Return_Spring_printed"))]
                                         + pair("Assembly_part"),
        "plate5_red_wrist_base": [("wrist_base_watchband", made["wrist_base_watchband"])],
        "plate6_any_color_discs": [(f"Disc_small_{i + 1}", original("Disc_small")) for i in range(DISCS)],
    }


def main():
    (HERE / "stl").mkdir(exist_ok=True)
    made = {"wrist_base_watchband": watch_base(), "watch_fit_coupon_v3": watch_fit_coupon_v3()}
    for name, m in made.items():
        assert m.status().name == "NoError", (name, m.status())
        assert len(m.decompose()) == 1, (name, "has loose pieces or hidden pockets")
        tm = L.to_trimesh(m)
        print(f"{name:22s} size {np.round(tm.extents, 1)} mm  volume {m.volume():.0f} mm3  watertight {tm.is_watertight}")
    every = plates(made)
    L.write_project_3mf(HERE / "mk3_all_plates_kobra3.3mf", every)
    print(f"all plates -> mk3_all_plates_kobra3.3mf ({len(every)} plates)")
    (HERE / "plates").mkdir(exist_ok=True)
    for name, parts in every.items():
        L.write_3mf(HERE / "plates" / f"{name}_kobra3.3mf", parts)
        print(f"  {name:32s} {len(parts):2d} parts")
        for part_name, m in parts:
            tm = m if isinstance(m, trimesh.Trimesh) else L.to_trimesh(m)
            stem = part_name.rsplit("_", 1)[0] if part_name.rsplit("_", 1)[-1].isdigit() else part_name
            tm.export(HERE / "stl" / f"{stem}.stl")
    return made


if __name__ == "__main__":
    main()
