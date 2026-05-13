# AGENTS.md

이 저장소에서 작업할 때는 아래 파일을 우선순위로 보면 된다.

## 1. 최우선 파일

### `app.py`

프로젝트의 실제 백엔드 진입점이다.

담당:

- Flask 라우팅
- 주문 접수
- 테이블 상태 조회
- 관리자 API
- `data.json` 파일 읽기/쓰기
- 데이터 초기화 로직

수정 시 특히 확인할 것:

- 현재 상태 저장은 SQLite이며, HTTP 라우트는 대부분 `db.py` 함수에 위임한다.
- 주문 접수 시 매출과 재고가 즉시 바뀐다.
- 취소/테이블 초기화가 재고, 매출, 통계에 어떤 영향을 주는지 반드시 확인한다.

### `db.py`

실제 운영 데이터 접근 계층이다.

담당:

- SQLite 연결
- 스키마 생성
- 메뉴 조회
- 주문/재고 트랜잭션
- 관리자 대시보드 데이터 집계

수정 시 특히 확인할 것:

- 주문 생성은 SQLite의 `BEGIN IMMEDIATE` 트랜잭션 안에서 처리된다.
- 현재 매출/판매 통계는 별도 테이블에 누적된다.
- 주문 취소/테이블 비우기 정책이 비즈니스 의미와 맞는지 항상 확인한다.

### `data.json`

이제 실시간 운영 원본은 아니다.

주 용도:

- 기존 데이터 백업
- `scripts/migrate_json_to_sqlite.py` 입력 파일

수정 시 특히 확인할 것:

- 마이그레이션 전에만 의미가 있다.
- 이미지 파일명 불일치가 있으면 SQLite로 그대로 옮겨질 수 있다.

## 2. 화면별 핵심 파일

### `templates/customer_menu.html`

손님이 보는 메뉴 화면.

자주 수정하는 영역:

- 상단 안내문
- 계좌/운영 공지
- 카드 디자인
- 추천 배지
- 품절 표시
- `?table=` 기반 주문 현황 표시

연결 API:

- `GET /api/table_status/<table_id>`

### `templates/server_order.html`

현장 스태프용 주문 입력 화면.

자주 수정하는 영역:

- 테이블 선택 UI
- 장바구니
- 주문 전송 UX
- 테이블별 주문 현황
- 서빙 처리/삭제 버튼

연결 API:

- `POST /api/order`
- `GET /api/table_status/<table_id>`
- `POST /api/serve`
- `POST /api/cancel_order`

### `templates/admin_panel.html`

관리자용 운영 대시보드.

자주 수정하는 영역:

- 테이블 카드
- 미결제 금액 표시
- 입금/서빙 토글
- 주문 삭제
- 테이블 비우기
- 가격/재고 편집 표

연결 API:

- `GET /api/orders`
- `POST /api/admin/update_menu`
- `POST /api/item_pay`
- `POST /api/serve`
- `POST /api/cancel_order`
- `POST /api/clear`

## 3. 이미지 관련 파일

### `static/`

현재 손님/스태프 메뉴 카드에 쓰이는 이미지 위치다.

최근 정리된 주요 파일:

- `nacho.png`
- `oreo.png`
- `brown.png`
- `sausage.png`
- `pasta.png`
- `cheeze.png`
- `water.png`

작업 규칙:

- 메뉴 카드 이미지는 투명 PNG가 가장 다루기 쉽다.
- 카드 슬롯 배경은 HTML에서 따로 그려진다.
- `menu[*].img`와 실제 파일명은 반드시 일치시킨다.

## 4. 주의가 필요한 파일

### `uploads/`

여기 들어 있는 HTML은 `templates/`와 현재 서로 다르다.
서버 렌더링 기준은 `templates/`다.

작업 시 기본 원칙:

- 기능 수정은 `templates/` 기준으로 한다.
- `uploads/`까지 동기화할지는 별도 배포 목적이 있을 때만 판단한다.

## 5. 운영 흐름 요약

### 주문 생성

1. 스태프가 `/table/<id>`에서 메뉴 선택
2. `POST /api/order`
3. `tables[table_id].orders`에 항목 추가
4. 재고 감소
5. 매출 증가
6. 판매 통계 증가

### 주문 처리

- 입금 토글: `/api/item_pay`
- 서빙 토글: `/api/serve`
- 주문 삭제: `/api/cancel_order`
- 테이블 종료: `/api/clear`

## 6. 수정 전 체크리스트

다음 변경을 할 때는 특히 여러 파일을 함께 본다.

### 메뉴 자체를 바꿀 때

- 운영 데이터: SQLite `menu_items`
- 초기 기본값: `db.py`의 `INITIAL_MENU`
- `static/`

### 주문 정책을 바꿀 때

- `app.py`
- `db.py`
- `templates/server_order.html`
- `templates/admin_panel.html`

### 손님 화면 디자인을 바꿀 때

- `templates/customer_menu.html`
- 필요 시 `templates/preview.html`

## 7. 현재 확인된 잠재 이슈

- 일부 와인/기타 메뉴 이미지는 현재 `static/`에서 확인되지 않는다.
- 일부 와인/기타 이미지 파일은 현재 `static/`에서 확인되지 않는다.
- 주문 취소 시 매출은 줄지만 재고는 복구되지 않는다.
- 테이블을 비우면 테이블 상태는 사라지지만 누적 매출과 판매 통계는 그대로 남는다.

이 네 가지는 기능 수정 전에 먼저 의도를 확인하거나 명시적으로 정리하는 편이 좋다.
