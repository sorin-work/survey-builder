// Renders the result charts. Each <canvas data-chart="..."> carries its own
// data as JSON: {kind: "bar" | "pie", labels: [...], counts: [...]}.
(function () {
  const palette = ["#3b5bdb", "#f59f00", "#2b8a3e", "#c92a2a", "#7048e8", "#1098ad", "#e8590c", "#5c940d"];

  function render(canvas) {
    const spec = JSON.parse(canvas.dataset.chart);
    const isPie = spec.kind === "pie";
    const isLine = spec.kind === "line";
    new Chart(canvas, {
      type: isPie ? "doughnut" : isLine ? "line" : "bar",
      data: {
        labels: spec.labels,
        datasets: [
          {
            data: spec.counts,
            backgroundColor: isPie ? spec.labels.map((_, i) => palette[i % palette.length]) : palette[0],
            borderRadius: isPie ? 0 : 4,
            borderColor: palette[0],
            tension: 0.25,
            fill: false,
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { display: isPie, position: "right" } },
        scales: isPie
          ? {}
          : {
              y: spec.signed
                ? { min: -100, max: 100, ticks: { stepSize: 50 } }
                : { beginAtZero: true, ticks: { precision: 0 } },
            },
      },
    });
  }

  document.querySelectorAll("canvas[data-chart]").forEach(render);
})();
