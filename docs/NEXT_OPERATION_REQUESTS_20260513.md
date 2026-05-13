# Next Operation Requests Plan

Date: 2026-05-13
Status: Planning only — no code changes yet

---

## 1. Summary

The event/operator team has requested a second round of improvements after stabilization. The requests fall into five areas:

1. **Excel export overhaul** — show actual sold prices, chronological ledger, menu-level summary, and final totals.
2. **Menu page cosmetics** — replace hash brown and cheesecake images, change "KRW" labels to "원".
3. **Admin layout tuning** — optimize for 25 tables on laptop/tablet, review card density.
4. **Wine additional order time behavior** — operator wants a time reset when wine is reordered; needs careful design to avoid destroying data.
5. **Order arrival sequence display** — serving team wants to see order sequence for prioritization.
6. **Admin login** — acknowledged as desirable but not required now.

---

## 2. Direct / Low-Risk Changes

These can be implemented immediately with no design decisions pending.

| # | Change | Scope | Risk |
|---|--------|-------|------|
| A | KRW → 원 label change | 3 templates (customer_menu, server_order, admin_panel) | None — CSS class `.krw` stays, only visible text changes |
| B | Replace hash brown image (`brown.png`) | `static/brown.png` swap | None — requires new asset file from operator |
| C | Replace cheesecake image (`cheeze.png`) | `static/cheeze.png` swap | None — requires new asset file from operator |
| D | Verify stock restoration on cancel | Already implemented in `db.py:516-520` | None — documentation/confirmation only |

### Detail: Stock Restoration Verification

Already fixed in the previous stabilization patch. The `cancel_order()` function in `db.py:496-537`:
- Uses `BEGIN IMMEDIATE` transaction
- Restores stock via `UPDATE menu_items SET stock = stock + 1 WHERE id = ?` (line 517-520)
- Only restores when `menu_item_id IS NOT NULL`
- Rolls back on failure, so stock stays consistent

**Status: Confirmed working. No code change needed.**

---

## 3. Design Decisions Needed

These items require operator input before implementation.

| # | Decision | Owner input needed | Default recommendation |
|---|----------|--------------------|----------------------|
| 1 | Wine time reset behavior | Which option from Section 7 | Option D: manual reset button |
| 2 | Order sequence display | Want it? Which format? | Lightweight option from Section 8 |
| 3 | Admin login | Priority level | Defer unless owner escalates |
| 4 | New image files | Provide `brown.png` and `cheeze.png` replacement files | Blocked until files received |

---

## 4. Excel Export Plan

### Current State Analysis

The current export (`app.py:76-142`, `db.py:301-361`) already has solid foundations:

**What exists:**
- `order_ledger` table stores every order permanently (active, cleared, cancelled)
- Each ledger row already has its own `price` column — this is the **actual sold price at time of sale**, copied from `menu_items.price` during `place_order()` (`db.py:394-395`)
- The export already has three sheets: Summary, Menu Sales, Order Ledger
- Menu Sales sheet already aggregates by `menu_name` using `SUM(price)` from ledger — this correctly reflects actual sold prices
- Order Ledger sheet is already chronological (`ORDER BY created_at, id`)

**Critical finding: actual sold price is already stored correctly.**

The `place_order()` function reads the current price at order time (`item["price"]`) and writes it into both `orders` and `order_ledger`. If the admin changes a menu price mid-event via the menu management panel, subsequent orders pick up the new price. The ledger preserves whatever price was active when each order was placed.

This means the export already reflects actual sold prices, not current menu prices. The data model is sound.

**What needs improvement:**

1. **Summary sheet is sparse** — only shows 4 aggregate numbers. Operator wants a more complete summary with final revenue and total count broken down clearly.
2. **Menu Sales sheet lacks individual price tracking** — it groups by `menu_name` and sums `price`, but doesn't show the different prices an item may have been sold at if the price changed mid-event.
3. **Order Ledger sheet column order** — "주문 시각" and "표시 시각" are somewhat redundant; the column ordering could be more intuitive.
4. **Cancelled order handling** — Menu Sales query already excludes cancelled orders (`WHERE final_state <> 'cancelled'`). Summary sheet counts them separately. This is correct.
5. **No explicit "final total revenue" row** — The summary sheet shows `cumulative_revenue` from `app_metrics`, but this is a running counter. A computed sum from the ledger would be more trustworthy for reconciliation.

