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
  some gussets skipped is meant to be anchored by hand, so it gets only
  those gusset-to-boss fillets, no base fillet. A boss with all gussets
  skipped is a plain boss and gets the base fillet. Indices beyond the gusset
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

- **Boss type**: a thread boss (a screw threads into its blind bore) or a
  screw head boss (the screw passes through; its head sits in a bore from
  below). Both stand on the sketch plane with the same reference point,
  the sketch point on the face they grow from, so the template, gussets
  and base fillet are shared; only the cutter differs.
- **The boss is sized by its wall thickness where the wall is thinnest**,
  not by its base diameter: around the bore entry at the top of a thread
  boss, around the screw seat of a screw head boss (with no thread bore,
  it is the top radius). That is where the boss is weakest and most loaded
  (thread-forming hoop stress at the entry, the clamp load at the seat),
  and screw makers' boss guidelines size it there too. The outer draft
  only thickens the wall further down, so height and draft changes never
  thin the critical wall. The base diameter (the footprint, which the
  gussets reach out from) and the wall thickness at the base (where sink
  marks come from) follow, and the panel shows both. Files saved while the
  base diameter drove the boss have it converted to the wall thickness
  that gives the same boss.
- **Screw head cutter**, cut once after the fuse like the bore: the screw
  bore from the boss top (diameter measured there) down to the screw seat,
  `topWallThickness` below the top, and the screw seat bore
  (`screwSeatDiameter`, measured at the seat) from there on through the
  part. Each has its own draft, both widening downwards so one core pulls
  out through the bottom. The screw bore runs on below the seat inside the
  wider screw seat bore, so the two pieces never share a face; how far is
  capped at half the flat seat's width, which keeps it inside even with
  steep drafts.
  - The **entry chamfer** (45°, where the screw bore opens into the seat)
    is a cone that meets the screw bore wall exactly `entryChamferSize`
    above the seat; with draft, its width on the seat is a hair wider.
  - The **screw seat fillet** rounds the screw seat bore tool's top rim, so
    the part gets a rounded inside corner where the seat meets the bore
    wall.
  - The chamfer and the fillet must leave a flat ring between them for the
    screw head to press against, and the chamfer must be shallower than
    the top wall.
- **Part thickness below a screw head boss is measured**, not entered and
  not picked as a face (a picked face would depend on topological names):
  a line from the sketch point along the boss axis downwards is intersected
  with the Body's previous shape, and the material span starting at the
  sketch point (chained if split) ends at the part's bottom face. The
  screw seat bore ends there and the rubber pad cutout, a plain cylinder,
  is sunk into it. A sketch point with no material directly below is an
  error. With no previous shape the thickness is 0.
- **Rubber pad cutout** must be shallower than the part is thick below the
  boss, or it would break through.
- **Screw head preview** also cuts the Body's previous shape with the
  cutters, since the screw seat bore and the rubber pad cutout lie mostly
  in the part, where a boss-only preview would not show them.
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

- Ribs as boss supports (the `Ribs` tile is disabled).

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
  tangent to two drafted flanks. Both are built by `cutterprofile.py`,
  which also covers the flat and corner radius tips.
- **Path edges are lines and arcs** (full circles included). Another curve
  type is an error. An arc must be wider than the rib is at its base, or
  its inner flank would fold over the arc's centre.
- **The rib is the exact volume the cutter sweeps**, built in memory on
  every recompute from pieces that meet on shared flat faces, then fused
  into the Body's previous shape in one boolean:
  1. every edge sweeps the cutter's whole silhouette (drawn in the plane
     across the edge at its start, tip at the rib height, foot on the
     sketch plane): extruded along a line, revolved about an arc's centre;
  2. every point where edges end gets a wedge of the revolved cutter for
     each gap wider than half a turn between the directions its edges
     leave in. An edge running on through the point, like the bar of a T,
     counts both ways. So a loose end gets a half cutter, a corner a wedge
     on its outside only, and a tangent join or a T nothing.
  The pieces are fused and refined into the ribs, which are the feature's
  `AddSubShape`. Paths crossing mid-way are junctions too, with each
  crossing path leaving both ways.
