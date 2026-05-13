# Sommelier HDM 운영 구조

이 프로젝트는 Flask 단일 앱으로 운영되는 소규모 주점 주문 시스템이다.
브라우저 화면은 역할별로 3개가 있고, 상태는 SQLite 파일에 저장된다.

## 1. 핵심 파일

- `app.py`
  - Flask 서버 본체
  - 라우팅, 주문 API, 관리자 API 담당
- `db.py`
  - SQLite 연결, 스키마 생성, 주문/재고/관리자 데이터 처리
- `data.json`
  - 이전 상태 이관용 원본 데이터 또는 백업 파일
- `templates/customer_menu.html`
  - 손님이 보는 메뉴 페이지
- `templates/server_order.html`
  - 스태프가 테이블별 주문을 넣고 처리하는 페이지
- `templates/admin_panel.html`
  - 운영자가 테이블 현황, 결제/서빙 상태, 가격, 재고를 관리하는 페이지
- `templates/preview.html`
  - 모바일 화면 구성을 한눈에 보여주는 정적 프리뷰 문서
- `static/`
  - 메뉴 이미지 자산
- `uploads/`
  - 현재 `templates/`와 내용이 다른 별도 HTML 사본들이 들어 있다.
  - 서버 렌더링에는 직접 쓰이지 않는다.

## 2. 실행 흐름

### 앱 시작

`app.py` 실행 시 Flask 앱이 뜬다.

```bash
python3 app.py
```

기본 설정:

- host: `0.0.0.0`
- port: `5000`
- debug: `True`

### 첫 진입

- `/`
  - `/menu`로 리다이렉트
- `/menu`
  - 손님용 메뉴 페이지
- `/table/<table_id>`
  - 해당 테이블용 스태프 주문 페이지
- `/admin`
  - 관리자 통합 패널

## 3. 데이터 저장 방식

현재 앱은 SQLite를 사용한다.

관련 파일:

- `db.py`
  - SQLite 접속
  - 테이블 생성
  - 주문 트랜잭션
  - 관리자 집계 조회
- `scripts/init_sqlite.py`
  - 스키마 생성
- `scripts/migrate_json_to_sqlite.py`
  - 기존 `data.json`을 SQLite로 이전

상세 절차는 `PYTHONANYWHERE_SQLITE_SETUP.md`를 따른다.

### menu

각 메뉴 항목은 대략 아래 구조를 가진다.

```json
{
  "id": 5,
  "category": "food",
  "name": "나쵸 세트",
  "price": 15000,
  "is_alcohol": false,
  "stock": 50,
  "img": "nacho.png",
  "is_best": false
}
```

### tables

테이블별 주문은 다음처럼 누적된다.

```json
{
  "3": {
    "entry_time": "2026-05-13T18:10:00.000000",
    "orders": [
      {
        "menu_name": "나쵸 세트",
        "price": 15000,
        "status": "대기 중",
        "is_paid": false,
        "time": "18:12"
      }
    ]
  }
}
```

## 4. 화면별 운영 방식

### 4.1 손님 메뉴 `/menu`

사용 파일:

- `app.py`
- `templates/customer_menu.html`

동작:

- `menu`에서 `is_alcohol == false` 이고 이름이 `"합석 비용"`이 아닌 항목만 노출
- 음식과 기타 항목을 카드형 그리드로 렌더링
- `?table=3` 같은 쿼리 파라미터가 있으면 60초마다 해당 테이블 주문 현황 조회
- 품절 메뉴는 카드에 Sold out 상태 표시

관련 API:

- `GET /api/table_status/<table_id>`

### 4.2 스태프 주문 `/table/<table_id>`

사용 파일:

- `app.py`
- `templates/server_order.html`

동작:

- 전체 메뉴를 카테고리별로 노출
  - liquor
  - food
  - etc
- 상단 입력창에서 현재 대상 테이블 변경 가능
- 메뉴를 장바구니에 담고 최종 주문 전송
- 같은 화면에서 해당 테이블 주문 현황을 5초마다 갱신
- 주문 상태를 서빙 완료/대기 중으로 토글
- 단일 주문을 삭제 가능

관련 API:

- `POST /api/order`
- `GET /api/table_status/<table_id>`
- `POST /api/serve`
- `POST /api/cancel_order`

### 4.3 관리자 `/admin`

사용 파일:

- `app.py`
- `templates/admin_panel.html`

동작:

