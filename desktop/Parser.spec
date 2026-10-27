# Build from the repository root: pyinstaller --clean --noconfirm desktop/Parser.spec
from pathlib import Path
root = Path(SPECPATH).parent
analysis = Analysis(
    [str(root / 'desktop' / 'launcher.py')],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / 'frontend' / 'dist'), 'frontend/dist')],
    hiddenimports=[
        'uvicorn.logging', 'uvicorn.protocols.http.h11_impl',
        'uvicorn.lifespan.on', 'uvicorn.loops.asyncio',
        'sqlalchemy.dialects.sqlite.pysqlite',
    ],
    hookspath=[],
    excludes=['pytest','_pytest','pytest_asyncio','numpy','pandas','matplotlib','IPython'],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz, analysis.scripts, analysis.binaries, analysis.datas,
    [],
    name='2GIS-Business-Parser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
)