- **The rib crossings fillet is a toolpath, not a fillet**: OpenCascade's
  fillet fails where two ball tips cross, since the concave edge between
  them fades out flat at the top. Instead, in every inside corner
  (narrower than half a turn) the cutter also runs along an arc from path
  to path, whose radius is the fillet radius plus half the rib's base
  width, so the rib wall is rounded with the fillet radius at its base.
  Above, the rounding grows as the rib narrows, and a ball tip can leave a
  dip in the top, as it would in the mould.
  - The arc is not quite tangent: it cuts into each path by 1% of the
    fillet radius, a kink of about 8° at the rib wall. Exactly tangent, a
    ball cutter's sweeps touch along a whole cross-section and the fuse
    fails.
  - In a sharp corner the arc can pass so far from the corner that steel
    would stand between it and the paths down to the base; the cutter then
    also runs along the bisector from the corner to the arc. A corner too
    sharp for one such pass, or a path too short to reach the arc, is an
    error naming the fillet radius.
  - The ribs without fillets are fused first. The fillet sweeps are fused
    into them and the result is checked: valid, a plausible volume, and
    every fillet sweep inside it (a boolean can silently drop a piece).
    A failed check retries with a slightly different overlap, and only
    then reports an error.
- **Live preview as in the boss wizard**: the same hidden `IsPreviewing`
  flag (`preview.py`), the Body's previous shape and the fused ribs as a
  compound, no fuse into the part.
- **Visibility while editing** (both wizards, `featurevisibility.py`): the
  feature alone is shown while the wizard is open. Cancel restores nothing
  by hand, because aborting the transaction also undoes visibility
  changes, including PartDesign hiding the previous tip when a feature is
  created.

### Still open

- Nothing for the ribs.

## Sketch Mirror

Not a wizard and not a feature: one command that edits the sketch being
edited in the Sketcher, in one transaction. It keeps the preselection as
the elements to mirror and waits for the mirror line to be clicked, since
the Sketcher's own Symmetric constraint only relates geometry that has
already been drawn.

### Decided

- **Copy plus constraints, no own geometry math at recompute.** Each
  element is copied once, reflected, and tied to its original with
  sketcher constraints; from then on the solver keeps it mirrored.
  FreeCAD's `SketchObject.addSymmetric()` is not used: its Python binding
  never adds the symmetry constraints, and it crashed FreeCAD 1.1.3.
- **Constraints per element**, as FreeCAD's own C++ mirror sets them:
  a point is `Symmetric` to its copy, a line both end points, a circle
  its centre plus `Equal`, an arc both end points plus `Equal`. An arc's
  copy runs the other way round, so its start mirrors the original's end.
  Nothing else is copied: constraints between the originals already hold
  the copies in place through the symmetry.
- **A point on the mirror line is `Coincident` with its copy**, not
  `Symmetric`: symmetry of two coincident points about the line is
  degenerate and the solver reports a conflict. Coincident also closes a
  mirrored half profile at the line. A point that only happens to lie on
  the line when mirroring stays coincident with its copy afterwards.
- **Arc copies are nudged by 1e-6 mm**: their centre is moved along the
  chord bisector, with both end points kept exact. On an exact copy of a
  half circle (a slot end) the centre lies on the chord, where `Equal`
  has no slope, and the solver flags a constraint as redundant (the same
  singularity FreeCAD nudges its own arc copies for, issue #13551). The
  radius error this leaves is far below the solver's tolerance, so the
  solver never pulls the centre back exactly, even through later edits.
- **Prompting without a task panel**: the Sketcher's own panel stays
  open, so the command has none. While it waits, *Click mirror line*
  follows the cursor over the 3D view (`cursorhint.py`, a child of the
  main window polled to the cursor, since Wayland does not let an
  application place tool tip windows), and the status bar says the same.
- **Mirror lines**: sketch lines (construction or not), external edges
  that are lines, and the H and V axes. Mirroring about a point is not
  supported.
- **Mirrored**: points, lines, circles and arcs. Ellipses, conics and
  B-splines carry internal alignment geometry and are skipped with a
  warning; internal alignment geometry selected on its own is ignored.

### Still open

- Ellipses, conics and B-splines.
