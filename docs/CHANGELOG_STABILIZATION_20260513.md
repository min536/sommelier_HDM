# Stabilization Change Summary

## 1. Overview

2026-05-13 기준 최근 안정화 작업은 Flask + SQLite 기반 주점 주문 시스템의 운영 안전성과 모바일 사용성을 개선하는 데 집중되었다. Git 기록상 핵심 안정화 커밋은 `4f1b8bb`이며, 이후 `7a7f401`부터 `6fe20a5`까지는 검증 과정에서 발견된 payload 검증, 실패 알림, 모바일 표시 균형, 메뉴 가격 가독성 등의 후속 보정이다.

저장소에서 확인되는 주요 방향은 다음과 같다.

- 주문/관리 API의 위험한 요청 입력을 더 방어적으로 처리한다.
- 위치 기반 `order_idx` 대신 안정적인 `order_id`로 주문 조작을 수행한다.
- 주문 취소 시 재고/매출/판매 통계가 함께 보정되도록 한다.
- KST 기준 timestamp를 사용한다.
- 스태프 주문 화면과 관리자 화면의 모바일 조작성, 수량/가격/상태 표시 가독성을 개선한다.
- 손님 메뉴 화면의 가격 표시와 상단 연도 라벨을 조정한다.

## 2. Main Changes

### 주문 생성 및 요청 검증

**What changed**

- `/api/order`가 JSON body 부재, 빈 테이블 번호, 빈 주문 항목을 400 JSON 오류로 거절한다.
- `items` 배열 안의 값이 비어 있거나 문자열이 아닌 경우도 400으로 거절한다.
- `order_id`는 양의 정수이며 `bool`이 아니어야 한다.
- 관리자 메뉴 수정 API에서 음수 가격/재고를 거절한다.

**Why it matters**

- 잘못된 payload가 SQLite binding 오류나 500으로 이어지는 것을 줄인다.
- 운영 중 빈 주문, 이상한 테이블 ID, 음수 재고/가격 같은 데이터 오염 가능성을 낮춘다.

**Relevant files**

- `app.py`

### 안정적인 주문 조작 ID 사용

**What changed**

- 테이블 상태와 관리자 대시보드 데이터에 각 주문의 `order_id`가 포함된다.
- 입금 토글, 서빙 토글, 주문 삭제는 `order_id`와 `table_id`를 함께 확인한 뒤 처리한다.
- 관리자 화면의 묶음 주문 처리는 각 묶음이 가진 `orderIds` 배열을 순회한다.
- 현재 활성 파일 기준 `app.py`, `db.py`, `templates/server_order.html`, `templates/admin_panel.html`에는 `order_idx`, `_order_id_for_index`, `OFFSET` 참조가 없다.

**Why it matters**

- 주문 삭제 후 순번이 밀려 다른 주문을 처리하는 위험을 줄인다.
- 같은 메뉴가 여러 개 묶여 보여도 내부 주문 ID 배열을 유지해 batch 작업 대상이 명확하다.
- `table_id`와 `order_id`를 함께 확인해 다른 테이블 주문을 잘못 조작하는 일을 방지한다.

**Relevant files**

- `db.py`
- `app.py`
- `templates/server_order.html`
- `templates/admin_panel.html`

### 취소/정리와 재고/매출 처리

**What changed**

- 주문 생성은 `BEGIN IMMEDIATE` 트랜잭션 안에서 재고 감소, 주문 생성, ledger 기록, 매출/판매 통계 증가를 함께 처리한다.
- 주문 취소는 같은 트랜잭션 안에서 ledger 상태를 `cancelled`로 바꾸고, 활성 주문을 삭제하며, 재고를 1 복구하고, 누적 매출/판매 통계를 차감한다.
- 테이블 비우기는 ledger의 active 주문을 `cleared`로 표시하고 테이블을 삭제한다.

**Why it matters**

- 주문과 재고/매출이 일부만 반영되는 상태를 줄인다.
- 취소 후 품절 상태가 잘못 유지되는 운영 문제를 줄인다.
- 취소와 테이블 정리의 의미가 ledger에 남는다.

**Relevant files**

- `db.py`

### KST timestamp 처리와 체류 시간 표시

**What changed**

- `ZoneInfo("Asia/Seoul")` 기반 KST 시간이 도입되었다.
- 주문 `created_at`, 테이블 `entry_time`, 주문 `display_time`, 취소/정리 시간이 KST 기준으로 생성된다.
- 관리자 화면의 체류 시간은 60분 미만은 `N분`, 60분 이상은 `N시간 M분` 형식으로 표시된다.

**Why it matters**

- 서버 timezone이 KST가 아니어도 운영 시각이 어긋날 가능성을 낮춘다.
- 장기 체류 테이블을 현장에서 더 읽기 쉽게 확인할 수 있다.

