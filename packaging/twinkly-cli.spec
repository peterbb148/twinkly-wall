# PyInstaller bundles the Python runtime, embedded bitmap fonts, and dependency data.
# User settings and images remain external; never embed local config/settings.yaml.
import sys
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
    name="twinkly-cli",
    console=True,
    target_arch="arm64" if sys.platform == "darwin" else None,
    codesign_identity=None,
    strip=False,
    upx=False,
)
