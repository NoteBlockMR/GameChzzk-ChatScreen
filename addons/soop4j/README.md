# SOOP 채팅 애드온 (시험 버전)

[soop4j 0.0.5](https://github.com/zzik2/soop4j)를 사용하는 선택형 Java 애드온입니다. 치지직 Lua 채팅과 SOOP 일반 채팅을 같은 패널에 시간순으로 표시합니다. 플랫폼 이름과 색상으로 구분합니다. 영상 동시송출 기능은 포함하지 않습니다.

## 실행

1. Java 11 이상을 설치합니다. 소스에서 빌드한다면 JDK 11 이상이 필요합니다.
2. 배포 패키지의 `obs-plugin` 폴더에 있는 `chzzk-chat.lua`를 OBS에 등록합니다. 함께 제공된 HTML과 Lua 모듈이 필요합니다.
3. `addons/soop4j/start.cmd`를 실행하고 **공개 SOOP BJ ID**를 입력합니다. 스트림키, 로그인 비밀번호는 입력하지 않습니다.
4. OBS Lua 설정에서 **SOOP 채팅 함께 표시**를 켜고 **SOOP 방송 ID**에 같은 ID를 입력합니다.
5. **현재 장면에 채팅 추가 / 설정 적용** 또는 **게임 + 채팅 합성 장면 만들기 / 갱신**을 누릅니다.

애드온 창은 실행 상태로 두세요. 종료하려면 Ctrl+C를 누릅니다. SOOP 방송 ID를 변경하려면 애드온을 종료·재실행하고 OBS 설정도 변경합니다. 애드온 하나가 한 SOOP 채널을 담당합니다. 치지직 채널 설정은 기존처럼 필요합니다. SOOP만 단독으로 시작하는 모드는 이번 버전에 포함하지 않습니다.

## 동작과 제한

- Java 애드온은 `127.0.0.1:18767`에 읽기 전용 `/state`만 제공합니다. OBS Lua의 `18766` 서버는 유지합니다.
- SOOP 설정을 끄면 브라우저가 SOOP 데이터를 요청하지 않습니다. 별도로 실행한 Java 프로세스는 직접 종료하세요.
- 두 플랫폼은 독립적으로 갱신됩니다. SOOP 서버 재연결 중에는 최근 메시지를 유지합니다. 애드온 HTTP 응답이 30초 넘게 없으면 SOOP 표시를 비우며, 방송 ID가 다르면 즉시 비웁니다. 치지직 삭제/제재 결과는 기존 수신기 상태에 따라 반영됩니다.
- 플랫폼별 최근 100개를 보관하고 합쳐서 최신 100개를 표시합니다. SOOP 시간은 애드온 수신 시각이며 치지직 서버 시각과 완전히 일치하지 않을 수 있습니다.
- 공개 일반 채팅 읽기 전용입니다. 채팅 전송, 로그인·성인·비밀번호 제한 방송, SOOP 제재/삭제 연동, 이미지 이모티콘, SOOP 후원·구독 알림은 이번 범위에 포함하지 않습니다.
- 방송이 꺼져 있거나 연결이 실패하면 재시도합니다. TLS 인증서 검증을 해제하지 않습니다. SOOP 비공식 API 변경 시 수신이 중단될 수 있습니다.
- 연결 상태는 애드온 콘솔에 표시합니다. 방송 화면에는 연결 상태 문구를 추가하지 않습니다.

## 개발 및 검증

`powershell -File addons/soop4j/build.ps1`로 빌드합니다. Maven Central에서 고정 버전 의존성을 받고 `dependencies.json`의 SHA256을 검사합니다. Java 11 호환 바이트코드를 생성합니다. Python은 개발 테스트에만 쓰이며 실행에는 필요하지 않습니다.

검증 명령:

```powershell
.\.venv\Scripts\python.exe tests/soop_addon_smoke.py
node tests/obs_overlay_merge.cjs
.\.venv\Scripts\python.exe tests/run_obs_lua.py tests/obs_compose.lua
```

## 라이선스

애드온 코드는 프로젝트 MIT 라이선스를 따릅니다. soop4j / Java-WebSocket / SLF4J는 MIT, Gson은 Apache-2.0입니다. 원문은 `licenses` 폴더에 포함합니다. `lib`의 JAR와 라이선스 파일을 함께 보관하세요.
