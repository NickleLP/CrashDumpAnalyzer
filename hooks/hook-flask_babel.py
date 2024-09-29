from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all data files from flask_babel
datas = collect_data_files('flask_babel')

# Collect all submodules from flask_babel
hiddenimports = collect_submodules('flask_babel')
