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
    titulo: "BACKEND",
    descripcion: "Cómo funciona el servidor con FastAPI: recibe las peticiones del juego, consulta la base de datos y responde a la página.",
    youtube: "https://youtu.be/ZnD-XId83ys?si=_E9Ae_nPHNkBoY8W",
    archivo: "",
  },
  {
    titulo: "FRONTED",
    descripcion: "La parte visual del proyecto hecha con Astro y Svelte: páginas, tablero interactivo, galería y audios en jñatjo.",
    youtube: "https://youtu.be/av7-CJd_CEo?si=OOwnXibPDph2lN-j",
    archivo: "",
  },
  {
    titulo: "LECTOR RFID",
    descripcion: "Cómo el lector RFID detecta cada tarjeta física de la lotería y la envía al servidor para cantarla en el juego.",
    youtube: "https://youtu.be/RBHUbg6xmKE?si=BioXQ24ppLaw_4RU",
    archivo: "",
  },
  {
    titulo: "RECURSOS MULTIMEDIA",
    descripcion: "Las imágenes y los audios de las tarjetas: cada palabra con su ilustración y su pronunciación en lengua mazahua.",
    youtube: "https://youtu.be/wFHY27v4cl4?si=IDaFpZTyRM-a5Tw2",
    archivo: "",
  },
];
