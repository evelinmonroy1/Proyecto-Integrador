import { API } from "./config.js";

// Audio compartido: se usa en la pantalla del jugador cuando sale una tarjeta.
const CLAVE = "sonido-loteria";
const SILENCIO = "data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

let silenciado = false;
try {
  silenciado = localStorage.getItem(CLAVE) === "off";
} catch {}

let actual = null;
let desbloqueado = false;

export const estaActivo = () => !silenciado;

export function detener() {
  actual?.pause();
  actual = null;
}

export function fijarActivo(valor) {
  silenciado = !valor;
  try {
    localStorage.setItem(CLAVE, valor ? "on" : "off");
  } catch {}
  if (!valor) detener();
}

// Los navegadores del celular solo dejan sonar el audio después de un toque.
// Con el primer toque en la página se reproduce un sonido vacío para "abrir" el audio.
export function desbloquear() {
  if (desbloqueado || typeof Audio === "undefined") return;
  const a = new Audio(SILENCIO);
  a.play()
    .then(() => {
      desbloqueado = true;
      document.removeEventListener("pointerdown", desbloquear);
    })
    .catch(() => {});
}

if (typeof document !== "undefined") {
  document.addEventListener("pointerdown", desbloquear, { passive: true });
}

// forzar = true: suena aunque el jugador tenga el sonido apagado (botón "Escuchar")
export async function reproducir(palabra, forzar = false) {
  if (!palabra?.audio_url) return false;
  if (silenciado && !forzar) return false;
  detener();
  actual = new Audio(`${API}${palabra.audio_url}`);
  try {
    await actual.play();
    return true;
  } catch {
    return false;
  }
}