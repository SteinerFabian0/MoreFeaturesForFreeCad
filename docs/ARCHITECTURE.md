# Architecture

## Shape of the addon

Every feature is a **wizard**: a command opens a task panel, the panel
collects a complete, self-contained request, and a backend turns that
request into document objects. The three layers only meet at two seams:

```
command (commands/)  ->  task panel (taskpanels/)  ->  builder (<feature>/builder.py)
   selection checks        editing a parameter set       CAD logic
```

- A feature's inputs live in one dataclass plus a `ParameterField` schema
  (`boss/parameters.py`). The panel form is generated from the schema,
  and the backend should mirror the same schema onto its document object
  as FreeCAD properties, so an input is declared once and appears in the
  panel, the property view and the saved file alike. A module-level
  check fails at import if the dataclass and the schema drift apart.
- The panel never touches geometry. It hands `builder.buildBosses()` a
  `BossRequest` (sketch, target part, parameters, ignored point indices).
- Adding a feature: a `<feature>/` package (parameters + builder), a
  command module, a panel, and one line in `registry.py`. Pieces that are
  not feature-specific (`schema.py`, `fieldform.py`, `pointpicker.py`,
  `sketchpoints.py`) are shared.

## Decisions to make before the boss backend

### Decided

- **PartDesign only.** The wizard works on a sketch inside a PartDesign
  Body, and that Body is the target. The Part workbench is not supported.
- **One feature in the tree.** OK creates a single
  `PartDesign::FeatureAdditivePython` in the Body's feature chain, like a
  Pad. It absorbs its sketch the way a Pad does, and double-clicking it
  reopens the wizard. The internal steps never appear in the tree.
- **Build sequence, in memory on every recompute.** Nothing is stored
  between recomputes, so nothing depends on FreeCAD's fragile topological
  names; edges to fillet are found by geometry, never by name.
  1. Template (`boss/geometry.py`), in a local frame (base on the origin,
     axis +Z): drafted boss → all gussets at once (profile extruded along
     the gusset angle, no pattern) → gussets cut off below z = 0 and above
     their height cap → inset → top fillet on the boss's top rim.
  2. In the Body (`boss/feature.py`): for each non-ignored point, copy the
     template, rotate it about its axis by the instance's offset, and place
     it with the sketch's placement, so the sketch normal is the boss axis
     → fuse all copies into the Body's previous shape in one boolean →
     boss base fillet on the fused result → bores cut into the fused result.
- **Bore** is cut once, after the fuse, into every boss. It starts at the
  boss top, narrows by the bore draft and ends flat. Its depth is at most
  0.6 mm more than the boss height (larger values are clamped), so it may
  cut into the part below the boss. A bore diameter of 0 means no bore.
- **Gusset profile** (as in `ExampleFiles/BossWithGussets.FCStd`): drawn in
  the vertical plane at the gusset's outer end, ridge arc top on z = 0,
  arc width = gusset base thickness, sides drafted outward, bottom at
  least 3 × boss height below z = 0, and always deep enough that the bottom
  edge stays below z = 0 over the gusset's whole run (steep gussets would
  otherwise leave a gap underneath and come loose from the boss).
- **Per-instance rotation offset** (phase), stored per sketch point. It
  turns only gussets or ribs, since the boss body is round.
- **Bore diameter** is measured at the bore entry (top). **Bore bottom**
  is flat.
- **Boss base fillet** is one fillet with one radius, on the fused
  result: the chain where each boss (and its gussets) meets the face it
  stands on, plus both flat sides of every gusset where they meet the boss
  wall. Separate base and gusset fillets fail when their radii are equal,
  since each would roll into the other's rounded corner. Edges are found
  by geometry: the placed template footprint bordering an upward-facing
  flat face in the sketch plane, and edges between the boss's round wall
  and a sloped flat face (exactly two per gusset, else an error). The
  sketch must lie on the face the bosses stand on. A boss hanging over the
  part's edge leaves an open chain, which does not fillet.
- **Gusset angle** is 20–70°. Shallower, only the rounded ridge reaches the
  boss; steeper, drafted gussets grow wide enough to swallow the boss wall.
- **Gusset height** = base length × tan(angle), capped 0.5 mm below the
  boss top. That top 0.5 mm stays a plain round rim, so the top fillet
  always runs around a single circle.
- **Instances are keyed by sketch geometry id** (`getGeometryId`), not
  geometry index. Deleting an element renumbers every later index, but
  never an id. So: a new point gets a boss with no rotation, a moved point
  keeps its settings, and a deleted point's settings are dropped. Only a
  point that is deleted and redrawn counts as new.

### Still open

1. **Validation.** Which input combinations are impossible depends on the
   geometry, so it comes with the backend. The panel can then list
   problems live and block OK on errors.

## Not implemented yet

- Rib settings (the `Ribs` support mode shows no fields yet).
- Visual marking of ignored points in the 3D view. Once a live preview
  exists, ignored bosses simply disappear.
- Expression binding (`Gui.ExpressionBinding`) on the quantity fields.
  It needs the feature object.
