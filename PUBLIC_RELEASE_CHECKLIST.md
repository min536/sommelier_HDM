# Public Release Checklist

공개 저장소로 전환하기 전에 아래 항목을 확인하세요.

## 민감 정보

- [ ] 실제 계좌번호와 예금주가 코드/템플릿/문서에 남아 있지 않다.
- [ ] 실제 관리자 아이디와 비밀번호가 코드/문서에 남아 있지 않다.
- [ ] `.env`, SQLite DB, Excel 매출 파일, 운영 백업 파일이 Git에 추적되지 않는다.
- [ ] `data.json`은 로컬 운영 데이터로만 두고, 공개 예시는 `data.example.json`을 사용한다.

## Git/GitHub

- [ ] 공개용 저장소 이름은 `korea-university-sommelier-event-pos`처럼 개인 식별자 없이 학교/용도가 드러나는 이름을 쓴다.
- [ ] 기존 원격 저장소에 민감 정보가 올라간 적이 있다면 새 저장소 또는 히스토리 정리를 선택한다.
- [ ] `git status`에서 공개 의도와 맞지 않는 파일이 staged/untracked 상태로 남아 있지 않다.

## 실행 확인

- [ ] `python3 scripts/init_sqlite.py`
- [ ] `python3 app.py`
- [ ] `/menu`, `/table/1`, `/admin` 화면이 열린다.
- [ ] 주문 생성, 입금 토글, 서빙 토글, 테이블 비우기가 동작한다.
