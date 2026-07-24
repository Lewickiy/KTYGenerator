# Procedural KTY Generator

Procedural Blender Python generator for cardboard transport boxes (КТЯ). It creates geometry, materials, metadata, optional `.blend` exports, and PNG renders without external models or textures.

## Visual states

- `closed`: top flaps are flat in transport position.
- `open`: four independent top flaps rotate outward, the lighter inner cardboard material is visible, and the open rim reads as an empty box.
- `damaged`: flaps sag asymmetrically, wall panels are slightly misaligned, dark crushed corner dents and jagged tear strips are added so damage is visible in the final render.

## Usage

```bash
blender --background --python main.py -- --quality high --state open --size 600x400x400 --seed 42
blender --background --python main.py -- --quality ultra-high --state damaged --damage-level 0.85
```

For metadata-only validation outside Blender:

```bash
python3 launcher.py --quality high --state damaged --no-export --no-render
```

Exports are written to `exports/`; renders are written to `renders/`.
