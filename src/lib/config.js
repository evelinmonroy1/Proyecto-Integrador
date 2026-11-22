// Dónde está el servidor (la API).
// - En desarrollo (npm run dev, puerto 4321) el servidor está en el puerto 8000.
// - Ya publicado, la página y la API salen del MISMO servidor: no hay que configurar nada.
const enNavegador = typeof window !== "undefined";
const desarrollo = enNavegador && window.location.port === "4321";
const host = enNavegador ? window.location.hostname : "127.0.0.1";

export const API = !enNavegador
  ? ""
  : desarrollo
    ? `http://${host}:8000`
    : window.location.origin;

export const WS = !enNavegador
  ? ""
  : desarrollo
    ? `ws://${host}:8000`
    : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