**Relevant files**

- `db.py`
- `templates/admin_panel.html`

### 스태프 주문 화면 장바구니 안정화

**What changed**

- 빈 장바구니 제출을 클라이언트에서 막고, 서버도 빈 `items`를 거절한다.
- 제출 중에는 `submitting` 상태로 중복 탭을 무시하고 버튼을 비활성화한다.
- 제출 성공 시에만 장바구니를 비우고, 실패 시 장바구니를 유지한다.
- 장바구니 모달에서 같은 메뉴를 묶어 보여주며 `+`, `-`로 수량을 조정할 수 있다.
- 수량이 0이 되면 해당 메뉴 행이 사라지고, 총액이 갱신된다.
- 제출 payload는 기존처럼 메뉴명 flat list를 유지한다.

**Why it matters**

- 바쁜 현장에서 실수로 빈 주문이나 중복 주문을 넣는 위험을 줄인다.
- 주문 전 수량과 총액을 확인하고 바로 수정할 수 있다.
- 서버 API 계약을 크게 바꾸지 않으면서 UI만 개선했다.

**Relevant files**

- `templates/server_order.html`
- `app.py`

### 실패 알림과 운영 UI 피드백

**What changed**

- 스태프 화면의 서빙/삭제 요청 실패 시 짧은 한국어 alert를 보여준다.
- 관리자 batch 입금/서빙/삭제 요청은 실패 개수를 모아 한 번에 알린다.
- 관리자 테이블 비우기 실패도 HTTP 실패나 네트워크 오류를 감지해 alert를 보여준다.

**Why it matters**

- 요청이 실패했는데 화면만 조용히 새로고침되어 작업자가 성공으로 오해하는 상황을 줄인다.

**Relevant files**

- `templates/server_order.html`
- `templates/admin_panel.html`

### 모바일 가독성과 터치 조정

**What changed**

- 스태프 화면 장바구니 수량 조절 버튼과 수량 숫자 표시 크기를 조정했다.
- 스태프 테이블 주문 내역에서 메뉴명, 수량, 상태 표시 배치를 조정했다.
- 관리자 실시간 현황의 메뉴명, 수량, 입금/서빙/삭제 버튼 비율을 여러 차례 조정했다.
- 관리자 메뉴/재고 관리 모바일 레이아웃에서 Price/Stock 영역을 같은 폭으로 맞췄다.
- 관리자 Excel 다운로드 버튼을 상단 헤더에서 메뉴/재고 관리 아래로 이동했다.

**Why it matters**

- 모바일로 주문과 관리를 수행하는 운영 환경에서 작은 글씨와 잘못 누르기 쉬운 버튼의 부담을 줄인다.
- 수량, 상태, 결제/서빙 액션의 시각적 우선순위를 현장 사용 흐름에 맞게 조정했다.

**Relevant files**

- `templates/server_order.html`
- `templates/admin_panel.html`

### 손님 메뉴 화면 표시 조정

**What changed**

- 손님 메뉴 화면과 스태프 주문 화면의 메뉴 가격 표시 크기가 조정되었다.
- 손님 메뉴 상단 라벨은 `2026 · Korea University`로 표시된다. 이전의 `Est.` 접두어는 제거되었다.

**Why it matters**

- 메뉴 가격을 더 쉽게 확인할 수 있게 했다.
- 상단 문구를 요청된 표현으로 정리했다.

**Relevant files**

- `templates/customer_menu.html`
- `templates/server_order.html`

## 3. Files Changed

- `TODO.md`  
  안정화 목표, 수용 기준, 검증 체크리스트를 담은 작업 문서가 추가되었다.

- `app.py`  
  주문/관리 API의 JSON body, 테이블 ID, 주문 ID, 가격/재고, 주문 항목 검증이 강화되었다.

- `db.py`  
  SQLite 주문 처리, ledger, KST timestamp, order_id 기반 주문 조작, 취소 시 재고 복구 로직이 확인된다.

- `templates/server_order.html`  
  스태프 주문 화면의 장바구니 제출 방지, 중복 제출 방지, 수량 조절, 총액 표시, 주문 상태 조작 실패 알림, 모바일 표시 개선이 반영되었다.

- `templates/admin_panel.html`  
  관리자 대시보드의 order_id 기반 batch 처리, 체류 시간 표시, 실패 알림, 테이블 비우기 실패 처리, 모바일 버튼/수량/Price/Stock 표시 조정, Excel 버튼 위치 변경이 반영되었다.

- `templates/customer_menu.html`  
  손님 메뉴 가격 표시와 상단 연도 라벨이 조정되었다.

## 4. Validation Evidence

