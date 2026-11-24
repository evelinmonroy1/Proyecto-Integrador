<script>
  import "../lib/auth.js";
  import { onMount } from "svelte";
  import { API, WS } from "../lib/config.js";
  import Podio from "./Podio.svelte";
  import Avatar from "./Avatar.svelte";

  // ---------- Formulario ----------
  let filas = $state(2);
  let columnas = $state(2);
  let creando = $state(false);

  // ---------- Partida y sala ----------
  let partida = $state(null);
  let jugadores = $state([]);
  let error = $state("");
  let conectado = $state(false);
  let copiado = $state(false);
  let urlJugar = $state("");
  let iniciando = $state(false);

  // ---------- Juego ----------
  let detecciones = $state([]); // la más reciente primero
  let ganadores = $state([]);
  let palabras = $state([]);
  let enviando = $state(false);
  let sonido = $state(true);
  let sonidoBloqueado = $state(false);

  const casillas = $derived(filas * columnas);
  const enLinea = $derived(jugadores.filter((j) => j.conectado).length);
  const enEspera = $derived(partida?.estado === "espera");
  const enJuego = $derived(partida?.estado === "en_juego");
  const finalizada = $derived(partida?.estado === "finalizada");
  const ultima = $derived(detecciones[0] ?? null);
  const pendientes = $derived(
    palabras.filter((p) => !detecciones.some((d) => d.palabra.id === p.id))
  );
  const medallas = { 1: "🥇", 2: "🥈", 3: "🥉" };

  // Aviso de ¡LOTERÍA! cuando un jugador completa su tablero
  let loteria = $state(null); // el jugador que ganó, mientras se muestra el aviso
  let temporizadorLoteria;
  function mostrarLoteria(jugador) {
    loteria = jugador;
    clearTimeout(temporizadorLoteria);
    temporizadorLoteria = setTimeout(() => (loteria = null), 7000);
  }

  // Mientras la partida está en juego, se ocultan los botones de arriba del panel
  // (Administrar palabras, Vincular tarjetas, Cerrar sesión) para ganar espacio.
  $effect(() => {
    document.body.classList.toggle("en-partida", !!partida && !enEspera);
    return () => document.body.classList.remove("en-partida");
  });

  let socket = null;
  let cerrar = false;
  let reintento;
  let audioActual = null;

  const urlMedia = (ruta) => (ruta ? `${API}${ruta}` : null);

  // ---------- Audio ----------
  function reproducir(palabra) {
    if (!sonido || !palabra.audio_url) return;
    audioActual?.pause();
    audioActual = new Audio(urlMedia(palabra.audio_url));
    audioActual.play().then(() => (sonidoBloqueado = false)).catch((err) => {
      // Solo avisamos si el navegador bloqueó el audio (no si falta el archivo)
      if (err.name === "NotAllowedError") sonidoBloqueado = true;
    });
  }

  // Sonido de fin de partida: el archivo va en public/sonidos/fin.mp3
  function sonarFin() {
    if (!sonido) return;
    audioActual?.pause();
    audioActual = new Audio("/sonidos/fin.mp3");
    audioActual.play().catch(() => {}); // si falta el archivo o el navegador lo bloquea, no pasa nada
  }

  function activarSonido() {
    sonidoBloqueado = false; // este clic desbloquea el audio en el navegador
    if (ultima) reproducir(ultima.palabra);
  }

  // ---------- Crear partida ----------
  async function crearPartida() {
    error = "";
    creando = true;
    try {
      const r = await fetch(`${API}/api/partidas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filas: Number(filas), columnas: Number(columnas) }),
      });
      const datos = await r.json();
      if (!r.ok) {
        error = typeof datos.detail === "string" ? datos.detail : "Revisa los datos";
        return;
      }
      entrarSala(datos);
    } catch {
      error = "No se pudo conectar con el servidor";
    } finally {
      creando = false;
    }
  }

  function entrarSala(p) {
    partida = p;
    localStorage.setItem("admin_codigo", p.codigo);
    if (p.estado !== "espera") cargarJuego();
    conectarWs();
  }

  // Recupera tarjetas y podio del servidor (al recargar o al reconectar)
  async function cargarJuego() {
    try {
      const [rp, rd, rg] = await Promise.all([
        fetch(`${API}/api/palabras`),
        fetch(`${API}/api/partidas/${partida.codigo}/detecciones`),
        fetch(`${API}/api/partidas/${partida.codigo}/podio`),
      ]);
      if (rp.ok) palabras = await rp.json();
      if (rd.ok) detecciones = (await rd.json()).reverse();
      if (rg.ok) ganadores = (await rg.json()).podio;
    } catch {}
  }

  // ---------- WebSocket (con reconexión automática) ----------
  function conectarWs() {
    cerrar = false;
    socket = new WebSocket(`${WS}/api/partidas/${partida.codigo}/ws?rol=admin`);
    socket.onopen = () => {
      conectado = true;
      if (partida.estado !== "espera") cargarJuego(); // recupera lo que se perdió
    };
    socket.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.tipo === "jugadores") jugadores = m.jugadores;
      if (m.tipo === "inicio") {
        partida = m.partida;
        cargarJuego();
      }
      if (m.tipo === "tarjeta") {
        if (!detecciones.some((d) => d.orden === m.orden)) {
          detecciones = [{ orden: m.orden, palabra: m.palabra }, ...detecciones];
        }
        reproducir(m.palabra);
      }
      if (m.tipo === "ganador") {
        if (m.lugar === 1) mostrarLoteria(m.jugador);
        if (!ganadores.some((g) => g.lugar === m.lugar)) {
          ganadores = [...ganadores, { lugar: m.lugar, jugador: m.jugador }].sort(
            (a, b) => a.lugar - b.lugar
          );
        }
      }
      if (m.tipo === "fin") {
        ganadores = m.podio;
        partida = { ...partida, estado: "finalizada" };
        sonarFin();
      }
    };
    socket.onclose = (e) => {
      conectado = false;
      if (!cerrar && e.code !== 4404) reintento = setTimeout(conectarWs, 2000);
    };
  }

  function salirDeSala() {
    cerrar = true;
    clearTimeout(reintento);
    socket?.close();
    audioActual?.pause();
    clearTimeout(temporizadorLoteria);
  }

  function nuevaPartida() {
    if (enJuego && !confirm("La partida sigue en curso. ¿Descartarla?")) return;
    salirDeSala();
    localStorage.removeItem("admin_codigo");
    partida = null;
    jugadores = [];
    detecciones = [];
    ganadores = [];
    palabras = [];
    loteria = null;
    error = "";
  }

  // ---------- Acciones ----------
  async function iniciar() {
    if (!confirm(`¿Iniciar con ${jugadores.length} jugador(es)? Ya no podrá entrar nadie más.`)) return;
    error = "";
    iniciando = true; // este clic también desbloquea el audio del navegador
    try {
      const r = await fetch(`${API}/api/partidas/${partida.codigo}/iniciar`, { method: "POST" });
      const d = await r.json();
      if (!r.ok) error = typeof d.detail === "string" ? d.detail : "No se pudo iniciar";
      // el cambio de estado llega por el WebSocket
    } catch {
      error = "No se pudo conectar con el servidor";
    } finally {
      iniciando = false;
    }
  }

  async function lanzar(ruta, cuerpo) {
    error = "";
    enviando = true;
    try {
      const r = await fetch(`${API}/api/partidas/${partida.codigo}/${ruta}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      });
      if (!r.ok) {
        const d = await r.json();
        error = typeof d.detail === "string" ? d.detail : "No se pudo registrar la tarjeta";
      }
      // la tarjeta llega por el WebSocket para todos, incluido este panel
    } catch {
      error = "No se pudo conectar con el servidor";
    } finally {
      enviando = false;
    }
  }

  async function expulsar(j) {
    if (!confirm(`¿Expulsar a ${j.nombre}?`)) return;
    error = "";
    try {
      const r = await fetch(`${API}/api/partidas/${partida.codigo}/jugadores/${j.id}`, {
        method: "DELETE",
      });
      if (!r.ok) {
        const d = await r.json();
        error = d.detail ?? "No se pudo expulsar";
      }
    } catch {
      error = "No se pudo conectar con el servidor";
    }
  }

  async function copiarTexto(texto) {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(texto);
        return true;
      }
    } catch {}
    // Método alternativo para http:// con IP (no es un sitio seguro)
    const area = document.createElement("textarea");
    area.value = texto;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {}
    document.body.removeChild(area);
    return ok;
  }

  async function copiarCodigo() {
    const ok = await copiarTexto(partida.codigo);
    if (ok) {
      copiado = true;
      setTimeout(() => (copiado = false), 2000);
    }
  }


  // ---------- Al abrir la página ----------
  // Si la partida ya terminó, también se recupera para volver a ver el podio.
  // El botón "Crear una nueva partida" es lo que cierra la sesión del administrador.
  async function reanudar() {
    const guardado = localStorage.getItem("admin_codigo");
    if (!guardado) return;
    try {
      const r = await fetch(`${API}/api/partidas/${guardado}`);
      if (r.ok) {
        const p = await r.json();
        return entrarSala(p);
      }
      localStorage.removeItem("admin_codigo");
    } catch {}
  }

  onMount(() => {
    urlJugar = `${location.origin}/jugar`;
    reanudar();
    return salirDeSala;
  });
