# Windows 배포본

`ChzzkChatLounge.exe`를 실행하세요. **폴더 전체가 필요**합니다. Python과 Node.js를 별도로 설치할 필요가 없습니다.

Electron 44.9.0 실행기가 동봉된 CPython으로 기존 Python/PySide6 앱을 실행합니다. UI를 JavaScript로 재작성한 빌드는 아닙니다. 게임 캡처·채팅 UI·제재 메시지 숨김을 포함한 Python 소스를 `resources/backend`에 포함합니다.

## 오진 가능성을 줄이기 위한 배포 구성

- 일반 폴더형 배포. 실행 시 임시 폴더에 실행 파일을 풀어내는 단일 파일 패커, UPX, 난독화를 사용하지 않습니다.
- 관리자 권한 요구, 자동 시작 등록, 서비스 설치, 백신 예외 추가를 하지 않습니다.
- 번들 런타임만 직접 실행하며 셸 명령이나 실행 시 코드 다운로드를 사용하지 않습니다.
- Electron과 Python의 라이선스 및 패키지 메타데이터를 보존합니다.
- 버전과 제품 이름을 지정하고 파일별 `SHA256SUMS.txt`를 생성합니다. 해시는 무해함의 인증이 아니라 파일 일치 확인용입니다.
- **게시자 코드 서명은 적용하지 않았습니다.** 실제 서명 인증서가 필요합니다. 오진·SmartScreen 경고가 없다고 보장할 수 없습니다.

배포 전 본인/조직의 코드 서명 인증서로 서명하면 게시자와 파일 무결성을 확인할 수 있습니다. 서명 후에는 해시도 새로 생성해야 합니다. 오진이 발생하면 백신을 끄기보다 해당 업체에 검토를 요청하세요.

공식 안내: https://www.electronjs.org/docs/latest/tutorial/code-signing
Microsoft 개발자 FAQ: https://learn.microsoft.com/en-us/defender-xdr/developer-faq

## 재빌드

프로젝트의 `.venv`에 requirements.txt 패키지가 설치되어 있어야 합니다.

```powershell
npm ci
npm run build
```

로그: `%APPDATA%/CHZZK Chat Lounge/last-run.log`
