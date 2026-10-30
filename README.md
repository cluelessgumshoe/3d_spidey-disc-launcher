# Spidey disc launchers on an Apple Watch band

Remixes of MechBrick's Spidey disc launchers for my son's costume: the launcher fused into one solid piece with a wrist plate that takes an Apple Watch band, plus a belt holder for spare discs.

| Folder | What it is | Status |
|---|---|---|
| [`mk1/`](mk1/README.md) | [Spidey Disc Launcher MK-I](https://makerworld.com/en/models/575061-spidey-disc-launcher-mk-i): single shot, 30.5 mm discs, metal return spring. One-piece launcher, belt canister (dispenser with cap). | v1 printed and worn (git tag `mk1-v1`); v2 ready to print |
| [`mk3/`](mk3/README.md) | [Spidey Disc Launcher Mark-III](https://makerworld.com/en/models/3182162-spidey-disc-launcher-mark-iii-quick-eject): 4-disc quick-eject cartridge, 24.4 mm discs. Watch band wrist base. | In progress |

Each folder has its own README, generator script, print plates (`*_all_plates_kobra3.3mf`, one 3MF with every plate) and STLs.

```bash
pip install numpy trimesh manifold3d
python mk1/launcher.py
python mk3/mk3.py
```

`mk3/mk3.py` reuses the band slot shape and 3MF writers from `mk1/launcher.py`.

Both originals are by MechBrick and licensed CC BY-NC-SA (check each model page); these remixes use the same license: credit MechBrick, not for sale.
