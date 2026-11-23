# Windows V0.5 실행 오류 수정 - tzdata

## 증상

`ModuleNotFoundError: No module named 'tzdata'` 및
`ZoneInfoNotFoundError: No time zone found with key Asia/Seoul`

## 원인

Windows Python 3.12의 `zoneinfo`에서 IANA 시간대 데이터베이스를 찾지 못함.
기존 `requirements.txt`에 `tzdata` 설치 항목이 누락되어 있었음.

## 이미 기존 ZIP으로 가상환경을 설치한 경우

이미 현재 프로젝트 폴더에 있는 상태에서 다음을 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install tzdata
.\.venv\Scripts\python.exe -c "from zoneinfo import ZoneInfo; print(ZoneInfo('Asia/Seoul'))"
.\.venv\Scripts\python.exe server.py
```

정상 확인: 터미널에서 `Asia/Seoul`이 표시되고 서버가 127.0.0.1:8502에서 열립니다.

## 새 수정 ZIP을 사용한다면

이 버전의 requirements.txt에는 `tzdata>=2025.2,<2028`이 포함됩니다.
기존 `.venv`는 그대로 두고 다음 명령으로 누락 패키지만 설치해도 됩니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

## 변경 범위

이 패키지에서 **기존 코드, UI, 데이터, 그래프, 상태 로직은 전혀 변경하지 않음**.
수정: `requirements.txt` 한 파일에 tzdata 의존성 한 줄 추가.
추가: 이 복구 안내 문서.
GitHub 업로드 없음. MP4/CG 새로 만들지 않음.
