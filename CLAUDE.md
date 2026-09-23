# MoreFeaturesForFreeCad

FreeCAD addon (Python, PySide/Qt). See [README.md](README.md) for layout and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for design decisions.

## Coding style

Follow [docs/CODING_STYLE.md](docs/CODING_STYLE.md). The single most
important rule in it: minimal comments — code must explain itself through
naming, not narration. Inline comments only for a non-obvious *why*, never
for *what*/*how*.

## CAD logic is built step by step

The user specifies the geometry/modelling approach for each feature. Do not
implement or change CAD backend logic (shape building, document objects,
booleans) beyond what they have explicitly specified and approved.
