let chart;

export function actualizarGrafico(canvas, historial, label) {
  if (typeof Chart === "undefined") return;
  chart?.destroy();
  chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: historial.puntos.map((point) => new Date(point.t).toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" })),
      datasets: [{ label, data: historial.puntos.map((point) => point.v), borderColor: "#56d6c6", backgroundColor: "#56d6c61c", fill: true, tension: .35, pointRadius: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: "#91a3b5", maxTicksLimit: 6 }, grid: { color: "#26364880" } }, y: { ticks: { color: "#91a3b5" }, grid: { color: "#26364880" } } },
    },
  });
}

export function limpiarGrafico() {
  chart?.destroy();
  chart = undefined;
}
