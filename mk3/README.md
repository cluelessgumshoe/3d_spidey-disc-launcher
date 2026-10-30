# Mark III on a watch band (v2, in progress)

Remix of [Spidey Disc Launcher Mark-III (Quick-Eject)](https://makerworld.com/en/models/3182162-spidey-disc-launcher-mark-iii-quick-eject) by MechBrick: the 4-disc removable cartridge version. Our MK-I fork is in [`../mk1/`](../mk1/README.md).

## What's different from MechBrick's Mark III

- **Watch band wrist base.** Same base, same launcher side (checked: identical volume inside the end walls), but the strap bars on the outside of each end wall are filled and a band rail is added there. The band slot opens straight down so the base still prints flat, and the band drops down the sides of the wrist. Replaces the base, both straps and the lock.
- Everything else is MechBrick's files, unchanged, laid out on plates.

## Still to do

- **Metal return spring.** You'd rather use the metal 5.5 x 38 mm spring than the printed zigzag return spring. The body has room for it (about 7.4 mm of height under the built-in support), but how the pusher, spring and body hook together isn't clear from the files alone. Easiest path: build it once with the printed spring, then swap.

## Print plates

**Open `mk3_all_plates_kobra3.3mf` as a project** (single-plate files are in `plates/`, STLs of every part in `stl/`).

| Plate | Color | What's on it |
|---|---|---|
| 1 `plate1_any_color_fit_test_v3` | any | Band fit coupon v3, printed flat like the base. 1 / 2 / 3 notches on top = -0.20 / -0.10 / 0.00. **Print this first.** |
| 2 `plate2_red_launcher` | red | Launcher body, pusher, trigger lever, palm pad, trigger button |
| 3 `plate3_black_cartridges` | black | Two cartridges: bodies, clips C and D, loading covers |
| 4 `plate4_black_springs_and_pins` | black | Two Y launch springs, printed return spring, two sprues of printed pins |
| 5 `plate5_red_wrist_base` | red | Watch band wrist base |
| 6 `plate6_any_color_discs` | any | 12 small discs (24.4 mm), three cartridge loads |

Your MK-I discs (30.5 mm) don't fit the Mark III.

## Before printing

1. **Band fit:** print plate 1, push the band all the way in from the open end and tug. Set `FIT` in `mk3.py` to the one that clicks and holds, then rerun. (The MK-I coupon printed standing up liked -0.20; flat printing usually comes out a bit tighter, so this one goes looser.)
2. **Built-in supports:** MechBrick's body has thin built-in supports; remove them before assembly.

## Print settings

- **Plain PLA for everything** (MechBrick: not PETG, not matte or silk), especially the launch springs.
- Print MechBrick's parts with the settings from the Mark III page (0.2 mm layers).
- The base prints flat as laid out, no supports.

## Changing the design

```bash
python mk3/mk3.py
```

Uses the slot shape, latch settings and 3MF writers from `../mk1/launcher.py`.

## Credits

Remix of MechBrick's Spidey Disc Launcher Mark-III. Check its license on the model page before sharing; this remix uses the same license.
