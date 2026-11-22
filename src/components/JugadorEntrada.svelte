<script>
  import { onMount } from "svelte";
  import { API, WS } from "../lib/config.js";
  import TableroJuego from "./TableroJuego.svelte";
  import Avatar from "./Avatar.svelte";
  import AvatarEditor from "./AvatarEditor.svelte";
  import { aleatorio } from "../lib/avatar.js";

  // "codigo" -> "perfil" -> "sala"
  let paso = $state("codigo");
  let codigo = $state("");
  let nombre = $state("");
  let avatar = $state(aleatorio());
  let partida = $state(null);
  let yo = $state(null);
  let jugadores = $state([]);
  let error = $state("");
  let cargando = $state(false);
  let conectado = $state(false);

  // Juego
  let tablero = $state(null);
  let detecciones = $state([]); // la más reciente primero
  let ganadores = $state([]);

  // Aviso de ¡LOTERÍA!
  let loteria = $state(null); // { nombre, yo } mientras se muestra el aviso
  let temporizadorLoteria;

  function mostrarLoteria(jugador) {
    loteria = { nombre: jugador.nombre, yo: jugador.id === yo?.id };
    clearTimeout(temporizadorLoteria);
    temporizadorLoteria = setTimeout(() => (loteria = null), 4000);
  }

  const otros = $derived(jugadores.filter((j) => j.id !== yo?.id));
  const finalizada = $derived(partida?.estado === "finalizada");

  let socket = null;
  let cerrar = false;
  let reintento;

  // ---------- Paso 1: validar el código ----------
  async function verificarCodigo() {
    error = "";
    const limpio = codigo.trim().toUpperCase();
    if (limpio.length < 4) {
      error = "Escribe el código que aparece en la pantalla del administrador";
      return;
    }
    cargando = true;
    try {
      const r = await fetch(`${API}/api/partidas/${limpio}`);
      const datos = await r.json();
      if (!r.ok) {
        error = datos.detail ?? "Código no válido";
        return;
      }
      if (datos.estado !== "espera") {
        error = "Esa partida ya comenzó o terminó";
        return;
      }
      codigo = limpio;
      partida = datos;
      paso = "perfil";
    } catch {
      error = "No se pudo conectar con el servidor";
    } finally {
      cargando = false;
    }
  }

  // ---------- Paso 2: unirse con nombre y avatar ----------
  async function unirse() {
    error = "";
    if (!nombre.trim()) {
      error = "Escribe tu nombre";
      return;
    }
    if (!avatar) {
      error = "Elige tu avatar";
      return;
    }
    cargando = true;
    try {
      const r = await fetch(`${API}/api/partidas/${codigo}/jugadores`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre: nombre.trim(), avatar }),
      });
      const datos = await r.json();
      if (!r.ok) {
        error = typeof datos.detail === "string" ? datos.detail : "Revisa tus datos";
        return;
      }
      yo = datos.jugador;
      partida = datos.partida;
      localStorage.setItem("jugador", JSON.stringify({ codigo, id: yo.id }));
      entrarSala();
    } catch {
      error = "No se pudo conectar con el servidor";
    } finally {
      cargando = false;
    }
  }

  // ---------- Datos del juego ----------
  // Se mezclan por número de orden / lugar: si llega lo mismo por el WebSocket
  // y por una consulta, no se duplica ni se pierde nada.
  function agregarTarjetas(nuevas) {
    const porOrden = new Map(detecciones.map((d) => [d.orden, d]));
    for (const d of nuevas) porOrden.set(d.orden, d);
    detecciones = [...porOrden.values()].sort((a, b) => b.orden - a.orden);
  }

  function agregarGanadores(nuevos) {
    const porLugar = new Map(ganadores.map((g) => [g.lugar, g]));
    for (const g of nuevos) porLugar.set(g.lugar, g);
    ganadores = [...porLugar.values()].sort((a, b) => a.lugar - b.lugar);
  }

  // Recupera tablero, tarjetas y podio del servidor (al iniciar, recargar o reconectar)
  async function cargarJuego() {
    if (!yo) return;
    try {
      const [rt, rd, rg] = await Promise.all([
        fetch(`${API}/api/partidas/${codigo}/jugadores/${yo.id}/tablero`),
        fetch(`${API}/api/partidas/${codigo}/detecciones`),
        fetch(`${API}/api/partidas/${codigo}/podio`),
      ]);
      if (rt.ok) tablero = await rt.json();
      if (rd.ok) agregarTarjetas(await rd.json());
      if (rg.ok) {
        const datos = await rg.json();
        agregarGanadores(datos.podio);
        // Si la partida ya terminó y no nos llegó el aviso, lo recuperamos aquí
        if (datos.estado === "finalizada") {
          partida = { ...partida, estado: "finalizada" };
        }
      }
    } catch {}
  }

  // ---------- Sala y juego (WebSocket con reconexión) ----------
  function entrarSala() {
    paso = "sala";
    conectarWs();
  }

  function conectarWs() {
    cerrar = false;
    socket = new WebSocket(`${WS}/api/partidas/${codigo}/ws?rol=jugador&jugador_id=${yo.id}`);
    socket.onopen = () => {
      conectado = true;
      if (partida?.estado !== "espera") cargarJuego(); // recupera lo que se perdió
    };
    socket.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.tipo === "jugadores") jugadores = m.jugadores;
      if (m.tipo === "inicio") {
        partida = m.partida;
        cargarJuego();
      }
      if (m.tipo === "tarjeta") {
        agregarTarjetas([{ orden: m.orden, palabra: m.palabra }]);
      }
      if (m.tipo === "ganador") {
        agregarGanadores([{ lugar: m.lugar, jugador: m.jugador }]);
        if (m.lugar === 1) mostrarLoteria(m.jugador);
      }
      if (m.tipo === "fin") {
        agregarGanadores(m.podio);
        partida = { ...partida, estado: "finalizada" };
      }
      if (m.tipo === "expulsado" && m.jugador_id === yo.id) {
        salir(false);
        error = "El administrador te sacó de la partida";
      }
    };
    socket.onclose = (e) => {
      conectado = false;
      if (cerrar) return;
      if (e.code === 4404) {
        // el servidor ya no reconoce al jugador o la partida
        salir(false);
        return;
      }
      reintento = setTimeout(conectarWs, 2000);
    };
  }

  function cerrarSocket() {
    cerrar = true;
    clearTimeout(reintento);
    socket?.close();
  }

  // Si estaba en espera, también lo quita de la lista del administrador
  async function salir(avisar = true) {
    if (avisar && partida?.estado === "espera" && yo) {
      try {
        await fetch(`${API}/api/partidas/${codigo}/jugadores/${yo.id}`, { method: "DELETE" });
      } catch {}
    }
    cerrarSocket();
    localStorage.removeItem("jugador");
    paso = "codigo";
    codigo = "";
    nombre = "";
    avatar = aleatorio();
    yo = null;
    partida = null;
    jugadores = [];
    tablero = null;
    detecciones = [];
    ganadores = [];
    loteria = null;
  }

  // ---------- Al abrir la página ----------
  async function reanudar() {
    let guardado;
    try {
      guardado = JSON.parse(localStorage.getItem("jugador"));
    } catch {}
    if (!guardado) return;

    try {
      const [rp, rj] = await Promise.all([
        fetch(`${API}/api/partidas/${guardado.codigo}`),
        fetch(`${API}/api/partidas/${guardado.codigo}/jugadores`),
      ]);
      if (rp.ok && rj.ok) {
        const p = await rp.json();
        const lista = await rj.json();
        const mio = lista.find((j) => j.id === guardado.id);
        if (mio) {
          codigo = guardado.codigo;
          partida = p;
          yo = mio;
          jugadores = lista;
          return entrarSala();
        }
      }
      localStorage.removeItem("jugador");
    } catch {}
  }

  onMount(() => {
    reanudar();
    return cerrarSocket;
  });
