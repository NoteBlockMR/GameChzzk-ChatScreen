"""OBS의 게임 캡처와 함께 사용할 채팅 브라우저 소스 설정."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QLineEdit, QPushButton)
from channel import chat_url


class ObsSetupDialog(QDialog):
    def __init__(self, channel, width, height, parent=None):
        super().__init__(parent)
        self.setWindowTitle('OBS에서 게임 + 채팅 함께 녹화')
        self.resize(640, 440)
        layout = QVBoxLayout(self)
        heading = QLabel('같은 OBS 장면에 게임과 채팅을 추가하세요')
        heading.setStyleSheet('font-size:18px;color:#00e8a4;font-weight:bold;')
        layout.addWidget(heading)
        layout.addWidget(QLabel('브라우저 소스 URL'))
        self.url = QLineEdit(chat_url(channel))
        self.url.setReadOnly(True)
        row = QHBoxLayout()
        row.addWidget(self.url, 1)
        copy = QPushButton('주소 복사')
        copy.clicked.connect(self.copy_url)
        row.addWidget(copy)
        layout.addLayout(row)
        self.dimensions = QLabel(f'너비: {max(280, width)} px    높이: {max(200, height)} px')
        self.dimensions.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.dimensions)
        steps = QLabel(
            '1. OBS 소스에서 + → 게임 캡처 → 실행 중인 게임 선택\n'
            '2. 같은 장면에서 + → 브라우저 → 이름: 치지직 채팅\n'
            '3. 로컬 파일은 끄고 위 URL과 너비·높이 입력\n'
            '4. 소스 목록에서 치지직 채팅을 게임 캡처보다 위로 이동\n'
            '5. OBS 미리보기에서 채팅 위치·크기 조절 후 소스 잠금\n'
            '6. 게임 소리를 오디오 믹서에서 확인하고 녹화 시작'
        )
        steps.setWordWrap(True)
        layout.addWidget(steps)
        notes = QLabel(
            '게임 위 오버레이와 OBS 채팅은 같은 채널을 각각 표시합니다. '
            'Ctrl+Alt+F9는 게임 위 채팅만 숨깁니다. 녹화에서 숨기려면 OBS 소스의 눈 아이콘을 끄세요.\n\n'
            'OBS 로그인은 별도입니다. 필요하면 브라우저 소스를 우클릭 → 상호작용에서 로그인하세요. '
            '채널 변경 시 OBS URL도 다시 붙여 넣어야 합니다. '
            '위치·불투명도는 자동 동기화되지 않습니다.\n\n'
            '현재 화면 그대로 녹화하려면 게임과 오버레이가 있는 모니터를 디스플레이 캡처로 선택할 수도 있습니다.'
        )
        notes.setWordWrap(True)
        layout.addWidget(notes)
        self.feedback = QLabel('OBS 소스는 위 순서대로 한 번 설정해 주세요.')
        layout.addWidget(self.feedback)
        close = QPushButton('닫기')
        close.clicked.connect(self.accept)
        layout.addWidget(close)

    def copy_url(self):
        QApplication.clipboard().setText(self.url.text())
        self.feedback.setText('복사했습니다. OBS 브라우저 소스의 URL에 붙여 넣으세요.')
