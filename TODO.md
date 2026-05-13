# TODO: Pub Ordering System Stabilization

## 0. Scope and Assumptions

- This stabilization work targets a staff-operated table ordering flow.
- Staff members use mobile phones as the primary ordering/admin interface.
- Customers are not expected to submit orders directly in this patch.
- Customer self-ordering is intentionally out of scope.
- Admin/staff authentication is intentionally out of scope for now.
- URL obfuscation may reduce accidental discovery, but it is **not real security** and should never be treated as authorization. If the URL leaks, anyone can access staff/admin pages and all API endpoints.
- The main goal is to reduce ordering mistakes, prevent incorrect order operations, improve table operation visibility, and make the mobile UI easier to use in a busy pub/bar environment.

---

## 1. High-Priority Staff Ordering UX Fixes

### 1. Prevent empty cart submission

**Goal:** Staff should not be able to submit an empty cart.

**Expected behavior:**
- If the cart is empty, block submission.
- Show a clear Korean message such as "장바구니가 비어 있습니다." or "담긴 메뉴가 없습니다."

**Acceptance criteria:**
- Empty cart submission does not create a table/order record.
- The user-visible message is clear.
- Existing successful order flow remains unchanged.

---

### 2. Prevent duplicate submission of the same pending cart

**Goal:** Prevent repeated submission of the exact same cart while the previous submit request is still pending. Do not block legitimate additional orders after success.

**Problem:** In a real pub environment, staff may tap the final submit button multiple times if the network is slow or the UI does not respond immediately. This can create duplicate orders from the same cart.

**Expected behavior:**
- When staff taps the final submit button, immediately set a submitting/pending state.
- While the submit request is pending, ignore additional taps on the final submit button.
- Visually disable the final submit button while submission is pending.
- Show an in-progress label if practical, such as "주문 처리 중..."
- If the request succeeds, clear/reset the cart as currently intended.
- If the request fails, clear the pending state and re-enable the button so staff can retry.
- After a successful order, staff must still be able to add new items and submit a legitimate additional order normally.

**Acceptance criteria:**
- Rapid repeated taps during one network request create only one order.
- A later additional order after success is still possible.
- Failed submission can be retried.
- The UI clearly indicates that submission is in progress.

---

### 3. Add item removal in the order confirmation/cart modal

**Goal:** Staff must be able to remove mistakenly added items before final submission.

**Current concern:** When staff taps "담기", the order confirmation/cart modal does not provide an obvious way to cancel/remove an item. This is risky because staff may need to correct mistakes quickly while taking orders.

**Expected behavior:**
- Each cart row has a readable remove/cancel button.
- Korean label should be clear, such as "삭제", "취소", or "빼기".
- Removing an item updates cart state immediately.
- The cart count and total price update immediately.
- The modal remains usable on mobile.

**Acceptance criteria:**
- A single item can be removed without clearing the entire cart.
- Removing one item does not affect unrelated items.
- Cart count updates correctly.
- Total price updates correctly.
- The remove button is large enough for mobile tapping.

---

### 4. Add quantity controls in the order confirmation/cart modal

**Goal:** Staff should be able to increase or decrease item quantity directly from the order confirmation/cart modal.

**Current concern:** Staff may add an item, then realize the quantity should be changed. They should not need to close the modal and repeatedly tap menu cards to correct quantity.