</script>

{#if loteria}
  <button class="loteria" onclick={() => (loteria = null)} aria-live="assertive">
    <span class="loteria-grande">¡LOTERÍA!</span>
    <span class="loteria-texto">
      {loteria.yo ? "¡Completaste tu tablero!" : `${loteria.nombre} completó su tablero`}
    </span>
  </button>
{/if}

{#if paso === "sala" && partida?.estado !== "espera"}
  <TableroJuego
    {codigo}
    {tablero}
    {detecciones}
    {ganadores}
    {yo}
    {finalizada}
    {conectado}
    onsalir={() => salir(true)}
  />
{:else}
  <div class="estrecho">
    {#if paso === "codigo"}
      <section class="tarjeta">
        <h2>Únete a la partida</h2>
        <p class="ayuda">Escribe el código que ves en la pantalla.</p>

        <input
          class="entrada-codigo"
          bind:value={codigo}
          oninput={() => (codigo = codigo.toUpperCase())}
          onkeydown={(e) => e.key === "Enter" && verificarCodigo()}
          maxlength="8"
          placeholder="CÓDIGO"
          autocomplete="off"
          autocapitalize="characters"
          spellcheck="false"
        />

        {#if error}<p class="error">{error}</p>{/if}

        <button class="boton" onclick={verificarCodigo} disabled={cargando}>
          {cargando ? "Buscando…" : "Continuar"}
        </button>
      </section>
    {:else if paso === "perfil"}
      <section class="tarjeta">
        <p class="ayuda">Partida <strong>{codigo}</strong></p>
        <h2>¿Cómo te llamas?</h2>

        <input
          class="entrada"
          bind:value={nombre}
          maxlength="20"
          placeholder="Tu nombre"
          autocomplete="off"
        />

        <h2 class="subtitulo">Arma tu avatar</h2>
        <AvatarEditor bind:valor={avatar} />

        {#if error}<p class="error">{error}</p>{/if}

        <button class="boton" onclick={unirse} disabled={cargando}>
          {cargando ? "Entrando…" : "¡Entrar a jugar!"}
        </button>
        <button class="secundario" onclick={() => { paso = "codigo"; error = ""; }}>← Cambiar código</button>
      </section>
    {:else}
      <section class="tarjeta sala">
        <p class="ayuda">Partida <strong>{codigo}</strong></p>
        <div class="mi-avatar"><Avatar codigo={yo.avatar} emoji={yo.emoji} /></div>
        <h2>{yo.nombre}</h2>
        <p class="espera">Esperando a que el administrador inicie la partida…</p>
        <p class="conexion" class:caida={!conectado}>
          {conectado ? "Conectado" : "Reconectando…"}
        </p>
      </section>

      <section class="tarjeta">
        <div class="encabezado">
          <h2>En la sala</h2>
          <span class="contador">{jugadores.length}</span>
        </div>
        {#if otros.length === 0}
          <p class="ayuda">Eres la primera persona en llegar.</p>
        {:else}
          <ul class="lista">
            {#each otros as j (j.id)}
              <li class:fuera={!j.conectado}>
                <span class="avatar"><Avatar codigo={j.avatar} emoji={j.emoji} /></span>
                <span class="nombre">{j.nombre}</span>
              </li>
            {/each}
          </ul>
        {/if}
      </section>

      {#if error}<p class="error">{error}</p>{/if}
      <button class="secundario" onclick={() => salir(true)}>Salir de la partida</button>
    {/if}
  </div>
{/if}

<style>
  .estrecho {
    max-width: 520px;
    margin: 0 auto;
  }
  .tarjeta {
    background: white;
    border: 2px solid var(--arena);
    border-radius: var(--radio);
    padding: 1.5rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 6px 0 rgba(181, 131, 90, 0.2);
  }
  h2 {
    font-size: 1.4rem;
  }
  .subtitulo {
    margin-top: 1.4rem;
    font-size: 1.15rem;
  }
  .ayuda {
    color: #6b5a4a;
    margin: 0.4rem 0 1rem;
  }
  .entrada-codigo,
  .entrada {
    width: 100%;
    font: inherit;
    padding: 0.9rem 1rem;
    border: 3px solid var(--cafe);
    border-radius: 14px;
    background: var(--crema);
    margin: 0.6rem 0 1rem;
  }
  .entrada-codigo {
    text-align: center;
    font-size: 2rem;
    font-weight: bold;
    letter-spacing: 0.3em;
    padding-left: 1.3em;
  }
  .entrada {
    font-size: 1.2rem;
  }
  .entrada-codigo:focus,
  .entrada:focus {
    outline: 3px solid var(--salvia);
  }

  .boton {
    width: 100%;
    padding: 1rem;
    border: none;
    border-radius: 14px;
    background: var(--terracota-oscuro);
    color: white;
    font-size: 1.15rem;
    font-weight: bold;
    box-shadow: 0 5px 0 rgba(46, 31, 31, 0.25);
  }
  .boton:active {
    transform: translateY(3px);
    box-shadow: 0 2px 0 rgba(46, 31, 31, 0.25);
  }
  .boton:disabled {
    opacity: 0.6;
  }
  .secundario {
    width: 100%;
    margin-top: 0.8rem;
    background: transparent;
    border: 2px solid var(--cafe);
    border-radius: 12px;
    padding: 0.6rem 1.2rem;
    color: var(--cafe);
    font-weight: bold;
  }
  .error {
    background: #fbe3e1;
    color: #8f2a26;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0 0 1rem;
  }

  .sala {
    text-align: center;
    background: var(--arena);
  }
  .mi-avatar {
    font-size: 6rem;
    line-height: 1;
    margin: 0.4rem 0 0.8rem;
  }
  .espera {
    color: #6b5a4a;
    margin: 0.6rem 0 1rem;
  }
  .conexion {
    display: inline-block;
    margin: 0;
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

  .encabezado {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.8rem;
  }
  .contador {
    background: var(--salvia);
    color: white;
    padding: 0.2rem 0.8rem;
    border-radius: 999px;
    font-weight: bold;
  }
  .lista {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.6rem;
  }
  li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.7rem;
    border: 2px solid var(--salvia);
    border-radius: 12px;
    background: var(--crema);
  }
  li.fuera {
    opacity: 0.5;
  }
  .avatar {
    font-size: 1.6rem;
  }
  .nombre {
    font-weight: bold;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
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
    gap: 1rem;
    border: none;
    padding: 1rem;
    background: rgba(20, 33, 61, 0.92);
    color: white;
    text-align: center;
    animation: aparece 0.35s ease-out;
  }
  .loteria-grande {
    font-size: clamp(3rem, 16vw, 7rem);
    font-weight: 900;
    letter-spacing: 0.06em;
    color: var(--terracota);
    text-shadow: 0 6px 0 rgba(0, 0, 0, 0.35);
    animation: rebote 0.9s ease-in-out infinite alternate;
  }
  .loteria-texto {
    font-size: clamp(1.2rem, 5vw, 2rem);
    font-weight: bold;
  }
  @keyframes aparece {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }
  @keyframes rebote {
    from { transform: scale(1) rotate(-2deg); }
    to { transform: scale(1.08) rotate(2deg); }
  }
</style>