# app.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(['app.py'],
             pathex=[],
             binaries=[],
             datas=[
                 ('templates', 'templates'),
                 ('static', 'static'),
                 ('translations', 'translations'),
                 ('changelog.md', '.')
             ],
             hiddenimports=[
                 'flask_babel',
                 'jinja2.ext.i18n',
                 'babel.numbers'
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data,
          cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='CrashDumpAnalyzer',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='CrashDumpAnalyzer')
