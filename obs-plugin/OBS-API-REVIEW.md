# OBS 공식 문서 대조 기록

- https://docs.obsproject.com/scripting : Lua 바인딩 차이, timer_add/remove, source_list_release, 참조 해제 규칙을 확인했습니다. 전역 타이머 콜백과 목록 해제는 유지했습니다. 예상하지 못한 타이머 예외는 콜백을 제거하고 수신기를 종료하여 반복 오류를 방지하도록 수정했습니다.
- https://docs.obsproject.com/reference-scenes : 개별 위치/배율/정렬/경계 API와 장면 참조 소유권을 확인했습니다. 합성 전에 실제 Lua 바인딩 제공 여부를 검사합니다. 유효하지 않은 캔버스·장면 생성 실패를 처리하고, 배치 예외 발생 후에도 합성 코드가 소유한 장면/게임/설정 참조를 해제합니다.
- https://docs.obsproject.com/reference-sources : obs_get_source_by_name/create의 소유 참조와 obs_scene_get_source/from_source의 빌린 참조를 구분했습니다.
- https://github.com/obsproject/obs-studio/blob/master/shared/obs-scripting/obs-scripting-lua.c : OBS가 error()를 로그 함수로 바꾸는 구현을 확인했습니다. 기존 모듈의 assert 기반 예외 처리를 유지합니다. 스크립트 로드가 새 Lua 상태를 생성하므로 require 캐시 강제 초기화와 잘못된 설명은 제거했습니다.

검증: tests/obs_compose.lua(배치·반복 갱신·없는 API·배치 예외 시 참조 해제), tests/obs_error_hook.lua(OBS error 훅·전송 실패·연결 후 timeout 해제), tests/obs_lua_retry.lua(재시도 간격·로그 제한).

공식 웹 문서는 최신 버전 기준입니다. 실제 설치 OBS에서 노출되는 Lua 함수는 다를 수 있어 실행 전 제공 여부를 검사합니다. libcurl/Schannel 통신은 OBS API 문서의 범위 밖이며 별도 검증이 필요합니다. 실제 OBS 녹화 및 종료 시 메모리 누수 카운터까지 검증한 것은 아닙니다.
