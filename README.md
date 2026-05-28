# Korea University Sommelier Event POS

고려대학교 소믈리에 주점 통합 관리 시스템입니다. 손님 메뉴 화면, 스태프 주문 입력 화면, 관리자 대시보드를 한 SQLite 데이터베이스로 연결합니다.

## 주요 기능

- 손님용 메뉴 화면: `/menu`
- 테이블별 스태프 주문 입력: `/table/<table_id>`
- 관리자 대시보드: `/admin`
- 주문 생성 시 재고와 매출 즉시 반영
- 입금/서빙 상태 토글
- 테이블 비우기와 매출 원장 Excel 내보내기
- SQLite 기반 로컬 운영 데이터 저장

## 빠른 시작

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 scripts/init_sqlite.py
python3 app.py
```

브라우저에서 `http://localhost:5000/menu`, `http://localhost:5000/table/1`, `http://localhost:5000/admin`을 확인합니다.

## 환경변수

운영 전에는 `.env.example`을 참고해 아래 값을 반드시 별도로 설정하세요.

| 변수 | 설명 |
| --- | --- |
| `SECRET_KEY` | Flask 세션 서명 키 |
| `ADMIN_USERNAME` | 관리자 로그인 아이디 |
| `ADMIN_PASSWORD` | 관리자 로그인 비밀번호 |
| `PAYMENT_ACCOUNT` | 손님 메뉴에 표시할 입금 계좌 문구 |
| `PAYMENT_HOLDER` | 손님 메뉴에 표시할 예금주 |
| `SQLITE_PATH` | SQLite 파일 경로, 생략 시 `./sommelier.sqlite3` |

## 공개 저장소 주의사항

이 저장소는 공개 배포를 위해 실제 운영 계좌, 로컬 DB, 업로드 사본, 개인 개발 설정을 제외하도록 정리되어 있습니다. 실제 운영 데이터는 `data.json`, `*.sqlite3`, `uploads/`, `templates.old/` 등에 남을 수 있으므로 Git에 올리지 마세요.

이미 민감한 값이 들어간 커밋을 원격 저장소에 올린 적이 있다면 `.gitignore`만으로는 기록이 지워지지 않습니다. 공개 전에는 새 저장소로 옮기거나 Git 히스토리 정리를 검토하세요.

## 문서

- [운영 가이드](OPERATIONS.md)
- [PythonAnywhere SQLite 세팅](PYTHONANYWHERE_SQLITE_SETUP.md)
- [공개 전 체크리스트](PUBLIC_RELEASE_CHECKLIST.md)
- [보안 안내](SECURITY.md)
