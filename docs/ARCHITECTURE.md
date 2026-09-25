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
- The panel never touches geometry. It hands `builder.commitBosses()` a
  `BossRequest` (sketch, target part, parameters, ignored point indices).
- Adding a feature: a `<feature>/` package (parameters + builder), a
  command module, a panel, and one line in `registry.py`. Pieces that are
  not feature-specific (`schema.py`, `fieldform.py`, `pointpicker.py`,
  `sketchpoints.py`) are shared.

## Decisions to make before the boss backend

### Decided

- **PartDesign only.** The wizard works on a sketch inside a PartDesign
  Body, and that Body is the target. The Part workbench is not supported.
- **One feature in the tree.** The wizard edits a single
  `PartDesign::FeatureAdditivePython` in the Body's feature chain, like a
  Pad. It absorbs its sketch the way a Pad does, and double-clicking it
  reopens the wizard. The internal steps never appear in the tree.
- **The feature exists while the wizard is open**, as with a Pad: opening
  the wizard creates it (or, when editing, starts from it) inside one
  transaction. OK commits that transaction, Cancel aborts it, so a new
  feature disappears again and an edited one is restored. This is what
  lets the length, angle and count inputs bind to the feature's
  properties through `Gui.ExpressionBinding`, taking expressions (e.g. a
  VarSet's variables) exactly like FreeCAD's own inputs. Checkboxes,
  choices and the per-instance rotations and skipped gussets take plain
  values only.
- **Live preview while the wizard is open.** Every input change (debounced)
  writes the request into the feature and recomputes that feature alone,
  with a hidden, unsaved `IsPreviewing` flag set. In preview the feature
  skips the fuse and the base fillet: its shape is a compound of the
  base shape and the placed bosses, each bored on its own. The panel
  shows only the boss feature meanwhile. OK clears the flag and runs the
  full document recompute; Cancel restores the previous visibility.
- **Build sequence, in memory on every recompute.** Nothing is stored
  between recomputes, so nothing depends on FreeCAD's fragile topological
  names; edges to fillet are found by geometry, never by name.
  1. Template (`boss/geometry.py`), in a local frame (base on the origin,
     axis +Z): drafted boss → all kept gussets at once (profile extruded
     along the gusset angle, no pattern) → gussets cut off below z = 0 and
     above their height cap → inset → top fillet on the boss's top rim.
  2. In the Body (`boss/feature.py`): for each non-ignored point, copy the
     template for its skipped gussets, rotate it about its axis by the instance's offset, and place
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
- **Skipped gussets**, stored per sketch point as indices into the gusset
  pattern. A skipped gusset leaves a gap; the others keep their angles.
  Bosses leaving out the same gussets share one template, and the base
  fillet expects two gusset-to-boss edges per kept gusset. A boss with
  any gusset skipped is meant to be anchored by hand, so it gets only
  those gusset-to-boss fillets, no base fillet. Indices beyond the gusset
  count are dropped when the wizard commits.
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

- **Opened without the addon**, a feature's code does not load, so FreeCAD
  would silently keep its last saved shape through every later change.
  Each feature therefore carries a read-only `RequiredAddon` property bound
  to an expression on `RequiresMoreFeaturesForFreeCadAddon`, a property the
  addon adds on load and never saves. Without the addon the expression
  cannot resolve, so the first recompute that reaches the feature marks it
  invalid and stops everything after it. It still opens showing its saved
  shape, and a copy saved without the addon stays broken, loudly, even once
  the addon is back.

### Still open

1. **Validation.** Which input combinations are impossible depends on the
   geometry, so it comes with the backend. The panel can then list
   problems live and block OK on errors.

## Not implemented yet

- Rib settings (the `Ribs` support mode shows no fields yet).

## Rib Wizard

A rib is the inverse of the mould maker's cut: a cutter is run along every
line of the path sketch, and the volume it sweeps becomes the rib. The path
lines are the cutter's centre, so ribs come out wider than the sketch and
with rounded ends. The cutter's taper is the rib's draft.

### Decided

- **PartDesign only, one feature in the tree**, absorbing its path sketch
  and editing inside one transaction, exactly like the boss feature.
- **The cutter is picked, not drawn:** a ball, flat or corner radius tip,
  its size (ball radius; or tip diameter and corner radius), a taper angle
  of 0–45° per side from the cutter axis, and the rib height from the
  sketch plane to the rib top. The corner radius is at most half the tip
  diameter.
- **The corner radius cutter's tip diameter** is measured where its flanks,
  carried on past the corner radius, meet the tip plane. With a taper, the
  flat of its tip is therefore narrower than the tip diameter.
- **The path lines mark the rib's centre line at its base**, in the sketch
  plane, which is also the cutter's axis. The panel shows the resulting rib
  width at the base.
- **The tapered ball cutter's silhouette is the gusset profile**: an arc
  tangent to two drafted flanks. The rib backend is to share that profile
  with the boss gussets.

### Still open

- The rib backend: shape building, and the live preview. Until then the
  feature passes the Body's shape on unchanged.
- The vertical fillet where ribs meet or cross: its radius is already an
  input and saved, but not built.
