# PyInstaller bundles the Python runtime, embedded bitmap fonts, and dependency data.
# User settings and images remain external; never embed local config/settings.yaml.
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / "packaging" / "entrypoint.py")],
    pathex=[str(root / "src")],
    datas=[],
    hiddenimports=[],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="twinklysay",
    console=True,
    target_arch="arm64",
    codesign_identity=None,
    strip=False,
    upx=False,
)