### Proposed Sheet Structure

#### Sheet 1: "요약 (Summary)"
| Row | Content |
|-----|---------|
| 누적 매출 | Sum of `price` from non-cancelled ledger rows |
| 유효 판매 건수 | Count of non-cancelled rows |
| 취소 건수 | Count of cancelled rows |
| 미입금 건수 | Count of non-cancelled, unpaid rows |
| 미입금 금액 | Sum of `price` from non-cancelled, unpaid rows |

Change: compute revenue from ledger `SUM(price)` rather than relying on `app_metrics.cumulative_revenue`. The counter approach is prone to drift if bugs occur; a ledger sum is self-correcting.

#### Sheet 2: "메뉴별 매출 (Menu Sales)"
Keep existing structure, add columns:

| 메뉴명 | 판매 수량 | 매출 합계 | 평균 판매가 |
|--------|----------|----------|-----------|

Average sold price = revenue / quantity. This surfaces any mid-event price changes at a glance.

#### Sheet 3: "주문 원장 (Order Ledger)"
Reorder columns for chronological readability:

| 주문 ID | 주문 시각 | 테이블 | 메뉴명 | 판매가 | 서빙 상태 | 입금 여부 | 최종 상태 | 정리 시각 | 취소 시각 |

Changes from current:
- Rename "가격" → "판매가" to make it explicit this is the actual sold price
- Remove "표시 시각" (redundant with 주문 시각; it's just HH:MM of the same timestamp)
- Move "주문 시각" to second column for chronological scanning

### Implementation Scope

- **Backend (`db.py`)**: Add `SUM(price)` and `COUNT(*)` aggregates computed from ledger. Add unpaid amount sum.
- **Backend (`app.py`)**: Update `export_sales()` sheet construction with new column layout.
- **No schema change needed.** The `order_ledger` already stores the correct sold price.
- **No frontend change needed.** Export is server-generated XLSX download.

### Risk Assessment

**Low risk.** The data model is already correct. This is a presentation-layer change to the XLSX generator. No order flow, no stock management, no table operations are affected.

---

## 5. Menu Page Change Plan

### 5.1 Image Replacement

**Hash brown** (`static/brown.png`, referenced in `db.py:23` as `"brown.png"`):
- Replace the file at `static/brown.png` with the new image
- No code change needed — the filename stays the same
- The `INITIAL_MENU` constant and database `img` column both reference `"brown.png"`

**Cheesecake** (`static/cheeze.png`, referenced in `db.py:26` as `"cheeze.png"`):
- Replace the file at `static/cheeze.png` with the new image
- No code change needed — same filename preservation

**Prerequisite:** Operator must provide the new image files. Recommended format: PNG, similar dimensions to existing images (~1000px wide based on current file sizes). If filenames differ, a simple rename at drop-in time is sufficient.

### 5.2 KRW → 원 Label Change

Current "KRW" labels appear in:

| File | Line(s) | Context |
|------|---------|---------|
| `customer_menu.html` | 381, 407 | `<span class="krw">KRW</span>` on menu cards |
| `server_order.html` | 595 | `<span class="krw">KRW</span>` on menu cards |
| `admin_panel.html` | 473 | KPI revenue display |
| `admin_panel.html` | 569 | Table card remaining bill |

All use the same pattern: `<span class="krw">KRW</span>`.

Change: replace the text content `KRW` → `원` in all four locations. The CSS class `.krw` can stay as-is (it controls font/spacing styling). Alternatively, rename the CSS class to `.currency` if desired, but this is cosmetic.

Note: The cart total in `server_order.html:686` already uses `원` (`총액: ${total.toLocaleString('ko-KR')}원`). So this change actually makes all currency labels consistent.

### 5.3 Explicitly Excluded

Menu item rename (e.g., "버섯크림 파스타") is **not** included in this planning document. It will be handled as a separate task.

---

## 6. Admin Page Change Plan

### 6.1 Admin Usage Context

The operator confirmed:
- Admin is used on **laptop or tablet** by team leads
- Phone-first optimization is **not needed** for admin
- Current mobile breakpoints (720px, 420px) can remain for emergency phone access but should not drive design decisions

### 6.2 25-Table Card Density

**Current grid:** `grid-template-columns: repeat(auto-fill, minmax(320px, 1fr))` (`admin_panel.html:143`)

At common screen widths with 25 tables:

| Screen width | Cards per row | Rows needed | Scroll depth |
|-------------|---------------|-------------|--------------|
| 1280px (laptop) | 3 | 9 | Heavy scrolling |
| 1440px (laptop) | 4 | 7 | Moderate scrolling |
| 1920px (desktop) | 5 | 5 | Manageable |
| 1024px (tablet landscape) | 3 | 9 | Heavy scrolling |
| 768px (tablet portrait) | 2 | 13 | Very heavy scrolling |

**Assessment:** At 320px minimum card width, a 1280px laptop shows 3 cards per row and requires scrolling through 9 rows of cards. For 25 tables this means significant vertical scrolling to find a specific table.

**Recommended changes (if operator agrees):**

1. **Reduce minimum card width to 280px** — allows 4 cards per row on 1280px screens (7 rows instead of 9). Still readable for table cards. Test to make sure order rows don't clip.

2. **Consider a compact card variant** — add a collapsible order list. Show card-top (table number, duration, bill) at a glance; expand to see individual orders on click. This would dramatically reduce scroll depth. However, this adds interaction complexity and may slow down operations.

3. **Add a "jump to table" number input** — quick navigation without scrolling. Simpler than collapsible cards.

**Recommendation: Option 1 (280px min-width) + Option 3 (jump-to-table input).** These are low-risk, non-breaking changes that improve 25-table usability without adding interaction complexity.

Option 2 (collapsible cards) is higher complexity and may slow down the operator workflow. Defer unless Option 1+3 are insufficient.

### 6.3 Touch Target Sizes on Admin

Current admin `.mini-btn` is `min-height: 31px` base / `min-height: 31px` at 720px. These are below the 44px target from the stabilization work — but since admin is laptop/tablet-first, this is acceptable if operated with a mouse or stylus. The 720px mobile override already increases to `min-height: 31px`.

**Note:** The stabilization patch updated `server_order.html` buttons to 44px but the admin panel buttons were left at their original 31px base sizes for the desktop/tablet context. This is intentional — admin is not phone-first. However, if tablet touch usage is common, consider bumping to 36-38px base.

---

## 7. Wine Timer / Time Reset Options

### Current Behavior

When any order is placed for a table, `place_order()` runs:
```
INSERT OR IGNORE INTO dining_tables (table_id, entry_time) VALUES (?, ?)
```
(`db.py:370-373`)

The `INSERT OR IGNORE` means `entry_time` is set on the **first** order and never updated. All subsequent orders (including wine) do not change `entry_time`. The admin panel shows duration as `Math.floor((new Date() - new Date(info.entry_time)) / 60000)` — this is always measured from the first order.

### The Problem

The operator says "wine additional order resets time." This probably means: when a table orders more wine, the staff wants the long-stay timer to reset, because the table has committed to staying longer and just paid for more wine.

But blindly resetting `entry_time` destroys the original table start time, which is useful for:
- Knowing total table occupancy time
- Reconciling with the order ledger
- Understanding turnover patterns

### Options Analysis

#### Option A: Reset `entry_time` on Wine Order

**How:** Change `INSERT OR IGNORE` to `INSERT OR REPLACE` (or add an UPDATE) when the ordered item has `is_alcohol = True`.

**Pros:**
- Simplest implementation (1-2 lines of SQL)
- Duration timer resets automatically
- Matches the literal operator request

**Cons:**
- **Destroys original table start time** — no way to recover when the table actually sat down
- If staff accidentally orders and cancels wine, the timer is permanently reset
- The `order_ledger` still has the original first order timestamp, creating a discrepancy
- Breaks the semantic meaning of `entry_time` — it becomes "last wine order time" rather than "when the table started"

**Verdict: Not recommended.** Data loss is permanent and the semantic confusion will cause problems.

#### Option B: Add `last_wine_order_time` Column

**How:** Add a new column to `dining_tables`. Update it on wine/alcohol orders. Display logic uses this timestamp when available.

**Pros:**
- Preserves original `entry_time`
- Admin can see both: "table since 19:30, last wine at 21:15"
- Duration timer can be based on either timestamp depending on context

**Cons:**
- Schema change required (ALTER TABLE or re-init)
- Display logic becomes more complex — which time does the long-stay warning use?
- Operator may not care about the distinction; they just want the timer number to change

**Verdict: Viable but may be over-engineering for the actual need.**

#### Option C: Display Both Durations

**How:** Keep `entry_time` as-is. Add `last_wine_order_time`. Show two durations: "입장 2시간 10분 · 와인 주문 42분".

**Pros:**
- Maximum information
- No data loss

**Cons:**
- Clutters the card header, especially with 25 tables
- Staff may find two timers confusing in a busy environment
- The long-stay warning (120min pulse) — which timer triggers it?

**Verdict: Too complex for the pub environment. Information overload.**

#### Option D: Manual "Reset Timer" Button (Recommended)

**How:** Add a small button on the admin table card that resets `entry_time` to now. No automatic behavior tied to wine orders.

**Pros:**
- **Intentional, not automatic** — staff explicitly decides when to reset
- Simple implementation (one API endpoint, one button)
- No schema change beyond what already exists
- Works for any reason, not just wine orders — staff might reset for other operational reasons
- Can be combined with a separate `original_entry_time` column if the owner wants history
- No risk of accidental resets from order flow

**Cons:**
- Extra manual step for staff
- Staff might forget to reset

**Verdict: Recommended.** This is the safest option with the least surprise. The operator's real need is "I want to be able to reset the timer," not "the timer must auto-reset on wine." A manual button gives full control without destroying data. If automatic behavior is later desired, it can be layered on top.

### Implementation for Option D

1. Add API endpoint `POST /api/admin/reset_timer` accepting `{table_id}`
2. Update `dining_tables SET entry_time = ?` for the given table
3. Add a small "타이머 초기화" button on the admin card, near the duration display
4. Optionally: log the original `entry_time` to the ledger before overwriting, so history is not completely lost

### My Recommendation

**Start with Option D.** If the operator finds manual resets tedious and specifically wants auto-reset on wine, upgrade to a hybrid of B+D: add `last_wine_order_time`, auto-update it on alcohol orders, use it for duration display, and keep the manual reset as a fallback. But try D first — it's simpler and reversible.

---

## 8. Order Sequence Display Plan

### The Request

The serving team wants to see order arrival sequence to know which table's food to prepare first.

### Current State

- Each order has a database `id` (auto-increment, globally unique)
- Orders are displayed grouped by `menu_name + status + is_paid` within each table card
- The `display_time` (HH:MM) is shown in the server order page but not prominently in admin
- There is no visible "order #" label anywhere

### Options

#### Option 1: Global Order Sequence Number

Display: `주문 #142` on each grouped order row.

**Pros:** Serving team can say "table 5's order #142 first, then table 8's #145."
**Cons:** Numbers grow large quickly. With 25 tables and multiple orders each, numbers reach hundreds fast. Also, grouped orders span multiple IDs — showing which one?

#### Option 2: Table-Local Sequence Number

Display: `#1`, `#2`, `#3` within each table.

**Pros:** Small numbers, easy to reference.
**Cons:** Not useful for cross-table prioritization, which is the actual serving team need.

#### Option 3: Order Time Display

Display: `19:32` next to each order group.

**Pros:** Absolute time is universally understood. Already stored as `display_time`.
**Cons:** Doesn't give explicit priority ordering. Staff must mentally sort "19:32 before 19:35."

#### Option 4: "Minutes Ago" Display

Display: `12분 전` next to each order group.

**Pros:** Immediately shows urgency — "this order has been waiting 12 minutes."
**Cons:** Needs periodic re-rendering. Current 5s refresh cycle handles this naturally.

### Recommendation: Option 3 (Order Time) with Visual Urgency

Show `display_time` (HH:MM) on each grouped order row in the admin card. Additionally, apply a subtle visual indicator (background color or icon) for orders waiting more than a configurable threshold (e.g., 10+ minutes).

This is:
- **Low clutter** — just 5 characters per row
- **Already stored** — no schema or backend change needed
- **Cross-table comparable** — "19:32 on table 5 came before 19:35 on table 8"
- **No ID confusion** — times are intuitive, IDs are not

Implementation:
1. Add `display_time` to the admin card order row (currently not shown)
2. Optionally: add a `.waiting-long` class for orders older than 10 minutes, with a subtle warm background

If the operator later wants explicit sequence numbers, they can be added alongside the time without removing it.

---

## 9. Implementation Order

| Phase | Items | Dependencies | Estimated Effort |
|-------|-------|-------------|-----------------|
| **Phase 1** | KRW → 원 label change | None | 15 minutes |
| **Phase 2** | Excel export improvements | None | 1-2 hours |
| **Phase 3** | Image replacement (hash brown, cheesecake) | New image files from operator | 5 minutes per image |
| **Phase 4** | Order time display in admin cards | None | 30 minutes |
| **Phase 5** | Admin 25-table layout tuning (280px grid + jump-to-table) | None | 1 hour |
| **Phase 6** | Wine timer reset button | Owner decision on Option D vs others | 1 hour |
| **Phase 7** | Admin login | Owner decision on priority | 2-4 hours (basic session auth) |

### Rationale

- Phase 1 is trivial and immediately visible to operator.
- Phase 2 has no dependencies and the most operational value (export is used for accounting).
- Phase 3 is blocked on asset delivery but zero-code when assets arrive.
- Phases 4-5 improve admin usability for the 25-table scenario.
- Phase 6 needs the owner's decision from Section 7.
- Phase 7 is deferred unless escalated.

---

## 10. Acceptance Criteria

### Phase 1: KRW → 원
- [ ] Customer menu shows prices as "12,000원" not "12,000KRW"
- [ ] Server order page shows prices as "12,000원"
- [ ] Admin KPI revenue shows "원" not "KRW"
- [ ] Admin table card remaining bill shows "원" not "KRW"
- [ ] Cart total already uses "원" — no regression

### Phase 2: Excel Export
- [ ] Summary sheet shows revenue computed from ledger SUM, not app_metrics counter
- [ ] Summary sheet shows unpaid amount
- [ ] Menu Sales sheet shows average sold price per menu
- [ ] Order Ledger sheet column header reads "판매가" (not "가격")
- [ ] Order Ledger is sorted by 주문 시각 ascending
- [ ] Cancelled orders are included in ledger with `final_state = 'cancelled'`
- [ ] Cancelled orders are excluded from Menu Sales aggregates
- [ ] Menu Sales revenue correctly reflects actual sold prices, not current menu prices
- [ ] Export downloads successfully with all three sheets

### Phase 3: Image Replacement
- [ ] Hash brown card shows new image
- [ ] Cheesecake card shows new image
- [ ] Images load without error on customer, server, and admin pages
- [ ] No broken image placeholders

### Phase 4: Order Time in Admin
- [ ] Each order group row in admin card shows order time (HH:MM)
- [ ] Time display does not cause card layout overflow
- [ ] Time is readable at admin card sizes

### Phase 5: Admin 25-Table Layout
- [ ] At 1280px width, 4 table cards fit per row (280px minimum)
- [ ] Table cards remain readable at 280px width
- [ ] Jump-to-table input navigates to the correct table card
- [ ] No horizontal overflow at any supported width
- [ ] Order content within cards is not clipped

### Phase 6: Wine Timer Reset
- [ ] Reset button is visible on admin table cards
- [ ] Clicking reset updates the displayed duration to "0분"
- [ ] Original entry_time is overwritten in the database
- [ ] Reset only affects the targeted table
- [ ] Reset does not affect orders or payment status

### Phase 7: Admin Login (if implemented)
- [ ] Admin page requires authentication
- [ ] Unauthenticated access redirects to login
- [ ] Server order pages remain accessible without login
- [ ] Customer menu remains accessible without login
- [ ] Session persists across page refreshes
- [ ] URL-only access without session is blocked

---

## 11. Questions for Owner

1. **Image files:** 해시브라운과 치즈케이크 새 이미지 파일을 제공해 주세요. 파일 형식은 PNG 권장, 기존 이미지와 비슷한 해상도면 됩니다.

2. **와인 추가 주문 시 타이머 동작:** 관리자 카드에 "타이머 초기화" 버튼을 추가하는 방식을 권장합니다 (Option D). 와인 주문 시 자동 리셋은 최초 입장 시간 데이터를 파괴하고, 실수로 주문 후 취소할 경우에도 타이머가 이미 리셋되는 문제가 있습니다. 수동 버튼 방식으로 진행해도 괜찮은지 확인 부탁드립니다.

3. **주문 순서 표시:** 관리자 카드의 각 주문 그룹에 주문 시각(HH:MM)을 표시하는 것을 권장합니다. 별도의 주문 번호(#142 등)보다 직관적이고 화면을 덜 차지합니다. 이 방향이 괜찮은지 확인 부탁드립니다.

4. **관리자 로그인:** 현재로서는 후순위로 분류했습니다. 이벤트 전에 필요하다면 우선순위를 올려 주세요. 단, URL 난독화는 보안이 아닙니다.

5. **관리자 카드 크기:** 25개 테이블을 노트북에서 볼 때, 카드 최소 너비를 320px → 280px으로 줄이면 한 줄에 4개가 들어갑니다. 카드가 약간 좁아져도 괜찮은지 확인 부탁드립니다.

---

## Appendix: Infeasibility Notes

**없음.** 모든 요청 사항은 현재 시스템 구조 내에서 구현 가능합니다.

- Excel export: `order_ledger` 테이블에 이미 판매 시점 가격이 저장되어 있어, 별도 스키마 변경 없이 XLSX 생성 로직만 수정하면 됩니다.
- 이미지 교체: 파일만 교체하면 됩니다.
- KRW → 원: 텍스트 4곳 변경입니다.
- 타이머 리셋: API 엔드포인트 1개와 버튼 1개입니다.
- 주문 시각 표시: 이미 저장된 `display_time` 데이터를 표시만 하면 됩니다.
- 관리자 로그인: Flask session 기반으로 구현 가능하지만, 이벤트 운영 중 세션 만료 등 부작용을 고려해야 합니다.

## Appendix: Better Alternatives Identified

1. **Excel 매출 합계를 `app_metrics.cumulative_revenue` 대신 ledger SUM으로 계산하는 것을 권장합니다.** 카운터 방식은 버그 발생 시 누적 오차가 생기지만, 원장 합계는 자체 검증됩니다. 현재 카운터 값과 원장 합계 값을 둘 다 Summary에 표시해서 차이가 있으면 운영팀이 인지할 수 있게 하는 것도 방법입니다.

2. **주문 순서 표시에서 "경과 시간" (12분 전) 대신 "주문 시각" (19:32)을 권장합니다.** 경과 시간은 5초마다 갱신해야 하고, 화면이 갱신될 때 숫자가 계속 바뀌어 시각적으로 산만합니다. 주문 시각은 고정값이라 안정적입니다.

3. **관리자 카드 축소(280px) + "테이블 이동" 입력란 조합을 권장합니다.** 접기/펼치기 카드는 조작 단계가 늘어나고, 전체 축소보다는 빠른 네비게이션이 25개 테이블 관리에 더 효과적입니다.
