from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('flask_babel')
datas = collect_data_files('flask_babel')
