# PyInstaller spec for the standalone Windows build of DataScopia.
#
# This repo (datascopia-desktop) deliberately does NOT hold a copy of the app's source - that
# lives in the main repo (https://github.com/boandme/dataScopia), which also runs the
# hosted web version via Render. This repo pulls that source in fresh at build time (see
# .github/workflows/build.yml, which checks it out to ./source before running PyInstaller), so a
# fix merged there is already in the next desktop build with nothing to manually re-sync.
#
# Build with (from this repo's root), after checking out the main repo's source to ./source
# (or point DATASCOPIA_SOURCE at wherever you checked it out instead):
#   pyinstaller packaging/datascopia.spec --clean
# Output lands in dist_desktop/DataScopia/ (DataScopia.exe plus its support files, all flat in
# this one folder - see contents_directory below for why this isn't the usual _internal/ split).
#
# The entry point is desktop_app.py, not run.py: run.py opens the app in the system's default
# browser (the right behavior for `python run.py` from source), but a packaged app should feel
# like an app - its own window, its own icon and taskbar entry, closing it actually quits it -
# not a terminal window sitting behind a browser tab. desktop_app.py shows the same server in a
# native window via pywebview (using the WebView2 runtime Windows 10/11 ships with by default) -
# this is why requirements-desktop.txt (from the source checkout) is installed in addition to
# requirements.txt, on top of what the hosted web deployment needs.
#
# Why this looks more involved than a typical PyInstaller spec: the source's run.py and wsgi.py
# load apps/api/app/main.py by reading its actual file from disk at startup (importlib's
# spec_from_file_location), not via a plain `import main` - a deliberate convention in that repo
# so apps/ doesn't need __init__.py files to work as an importable package. PyInstaller's static
# analyzer can only discover the *compiled entry script's* imports, so it never sees main.py's
# dependencies at all unless told explicitly - hence the hiddenimports list below, which tells
# PyInstaller to analyze those modules too (as if the entry script had imported them), and the
# `datas` entries, which copy the real .py source for apps/api/app and the real static apps/web
# files, since both are read straight off disk at runtime (one via spec_from_file_location, the
# other via Flask's send_file/static_folder) rather than through the frozen import mechanism.

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

# SPECPATH is injected by PyInstaller into the spec file's exec namespace (there's no __file__
# here - the spec isn't run as a normal module import). DATASCOPIA_SOURCE overrides where the
# checked-out main-repo source lives; the default assumes it's been checked out to ./source next
# to this repo's own root, which is what .github/workflows/build.yml does and what you'd also do
# for a local test build (see this repo's README).
PROJECT_ROOT = Path(os.environ.get("DATASCOPIA_SOURCE") or Path(SPECPATH).resolve().parent.parent / "source")
if not (PROJECT_ROOT / "run.py").exists():
    raise RuntimeError(
        f"No main-repo source found at {PROJECT_ROOT} (set DATASCOPIA_SOURCE, or check out "
        "boandme/kaggle_datasetAnalysis to a 'source' directory next to this repo's root)."
    )

