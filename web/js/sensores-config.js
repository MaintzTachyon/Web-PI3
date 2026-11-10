// Configuración centralizada del aula L419.
//
// Para mover un sensor de ubicación, edita aquí sus coordenadas (x, y).
// El sistema de coordenadas corresponde al viewBox del plano SVG: 0 0 900 560.
// No es necesario tocar el SVG, el CSS ni el renderizador de marcadores.
export const AULA = "L419";

export const SENSORES_CONFIG = [
  {
    id: "sensor-co2-01",
    tipo: "co2",
    medicion: "co2",
    etiqueta: "CO₂",
    unidad: "ppm",
    variable_principal: "co2_ppm",
    x: 115,
    y: 125,
    decimales: 0,
  },
  {
    id: "sensor-audio-01",
    tipo: "audio",
    medicion: "audio",
    etiqueta: "Ruido",
    unidad: "dB",
    variable_principal: "leq_db",
    x: 785,
    y: 420,
    decimales: 1,
  },
  {
    id: "sensor-temperatura-01",
    tipo: "temperatura",
    medicion: "temperatura",
    etiqueta: "Temperatura",
    unidad: "°C",
    variable_principal: "temperatura_c",
    x: 500,
    y: 125,
    decimales: 1,
  },
  {
    id: "sensor-humedad-01",
    tipo: "humedad",
    medicion: "humedad",
    etiqueta: "Humedad",
    unidad: "%",
    variable_principal: "humedad_pct",
    x: 160,
    y: 310,
    decimales: 0,
  },
  {
    id: "sensor-luminosidad-01",
    tipo: "luminosidad",
    medicion: "luminosidad",
    etiqueta: "Luminosidad",
    unidad: "lux",
    variable_principal: "iluminancia_lux",
    x: 550,
    y: 310,
    decimales: 0,
  },
  {
    id: "sensor-presencia-01",
    tipo: "presencia",
    medicion: "presencia",
    etiqueta: "Presencia",
    unidad: "personas",
    variable_principal: "personas",
    x: 450,
    y: 300,
    decimales: 0,
  },
];

export function obtenerConfiguracion(id) {
  return SENSORES_CONFIG.find((s) => s.id === id);
}

export function obtenerUbicaciones() {
  return Object.fromEntries(
    SENSORES_CONFIG.map((s) => [s.id, { x: s.x, y: s.y }])
  );
}

export function obtenerIds() {
  return SENSORES_CONFIG.map((s) => s.id);
}
