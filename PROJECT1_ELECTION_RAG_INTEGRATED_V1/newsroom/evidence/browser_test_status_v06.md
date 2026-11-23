# V0.6 브라우저 검증 한계
Playwright Chromium으로 `http://127.0.0.1:8502` 접속을 시도했으나 실행환경 관리 정책으로 `net::ERR_BLOCKED_BY_ADMINISTRATOR` 오류가 발생했습니다. 따라서 실제 브라우저 클릭·렌더링·모바일 레이아웃은 미검증입니다. Python API 및 JavaScript 문법 검사와 자동 테스트는 통과했습니다. Windows 11에서 더블클릭 실행 후 직접 확인이 필요합니다.
