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
filleted where they meet or cross. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the build
sequence and what is still to be decided.

## Boss Wizard

PartDesign only.

1. In a PartDesign Body, draw a sketch on the face the bosses grow from.
   Every **point** in it marks one boss.
2. Select the sketch and run **Boss Wizard** (More Features toolbar/menu,
   or search it from the S-menu in any workbench).
3. The instance table lists every point. Untick a row, or press **Ignore
   instances...** and click points in the 3D view, to leave a point
   without a boss. Clicking an ignored point again brings its boss back.
   Select a row to fine-tune that boss below the Supports settings: a
   rotation offset that turns its gussets/ribs, and one checkbox per
   gusset to leave single gussets out (e.g. next to a wall you rib into
   by hand). **Apply to all bosses** copies both to every boss.
4. Set up the boss and press OK. The wizard remembers the values for next
   time. Length, angle and count inputs also take expressions, e.g.
   `VarSet.DraftAngle`: type `=` in the field or click its f(x) icon. Double-click the `Boss` feature in the tree to change it later.

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
  - `commands/` - one module per command: resources, selection checks,
    opening the task panel.
  - `taskpanels/` - task panels. `fieldform.py` builds a form from a field
    schema, `pointpicker.py` does click-to-toggle picking in the 3D view,
    `bosspanel.py` is the Boss Wizard panel, `ribpanel.py` the Rib Wizard
    panel, `featurevisibility.py` what both show while editing.
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
