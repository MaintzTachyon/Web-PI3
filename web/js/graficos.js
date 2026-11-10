let chart;

export function actualizarGrafico(canvas, historial, label) {
  if (typeof Chart === "undefined") return;
  chart?.destroy();
  chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: historial.puntos.map((point) => formatoEje(point.t, historial.rango)),
      datasets: [{ label, data: historial.puntos.map((point) => point.v), borderColor: "#56d6c6", backgroundColor: "#56d6c61c", fill: true, tension: .35, pointRadius: 2 }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { ticks: { color: "#91a3b5", maxTicksLimit: 6 }, grid: { color: "#26364880" } }, y: { ticks: { color: "#91a3b5" }, grid: { color: "#26364880" } } },
    },
  });
}

// En rangos de un día o más, solo la hora se repetiría: se agrega el día.
function formatoEje(t, rango) {
  const fecha = new Date(t);
  if (rango === "24h" || rango === "7d") {
    return fecha.toLocaleString("es-PE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }
  return fecha.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });
}

export function limpiarGrafico() {
  chart?.destroy();
  chart = undefined;
}
