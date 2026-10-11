# MoreFeaturesForFreeCad

Wizards that turn multi-step modelling chores into one parametric feature,
configured in a task panel the way SolidWorks feature wizards are.

> **Alpha.** Expect breaking changes; files made with one version may not
> open cleanly in the next. Requires FreeCAD 1.1 or newer.

Anyone opening a file that uses these features needs this addon installed.
Without it the part still shows its last saved shape, but the feature can't
rebuild: the first recompute that reaches it fails with an error naming
this addon (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)). To share a
part with someone who doesn't have the addon, export it as STEP.

Status: the **Boss Wizard** task panel is in place — point selection,
ignoring instances, and every boss/bore/inset/gusset setting. Pressing OK
creates one `Boss` feature in the Body: drafted boss, gussets, inset and
top fillet, placed on every point, fused into the part, filleted into it
and bored. Double-clicking the feature reopens the wizard to edit it. The
**Rib Wizard** grows drafted ribs along the lines and arcs of a sketch,
filleted where they meet or cross. **Pocket Push** pushes a drafted
cavity into the part through every closed outline of a sketch, wrapped in
walls of constant thickness. **Hole Fill** fills the closed perimeter of
a sketch with round holes in a hexagonal pattern, as for a perforated
speaker grille. **Sketch Mirror** mirrors sketch
elements about a line, as copies held symmetric by constraints. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the build
sequence and what is still to be decided.

## Boss Wizard

PartDesign only.

1. In a PartDesign Body, draw a sketch on the face the bosses grow from.
   Every **point** in it marks one boss.
2. Select the sketch and run **Boss Wizard** (More Features toolbar/menu,
   or search it from the S-menu in any workbench).
3. Pick the boss type: **Thread**, a boss a screw threads into, or
   **Screw head**, a boss the screw passes through, with its head seated
   in a bore that opens through the part's bottom face. Below come the
   bore and boss settings for that type, then the supports (none or
   gussets; ribs are not implemented yet). Only the settings for the
   chosen type and supports are shown.
4. The boss is sized by its wall thickness where it is thinnest: at the
   top of a thread boss, at the screw seat of a screw head boss. The
   outside draft thickens it below; the panel shows the resulting base
   diameter and wall thickness at the base.
5. At the bottom, the instance table lists every point. Untick a row, or
   press **Ignore instances...** and click points in the 3D view, to
   leave a point without a boss. Clicking an ignored point again brings
   its boss back. Select a row to fine-tune that boss below the table: a
   rotation offset that turns its gussets/ribs, and one checkbox per
   gusset to leave single gussets out (e.g. next to a wall you rib into
   by hand). **Apply to all bosses** copies both to every boss.
6. Press OK. The wizard remembers the values for next time. Length, angle
   and count inputs also take expressions, e.g. `VarSet.DraftAngle`: type
   `=` in the field or click its f(x) icon. Double-click the `Boss`
   feature in the tree to change it later.

### Screw head boss

The sketch stays on the face the bosses stand on, as for a thread boss;
the boss grows up from it.

- **Screw bore**: the hole the screw passes through, from the boss top
  (where its diameter is measured) through the top wall down to the screw
  seat, with a 45° entry chamfer where it opens into the seat, clearing
  the screw's under-head fillet.
- **Screw seat bore**: from the seat on down through the part below, its
  diameter measured at the seat, with a fillet around the seat's outer
  edge.

Each has its own draft angle, and both widen downwards, so the mould core
pulls out through the bottom.

**Enable rubber pad cutout** adds a round recess of the given diameter
and depth in the part's bottom face below each boss, e.g. for a rubber
foot. The part's thickness below each boss is measured straight down
from its sketch point, so there is no thickness to enter and bosses on
faces of different thickness each get it right.

## Rib Wizard

PartDesign only.

Draw the ribs the way the mould maker cuts their cavities: every line or
arc in the path sketch is the centre path of a cutter, and the rib is the
volume that cutter sweeps. The lines need not be connected; where they
meet, cross or end, the rib is rounded the way the cutter would leave it.

