<script>
  import { onMount } from 'svelte';
  import Chart from 'chart.js/auto';

  let { data = [], title = "Today's Detections by Hour" } = $props();
  let canvas = $state(null);
  let chart = null;

  function getGradient(ctx) {
    const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
    gradient.addColorStop(0, 'rgba(34, 197, 94, 0.8)');
    gradient.addColorStop(1, 'rgba(34, 197, 94, 0.1)');
    return gradient;
  }

  function renderChart() {
    if (!canvas || !data.length) return;
    const ctx = canvas.getContext('2d');
    const isDark = document.documentElement.classList.contains('dark');

    if (chart) chart.destroy();

    const now = new Date();
    const currentHour = now.getHours();

    chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => `${d.hour}:00`),
        datasets: [{
          label: 'Detections',
          data: data.map(d => d.count),
          backgroundColor: data.map(d =>
            d.hour === currentHour
              ? 'rgba(34, 197, 94, 1)'
              : 'rgba(34, 197, 94, 0.6)'
          ),
          borderRadius: 4,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          title: {
            display: true,
            text: title,
            color: isDark ? '#d1d5db' : '#374151',
            font: { size: 14, weight: '600' },
            padding: { bottom: 16 },
          },
          tooltip: {
            backgroundColor: isDark ? '#1f2937' : '#fff',
            titleColor: isDark ? '#f3f4f6' : '#111827',
            bodyColor: isDark ? '#d1d5db' : '#4b5563',
            borderColor: isDark ? '#374151' : '#e5e7eb',
            borderWidth: 1,
            cornerRadius: 8,
            padding: 10,
            callbacks: {
              title: (items) => {
                const h = parseInt(items[0].label);
                return `${h}:00 - ${h + 1}:00`;
              },
              label: (item) => `${item.raw} detection${item.raw !== 1 ? 's' : ''}`,
            },
          },
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: {
              color: isDark ? '#9ca3af' : '#6b7280',
              maxRotation: 0,
              callback: (val, i) => i % 3 === 0 ? data[i]?.hour + ':00' : '',
            },
          },
          y: {
            beginAtZero: true,
            grid: { color: isDark ? '#1f2937' : '#f3f4f6' },
            ticks: {
              color: isDark ? '#9ca3af' : '#6b7280',
              stepSize: 1,
              precision: 0,
            },
          },
        },
        animation: { duration: 600, easing: 'easeOutQuart' },
      },
    });
  }

  $effect(() => {
    if (data && canvas) renderChart();
  });

  onMount(() => {
    return () => { if (chart) chart.destroy(); };
  });
</script>

<div class="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-5">
  <div class="h-64 md:h-80">
    <canvas bind:this={canvas}></canvas>
  </div>
</div>
