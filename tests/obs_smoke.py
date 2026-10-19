"""OBS 설정 UI 검증. 실제 OBS 녹화 테스트는 아닙니다."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from obs_setup import ObsSetupDialog

app = QApplication([])
key = '0123456789abcdef0123456789abcdef'
original = app.clipboard().text()
try:
    dialog = ObsSetupDialog(f'https://chzzk.naver.com/live/{key}', 380, 560)
    assert dialog.url.text() == f'https://chzzk.naver.com/live/{key}/chat?theme=dark'
    assert dialog.url.isReadOnly()
    assert '380' in dialog.dimensions.text() and '560' in dialog.dimensions.text()
    dialog.copy_url()
    assert app.clipboard().text() == dialog.url.text()
    assert '복사했습니다' in dialog.feedback.text()
    dialog.close()
    try:
        ObsSetupDialog('https://evil.test/channel', 380, 560)
        raise AssertionError('Invalid URL accepted')
    except ValueError:
        pass
    print('PASS: OBS channel URL, copy action, panel dimensions, invalid URL rejection')
finally:
    app.clipboard().setText(original)
