document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-confirm]').forEach((button) => {
    button.addEventListener('click', (event) => {
      if (!window.confirm(button.dataset.confirm)) {
        event.preventDefault();
      }
    });
  });
});

function makeTableSortable(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const headers = table.querySelectorAll('thead th[data-sort]');
  let currentCol = null;
  let ascending = true;

  headers.forEach((th) => {
    th.style.cursor = 'pointer';
    th.style.userSelect = 'none';
    th.setAttribute('title', 'Click to sort');
    th.addEventListener('click', () => {
      const col = th.dataset.sort;
      ascending = currentCol === col ? !ascending : true;
      currentCol = col;
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {
        const colIndex = th.cellIndex;
        const aText = a.cells[colIndex] ? a.cells[colIndex].textContent.trim() : '';
        const bText = b.cells[colIndex] ? b.cells[colIndex].textContent.trim() : '';
        const aNum = parseFloat(aText.replace(/[^0-9.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^0-9.-]/g, ''));
        if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
          return ascending ? aNum - bNum : bNum - aNum;
        }
        return ascending ? aText.localeCompare(bText) : bText.localeCompare(aText);
      });
      rows.forEach((row) => tbody.appendChild(row));
      headers.forEach((header) => {
        header.textContent = header.textContent.replace(' ↑', '').replace(' ↓', '');
      });
      th.textContent += ascending ? ' ↑' : ' ↓';
    });
  });
}

function initSaleTotals() {
  const productSelect = document.getElementById('product_id');
  const priceInput = document.getElementById('selling_price');
  const quantityInput = document.getElementById('quantity');
  const totalPreview = document.getElementById('sale-total-preview');
  const totalValue = document.getElementById('sale-total-value');

  if (!productSelect || !priceInput || !quantityInput || !totalPreview || !totalValue) return;

  function updateTotal() {
    const price = parseFloat(priceInput.value) || 0;
    const qty = parseInt(quantityInput.value, 10) || 0;
    const total = price * qty;
    if (price > 0 && qty > 0) {
      totalValue.textContent = 'INR ' + total.toFixed(2);
      totalPreview.classList.remove('d-none');
    } else {
      totalPreview.classList.add('d-none');
    }
  }

  productSelect.addEventListener('change', function () {
    const pid = parseInt(this.value, 10);
    const price = window.PRODUCT_PRICES ? window.PRODUCT_PRICES[pid] : undefined;
    if (price !== undefined) {
      priceInput.value = Number(price).toFixed(2);
    }
    updateTotal();
  });

  priceInput.addEventListener('input', updateTotal);
  quantityInput.addEventListener('input', updateTotal);
  updateTotal();
}

function initStockPreviews() {
  const productSelect = document.getElementById('product_id');
  const quantityInput = document.getElementById('quantity');
  const meta = window.PRODUCT_META || {};
  if (!productSelect || !quantityInput) return;

  function productInfo() {
    return meta[parseInt(productSelect.value, 10)] || { quantity: 0, low_stock_limit: 0 };
  }

  function setAlert(el, type, message) {
    if (!el) return;
    el.className = `alert alert-${type} mt-3 mb-0`;
    el.textContent = message;
  }

  function updateIncoming() {
    const currentEl = document.getElementById('incoming-current');
    if (!currentEl) return;
    const qtyEl = document.getElementById('incoming-qty');
    const projectedEl = document.getElementById('incoming-projected');
    const validationEl = document.getElementById('incoming-validation');
    const info = productInfo();
    const incoming = parseInt(quantityInput.value, 10) || 0;
    const projected = Number(info.quantity || 0) + incoming;
    currentEl.textContent = info.quantity || 0;
    qtyEl.textContent = incoming;
    projectedEl.textContent = projected;
    if (incoming <= 0) setAlert(validationEl, 'warning', 'Quantity is required and must be positive.');
    else if (incoming > 100000) setAlert(validationEl, 'danger', 'Quantity is above the allowed receive limit.');
    else setAlert(validationEl, 'success', 'Projected stock looks valid.');
  }

  function updateOutgoing() {
    const currentEl = document.getElementById('outgoing-current');
    if (!currentEl) return;
    const qtyEl = document.getElementById('outgoing-qty');
    const remainingEl = document.getElementById('outgoing-remaining');
    const validationEl = document.getElementById('outgoing-validation');
    const submit = document.getElementById('outgoing-submit');
    const info = productInfo();
    const requested = parseInt(quantityInput.value, 10) || 0;
    const remaining = Number(info.quantity || 0) - requested;
    currentEl.textContent = info.quantity || 0;
    qtyEl.textContent = requested;
    remainingEl.textContent = remaining;
    if (requested <= 0) {
      setAlert(validationEl, 'warning', 'Quantity is required and must be positive.');
      if (submit) submit.disabled = true;
    } else if (remaining < 0) {
      setAlert(validationEl, 'danger', 'Insufficient stock. This dispatch cannot be saved.');
      if (submit) submit.disabled = true;
    } else {
      setAlert(validationEl, remaining <= Number(info.low_stock_limit || 0) ? 'warning' : 'success', 'Stock validation passed.');
      if (submit) submit.disabled = false;
    }
  }

  productSelect.addEventListener('change', () => {
    updateIncoming();
    updateOutgoing();
  });
  quantityInput.addEventListener('input', () => {
    updateIncoming();
    updateOutgoing();
  });
  updateIncoming();
  updateOutgoing();
}

