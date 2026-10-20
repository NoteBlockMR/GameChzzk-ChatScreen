import sys,runpy
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget
app=QApplication([]);window=QWidget();window.setWindowTitle('CHZZK Overlay Native Test');window.resize(360,500);window.show();app.processEvents()
try:
 sys.argv=['tests/run_obs_lua.py','tests/obs_overlay.lua']
 runpy.run_path('tests/run_obs_lua.py',run_name='__main__')
finally:window.close();app.processEvents()
