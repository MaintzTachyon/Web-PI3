// Configuración centralizada del aula L418.
//
// Para mover un sensor de ubicación, edita aquí sus coordenadas (x, y).
// El sistema de coordenadas corresponde al viewBox del plano SVG: 0 0 900 560.
// No es necesario tocar el SVG, el CSS ni el renderizador de marcadores.
//
// Los ids, tipos y variables principales deben coincidir con
// backend/config/sensores.yaml, que es la fuente de verdad que expone la API.
export const AULA = "L418";

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
    y: 125,
    decimales: 1,
  },
  {
    id: "sensor-luz-01",
    tipo: "luz",
    medicion: "luz",
    etiqueta: "Luminosidad",
    unidad: "lux",
    variable_principal: "lux",
    x: 550,
    y: 125,
    decimales: 0,
  },
  {
    id: "sensor-termico-01",
    tipo: "termico",
    medicion: "termico",
    etiqueta: "Ocupación",
    unidad: "personas",
    variable_principal: "ocupacion_est",
    x: 75,
    y: 230,
    decimales: 0,
  },
  {
    id: "sensor-magnetico-01",
    tipo: "magnetico",
    medicion: "magnetico",
    etiqueta: "Puerta",
    unidad: "",
    variable_principal: "puerta_abierta",
    formato: "puerta",
    x: 75,
    y: 290,
    decimales: 0,
  },
  {
    id: "sensor-ambiente-01",
    tipo: "ambiente",
    medicion: "ambiente",
    etiqueta: "Ambiente",
    unidad: "°C",
    variable_principal: "temp_c",
    x: 550,
    y: 310,
    decimales: 2,
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
