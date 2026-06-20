# Code-CAD Workflow — Decisions, Setup & Conventions

A reference for the parametric CAD workflow: what we chose, why, and exactly how to stand it up.

> **Scope note:** This document covers the **toolchain and workflow only**. All prior *design* specifics (dimensions, part list, material choices, naming) were reset and are being rebuilt from scratch — none of that is in here. Laser-cutting manufacturability checks are **deferred** and noted at the end.

-----

## 0. Core constraints (the box everything fits in)

- **iPad-only.** No desktop, laptop, or other machine anywhere in the loop.
- **Free.** No paid software, no subscriptions.
- **Code-based.** Geometry is defined in code, version-controlled as text.
- **Capability prioritized.** Where a trade-off existed, we chose the more capable option even if it adds a cloud dependency.

-----

## 1. The mental model — three places, one format

```
┌────────────────────┐      git push/pull      ┌────────────────────────────┐
│  iPad — a-Shell     │  ───────────────────▶   │  GitHub                    │
│  • edit code        │  ◀───────────────────   │  • repo = source of truth  │
│  • local git (lg2)  │                          │  • Codespaces = compute    │
│  • pure-Python only │                          └─────────────┬──────────────┘
└────────────────────┘                                        │ runs the kernel
                                                              ▼
┌────────────────────┐     view output (PNG/glTF/3D)   ┌────────────────────────────┐
│  iPad — Safari      │  ◀───────────────────────────  │  Codespace (Linux x86_64)  │
│  • VS Code (web)    │                                  │  • build123d (B-rep)       │
│  • 3D render viewer  │                                  │  • Gmsh + CalculiX (FEA)   │
└────────────────────┘                                  │  • Blender (photoreal)     │
                                                        └────────────────────────────┘
```

**Why this shape:** the CAD kernel (OpenCASCADE, via `OCP`) is compiled C++ and cannot run on the iPad — a-Shell only runs **pure-Python** packages and its compiler targets WebAssembly, which Python can’t import as a C-extension. So the kernel lives in the cloud (Codespaces). a-Shell stays useful as an **on-device editor + version-control client**; the cloud only *executes*.

-----

## 2. Decisions log

|Decision                     |Choice                                                                                    |Why / rejected alternative                                                                                                                                                     |
|-----------------------------|------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|Build a custom CAD tool?     |**No.**                                                                                   |Existing free code-CAD already exceeds a custom build; a hand-rolled tool would re-implement boolean CSG just to drill holes. (Scrapped.)                                      |
|Modeling kernel / language   |**build123d** (Python, OpenCASCADE B-rep)                                                 |Most capable code-CAD: full Python (loops, refs, filtering), real fillets/chamfers/lofts, STEP export, best assembly story. CadQuery is the close sibling (same `OCP` kernel). |
|Where it runs                |**GitHub Codespaces**                                                                     |`OCP` is compiled and can’t run on iPad. Codespaces = Linux x86_64, so the wheels `pip install` cleanly (the Apple-Silicon `mamba` caveat does **not** apply here).            |
|On-device fallback           |**Replicad** (JS/TS, OpenCASCADE-WASM)                                                    |If the cloud loop ever drags: same B-rep kernel + STEP export, but runs in Safari — instant, offline, no quota. Trade: JavaScript, smaller ecosystem, manual assemblies.       |
|“Combine the pieces”         |**Interference checking**                                                                 |Position parts in 3D, intersect two solids, read the clash **volume** (nonzero = collision). Not just co-rendering.                                                            |
|Stress analysis (FEA)        |**STEP → Gmsh → CalculiX**, scripted via **PyCCX**                                        |Runs headless in the Codespace. Feeds the *dumb* STEP solid (FEA wants geometry + mesh, not history; STEP beats STL because the mesher refines on true curved fillet surfaces).|
|“Recommend a corner radius”  |**Parametric fillet sweep** (+ Peterson Kt hand-checks)                                   |No push-button exists. Sweep radius → mesh → solve → plot peak stress vs radius → pick the knee.                                                                               |
|Rendering                    |**glTF → three.js / model-viewer** on-device; **Blender headless** in cloud for hero shots|Materials/textures/lighting live in the **renderer**, not the CAD. build123d/CadQuery export glTF with per-part color via OpenCASCADE’s glTF writer.                           |
|Manufacturability (laser cut)|**Deferred**                                                                              |Parked by request. Slot in later.                                                                                                                                              |

### Format roles (don’t mix these up)

|Format               |Use                                             |Produced by    |
|---------------------|------------------------------------------------|---------------|
|**STEP** (`.step`)   |Machine shop, FEA input, archival B-rep         |`export_step()`|
|**STL** (`.stl`)     |3D printing / slicers                           |`export_stl()` |
|**glTF/GLB** (`.glb`)|Rendering, web viewing (carries color/materials)|`export_gltf()`|

-----

## 3. Setup — Part A: GitHub + repo