**Implementation note:** The current cart structure is a flat array of `{name, price}` objects pushed individually. Implementing quantity controls will likely require refactoring to a `{name, price, quantity}` structure. This change also affects item removal (#3) and total price (#5), so these three items should share the same cart structure migration.

**Expected behavior:**
- Each grouped cart item row has `+` and `-` controls.
- `+` increases the item quantity by 1.
- `-` decreases the item quantity by 1.
- If quantity becomes 0, remove that item from the cart.
- Quantity must never become negative.
- Controls must be large enough for mobile tapping.
- Quantity changes must update the cart count and total price immediately.

**Acceptance criteria:**
- Increasing quantity works correctly.
- Decreasing quantity works correctly.
- Decreasing from 1 removes the item.
- No negative quantity is possible.
- Total price updates correctly.
- UI remains comfortable on common phone widths.

---

### 5. Show cart total price

**Goal:** Staff should be able to verify the order total before final submission.

**Expected behavior:**
- Show total price in the cart/order confirmation modal.
- Format in Korean won, for example: "총액: 12,000원"
- The total should update whenever items are added, removed, or quantity is changed.

**Acceptance criteria:**
- Total matches item prices and quantities.
- Total updates after add/remove/quantity changes.
- Total is visually readable on mobile.
- Existing order submission payload remains correct.

---

## 2. Order Correctness and Data Integrity

### 6. Validate risky request payloads

**Goal:** Prevent malformed or invalid requests from causing server errors or inconsistent state. This should be done **before** the order_id migration (#7) so that validation is in place when the API contract changes.

**Expected behavior:**
- Add defensive validation for JSON body presence.
- Reject missing JSON body with HTTP 400 and clear JSON error.
- Reject missing, non-integer, or negative order identifiers.
- Reject empty table IDs.
- Reject invalid quantity if quantity is accepted anywhere.
- Reject negative price and negative stock in menu update endpoints.
- Keep user-visible messages in Korean where appropriate.

**Acceptance criteria:**
- Invalid request body returns 400 instead of 500.
- Invalid order_id/order_idx returns 400 instead of modifying data.
- Empty table ID does not create weird table records.
- Negative price/stock cannot be saved.
- Existing valid requests continue to work.

---

### 7. Replace positional order_idx operations with stable order_id operations

**Goal:** Prevent wrong order items from being modified when orders are deleted, grouped, reordered, or updated concurrently.

**Current problem:**
- The system uses positional order indices (`order_idx`) with SQL `LIMIT 1 OFFSET ?` lookup (`db.py:438-449`).
- Positional indices are fragile because order positions shift after deletion or status updates.
- This can cause actions like serve, payment, cancellation, or batch operations to affect the wrong item.

**Example problem:**
- A table has: index 0 = item A, index 1 = item B, index 2 = item C.
- If item A is cancelled, item B becomes index 0 and item C becomes index 1.
- Any UI or API still using the old index may now modify the wrong item.

**Expected behavior:**
- Backend should return stable database order IDs in table status and dashboard/admin data.
- Frontend should store and pass `order_id` instead of `order_idx`.
- Endpoints for serve, item payment, cancellation, and batch operations should use `order_id`.
- Validate `order_id` as a positive integer.
- Remove or isolate old index-based code after migration.
- Keep the UI behavior as close to the current behavior as possible.

**Acceptance criteria:**
- Cancelling one item does not affect another item.
- Serving one item does not affect another item.
- Payment toggling one item does not affect another item.
- Batch serve/payment/cancel actions target the correct order rows.
- No important UI action depends on fragile positional index behavior.
- Any remaining index-based code is documented or intentionally isolated.

---

### 8. Restore stock when an order is cancelled

**Goal:** If an order is cancelled, the related menu item stock should be restored.

**Current problem:** `cancel_order()` in `db.py:498-538` decrements `cumulative_revenue` and updates `sales_stats`, but does **not** increment `menu_items.stock`. Cancelled items remain counted as consumed, causing premature sold-out status.

**Expected behavior:**
- Cancelling an order increments the related menu item stock by 1.
- This should happen inside the same transaction as cancellation.
- If cancellation fails, stock must not change.
- Do not let stock become inconsistent after cancellation.

**Policy note:** The current system allows cancellation of already-served items. For this stabilization work, either restore stock on all cancellations and document that cancellation means "order was not consumed", or restrict cancellation for already-served items and require a separate admin-only correction flow. Choose the simplest safe behavior after checking current UI expectations.

**Acceptance criteria:**
- Ordering an item decreases stock.
- Cancelling that item restores stock.
- Failed cancellation does not change stock.
- Stock does not become negative or inconsistent.
- Sold-out status reflects restored stock correctly after cancellation.

---

### 9. Use timezone-aware timestamps (KST)

**Goal:** Ensure all timestamps are correct for Korean Standard Time, regardless of server location.

**Current problem:** `db.py:359` uses `datetime.now()` which returns server-local time. If deployed on PythonAnywhere or any non-KST server, all timestamps (order times, entry times, display times) will be wrong by up to 9 hours.

**Expected behavior:**
- Replace `datetime.now()` with `datetime.now(ZoneInfo("Asia/Seoul"))` in all relevant locations.
- Ensure `display_time` (HH:MM format) and `created_at` / `entry_time` (ISO format) are all KST.

**Implementation note:** Be careful when changing naive ISO strings to timezone-aware ISO strings, because frontend parsing/display code may assume the old format. Verify admin duration calculation and `display_time` formatting after the change.

**Acceptance criteria:**
- Timestamps are correct in KST regardless of server timezone.
- Admin panel elapsed time calculations are correct.
- Export data timestamps are correct.
- Frontend timestamp parsing and display still works correctly.

---

## 3. Table Duration Display

### 10. Improve table stay duration display format

**Context:** The admin panel already calculates and displays table stay duration (`diffMins` in `admin_panel.html:519`, shown as e.g. `42m`). Tables staying 120+ minutes already get a red `long-stay` pulse animation. No new feature is needed.

**Goal:** Improve the existing duration display to be more readable for staff, especially for longer stays.

**Expected behavior:**
- For stays under 60 minutes: keep current format, e.g. "42분" or "42m".
- For stays 60 minutes or more: show hours and minutes, e.g. "1시간 12분" or "1h 12m".
- Keep the display compact and readable on mobile.
- The existing `long-stay` warning behavior should remain unchanged.

**Note:** The existing `dining_tables.entry_time` field already records the first order timestamp via `INSERT OR IGNORE` (`db.py:364-366`). Additional orders do not overwrite it. No new field or schema change is needed for duration tracking.

**Acceptance criteria:**
- Duration appears for active tables.
- Duration is easy to read on mobile.
- Long durations show hours + minutes instead of raw minutes.
- Existing long-stay warning still works.

---

## 4. Mobile UI / Pub Environment Usability

### 11. Improve mobile readability and touch targets

**Goal:** The system should be comfortable to use on phones in a dim, busy pub environment.

**Focus areas:**
- Cart modal buttons (remove, +/-, submit)
- Final submit button
- Admin/staff action buttons (payment, serving, cancellation, clear)
- Table duration display
- Total price display
- Small status labels (e.g. 11.5px italic status text, 10px KRW labels)

**Expected behavior:**
- Important buttons should be visually obvious.
- Important controls should be large enough for thumb tapping (minimum ~44x44px touch area).
- Avoid tiny 10px action buttons for important operations.
- Avoid cramped controls that are easy to mis-tap.
- Maintain the current visual style.
- Keep the layout compact but not cramped.
- Do not break small-screen layouts.
- Avoid horizontal overflow on common phone widths.

**Acceptance criteria:**
- Important buttons are readable and tappable on mobile.
- Text is readable in a dim pub/bar environment.
- Controls are not too close together.
- No horizontal overflow on common phone widths (360px+).
- Existing desktop/admin layout is not severely degraded.

---

## 5. Implementation Order

Recommended order, with rationale:

| Order | Item | Rationale |
|-------|------|-----------|
| 1 | Prevent empty cart submission | Simple, independent, immediate safety win |
| 2 | Prevent duplicate submission | Simple, independent, immediate safety win |
| 3 | Validate risky request payloads | Must be in place before cart/API changes |
| 4 | Show cart total price | Small change, high staff value |
| 5 | Add cart item removal | Requires cart structure consideration |
| 6 | Add cart quantity controls | Shares cart structure refactor with #5 |
| 7 | Restore stock on cancellation | Backend-only, independent |
| 8 | Use timezone-aware timestamps | Small backend change, verify parsing compatibility |
| 9 | Replace order_idx → order_id | Largest change, touches backend + frontend |
| 10 | Improve duration display format | Small UI tweak |
| 11 | Improve mobile readability | Visual polish, do last to avoid rework |

**Important implementation notes:**
- Items 4, 5, and 6 share cart structure changes. Consider implementing them together or sequentially in one patch. The current flat-array cart (`[{name, price}, ...]`) will likely need to become a quantity-based structure (`{name: {price, quantity}, ...}` or similar).
- Item 9 (order_id migration) is the largest structural change. If implementation risk is high, do it as a focused separate patch after the smaller cart/submit/validation fixes.
- Do not mix large refactors with visual cleanup unless necessary.

---

## 6. Validation Checklist

### Cart and submission
- [ ] Submit with empty cart — blocked with clear message.
- [ ] Add one item and submit — works normally.
- [ ] Rapidly tap final submit multiple times during a slow/pending request — only one order created.
- [ ] After successful submission, add another item and submit as a legitimate additional order — works normally.
- [ ] Simulate failed submission — retry is possible, button re-enabled.

### Cart editing
- [ ] Add one item, remove it — cart becomes empty.
- [ ] Add multiple different items, remove one item — others remain.
- [ ] Add same item multiple times, adjust quantity with `+` and `-` — works correctly.
- [ ] Decrease quantity to zero — item removed from cart.
- [ ] No negative quantity is possible.
- [ ] Total price is correct after every change.

### Order correctness
- [ ] Serve one item — only that item changes status.
- [ ] Toggle payment for one item — only that item changes.
- [ ] Cancel one item — only that item is cancelled.
- [ ] Delete/cancel one order, then operate on another order — correct item targeted.
- [ ] Batch serve/payment/cancel — correct rows modified.

### Stock
- [ ] Order an item — stock decreases.
- [ ] Cancel that item — stock restores.
- [ ] Sold-out status changes correctly if stock is restored above zero.
- [ ] Failed cancellation does not change stock.

### Timestamps
- [ ] Timestamps display correctly in KST.
- [ ] Entry time does not reset on additional orders.

### Table duration
- [ ] Duration displays correctly for active tables.
- [ ] Duration shows hours + minutes for stays over 60 minutes.
- [ ] Cleared/closed tables do not show misleading active duration.

### Mobile UI
- [ ] Check on narrow mobile viewport (360px).
- [ ] Check cart modal readability.
- [ ] Check `+`, `-`, remove, and final submit buttons are tappable.
- [ ] Check admin/staff action buttons are tappable.
- [ ] No horizontal overflow.
- [ ] Important text is not too small.

---

## 7. Follow-up Not Included in This TODO

The following are intentionally **not** part of this stabilization work:

- Real admin/staff authentication (session-based, token-based, etc.)
- Customer self-ordering
- WebSocket/SSE real-time updates (current 5s polling is acceptable for now)
- Printer/kitchen ticket integration
- Payment gateway integration
- QR code generation
- Full UI redesign
- Multi-language support
- Dark mode