- 5초마다 `/api/orders`를 호출해 전체 운영 상태 갱신
- 누적 매출 표시
- 테이블별 미결제 금액 표시
- 입금 여부 토글
- 서빙 여부 토글
- 주문 일괄 삭제
- 테이블 전체 비우기
- 가격/재고 변경 후 저장
- 120분 이상 체류한 테이블은 `Long stay` 강조

관련 API:

- `GET /api/orders`
- `POST /api/admin/update_menu`
- `POST /api/item_pay`
- `POST /api/serve`
- `POST /api/cancel_order`
- `POST /api/clear`

## 5. API별 상태 변화

### `POST /api/order`

입력:

```json
{
  "table_id": "3",
  "items": ["나쵸 세트", "물"]
}
```

변화:

- 테이블이 없으면 새로 생성
- 각 아이템을 주문 리스트에 추가
- 재고 `stock -= 1`
- 누적 매출 증가
- 판매 통계 증가

주의:

- 현재는 주문이 접수되는 순간 매출이 증가한다.
- 입금 여부(`is_paid`)와 누적 매출은 직접 연결되어 있지 않다.

### `POST /api/item_pay`

- 특정 주문의 `is_paid` 값을 토글

### `POST /api/serve`

- 특정 주문의 `status`
  - `"대기 중"`
  - `"서빙 완료"`
  사이를 토글

### `POST /api/cancel_order`

- 특정 주문을 삭제
- 누적 매출 차감
- 판매 통계도 1 차감

주의:

- 취소 시 재고는 다시 증가하지 않는다.

### `POST /api/clear`

- 테이블 전체를 삭제
- 이미 누적된 매출/판매 통계는 되돌리지 않는다.

## 6. 이미지와 카드 배경

현재 음식/물 이미지는 `static/` 아래에 있고, 손님/스태프 카드 이미지 슬롯은 HTML에서 아래 배경을 쓴다.

```css
background: linear-gradient(180deg, #F5EFE3 0%, #EDE4D2 100%);
```

최근 정리된 음식 및 물 이미지는 투명 배경 PNG 기반이다.
따라서 슬롯 배경이 그대로 비쳐서 카드 면과 자연스럽게 맞는다.

## 7. 현재 확인된 운영상 주의점

### 7.1 일부 메뉴 이미지는 아직 `static/`에 존재하지 않는다

현재 `data.json` 기준으로는 아래 항목들이 `static/`에서 확인되지 않는다.

- `Sparkling.png`
- `Dessert.jpg`
- `red.jpg`
- `White.png`
- `plus.jpg`
- `premium.jpg`

운영 전에는 이 자산들을 추가하거나, 메뉴의 `img` 값을 실제 파일명으로 맞춰야 한다.

### 7.2 `db.py` 기본 메뉴와 `data.json` 이전 원본은 둘 다 관리 포인트다

새 DB를 바로 초기화하면 `db.py`의 `INITIAL_MENU`가 들어간다.
반면 `scripts/migrate_json_to_sqlite.py`를 실행하면 `data.json`의 값이 DB를 덮어쓴다.
배포 경로를 하나로 정한 뒤 메뉴/이미지 기준도 같이 맞추는 편이 안전하다.

### 7.3 `uploads/` HTML은 현재 실사용 템플릿과 다르다

서버는 `templates/`를 렌더링한다.
`uploads/`는 배포 산출물 또는 과거 사본처럼 보이며, 현재 기준 문서로는 `templates/`를 우선 봐야 한다.

## 8. 자주 손대는 작업별 수정 위치

### 메뉴 이름, 가격, 기본 재고 변경

- 운영 중인 값: SQLite `menu_items`
- 초기 기본값: `db.py`의 `INITIAL_MENU`

운영 기본값을 바꾸는 경우 둘의 의도를 구분해서 관리한다.

### 손님 화면 문구/스타일 수정

- `templates/customer_menu.html`

### 주문 입력 UX 수정

- `templates/server_order.html`
- `POST /api/order`

### 관리자 기능 수정

- `templates/admin_panel.html`
- `/api/orders`
- `/api/item_pay`
- `/api/serve`
- `/api/cancel_order`
- `/api/clear`

### 이미지 수정

- `static/`
- `menu[*].img`

## 9. 요약

이 프로젝트는:

1. `data.json`을 단일 상태 저장소로 쓰고
2. Flask API가 이를 직접 갱신하며
3. 손님/스태프/관리자 페이지가 같은 상태를 각자 다른 관점에서 보여주는 구조다.

운영 관점에서 가장 중요한 파일은:

- `app.py`
- `data.json`
- `templates/customer_menu.html`
- `templates/server_order.html`
- `templates/admin_panel.html`

이다.