1. Create a free **GitHub account** (if you don’t have one). Free tier includes **120 Codespaces core-hours/month** (~60 real hours on a 2-core machine) + 15 GB storage. Add a payment method only if you want budget controls; you won’t be charged inside the free quota.
1. Create a **new repository** (private is fine; make it public later if/when you open-source the kit). Initialize with a README.
1. Create a **Personal Access Token (PAT)** for pushing from a-Shell:
   `GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens` → give it `Contents: Read/Write` on this repo. Save the token somewhere safe — you’ll paste it as the “password” when a-Shell pushes.

-----

## 4. Setup — Part B: a-Shell on the iPad (editing + git)

a-Shell is a free App Store app — nothing to compile. One-time config:

```bash
# identity
lg2 config --global user.name  "Your Name"
lg2 config --global user.email "you@example.com"

# clone your repo (HTTPS)
cd ~/Documents
lg2 clone https://github.com/USERNAME/REPO.git
cd REPO
```

Edit files with `vim` or `pico`. Day-to-day git:

```bash
lg2 add .
lg2 commit -m "message"
lg2 push            # prompts for username + PAT (use the token as the password)
lg2 pull
```

> **If `lg2 push` auth is finicky:** you don’t strictly need it. The Codespace is already authenticated to GitHub, so the frictionless path is to **commit locally in a-Shell** (offline) and **push from the Codespace terminal** with plain `git push`. Use a-Shell for offline editing + local history; use the Codespace as the always-works push point.

-----

## 5. Setup — Part C: Codespaces (where the kernel actually runs)

This is reproducible: commit a `.devcontainer/devcontainer.json` and every Codespace builds itself.

**`.devcontainer/devcontainer.json`**

```json
{
  "name": "code-cad",
  "image": "mcr.microsoft.com/devcontainers/python:3.12-bookworm",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "bernhard-42.ocp-cad-viewer"
      ]
    }
  },
  "forwardPorts": [3939],
  "postCreateCommand": "pip install --upgrade pip && pip install build123d ocp_vscode ocp_tessellate gmsh pyccx numpy scipy matplotlib trimesh && sudo apt-get update && sudo apt-get install -y calculix-ccx"
}
```

**What that installs**

|Package / tool                          |Role                                                                |
|----------------------------------------|--------------------------------------------------------------------|
|`build123d` (pulls `OCP`)               |The CAD kernel + Python API                                         |
|`ocp_vscode`, `ocp_tessellate`          |Live 3D preview inside VS Code (the **OCP CAD Viewer** extension)   |
|`bernhard-42.ocp-cad-viewer` (extension)|The viewer panel; port **3939** is forwarded so it renders in Safari|
|`gmsh`                                  |Meshing (reads STEP natively)                                       |
|`calculix-ccx` (apt) → binary `ccx`     |The FEA solver                                                      |
|`pyccx`                                 |Python wrapper tying Gmsh + CalculiX together                       |
|`numpy` / `scipy` / `matplotlib`        |Post-processing + plots (e.g. stress-vs-radius)                     |
|`trimesh`                               |Mesh utilities / quick checks                                       |

**Optional — photoreal rendering (adds build time + disk):** append to `postCreateCommand` or run on demand:

```bash
sudo apt-get install -y blender    # older but works headless; or download newest from blender.org
```

**Start it:** on the repo page → green **Code** button → **Codespaces** → *Create codespace on main*. It opens VS Code in the browser and runs `postCreateCommand` once. Stop it when done (idle codespaces still burn quota — stop, or delete to free storage).

> **If apt can’t find `calculix-ccx`:** it’s in Debian/Ubuntu universe; the bookworm image above has it. Otherwise install CalculiX via conda (`conda install -c conda-forge calculix`) or let PyCCX’s docs guide you.

-----

## 6. Repo structure

```
REPO/
├── .devcontainer/
│   └── devcontainer.json        # reproducible cloud env (Section 5)
├── lib/
│   └── common.py                # shared params, helpers, material colors
├── parts/                       # ONE file per part — the heart of the project
│   ├── __init__.py
│   ├── example_part.py
│   └── ...
├── assembly/
│   └── assembly.py              # imports parts, positions them, interference checks
├── analysis/
│   └── fea_example.py           # PyCCX stress studies + fillet sweeps
├── render/
│   ├── viewer.html              # on-device three.js / model-viewer
│   └── blender_render.py        # headless photoreal (cloud, optional)
├── export/                      # GENERATED artifacts (gitignored — reproducible from code)
├── .gitignore
└── README.md
```

**`.gitignore`**

```gitignore
export/
__pycache__/
*.pyc
.venv/
# FEA scratch
*.frd
*.dat
*.cvg
*.sta
*.vtu
```

> Generated geometry is reproducible from code, so keep it **out** of git. When you’re ready to publish STEPs/renders for the open-source kit, attach them to a **GitHub Release** or track a `dist/` folder with **Git LFS** — don’t bloat the source history with binaries.