1. In a PartDesign Body, draw a sketch of the rib centre lines on the face
   the ribs grow from. Lines and arcs only; an arc must be wider than the
   rib is at its base.
2. Select the sketch and run **Rib Wizard**.
3. Pick the cutter's tip (ball, flat, or flat with a corner radius), its
   size, the taper angle (the rib's draft, 0 for none, up to 45°) and the
   rib height. The panel shows the resulting rib width at the base, where
   the path lines sit, and previews the ribs live. Press OK to fuse them
   into the part. The sketch nests under the `Rib` feature, like a Pad's
   profile; double-click the feature to change it later.
4. A rib crossings fillet radius above 0 rounds every inside corner where
   ribs meet or cross, as the mould maker would: the cutter also runs along
   an arc from rib to rib, so the rib wall is rounded with that radius at
   its base. With a ball tip this can leave a small dip in the rib top at
   the corner. A radius too large for a short rib or a very sharp corner is
   reported in the panel.

## Pocket Push

PartDesign only.

For a cavity that opens in one face of a thin part, like a battery tray in
the underside of a plate: the cavity is pushed into the part, and where the
part is too thin for it, walls of constant thickness wrap it and stand out
of the opposite face, so there is no need to pad and pocket by hand.

1. In a PartDesign Body, draw a sketch on the face the cavity opens in.
   Each closed outline in it becomes one cavity. Outlines may not overlap
   or lie inside one another; where their walls meet, they merge.
2. Select the sketch and run **Pocket Push**.
3. Enter the cavity depth (from the sketch plane to the cavity floor), the
   draft angle, and the side and top wall thicknesses. The side wall
   thickness is measured square to the drafted wall. The panel shows the
   resulting outer height and previews the result live.
4. **Inner corner radius** rounds the cavity's corners along the pull
   direction. The outside corners get that radius plus the side wall
   thickness (shown in the panel), so the wall keeps its thickness around
   every corner. Corners the sketch already rounds keep their own radius.
5. **Top surface fillet** rounds the outer edge around the top of the
   walls. With **Auto** ticked (the default) it takes the outer corner
   radius; untick it to enter your own, 0 for a sharp edge. The cavity
   floor's edge stays sharp.
6. The pocket is pushed against the sketch normal, which for a sketch on a
   face points out of the part. Tick **Reversed** for a sketch whose normal
   points into the part, such as one on a datum plane.
7. Press OK. The sketch nests under the `PocketPush` feature; double-click
   the feature to change it later.

The cavity is widest at the sketch plane, so the core pulls out through
it. A draft too steep for the depth, so that a rounded corner or the whole
outline would shrink away, or a fillet too large to fit, is reported in the
panel.

## Hole Fill

PartDesign only.

For a perforated area such as a speaker grille: a perimeter filled with
round holes in a hexagonal pattern, each cut through the part.

1. In a PartDesign Body, draw a sketch on the face the holes open in,
   holding **one closed perimeter**, e.g. a circle.
2. Select the sketch and run **Hole Fill**.
3. Enter the hole diameter and the pitch, the distance from a hole's
   centre to each of its six neighbours. The pitch must be larger than the
   hole diameter. The panel shows the land between holes, the open area of
   the pattern and how many holes fit, and previews the result live.
4. Holes are cut against the sketch normal, which for a sketch on a face
   points out of the part. Tick **Reversed** for a sketch whose normal
   points into the part, such as one on a datum plane.
5. Press OK. The sketch nests under the `HoleFill` feature; double-click
   the feature to change it later.

One hole sits on the perimeter's centre of area, with rows along the
sketch's X axis, and only holes that fit inside the perimeter whole are
cut, so the edge is never nicked. A 37.5 mm circle with 0.9 mm holes at
1.7 mm pitch gets 421 holes. Each hole runs from the sketch plane until it
first comes out of the part: through a rib below the plate if it hits one,
but not on into material below an air gap.

## Sketch Mirror

Sketcher only: the command is available while a sketch is being edited.

1. Select the lines, arcs, circles and points to mirror.
2. Run **Sketch Mirror**. The selection stays highlighted as the list of
   what will be mirrored, and *Click mirror line* follows the cursor over
   the 3D view.
3. Click the mirror line: a line of the sketch (construction or not), an
   external edge that is a line, or the horizontal or vertical axis.

Each element gets a mirrored copy, construction if its original is, held
symmetric to its original by constraints, so it follows every later edit
of the original. A point that lies on the mirror line is made coincident
with its copy instead, which joins a mirrored half profile into one closed
outline. Esc (or a click into empty space) cancels before the line is
picked; Undo removes the whole mirror in one step. Ellipses, conics and
B-splines are not mirrored yet and are reported in the Report view.

## Layout

- `InitGui.py` - thin bootstrap: registers the workbench and installs every
  command at startup, so commands work from any workbench.
- `morefeatures/` - implementation package (reloadable, see `dev/reload.py`).
  - `registry.py` - the list of command modules; a new feature is added here.
  - `schema.py` - `ParameterField` and field kinds, shared by every wizard.
  - `config.py` - persisted settings (last-used wizard values).
  - `sketchpoints.py` - reading a sketch's points as instance locations.
  - `cutterprofile.py` - the silhouette of a ball, flat or corner radius
    cutter; the ribs are swept with it and a boss gusset is its ball case.
  - `preview.py` - the hidden flag a feature recomputes under while its
    wizard previews it.
  - `fillet.py` - filleting that fails with a readable message.
  - `selection.py` - finding the sketch and Body a command works on.
  - `cursorhint.py` - a label following the cursor over the 3D view, for
    commands that wait for a click without a task panel.
  - `commands/` - one module per command: resources, selection checks,
    opening the task panel (or, for Sketch Mirror, waiting for the line).
  - `taskpanels/` - task panels. `fieldform.py` builds editors from a field
    schema, `tiles.py` the picture buttons modes are picked with, `pointpicker.py` does click-to-toggle picking in the 3D view,
    `bosspanel.py` is the Boss Wizard panel, `ribpanel.py` the Rib Wizard
    panel, `pocketpushpanel.py` the Pocket Push panel,
    `holefillpanel.py` the Hole Fill panel,
    `featurevisibility.py` what they show while editing.
  - `featureproperties.py` - mirrors a field schema onto a document object
    as FreeCAD properties.
  - `addoncheck.py` - makes a saved feature fail its recompute loudly when
    the file is opened without this addon.
  - `boss/` - everything specific to the boss feature: `parameters.py` (the
    inputs and their schema), `geometry.py` (the in-memory boss template),
    `feature.py` (the PartDesign feature that places and fuses it),
    `basefillet.py` (the boss base fillet on the fused part),
    `viewprovider.py` (its look in the GUI) and `builder.py` (the seam the
    panel calls).
  - `rib/` - the rib feature, laid out like `boss/`; `geometry.py` sweeps
    the cutter along the path.
  - `pocketpush/` - the pocket push feature, laid out like `boss/`;
    `geometry.py` builds the drafted cavities and walls.
  - `holefill/` - the hole fill feature, laid out like `boss/`;
    `geometry.py` lays out the hole pattern and finds where each hole
    comes out of the part.
  - `sketchmirror/` - Sketch Mirror: `geometry.py` (mirrored copies),
    `subelements.py` (selection names as sketcher geometry ids),
    `builder.py` (adds the copies and their constraints) and
    `linepicker.py` (waits for the mirror line to be clicked).
- `Resources/icons/` - workbench and command icons.
- `Resources/images/` - pictures shown inside task panels.
- `dev/reload.py` - reload `morefeatures/` modules without restarting.
- `package.xml` - Addon Manager metadata.

## Dev setup

This repo is symlinked into FreeCAD's Mod directory so edits here take
effect without reinstalling:

```
ln -s ~/Desktop/MoreFeaturesForFreeCad ~/.var/app/org.freecad.FreeCAD/data/FreeCAD/v1-1/Mod/MoreFeaturesForFreeCad
```

Restart FreeCAD after editing `InitGui.py` or a command class. For other
changes inside `morefeatures/`, run `dev/reload.py` from the FreeCAD
Python console instead.

## License

MIT, see [LICENSE](LICENSE). Every source file carries an SPDX header.