</script>

<!-- ===== Aviso: un jugador completó su tablero ===== -->
{#if loteria}
  <button class="loteria" onclick={() => (loteria = null)} aria-live="assertive">
    <span class="loteria-grande">¡LOTERÍA!</span>
    <span class="loteria-avatar"><Avatar codigo={loteria.avatar} emoji={loteria.emoji} /></span>
    <span class="loteria-nombre">{loteria.nombre}</span>
    <span class="loteria-texto">completó su tablero</span>
  </button>
{/if}

<!-- ===== Tarjeta con el código (se usa en la espera y en el juego) ===== -->
{#snippet codigoCaja()}
  <section class="tarjeta codigo-caja" class:compacto={!enEspera}>
    {#if enEspera}
      <p class="ayuda">Los jugadores entran en <strong>{urlJugar}</strong> con este código:</p>
    {/if}
    <button class="codigo" onclick={copiarCodigo} title="Copiar código">
      {partida.codigo}
    </button>
    <p class="copiar">
      {#if enEspera}
        {copiado ? "¡Copiado!" : "Toca el código para copiarlo"} ·
      {/if}
      Tablero {partida.filas}×{partida.columnas} · {partida.casillas} casillas
    </p>
    <p class="conexion" class:caida={!conectado}>
      {conectado ? "Sala en vivo" : "Reconectando…"}
    </p>
  </section>
{/snippet}

{#if !partida}
  <section class="tarjeta">
    <h2>Nueva partida</h2>
    <p class="ayuda">Elige el tamaño del tablero de los jugadores.</p>

    <div class="tamano">
      <label>
        Filas
        <select bind:value={filas}>
          {#each [2, 3, 4, 5, 6] as n}<option value={n}>{n}</option>{/each}
        </select>
      </label>
      <span class="por">×</span>
      <label>
        Columnas
        <select bind:value={columnas}>
          {#each [2, 3, 4, 5, 6] as n}<option value={n}>{n}</option>{/each}
        </select>
      </label>
    </div>

    <p class="casillas">Cada tablero tendrá <strong>{casillas}</strong> casillas</p>

    {#if error}<p class="error">{error}</p>{/if}

    <button class="boton" onclick={crearPartida} disabled={creando}>
      {creando ? "Creando…" : "Generar código de juego"}
    </button>
  </section>
{:else if enEspera}
  <!-- ===== Sala de espera ===== -->
  {@render codigoCaja()}

  {#if error}<p class="error">{error}</p>{/if}

  <section class="tarjeta">
    <div class="encabezado">
      <h2>Sala de espera</h2>
      <span class="contador">{jugadores.length} jugador{jugadores.length === 1 ? "" : "es"}</span>
    </div>

    {#if jugadores.length === 0}
      <p class="vacio">Esperando jugadores… comparte el código.</p>
    {:else}
      <ul class="lista">
        {#each jugadores as j (j.id)}
          <li class:fuera={!j.conectado}>
            <span class="avatar"><Avatar codigo={j.avatar} emoji={j.emoji} /></span>
            <span class="nombre">{j.nombre}</span>
            <span class="estado">{j.conectado ? "en línea" : "desconectado"}</span>
            <button class="expulsar" onclick={() => expulsar(j)} title="Expulsar">✕</button>
          </li>
        {/each}
      </ul>
      <p class="ayuda">{enLinea} en línea ahora</p>
    {/if}

    <button class="boton iniciar" onclick={iniciar} disabled={jugadores.length === 0 || iniciando}>
      {iniciando ? "Iniciando…" : "▶ Iniciar partida"}
    </button>
  </section>

  <button class="secundario" onclick={nuevaPartida}>Descartar y crear otra partida</button>
{:else}
  <!-- ===== Partida en juego o terminada: 3 columnas que ocupan toda la pantalla ===== -->
  <div class="panel">
    <!-- Columna izquierda: código y controles -->
    <aside class="col izq">
      {@render codigoCaja()}

      {#if error}<p class="error">{error}</p>{/if}

      {#if sonidoBloqueado}
        <div class="aviso-sonido">
          <span>🔇 El navegador bloqueó el audio.</span>
          <button onclick={activarSonido}>Activar sonido</button>
        </div>
      {/if}

      {#if !finalizada}
        <section class="tarjeta controles">
          <div class="encabezado">
            <h2>Control</h2>
            <span class="contador">{detecciones.length} de {palabras.length}</span>
          </div>

          <p class="ayuda">Las tarjetas salen solo cuando el lector RFID detecta una.</p>
          <label class="sonido">
            <input type="checkbox" bind:checked={sonido} />
            Reproducir el audio de cada tarjeta
          </label>
        </section>
      {/if}

      <button class="secundario" onclick={nuevaPartida}>
        {finalizada ? "Crear una nueva partida" : "Descartar y crear otra partida"}
      </button>
    </aside>

    <!-- Columna central: última tarjeta o podio -->
    <section class="col centro" class:con-podio={finalizada}>
      {#if finalizada}
        <Podio {ganadores} grande />
      {:else}
        <section class="tarjeta ultima">
          <h2>Última tarjeta</h2>
          {#if ultima}
            {#key ultima.orden}
              <div class="carta">
                {#if ultima.palabra.imagen_url}
                  <img src={urlMedia(ultima.palabra.imagen_url)} alt={ultima.palabra.mazahua} />
                {/if}
                <p class="mazahua">{ultima.palabra.mazahua}</p>
                <p class="espanol">{ultima.palabra.espanol}</p>
                {#if ultima.palabra.audio_url}
                  <button class="secundario chico" onclick={() => reproducir(ultima.palabra)}>
                    🔊 Escuchar de nuevo
                  </button>
                {/if}
              </div>
            {/key}
          {:else}
            <p class="vacio">Aún no ha salido ninguna tarjeta.</p>
          {/if}
        </section>
      {/if}
    </section>

    <!-- Columna derecha: ganadores, jugadores e historial -->
    <aside class="col der">
      {#if !finalizada}
        <section class="tarjeta">
          <h2>Ganadores</h2>
          {#if ganadores.length === 0}
            <p class="ayuda">Nadie ha completado su tablero todavía.</p>
          {:else}
            <ol class="podio-lista">
              {#each ganadores as g (g.lugar)}
                <li>
                  <span class="medalla">{medallas[g.lugar] ?? g.lugar}</span>
                  <span class="avatar"><Avatar codigo={g.jugador.avatar} emoji={g.jugador.emoji} /></span>
                  <strong>{g.jugador.nombre}</strong>
                </li>
              {/each}
            </ol>
          {/if}
        </section>
      {/if}

      <section class="tarjeta">
        <h2>Jugadores ({jugadores.length})</h2>
        <ul class="lista compacta">
          {#each jugadores as j (j.id)}
            <li class:fuera={!j.conectado}>
              <span class="avatar"><Avatar codigo={j.avatar} emoji={j.emoji} /></span>
              <span class="nombre">{j.nombre}</span>
            </li>
          {/each}
        </ul>
      </section>

      <section class="tarjeta hist">
        <h2>Tarjetas anteriores</h2>
        {#if detecciones.length <= 1}
          <p class="ayuda">Aquí aparecerá el historial.</p>
        {:else}
          <ol class="historial">
            {#each detecciones.slice(1, 13) as d (d.orden)}
              <li>
                <span class="orden">{d.orden}</span>
                {#if d.palabra.imagen_url}
                  <img src={urlMedia(d.palabra.imagen_url)} alt="" />
                {/if}
                <span><strong>{d.palabra.mazahua}</strong><br />{d.palabra.espanol}</span>
              </li>
            {/each}
          </ol>
          {#if detecciones.length > 13}
            <p class="mas">y {detecciones.length - 13} más…</p>
          {/if}
        {/if}
      </section>
    </aside>
  </div>
{/if}

<style>
  .tarjeta {
    background: white;
    border: 2px solid var(--arena);
    border-radius: var(--radio);
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 6px 18px rgba(15, 53, 87, 0.2);
  }
  h2 {
    font-size: 1.3rem;
    margin-bottom: 0.6rem;
  }
  .ayuda {
    color: #4a5d7a;
    margin: 0.4rem 0 1rem;
  }
  .tamano {
    display: flex;
    align-items: flex-end;
    gap: 1rem;
    margin-bottom: 0.8rem;
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-weight: bold;
  }
  select {
    font: inherit;
    padding: 0.6rem 1rem;
    border: 2px solid var(--cafe);
    border-radius: 12px;
    background: var(--crema);
  }
  .por {
    font-size: 1.6rem;
    padding-bottom: 0.4rem;
  }
  .casillas {
    margin: 0 0 1.2rem;
  }
  .boton {
    width: 100%;
    padding: 1rem;
    border: none;
    border-radius: 14px;
    background: var(--verde);
    color: white;
    font-size: 1.15rem;
    font-weight: bold;
    box-shadow: 0 5px 15px rgba(15, 53, 87, 0.2);
  }
  .boton:active {
    transform: translateY(3px);
    box-shadow: 0 2px 6px rgba(15, 53, 87, 0.2);
  }
  .boton:disabled {
    opacity: 0.5;
  }
  .iniciar {
    margin-top: 1.2rem;
    background: var(--terracota-oscuro);
  }
  .error {
    background: #fbe3e1;
    color: #8f2a26;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0 0 1rem;
  }

  /* Código */
  .codigo-caja {
    text-align: center;
    background: var(--arena);
  }
  .codigo {
    font-size: clamp(2.8rem, 12vw, 5rem);
    font-weight: bold;
    letter-spacing: 0.25em;
    padding: 0.2em 0.5em 0.2em 0.75em;
    border: 3px dashed var(--cafe);
    border-radius: 16px;
    background: var(--crema);
    color: var(--terracota-oscuro);
  }
  .compacto {
    padding: 0.8rem 1rem;
  }
  .compacto .codigo {
    font-size: 1.8rem;
  }
  .copiar {
    margin: 0.6rem 0 0;
    color: #4a5d7a;
  }
  .conexion {
    display: inline-block;
    margin: 0.8rem 0 0;
    padding: 0.25rem 0.8rem;
    border-radius: 999px;
    background: #dcefdc;
    color: #1f6a35;
    font-size: 0.9rem;
  }
  .conexion.caida {
    background: #fbe3e1;
    color: #8f2a26;
  }

  /* Listas de jugadores */
  .encabezado {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.8rem;
  }
  .contador {
    background: var(--salvia);
    color: white;
    padding: 0.25rem 0.9rem;
    border-radius: 999px;
    font-weight: bold;
    white-space: nowrap;
  }
  .vacio {
    text-align: center;
    color: #4a5d7a;
    padding: 1.5rem 0;
  }
  .lista {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
    gap: 0.8rem;
  }
  .lista.compacta {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.5rem;
  }
  .lista li {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.7rem 0.9rem;
    border: 2px solid var(--salvia);
    border-radius: 14px;
    background: var(--crema);
  }
  .lista.compacta li {
    padding: 0.4rem 0.6rem;
  }
  .lista li.fuera {
    opacity: 0.55;
    border-color: var(--arena);
  }
  .avatar {
    font-size: 2rem;
  }
  .compacta .avatar {
    font-size: 1.4rem;
  }
  .nombre {
    font-weight: bold;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .estado {
    font-size: 0.75rem;
    color: #4a5d7a;
  }
  .expulsar {
    border: none;
    background: transparent;
    color: var(--coral);
    font-size: 1.1rem;
    font-weight: bold;
  }

  /* Juego */
  .controles {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }
  .controles .encabezado {
    margin-bottom: 0;
  }
  .manual {
    display: flex;
    gap: 0.6rem;
  }
  .manual select {
    flex: 1;
    min-width: 0;
  }
  .sonido {
    flex-direction: row;
    align-items: center;
    font-weight: normal;
    gap: 0.5rem;
  }
  .aviso-sonido {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    background: #fff1cf;
    border: 2px solid var(--terracota);
    border-radius: 14px;
    padding: 0.7rem 1rem;
    margin-bottom: 1.2rem;
  }
  .aviso-sonido button {
    border: none;
    border-radius: 10px;
    padding: 0.5rem 1rem;
    background: var(--terracota-oscuro);
    color: white;
    font-weight: bold;
  }

  .ultima {
    text-align: center;
  }
  .carta {
    animation: aparecer 0.35s ease-out;
  }
  .carta img {
    width: auto;
    max-width: 100%;
    max-height: 42vh;
    object-fit: contain;
    border-radius: 14px;
    border: 3px solid var(--cafe);
  }
  .mazahua {
    font-size: 2rem;
    font-weight: bold;
    margin: 0.6rem 0 0;
  }
  .espanol {
    font-size: 1.2rem;
    color: #4a5d7a;
    margin: 0.2rem 0 0.8rem;
  }
  @keyframes aparecer {
    from {
      opacity: 0;
      transform: scale(0.92);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  .podio-lista {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  .podio-lista li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.5rem 0.8rem;
    border-radius: 12px;
    background: var(--crema);
    border: 2px solid var(--terracota);
  }
  .medalla {
    font-size: 1.6rem;
  }

  .historial {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.6rem;
  }
  .historial li {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.4rem 0.6rem;
    border: 2px solid var(--arena);
    border-radius: 12px;
    background: var(--crema);
  }
  .historial img {
    width: 40px;
    height: 60px;
    object-fit: cover;
    border-radius: 6px;
  }
  .orden {
    font-weight: bold;
    color: var(--cafe);
    min-width: 1.4rem;
  }

  .secundario {
    background: transparent;
    border: 2px solid var(--cafe);
    border-radius: 12px;
    padding: 0.6rem 1.2rem;
    color: var(--cafe);
    font-weight: bold;
  }
  .secundario.chico {
    padding: 0.4rem 0.9rem;
  }
  .secundario:disabled {
    opacity: 0.5;
  }


  /* Durante la partida se ocultan los botones y el título de arriba (de la página admin.astro)
     y la página deja de subir y bajar: todo se adapta al tamaño de la pantalla. */
  :global(body.en-partida .acciones),
  :global(body.en-partida header a[href="/admin/palabras"]),
  :global(body.en-partida header a[href="/admin/tarjetas"]),
  :global(body.en-partida #salir),
  :global(body.en-partida main > header) {
    display: none !important;
  }
  :global(body.en-partida) {
    overflow: hidden;
  }
  :global(body.en-partida main) {
    max-width: none !important;
    padding: 0.6rem 1rem !important;
  }

  /* ---------- Panel de 3 columnas que cabe en la pantalla ---------- */
  .panel {
    width: 100%;
    height: calc(100dvh - 56px);
    display: grid;
    grid-template-columns: minmax(250px, 300px) minmax(0, 1fr) minmax(260px, 340px);
    grid-template-rows: minmax(0, 1fr);
    gap: 0.8rem;
  }
  .col {
    min-width: 0;
    min-height: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    overflow: hidden;
  }
  .col .tarjeta {
    margin-bottom: 0;
    padding: 0.8rem 1rem;
  }
  .col h2 {
    font-size: 1.1rem;
    margin-bottom: 0.4rem;
  }
  .col .secundario {
    width: 100%;
  }
  .compacto {
    padding: 0.6rem 0.8rem !important;
  }
  .compacto .codigo {
    font-size: 1.6rem;
  }
  .compacto .conexion {
    margin-top: 0.4rem;
  }

  /* Centro: la tarjeta crece o se encoge según el espacio que haya */
  .centro.con-podio {
    overflow: auto;
  }
  .centro .ultima {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
  }
  .centro .carta {
    flex: 1 1 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .centro .carta img {
    flex: 1 1 0;
    min-height: 0;
    max-height: none;
    width: auto;
    max-width: 100%;
    object-fit: contain;
  }
  .centro .mazahua {
    font-size: clamp(1.4rem, 4vh, 2rem);
    margin-top: 0.4rem;
  }
  .centro .espanol {
    font-size: clamp(1rem, 2.6vh, 1.2rem);
    margin-bottom: 0.4rem;
  }

  /* Derecha: el historial usa el espacio que sobra y no se desplaza */
  .der .hist {
    flex: 1 1 0;
    min-height: 0;
    overflow: hidden;
  }
  .der .historial {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.4rem;
  }
  .der .historial li {
    padding: 0.25rem 0.4rem;
    gap: 0.4rem;
    font-size: 0.8rem;
    line-height: 1.15;
    min-width: 0;
  }
  .der .historial img {
    width: 28px;
    height: 42px;
  }
  .mas {
    margin: 0.4rem 0 0;
    color: #4a5d7a;
    font-size: 0.85rem;
  }

  /* Pantallas angostas o celulares: una sola columna, aquí sí se puede bajar */
  @media (max-width: 1000px) {
    :global(body.en-partida) {
      overflow: auto;
    }
    .panel {
      height: auto;
      grid-template-columns: 1fr;
      grid-template-rows: auto;
    }
    :global(body.en-partida main) {
      padding: 0.5rem 0.6rem !important;
    }
    .col {
      height: auto;
      overflow: visible;
    }
    /* En celular: primero la última tarjeta, luego código/controles, luego el resto */
    .centro { order: 1; }
    .izq { order: 2; }
    .der { order: 3; }
    .centro .ultima,
    .centro .carta,
    .der .hist {
      flex: none;
    }
    .centro .carta img {
      flex: none;
      max-height: 40vh;
      width: auto;
    }
    .der .hist {
      overflow: visible;
    }
    .der .historial li {
      font-size: 0.85rem;
    }
  }

  /* ---------- Aviso de ¡LOTERÍA! ---------- */
  .loteria {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.6rem;
    border: none;
    padding: 1rem;
    background: rgba(20, 33, 61, 0.94);
    color: white;
    text-align: center;
    animation: aparecer 0.35s ease-out;
  }
  .loteria-grande {
    font-size: clamp(3rem, 12vw, 7rem);
    font-weight: 900;
    letter-spacing: 0.06em;
    color: var(--terracota);
    text-shadow: 0 6px 0 rgba(0, 0, 0, 0.35);
    animation: rebote 0.9s ease-in-out infinite alternate;
  }
  .loteria-avatar {
    font-size: clamp(5rem, 16vh, 9rem);
    line-height: 1;
  }
  .loteria-nombre {
    font-size: clamp(2rem, 8vh, 4rem);
    font-weight: bold;
  }
  .loteria-texto {
    font-size: clamp(1.1rem, 3vh, 1.8rem);
    opacity: 0.9;
  }
  @keyframes rebote {
    from { transform: scale(1) rotate(-2deg); }
    to { transform: scale(1.08) rotate(2deg); }
  }
</style>
