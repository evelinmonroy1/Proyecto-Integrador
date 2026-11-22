// Avatares kawaii 3D por capas (como en Kahoot).
// El avatar se guarda como texto corto:  "k-animal-cabeza-cara-fondo"
// Ejemplo: "k-2-1-0-3"  = conejito + sombrero + sin accesorio de cara + 4.º color de fondo
// Las imágenes de los animalitos están en  public/avatares/

// Medidas de cada animalito (en % del ancho de su imagen):
//   cx, top  = centro y parte alta de la cabeza (ahí se pone el sombrero)
//   ancho    = ancho de la cara
//   ex, ey   = punto medio entre los ojos
//   sep      = distancia entre los ojos
export const ANIMALES = [
  { nombre: "Perrito",   archivo: "/avatares/perrito.webp",   cx: 50, top: 10, ancho: 54, ex: 50,   ey: 31.5, sep: 25.5 },
  { nombre: "Vaquita",   archivo: "/avatares/vaquita.webp",   cx: 50, top: 21, ancho: 44, ex: 51,   ey: 44,   sep: 26.5 },
  { nombre: "Conejito",  archivo: "/avatares/conejito.webp",  cx: 49, top: 12, ancho: 42, ex: 49,   ey: 36,   sep: 23.5 },
  { nombre: "Guajolote", archivo: "/avatares/guajolote.webp", cx: 53, top: 14, ancho: 40, ex: 54.8, ey: 34.6, sep: 22.5 },
  { nombre: "Gatito",    archivo: "/avatares/gatito.webp",    cx: 53, top: 15, ancho: 44, ex: 54.5, ey: 37,   sep: 23 },
  { nombre: "Potrito",   archivo: "/avatares/potrito.webp",   cx: 52, top: 14, ancho: 40, ex: 51.7, ey: 40,   sep: 24.6 },
];

export const CABEZA = ["Ninguno", "Sombrero", "Corona", "Moño", "Flor", "Gorra"];
export const CARA = ["Ninguno", "Lentes", "Lentes de sol"];
export const FONDOS = ["#bcd3b8", "#f0c7a5", "#bfdde3", "#f2e3bd", "#f3b9ad", "#d9c9ee"];
export const NOMBRES_FONDO = ["Verde", "Durazno", "Cielo", "Maíz", "Rosa", "Lila"];

// Cuántas opciones hay en cada posición (en el mismo orden que el texto)
export const CUANTAS = [ANIMALES.length, CABEZA.length, CARA.length, FONDOS.length];

// Si agregas opciones, también hay que ajustar este patrón en el servidor
// (backend/routers/partidas.py, línea PATRON_AVATAR).
export const PATRON = /^k-[0-5](-[0-5]-[0-2]-[0-5])?$/;

export const esAvatar = (texto) => typeof texto === "string" && PATRON.test(texto);

// "k-2-1-0-3" -> [2, 1, 0, 3]      ("k-2" -> [2, 0, 0, 0])
export function leer(texto) {
  if (!esAvatar(texto)) return [0, 0, 0, 0];
  const p = texto.split("-").slice(1).map(Number);
  return [p[0], p[1] ?? 0, p[2] ?? 0, p[3] ?? 0];
}

export const armar = (partes) => "k-" + partes.join("-");

export function aleatorio() {
  return armar(CUANTAS.map((n) => Math.floor(Math.random() * n)));
}

// Cambia una sola parte y devuelve el texto nuevo
export function cambiar(texto, posicion, valor) {
  const partes = leer(texto);
  partes[posicion] = valor;
  return armar(partes);
}

export const nombre = (texto) => ANIMALES[leer(texto)[0]].nombre;