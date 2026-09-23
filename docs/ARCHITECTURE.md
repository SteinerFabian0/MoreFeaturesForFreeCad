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
- **Build sequence, in memory on every recompute:** build one boss in a
  local frame (base on the origin, axis +Z) → for each non-ignored point:
  copy it, rotate it about its own axis by that instance's offset, and
  place it at the point in the sketch's orientation → fuse all copies
  into the Body's previous shape in one boolean. Nothing is stored between
  recomputes, so nothing depends on FreeCAD's fragile topological names.
- **Per-instance rotation offset** (phase), stored per sketch point. It
  turns only gussets or ribs, since the boss body is round.
- **Bore diameter** is measured at the bore entry (top). **Bore bottom**
  is flat.
- **Gusset height** = base length × tan(angle), capped at boss height.
- **Instances are keyed by sketch geometry id** (`getGeometryId`), not
  geometry index. Deleting an element renumbers every later index, but
  never an id. So: a new point gets a boss with no rotation, a moved point
  keeps its settings, and a deleted point's settings are dropped. Only a
  point that is deleted and redrawn counts as new.

### Still open

1. **Mounting plane.** The base fillet blends into the face the boss
   stands on. Is the sketch plane required to lie on that face?
2. **Modelling approach per sub-feature.** Your spec. One option for the
   round part of the boss (wall, draft, both fillets, bore, inset) is a
   single 2D half-section with the fillets drawn as arcs, revolved once,
   with no 3D fillet operations. Gussets need their own sequence,
   especially the vertical fillet where a gusset meets the drafted wall.
3. **Base fillet timing.** Blending into the body's face means either
   building the fillet into the boss before the boolean, or filleting the
   fused result afterwards.
4. **Validation.** Which input combinations are impossible depends on the
   geometry, so it comes with the backend. The panel can then list
   problems live and block OK on errors.

## Not implemented yet

- Rib settings (the `Ribs` support mode shows no fields yet).
- Visual marking of ignored points in the 3D view. Once a live preview
  exists, ignored bosses simply disappear.
- Expression binding (`Gui.ExpressionBinding`) on the quantity fields.
  It needs the feature object.
