import { sensoresDemo } from "../data/sensores-demo.js";

// Servido por el backend (puerto 8000 o producción) → mismo origen.
// Servido aparte con Live Server / http.server (puerto 5500) → API en 127.0.0.1:8000.
const DEV_PORTS = ["5500", "5501"];
export const API_BASE = window.GEMELO_API_BASE ?? (DEV_PORTS.includes(location.port) ? "http://127.0.0.1:8000" : "");
const REINTENTO_MS = 5000;
let demoMode = false;

async function request(path) {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`API ${response.status}`);
  return response.json();
}

export async function cargarCatalogo() {
  return request("/api/v1/sensores");
}

export async function cargarUltimas() {
  if (demoMode) {
    return { aula: "L419", generado: new Date().toISOString(), origen: "demo", sensores: sensoresDemo.map((sensor) => ({ ...sensor, actualizado: new Date().toISOString() })) };
  }
  return request("/api/v1/lecturas/ultimas");
}

export async function cargarHistorial(id, variable, rango = "1h") {
  if (demoMode) {
    const now = Date.now();
    const points = Array.from({ length: 20 }, (_, index) => ({ t: new Date(now - (19 - index) * 180000).toISOString(), v: 50 + Math.sin(index / 2) * 5 }));
    return { id, variable, unidad: "dB", rango, ventana_s: 30, puntos: points };
  }
  return request(`/api/v1/sensores/${encodeURIComponent(id)}/historial?variable=${encodeURIComponent(variable)}&rango=${rango}`);
}

export function activarDemo() {
  demoMode = true;
}

export function desactivarDemo() {
  demoMode = false;
}

export function suscribirStream({ onReading, onConnection, onError }) {
  if (demoMode) return () => {};
  let stream;
  let retry;
  let cerrado = false;
  const abrir = () => {
    stream = new EventSource(`${API_BASE}/api/v1/stream`);
    stream.addEventListener("lectura", (event) => onReading(JSON.parse(event.data)));
    stream.addEventListener("conexion", (event) => onConnection(JSON.parse(event.data)));
    stream.onerror = () => {
      onError();
      // EventSource reintenta solo; si el servidor lo cerró del todo, se reabre a mano.
      if (stream.readyState === EventSource.CLOSED && !cerrado) {
        window.clearTimeout(retry);
        retry = window.setTimeout(abrir, REINTENTO_MS);
      }
    };
  };
  abrir();
  return () => {
    cerrado = true;
    window.clearTimeout(retry);
    stream?.close();
  };
}