function initPriceUpdatePreview() {
  const form = document.querySelector('[data-price-update]');
  if (!form) return;
  const productSelect = document.getElementById('product_id');
  const currentInput = document.getElementById('current_price');
  const newPriceInput = document.getElementById('new_price');
  const marginPreview = document.getElementById('margin-preview');
  const prices = window.PRODUCT_PRICES || {};
  const costs = window.PRODUCT_COSTS || {};

  function update() {
    const productId = parseInt(productSelect.value, 10);
    const currentPrice = Number(prices[productId] || 0);
    const cost = Number(costs[productId] || 0);
    const newPrice = Number(newPriceInput.value || currentPrice || 0);
    currentInput.value = currentPrice.toFixed(2);
    const margin = newPrice > 0 ? ((newPrice - cost) / newPrice) * 100 : 0;
    marginPreview.textContent = `Expected gross margin: ${margin.toFixed(2)}%`;
    marginPreview.className = `alert ${newPrice < 0 ? 'alert-danger' : margin < 0 ? 'alert-warning' : 'alert-info'}`;
  }

  productSelect.addEventListener('change', update);
  newPriceInput.addEventListener('input', update);
  update();
}

document.addEventListener('DOMContentLoaded', () => {
  makeTableSortable('products-table');
  makeTableSortable('sales-table');
  initSaleTotals();
  initStockPreviews();
  initPriceUpdatePreview();
});

document.addEventListener('DOMContentLoaded', () => {
  const badge = document.getElementById('notificationBadge');
  const list = document.getElementById('notificationList');
  const markAllButton = document.getElementById('markAllNotificationsRead');
  const toastContainer = document.querySelector('.app-toast-container');
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
  let seenUnreadIds = new Set();

  if (!badge || !list) {
    return;
  }

  function iconFor(type) {
    if (type === 'warning') return 'bi-exclamation-triangle';
    if (type === 'success') return 'bi-check-circle';
    if (type === 'danger') return 'bi-x-circle';
    return 'bi-info-circle';
  }

  function updateBadge(count) {
    badge.textContent = count > 99 ? '99+' : String(count);
    badge.classList.toggle('d-none', count <= 0);
  }

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value;
    return div.innerHTML;
  }

  function renderNotifications(notifications) {
    if (!notifications.length) {
      list.innerHTML = '<div class="notification-empty">No notifications yet.</div>';
      return;
    }

    list.innerHTML = notifications.map((notification) => `
      <button class="notification-item ${notification.is_read ? '' : 'is-unread'}" type="button" data-notification-id="${notification.id}">
        <span class="notification-icon notification-${notification.type}">
          <i class="bi ${iconFor(notification.type)}"></i>
        </span>
        <span class="notification-copy">
          <span class="notification-message">${escapeHtml(notification.message)}</span>
          <span class="notification-time">${escapeHtml(notification.created_at)}</span>
        </span>
      </button>
    `).join('');
  }

  function showNotificationToast(notification) {
    if (!toastContainer) return;

    const toastEl = document.createElement('div');
    toastEl.className = `toast text-bg-${notification.type || 'info'} border-0 app-toast`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    toastEl.dataset.bsDelay = '4500';
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${escapeHtml(notification.message)}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    `;
    toastContainer.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
  }

  async function postNotification(url) {
    const response = await fetch(url, {
      method: 'POST',
      headers: csrfToken ? { 'X-CSRFToken': csrfToken } : {},
    });
    if (!response.ok) throw new Error('Notification request failed');
    return response.json();
  }

  async function fetchNotifications(showToasts = false) {
    const response = await fetch('/notifications/recent');
    if (!response.ok) return;

    const data = await response.json();
    const notifications = data.notifications || [];
    updateBadge(data.count || 0);
    renderNotifications(notifications);

    const unreadIds = new Set(notifications.filter((item) => !item.is_read).map((item) => item.id));
    if (showToasts) {
      notifications
        .filter((item) => !item.is_read && !seenUnreadIds.has(item.id))
        .forEach(showNotificationToast);
    }
    seenUnreadIds = unreadIds;
  }

  list.addEventListener('click', async (event) => {
    const item = event.target.closest('[data-notification-id]');
    if (!item) return;

    const result = await postNotification(`/notifications/mark_read/${item.dataset.notificationId}`);
    if (typeof result.count === 'number') {
      updateBadge(result.count);
    }
    await fetchNotifications(false);
  });

  if (markAllButton) {
    markAllButton.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();

      const result = await postNotification('/notifications/mark_all_read');
      if (typeof result.count === 'number') {
        updateBadge(result.count);
      }
      await fetchNotifications(false);
    });
  }

  fetchNotifications(false);
  window.setInterval(() => fetchNotifications(true), 30000);
});