# Local packages main.py imports normally (`from analysis.x import y`, `from dataset.x import y`,
# `import store`, etc.) - these ARE discoverable once their directories are on pathex, but only if
# something tells PyInstaller's analyzer to look at them in the first place. Explicitly analyzing
# "main" (and letting it pull in its own imports) covers the apps/api/app side; collect_submodules
# covers every analysis/dataset submodule even if one is only imported conditionally and so isn't
# reachable from main.py's top-level import statements alone.
#
# Third-party libraries the app actually imports (sklearn/scipy via analysis/report*.py, pyarrow
# via dataset/streaming.py, reportlab via analysis/report_pdf.py, google.auth/cryptography via
# apps/api/app/firebase.py) are deliberately NOT force-collected with collect_all: it pulls in
# each library's entire test suite and demo/sample subpackages (pyarrow.tests alone is
# enormous), bloating the build for nothing actually used at runtime. Once "main" is a hidden
# import, PyInstaller's analyzer reaches every one of those real import statements on its own and
# applies pyinstaller-hooks-contrib's existing, already-tuned hooks for each library - no manual
# override needed.
#
# kaggle/kagglehub are the one real exception: v1.4's "no module named 'kaggle'" bug happened
# because an earlier pass concluded they were never imported anywhere, based on a grep for
# top-level `import kaggle` statements only - which missed that dataset/kaggle_search.py imports
# both of them *inside* functions (`from kaggle import KaggleApi` inside search_kaggle_datasets,
# `import kagglehub` inside download_kaggle_dataset), invisible to that grep's anchoring and,
# worse, invisible to PyInstaller's own static analysis too, which only sees imports reachable
# from a script it's actually told to analyze - a function-local import it never calls into
# doesn't count. Explicitly naming them as hiddenimports is what makes PyInstaller analyze them
# at all, the same reason "main" needs to be named below.
hiddenimports = (
    ["main"]
    + collect_submodules("analysis")
    + collect_submodules("dataset")
    + collect_submodules("kaggle")
    + collect_submodules("kagglehub")
)

datas = [
    (str(PROJECT_ROOT / "apps" / "web"), "apps/web"),
    (str(PROJECT_ROOT / "apps" / "api" / "app"), "apps/api/app"),
    # .NET Framework refuses to fully load Python.Runtime.dll (pywebview's Windows backend needs
    # it) once the build has been downloaded and extracted from a ZIP - Windows tags every
    # extracted file with "Mark of the Web", and .NET treats that as an untrusted remote source
    # unless told otherwise here. Reproduced and confirmed against a real zipped-and-extracted
    # build; see the comment in DataScopia.exe.config itself. Must sit next to DataScopia.exe
    # (not in a subfolder), which is why contents_directory="." is also set below.
    (str(Path(SPECPATH).resolve() / "DataScopia.exe.config"), "."),
]

# v1.4.5 shipped with "No package metadata was found for werkzeug", failing on every single
# launch: werkzeug's own BaseWSGIServer.__init__ (werkzeug/serving.py) unconditionally does
# f"Werkzeug/{importlib.metadata.version('werkzeug')}" to build its HTTP Server header, every
# time a server starts - not a rare code path, the very first thing run.start_server() does.
# PyInstaller bundles a package's *code* once something imports it, but never its .dist-info
# metadata folder unless told to separately - copy_metadata is that separate step. Pinpointed by
# directly tracing the actual importlib.metadata call with a real traceback (werkzeug/serving.py
# line 813), not inferred from the error text. Covering Flask's other direct dependencies too,
# not just werkzeug alone: the same self-referential-version-check pattern is common enough in
# this ecosystem that waiting for each one to surface as its own bug report isn't worth it.
for _pkg in ("werkzeug", "flask", "jinja2", "click", "itsdangerous", "markupsafe", "blinker"):
    datas += copy_metadata(_pkg)

a = Analysis(
    [str(PROJECT_ROOT / "desktop_app.py")],
    pathex=[
        str(PROJECT_ROOT),
        str(PROJECT_ROOT / "apps" / "api" / "app"),
        str(PROJECT_ROOT / "packages" / "analysis" / "src"),
        str(PROJECT_ROOT / "packages" / "dataset" / "src"),
    ],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DataScopia",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # a real windowed app, not a terminal window behind the app window -
                     # desktop_app.py shows a message box instead if startup itself fails
    icon=str(Path(SPECPATH).resolve() / "datascopia.ico"),  # this repo's own icon, not the source checkout's
    version=str(Path(SPECPATH).resolve() / "version_info.txt"),  # Properties > Details metadata
    # Disables PyInstaller 6+'s default _internal/ subfolder, putting every support file flatly
    # next to DataScopia.exe instead - required so DataScopia.exe.config (above) actually sits
    # where .NET Framework looks for it (an .exe's config file must be a sibling of the .exe
    # itself, never in a subfolder). This belongs on EXE, not COLLECT - passing it to COLLECT
    # instead is a silent no-op (no error, just the default _internal layout again).
    contents_directory=".",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DataScopia",
)
