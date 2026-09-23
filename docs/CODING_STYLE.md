# Coding Style Guide

This document defines the coding style for this project (Python / PySide).
All code — new and refactored — must conform to these rules.

---

## 1. Comments — the most important rule

**Minimal comments. Code explains itself through naming.**

- Never write a comment that explains *what* the code does or *how* it
  works. If a comment is needed to understand a line, the line is
  written wrong — rename things or restructure until it isn't.
- Inline comments are allowed **only** when absolutely needed to explain
  **why** something is done — a non-obvious constraint, a workaround, a
  requirement that isn't visible in the code itself. Never to narrate
  syntax or logic.
- A short comment block at the top of a file is fine to state its
  purpose, but keep it to a line or two — not a description of its
  contents.
- No function/module docstrings that just restate the signature or repeat
  the function name in prose. Only document a function when it has a
  real precondition, invariant, or side effect a caller must know and
  the name/types don't already convey it.
- When in doubt: delete the comment and improve the name instead.

```python
# WRONG — explains what the code does
# increment retry counter
retryCount += 1

# WRONG — restates the function
def applyBiquadFilter(state, sample):
    """Applies a biquad filter to a sample."""
    ...

# CORRECT — no comment needed, names carry the meaning
retryCount += 1

# CORRECT — comment explains a non-obvious why
# FreeCAD only re-reads workbench icons on restart, not on Reload()
Gui.updateGui()
```

---

## 2. Indentation & Layout

- 4 spaces per indent level. No tabs.
- Line length: aim for 100 columns, never exceed 120.
- One statement per line, always. No `a = b = 0`, no `x = 1; y = 2`.
- One blank line between logically distinct sections of a function; no
  blank line directly after a function/class signature.

---

## 3. Naming

- `lowerCamelCase` for functions, methods, and variables.
- `PascalCase` for classes.
- `UPPER_SNAKE_CASE` for module-level constants.
- Names are descriptive even if long. `pinnedCommandsByWorkspace` beats
  `pinned`. Short names (`i`, `x`) are fine only for loop counters or
  coordinates with a tiny, obvious scope.
- Variables are nouns. Functions are verbs or verb phrases.
- Boolean-returning functions are named as questions and must not have
  side effects: `isMenuOpen()`, `hasPinnedCommand(cell)`.
- Private helpers (module- or class-internal, not part of the public
  API) are prefixed with a single underscore: `_buildGridCell(...)`.

---

## 4. Functions

- Each function does one thing. Keep them short; split when a function
  needs a comment to explain what its middle section does — that's a
  sign it should be two functions.
- Parameters that mirror an assignment (copying/transforming data) go
  `dst, src` order, matching `dst = src`.
- Methods that operate on an object's own state don't need that object
  passed in (it's `self`); free functions that operate on a passed-in
  object take it as the first parameter.
- No lazy initialization. State is set up explicitly (`__init__`, an
  explicit `setup()`/`install()`), never on first use inside an unrelated
  method.
- Avoid deep nesting and multiple early returns where a flatter
  structure reads just as clearly. Prefer guard clauses over nested
  `if`s when they reduce nesting, not when they add more branches.
- Type hints on function signatures are expected for anything beyond a
  trivial one-liner — they replace the "what type is this" comment.

---

## 5. Variables & State

- Declare/assign variables as close as possible to first use, in the
  smallest scope that needs them.
- Avoid module-level mutable state. If something must be process-global
  (e.g. the installed event filter instance), make that explicit and
  centralize it — don't scatter global reads/writes across files.
- Don't reuse a variable for an unrelated purpose partway through a
  function.

---

## 6. Structure

- Favor early, flat control flow over nested conditionals.
- Avoid `continue` and multiple `break`s inside a loop where restructuring
  the loop condition or extracting a function reads more clearly.
- Prefer composition and small pure functions over deep inheritance
  hierarchies — reserve subclassing for genuine Qt widget/`Workbench`
  interface requirements.

---

## 7. Imports & Modules

- Import only what's used.
- Standard library, then third-party (`PySide`, `FreeCAD`/`FreeCADGui`),
  then local (`smenu.*`) — each group separated by a blank line.
- No wildcard imports.

---

## Summary: Quick Reference

| Topic | Rule |
|---|---|
| Comments | Minimal. Never explain *what*/*how*. Only non-obvious *why*, and only if truly needed. |
| Docstrings | Only when there's a real precondition/invariant the name doesn't convey. |
| File header comment | One or two lines max, purpose only. |
| Indent | 4 spaces, no tabs |
| Line length | ~100 cols, hard max 120 |
| Naming | lowerCamelCase (functions/vars), PascalCase (classes), UPPER_SNAKE_CASE (constants) |
| Names | Descriptive over short; booleans phrased as questions |
| Statements per line | One, always |
| Lazy init | Never — explicit setup |
| Globals | Avoid; centralize if unavoidable |
| Functions | Short, single-purpose, type-hinted |
