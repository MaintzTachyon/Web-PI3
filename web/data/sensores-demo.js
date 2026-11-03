export const sensoresDemo = [
  {
    id: "sensor-co2-01", nodo: 1, tipo: "co2", etiqueta: "CO₂", valor: 650,
    unidad: "ppm", estado: "normal", actualizado: new Date().toISOString(), edad_s: 0,
    variables: { co2_ppm: { valor: 650, unidad: "ppm", etiqueta: "CO₂" }, delta_30s: { valor: 4, unidad: "ppm", etiqueta: "Cambio en 30 s" } },
    anomalias: [], diagnostico: { seq: 1234, perdidos: 0 },
  },
  {
    id: "sensor-audio-01", nodo: 2, tipo: "audio", etiqueta: "Ruido", valor: 48.2,
    unidad: "dB", estado: "normal", actualizado: new Date().toISOString(), edad_s: 0,
    variables: { leq_db: { valor: 48.2, unidad: "dB", etiqueta: "Nivel equivalente" }, lmax_db: { valor: 56.4, unidad: "dB", etiqueta: "Máximo" } },
    anomalias: [], diagnostico: { seq: 9876, perdidos: 0 },
  },
];