다음 내용은 로컬 명령 출력 또는 저장소 상태에서 확인했다.

- `git status --short --branch`  
  문서 작성 전 `## main...origin/main` 상태였고 애플리케이션 변경 사항은 없었다.

- `git log --oneline --decorate -12`  
  최근 안정화 관련 커밋으로 `4f1b8bb`, `7a7f401`, `d05826a`, `c200e20`, `a12ed65`, `cae3a4f`, `a64279b`, `5559a9d`, `6fe20a5`가 확인되었다.

- `git show --stat --oneline 4f1b8bb`  
  핵심 안정화 커밋이 `TODO.md`, `app.py`, `db.py`, `templates/admin_panel.html`, `templates/server_order.html`을 변경한 것이 확인되었다.

- `git show --stat --oneline 7a7f401..HEAD`  
  후속 polish 커밋들이 `app.py`, `templates/admin_panel.html`, `templates/server_order.html`, `templates/customer_menu.html`을 변경한 것이 확인되었다.

- `python3 -m py_compile app.py db.py`  
  최근 작업 중 반복 실행되었고 통과했다.

- `rg -n "order_idx|_order_id_for_index|OFFSET" app.py db.py templates/server_order.html templates/admin_panel.html`  
  최근 검증에서 활성 경로 기준 관련 참조가 없었다.

- `python3`에서 `import flask` 확인  
  현재 로컬 셸에서는 `ModuleNotFoundError: No module named 'flask'`가 발생했다. 따라서 Flask test client 기반 런타임 검증은 이 환경에서 수행되지 않았다.

- `find . -maxdepth 3 \( -iname '*test*' -o -path './tests/*' \) -print`  
  별도 테스트 파일/디렉터리는 확인되지 않았다.

## 5. Remaining Risks / Follow-ups

- `uploads/`와 `templates.old/`에는 예전 HTML이 남아 있다. `AGENTS.md` 기준 서버 렌더링은 `templates/`이므로 활성 경로는 아니지만, 별도 배포 용도로 사용한다면 동기화 여부를 따로 판단해야 한다.
- `templates/preview.html`에는 예전 preview용 문구와 샘플 가격 표시가 남아 있다. 현재 운영 렌더링 기준 파일인지 확인되지 않았으므로 이 문서에서는 운영 변경으로 보지 않았다.
- Flask 패키지가 현재 로컬 셸에 없어 API runtime smoke test는 수행하지 못했다.
- 자동화 테스트가 확인되지 않아 주문 생성/취소/재고 복구/order_id batch 처리의 최종 검증은 수동 운영 시나리오로 확인해야 한다.
- `TODO.md`는 admin/staff 인증이 이번 안정화 범위 밖이라고 명시한다. 따라서 URL 접근 제어는 여전히 별도 후속 과제다.

## 6. Recommended Manual Smoke Test

### 스태프 주문 화면

- `/table/<id>`에서 빈 장바구니로 최종 주문을 눌렀을 때 주문이 생성되지 않고 한국어 안내가 보이는지 확인한다.
- 메뉴를 여러 개 담고 장바구니 모달에서 `+`, `-`를 눌러 수량과 총액이 즉시 맞게 변하는지 확인한다.
- 수량을 0까지 내렸을 때 해당 행이 사라지고 장바구니 상태가 자연스럽게 바뀌는지 확인한다.
- 느린 네트워크 상황을 가정해 최종 주문 버튼을 여러 번 눌러도 중복 주문이 생기지 않는지 확인한다.
- 주문 후 테이블 주문 내역에서 수량과 `대기 중`/`서빙 완료` 표시가 읽기 쉬운지 확인한다.

### 관리자 화면

- `/admin`에서 테이블 카드의 체류 시간이 `N분` 또는 `N시간 M분` 형식으로 표시되는지 확인한다.
- 한 테이블에 같은 메뉴 여러 개를 주문한 뒤 입금/서빙/삭제 batch 버튼이 올바른 주문들에 적용되는지 확인한다.
- 주문 삭제 후 재고가 1 복구되고 누적 매출/판매 통계가 기대대로 보정되는지 확인한다.
- 테이블 비우기 성공 시 카드가 사라지고, 실패 상황에서는 실패 alert가 보이는지 확인한다.
- 모바일 폭에서 메뉴명, 수량, 입금/서빙/삭제 버튼, Price/Stock 입력칸이 겹치지 않는지 확인한다.

### 손님 메뉴 화면

- `/menu`에서 가격 표시가 너무 작거나 카드 밖으로 넘치지 않는지 확인한다.
- 상단 문구가 `2026 · Korea University`로 표시되고 `Est.`가 보이지 않는지 확인한다.
- 품절 메뉴 표시와 이미지 fallback이 기존처럼 보이는지 확인한다.
