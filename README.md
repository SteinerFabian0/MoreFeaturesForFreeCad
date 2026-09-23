# MoreFeaturesForFreeCad

Wizards that turn multi-step modelling chores into one parametric feature,
configured in a task panel the way SolidWorks feature wizards are.

Status: the **Boss Wizard** task panel is in place — point selection,
ignoring instances, and every boss/bore/inset/gusset setting. The CAD
backend is not built yet: pressing OK only logs the collected request to
the Report view. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for
where the backend plugs in and what is still to be decided.

## Boss Wizard

PartDesign only.

1. In a PartDesign Body, draw a sketch on the face the bosses grow from.
   Every **point** in it marks one boss.
2. Select the sketch and run **Boss Wizard** (More Features toolbar/menu,
   or search it from the S-menu in any workbench).
3. The instance table lists every point. Untick a row, or press **Ignore
   instances...** and click points in the 3D view, to leave a point
   without a boss. Clicking an ignored point again brings its boss back.
   Each row has a rotation offset that turns that boss's gussets/ribs;
   **Apply to all** sets them in one go.
4. Set up the boss and press OK. The wizard remembers the values for next
   time.

## Layout

- `InitGui.py` - thin bootstrap: registers the workbench and installs every
  command at startup, so commands work from any workbench.
- `morefeatures/` - implementation package (reloadable, see `dev/reload.py`).
  - `registry.py` - the list of command modules; a new feature is added here.
  - `schema.py` - `ParameterField` and field kinds, shared by every wizard.
  - `config.py` - persisted settings (last-used wizard values).
  - `sketchpoints.py` - reading a sketch's points as instance locations.
  - `commands/` - one module per command: resources, selection checks,
    opening the task panel.
  - `taskpanels/` - task panels. `fieldform.py` builds a form from a field
    schema, `pointpicker.py` does click-to-toggle picking in the 3D view,
    `bosspanel.py` is the Boss Wizard panel.
  - `boss/` - everything specific to the boss feature: `parameters.py` (the
    inputs and their schema) and `builder.py` (the backend seam, a stub).
- `Resources/icons/` - workbench and command icons.
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
