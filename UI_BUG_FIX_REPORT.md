# UI Bug Fix Report

Date: 2026-06-04

## Summary

Fixed the notification "Mark all read" flow and the sidebar collapse layout breakage at the root cause level. Notification reads now persist to the database and return fresh unread counts. Sidebar collapse no longer mixes Bootstrap Collapse with custom shell resizing, so desktop collapse is a stable 260px to 70px grid transition and mobile/tablet behavior remains an overlay.

## Issue 1: Notification Mark All Read

### Root Cause

- `mark_all_notifications_read` updated rows without a durable service contract in the current implementation path.
- The API returned only `{"ok": true}`, so the frontend had no immediate authoritative unread count after marking reads.
- The dropdown button click was allowed to bubble through the dropdown, which could close or destabilize the menu before the refreshed state rendered.
- Existing tests only asserted a non-negative unread count, so a broken persistence path could pass.

### Fix

- `app/services/notification_service.py`
  - Bulk read updates now commit the transaction and return the updated row count.
  - Single notification reads commit and return the notification.
- `app/routes/notification.py`
  - `POST /notifications/mark_all_read` now returns `ok`, `updated`, and fresh `count`.
  - `POST /notifications/mark_read/<id>` now returns `ok` and fresh `count`.
- `app/static/js/main.js`
  - Updates the badge immediately from API response counts.
  - Refreshes the dropdown after the write.
  - Prevents the "Mark all read" click from closing/bubbling before state refresh.
- `tests/test_notifications.py`
  - Covers two unread notifications, single read, mark all read, persisted zero count, and refreshed dropdown payload state.

### Before vs After

Before:
- Clicking "Mark all read" could close the dropdown while unread badges remained unchanged.
- Notifications could still appear unread after refresh.
- Tests did not catch the failure.

After:
- Single notification read changes unread count immediately.
- "Mark all read" changes unread count to zero immediately.
- `/notifications/recent` stays at zero after the write, matching page refresh behavior.
- Database persistence is covered by tests.

## Issue 2: Sidebar Collapse Layout

### Root Cause

- The hamburger button used Bootstrap Collapse attributes while `ui.js` also applied a custom `.sidebar-collapsed` desktop state.
- On desktop, Bootstrap could remove the sidebar from layout while CSS expected a reduced-width sidebar column.
- Sidebar labels were plain text nodes, but CSS tried to hide only child spans, so labels could remain squeezed inside the collapsed rail and render vertically.
- The main content grid used a plain `1fr` column, which can preserve overflowing child widths instead of allowing dashboard cards/charts to reflow cleanly.

### Fix

- `app/templates/base.html`
  - Removed Bootstrap Collapse wiring from the sidebar toggle.
  - Removed `collapse show` from the sidebar container.
- `app/static/js/ui.js`
  - Desktop toggles only `.sidebar-collapsed` and persists it in `localStorage`.
  - Mobile/tablet toggles `.show` plus backdrop.
  - Resets state on breakpoint changes.
  - Dispatches resize after desktop collapse so charts can recalculate.
- `app/static/css/style.css`
  - Expanded sidebar width: `260px`.
  - Collapsed sidebar width: `70px`.
  - App shell uses `minmax(0, 1fr)` so content can expand/reflow.
  - Sidebar links use `font-size: 0` when collapsed to hide plain text labels while keeping icons readable.
  - Main content and container have `min-width: 0` to prevent grid overflow/whitespace.

### Before vs After

Before:
- Dashboard cards could collapse into unreadable narrow columns.
- Sidebar text could become vertical.
- Large whitespace could appear after the hamburger click.
- Bootstrap and custom sidebar behavior fought each other.

After:
- Desktop collapse is a stable 260px to 70px transition.
- Icons remain visible and labels are hidden.
- Content column expands and dashboard grid can reflow.
- Mobile/tablet uses overlay sidebar behavior without desktop collapsed state.

## Files Modified

- `app/services/notification_service.py`
- `app/routes/notification.py`
- `app/static/js/main.js`
- `app/static/js/ui.js`
- `app/static/css/style.css`
- `app/templates/base.html`
- `tests/test_notifications.py`
- `UI_BUG_FIX_REPORT.md`

## Validation Results

### Automated Tests

- Focused notification test:
  - Command: `.\\venv\\Scripts\\python.exe -m pytest tests\\test_notifications.py`
  - Result: `1 passed, 6 warnings`
- Full test suite:
  - Command: `.\\venv\\Scripts\\python.exe -m pytest`
  - Result: `206 passed, 514 warnings in 300.40s`

### Authenticated Smoke Verification

Used isolated Flask testing config with an in-memory database and seeded admin user.

- Login: `200`
- Notifications:
  - Initial unread count: `2`
  - After single read: `1`
  - After mark all read: `0`
  - Refreshed unread count: `0`
- Major pages rendered with app shell/sidebar layout:
  - `/dashboard`: `200`
  - `/products/`: `200`
  - `/suppliers/`: `200`
  - `/warehouses/`: `200`
  - `/purchase-orders/`: `200`
  - `/sales/`: `200`
  - `/invoices/`: `200`
  - `/returns/`: `200`
  - `/reports/`: `200`

### Browser / Viewport Verification

- Flask dev server started successfully at `http://127.0.0.1:5000`.
- Browser CLI verification could not be completed because `agent-browser` is not installed in this environment.
- The route smoke confirms the templates and shared layout render, but final visual viewport checks at 1920px, 1366px, and 768px should still be clicked through manually in a browser.
