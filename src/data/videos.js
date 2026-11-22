// ============================================================
//  VIDEOS DEL SITIO
//  Para agregar un video, copia uno de los bloques { ... } y cambia sus datos.
//
//  Hay dos formas de poner un video:
//
//  1) De YouTube: pega el enlace completo en "youtube".
//       youtube: "https://www.youtube.com/watch?v=XXXXXXXXXXX"
//     (también sirven los enlaces cortos https://youtu.be/XXXXXXXXXXX)
//
//  2) Un archivo propio (.mp4): guárdalo en la carpeta public/videos/
//     y escribe su nombre en "archivo".
//       archivo: "/videos/mi-video.mp4"
//
//  Si un bloque no tiene ni "youtube" ni "archivo", se muestra como
//  "Próximamente" (sirve para dejar el espacio apartado).
// ============================================================

export const videos = [
  {
    titulo: "¿Cómo se juega la Lotería Mazahua?",
    descripcion: "Explicación del juego: cómo entrar con el código, marcar tu tablero y ganar.",
    youtube: "",
    archivo: "",
  },
  {
    titulo: "Saludos en mazahua",
    descripcion: "Aprende a decir buenos días, buenas tardes y buenas noches en jñatjo.",
    youtube: "",
    archivo: "",
  },
  {
    titulo: "Partes del cuerpo",
    descripcion: "Escucha y repite las partes del cuerpo en lengua mazahua.",
    youtube: "",
    archivo: "",
  },
  {
    titulo: "Presentación del proyecto",
    descripcion: "Cómo construimos la lotería: tarjetas RFID, servidor y página web.",
    youtube: "",
    archivo: "",
  },
];
