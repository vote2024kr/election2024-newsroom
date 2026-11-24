# 실제 선거구 지도 데이터 출처

- 제작자: 오마이뉴스(OhmyNews), 2024
- 자료: 제22대 국회의원선거 254개 지역구 경계, `2024_22_Elec_simplify.json`
- 공개 저장소: https://github.com/OhmyNews/2024_22_elec_map
- 배포에 사용한 경계 위치: https://raw.githubusercontent.com/vote2024kr/election2024-newsroom/main/PROJECT1_ELECTION_RAG_INTEGRATED_V1/newsroom/static/map_22nd_2024.geojson
- 라이선스: MIT. 원본 저장소의 LICENSE를 확인해 해당 저작권 고지와 허가 조건을 유지합니다.

검토용 ZIP의 원본 기반이 이전 시점이어서 지도 경계는 최초 지도 실행 시 HTTPS로 다운로드한 뒤
`newsroom/static/map_22nd_2024.geojson` 파일에 보관합니다. 254개 경계 ID와 형식을 검증합니다.
선거 결과나 투표율 수치를 지도 배포 원본에서 가져오지 않으며 기존 V5의 PostgreSQL 자료에서만 읽습니다.

코드는 정확한 지리경계가 없는 경우 가짜 지도를 그리지 않고 지도 자료 미확보 안내를 출력합니다.
