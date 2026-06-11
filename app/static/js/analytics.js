document.addEventListener('DOMContentLoaded', () => {
  if (typeof Chart === 'undefined' || typeof chartData === 'undefined') return;

  function finishLoading(id) {
    const card = document.querySelector(`[data-chart="${id}"]`);
    if (card) card.classList.remove('chart-loading');
  }

  function chart(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    new Chart(canvas, config);
    finishLoading(id);
  }

  chart('salesTrendChart', {
    type: 'line',
    data: {
      labels: chartData.monthly_labels || [],
      datasets: [{ label: 'Revenue', data: chartData.monthly_revenue || [], borderColor: '#2563eb', tension: 0.3 }],
    },
  });

  chart('movementChart', {
    type: 'bar',
    data: {
      labels: chartData.movement_labels || [],
      datasets: [
        { label: 'Incoming', data: chartData.incoming_values || [], backgroundColor: '#22c55e' },
        { label: 'Outgoing', data: chartData.outgoing_values || [], backgroundColor: '#f59e0b' },
      ],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });

  chart('stockTrendChart', {
    type: 'line',
    data: {
      labels: chartData.movement_labels || [],
      datasets: [{ label: 'Stock Quantity', data: chartData.stock_trend_values || [], borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,.12)', fill: true, tension: 0.35 }],
    },
    options: { responsive: true, scales: { y: { beginAtZero: true } } },
  });

  chart('topProductsChart', {
    type: 'bar',
    data: {
      labels: chartData.top_product_labels || [],
      datasets: [{ label: 'Units Sold', data: chartData.top_product_values || [], backgroundColor: '#14b8a6' }],
    },
  });

  chart('inventoryStatusChart', {
    type: 'doughnut',
    data: {
      labels: chartData.inventory_status_labels || [],
      datasets: [{ data: chartData.inventory_status_values || [], backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'] }],
    },
  });

  chart('categoryChart', {
    type: 'pie',
    data: {
      labels: chartData.category_labels || [],
      datasets: [{ data: chartData.category_values || [], backgroundColor: ['#2563eb', '#7c3aed', '#f97316', '#10b981', '#e11d48'] }],
    },
  });
});