-----

## 7. File templates

**A part — `parts/example_part.py`**

```python
from build123d import *
from ocp_vscode import show

# --- parameters (the things you'll sweep / tune) ---
LENGTH = 40.0
WIDTH  = 20.0
HEIGHT = 10.0

def build(length=LENGTH, width=WIDTH, height=HEIGHT):
    with BuildPart() as p:
        Box(length, width, height)
        # ... features: holes, fillets, etc.
    return p.part

part = build()

if __name__ == "__main__":
    show(part)                                   # live preview in VS Code
    export_step(part, "export/example_part.step")
    export_gltf(part, "export/example_part.glb", binary=True)
```

**Assembly + interference — `assembly/assembly.py`**

```python
from build123d import *
from ocp_vscode import show_all
from parts.example_part import part as part_a
from parts.other_part   import part as part_b

# position each part in the assembly
part_b = Pos(50, 0, 0) * part_b

# --- interference check ---
clash = part_a & part_b          # boolean intersection
vol = clash.volume               # 0.0 when there's no overlap
print(f"interference: {vol:.3f} mm^3  ->  {'CLASH' if vol > 1e-6 else 'clear'}")

show_all([part_a, part_b])
export_step(Compound([part_a, part_b]), "export/assembly.step")
export_gltf(Compound([part_a, part_b]), "export/assembly.glb", binary=True)
```

**FEA fillet sweep — pattern for `analysis/fea_example.py`** (PyCCX runs Gmsh + CalculiX under the hood)

```python
# Skeleton — see PyCCX docs for the meshing/boundary-condition API.
from parts.example_part import build

ALLOWABLE = 120.0   # MPa, your material limit / safety factor
for r in [0.5, 1.0, 1.5, 2.0, 3.0]:
    part = build()                       # regenerate with fillet radius = r
    export_step(part, "export/_tmp.step")# dumb solid -> the mesher
    # mesh   = gmsh reads _tmp.step, tetrahedralize        (via pyccx)
    # result = CalculiX solves with loads + fixtures        (via pyccx)
    # peak   = max von Mises from the .frd result
    # print(r, peak, "OK" if peak < ALLOWABLE else "TOO HIGH")
# then plot peak-stress vs radius and pick the knee
```

**On-device render — `render/viewer.html`** (simplest path; open in Safari)

```html
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script type="module"
    src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.5.0/model-viewer.min.js"></script>
  <style>html,body{margin:0;height:100%}model-viewer{width:100%;height:100%;background:#0e0e10}</style>
</head>
<body>
  <model-viewer src="../export/assembly.glb"
    camera-controls auto-rotate
    environment-image="neutral" exposure="1.0" shadow-intensity="1">
  </model-viewer>
</body>
</html>
```

For full control over PBR materials (metallic/roughness for an anodized-metal look), a custom HDRI, and a near-photoreal path-traced still on the iPad, step up to **three.js** + `MeshPhysicalMaterial` + an `.hdr` environment, and `three-gpu-pathtracer` for the hero frame. Materials are defined **here**, not in build123d.

-----

## 8. The daily loop

1. **Edit** a part file (a-Shell offline, or VS Code in the Codespace).
1. **Preview** live: run the part file with the OCP CAD Viewer open.
1. **Assemble + check**: run `assembly/assembly.py` → read the interference volume.
1. **Export** STEP (shop/FEA) / glTF (render) as needed.
1. **Analyze** (only where it earns it): run a fillet sweep / stress study.
1. **Render**: open `render/viewer.html` in Safari; Blender for a hero shot.
1. **Commit + push** (a-Shell `lg2`, or `git` from the Codespace).

-----

## 9. Quick command reference

```bash
# --- a-Shell (iPad) ---
lg2 clone https://github.com/USER/REPO.git
lg2 add . && lg2 commit -m "msg" && lg2 push

# --- Codespace terminal ---
python parts/example_part.py        # build + preview + export one part
python assembly/assembly.py         # assemble + interference check
git add . && git commit -m "msg" && git push
```

-----

## 10. Open / deferred

- [ ] **Laser-cut manufacturability** (DFM checks for flat parts) — parked, revisit later.
- [ ] First part definitions — rebuilding the design from scratch, one part at a time.
- [ ] Material / allowable-stress values for FEA — to be set when the design exists.
- [ ] HDRI + render styling for the “attractive render” pass.

-----

## References

- build123d — <https://build123d.readthedocs.io>
- OCP CAD Viewer (VS Code) — <https://github.com/bernhard-42/vscode-ocp-cad-viewer>
- Gmsh — <https://gmsh.info>
- CalculiX — <http://www.calculix.de>
- PyCCX — <https://pyccx.readthedocs.io>
- Replicad (on-device fallback) — <https://replicad.xyz>
- model-viewer — <https://modelviewer.dev>
- GitHub Codespaces — <https://docs.github.com/codespaces>