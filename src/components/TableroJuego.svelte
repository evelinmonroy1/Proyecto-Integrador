<script>
  import { API } from "../lib/config.js";
  import Podio from "./Podio.svelte";
  import Avatar from "./Avatar.svelte";

  let { codigo, tablero, detecciones, ganadores, yo, finalizada, conectado, onsalir } = $props();

  const medallas = { 1: "🥇", 2: "🥈", 3: "🥉" };
  const lugares = { 1: "primer lugar", 2: "segundo lugar", 3: "tercer lugar" };

  const url = (ruta) => (ruta ? `${API}${ruta}` : null);

  // Casillas que el jugador ya marcó con su frijolito: { posicion: true/false }
  let marcadas = $state({});

  // Al cargar (o recargar) el tablero, se toma lo que el servidor ya tiene guardado
  $effect(() => {
    if (!tablero) return;
    const m = {};
    for (const c of tablero.casillas) if (c.marcada) m[c.posicion] = true;
    marcadas = m;
  });

  const casillas = $derived(tablero?.casillas ?? []);
  const salieron = $derived(new Set(detecciones.map((d) => d.palabra.id)));
  const total = $derived(casillas.length);
  const cuantas = $derived(casillas.filter((c) => marcadas[c.posicion]).length);
  const porcentaje = $derived(total ? Math.round((cuantas / total) * 100) : 0);
  const completo = $derived(total > 0 && cuantas === total);
  const ultima = $derived(detecciones[0] ?? null);
  const anteriores = $derived(detecciones.slice(1));
  const laTengo = $derived(
    ultima ? casillas.some((c) => c.id === ultima.palabra.id) : false
  );
  const miLugar = $derived(ganadores.find((g) => g.jugador.id === yo?.id)?.lugar ?? null);

  // ---------- Tamaño del tablero ----------
  // Mide el espacio libre y elige la forma que haga las tarjetas más grandes:
  // si el tablero es de 4 filas x 2 columnas pero la pantalla es ancha,
  // lo dibuja de 2 filas x 4 columnas (las casillas siguen siendo las mismas).
  const SEPARACION = 8;
  let anchoMesa = $state(0);
  let altoMesa = $state(0);

  const forma = $derived.by(() => {
    const f = tablero?.filas ?? 1;
    const c = tablero?.columnas ?? 1;
    const medir = (cols, filas) => {
      const ancho = (anchoMesa - SEPARACION * (cols - 1)) / cols;
      const alto = ((altoMesa - SEPARACION * (filas - 1)) / filas) * (2 / 3);
      return Math.max(0, Math.floor(Math.min(ancho, alto)));
    };
    const normal = medir(c, f);
    const girado = medir(f, c);
    return girado > normal * 1.02
      ? { cols: f, filas: c, ancho: girado }
      : { cols: c, filas: f, ancho: normal };
  });

  // ---------- Avisos cortos ----------
  let aviso = $state("");
  let temporizador;
  function mostrarAviso(texto) {
    aviso = texto;
    clearTimeout(temporizador);
    temporizador = setTimeout(() => (aviso = ""), 2200);
  }

  // ---------- Marcar o quitar el frijolito ----------
  let sacude = $state(null);

  async function tocar(c) {
    if (finalizada || miLugar) return;
    const quiere = !marcadas[c.posicion];

    // No se puede marcar una tarjeta que todavía no ha salido
    if (quiere && !salieron.has(c.id)) {
      sacude = c.posicion;
      setTimeout(() => (sacude = null), 400);
      mostrarAviso("Esa tarjeta todavía no ha salido");
      return;
    }

    marcadas = { ...marcadas, [c.posicion]: quiere }; // se ve al instante
    try {
      const r = await fetch(`${API}/api/partidas/${codigo}/jugadores/${yo.id}/marcar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ posicion: c.posicion, marcada: quiere }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        marcadas = { ...marcadas, [c.posicion]: !quiere }; // se deshace
        mostrarAviso(typeof d.detail === "string" ? d.detail : "No se pudo marcar");
      }
    } catch {
      marcadas = { ...marcadas, [c.posicion]: !quiere };
      mostrarAviso("Sin conexión con el servidor");
    }
  }

  function salirClick() {
    if (finalizada || confirm("¿Salir de la partida? Ya no podrás volver a entrar.")) {
      onsalir();
    }
  }
</script>

<!-- Frijolito que se pone sobre la casilla marcada -->
{#snippet frijol()}
  <svg viewBox="0 0 60 42" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path
      d="M6 23 C4 10 18 3 32 5 C48 7 57 15 54 26 C51 36 36 39 24 37 C12 35 7 31 6 23 Z"
      fill="#7b4a2e" stroke="#0f3557" stroke-width="2.5" stroke-linejoin="round"
    />
    <circle cx="41" cy="15" r="3.2" fill="#0f3557" opacity="0.55" />
    <circle cx="33" cy="30" r="2.6" fill="#0f3557" opacity="0.5" />
    <circle cx="17" cy="26" r="2.2" fill="#0f3557" opacity="0.45" />
    <ellipse cx="22" cy="14" rx="9" ry="3.8" fill="#fff" opacity="0.32" transform="rotate(-18 22 14)" />
    <path d="M27 28 Q35 31 44 26" stroke="#ead9b9" stroke-width="2.4" fill="none" stroke-linecap="round" />
  </svg>
{/snippet}

<div class="pantalla" class:scroll={finalizada}>
  <!-- ===== Barra superior ===== -->
  <header class="barra">
    <span class="yo">
      <span class="avatar"><Avatar codigo={yo?.avatar} emoji={yo?.emoji} /></span>
      <strong class="nombre">{yo?.nombre}</strong>
    </span>
    <span class="derecha">
      <span class="punto" class:caido={!conectado} title={conectado ? "Conectado" : "Reconectando…"}></span>
      <span class="progreso">{cuantas} / {total}</span>
      <button class="salir" onclick={salirClick} aria-label="Salir de la partida">✕</button>
    </span>
  </header>
  <div class="barra-progreso"><div style:width="{porcentaje}%"></div></div>

  {#if finalizada}
    <div class="final">
      <Podio {ganadores} yoId={yo?.id} completado={completo} />
      <button class="boton" onclick={salirClick}>Jugar otra vez</button>
    </div>
  {:else if !tablero}
    <p class="centro">Cargando tu tablero…</p>
  {:else}
    {#if miLugar}
      <div class="felicidades">
        {medallas[miLugar]} ¡Completaste tu tablero! Vas en {lugares[miLugar]}.
      </div>
    {/if}

    <div class="juego">
      <!-- ===== Tarjeta que acaba de salir ===== -->
      <aside class="panel">
        <section class="actual">
          {#if ultima}
            {#key ultima.orden}
              <div class="carta">
                {#if ultima.palabra.imagen_url}
                  <img src={url(ultima.palabra.imagen_url)} alt={ultima.palabra.mazahua} />
                {/if}
                <div class="datos">
                  <p class="etiqueta-chica">Tarjeta detectada</p>
                  <p class="mazahua">{ultima.palabra.mazahua}</p>
                  <p class="espanol">{ultima.palabra.espanol}</p>
                  <p class="etiqueta" class:si={laTengo}>
                    {laTengo ? "✓ ¡La tienes!" : "No la tienes"}
                  </p>
                </div>
              </div>
            {/key}
          {:else}
            <p class="espera">Esperando la primera tarjeta…</p>
          {/if}
        </section>

        {#if anteriores.length > 0}
          <section class="anteriores">
            <h2>Ya salieron</h2>
            <ol class="historial">
              {#each anteriores as d (d.orden)}
                <li>
                  {#if d.palabra.imagen_url}
                    <img src={url(d.palabra.imagen_url)} alt="" />
                  {/if}
                  <span>{d.palabra.mazahua}</span>
                </li>
              {/each}
            </ol>
          </section>
        {/if}
      </aside>

      <!-- ===== Tablero: se ajusta solo al tamaño de la pantalla ===== -->
      <div class="zona">
        <div class="mesa" bind:clientWidth={anchoMesa} bind:clientHeight={altoMesa}>
          {#if forma.ancho > 0}
            <div
              class="tablero"
              style:grid-template-columns="repeat({forma.cols}, {forma.ancho}px)"
              style:grid-auto-rows="{Math.round(forma.ancho * 1.5)}px"
              style:gap="{SEPARACION}px"
            >
              {#each casillas as c (c.posicion)}
                {@const puesta = !!marcadas[c.posicion]}
                <button
                  class="casilla"
                  class:marcada={puesta}
                  class:sacude={sacude === c.posicion}
                  onclick={() => tocar(c)}
                  aria-label="{c.mazahua}{puesta ? ', marcada' : ''}"
                  aria-pressed={puesta}
                >
                  {#if c.imagen_url}
                    <img src={url(c.imagen_url)} alt="" loading="lazy" />
                  {:else}
                    <span class="sin-imagen">{c.mazahua}</span>
                  {/if}
                  {#if puesta}
                    <span class="frijol" style:--giro="{((c.posicion * 47) % 60) - 30}deg">
                      {@render frijol()}
                    </span>
                  {/if}
                </button>
              {/each}
            </div>
          {/if}
        </div>
        {#if aviso}<div class="aviso" role="status">{aviso}</div>{/if}
      </div>
    </div>
  {/if}
</div>

<style>
  /* La pantalla de juego ocupa todo el alto visible: no hay que subir ni bajar */
  .pantalla {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding: max(0.5rem, env(safe-area-inset-top)) 0.6rem max(0.5rem, env(safe-area-inset-bottom));
    background: var(--crema);
    box-sizing: border-box;
    overflow: hidden;
  }
  .pantalla.scroll {
    overflow: auto;
  }
  .centro {
    text-align: center;
    padding: 2rem 0;
    color: #4a5d7a;
  }

  /* Barra superior */
  .barra {
    flex: 0 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.6rem;
    padding: 0.3rem 0.7rem;
    background: white;
    border: 2px solid var(--arena);
    border-radius: 14px;
  }
  .yo,
  .derecha {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    min-width: 0;
  }
  .avatar {
    font-size: 1.9rem;
    line-height: 1;
  }
  .nombre {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .progreso {
    background: var(--salvia);
    color: white;
    padding: 0.2rem 0.8rem;
    border-radius: 999px;
    font-weight: bold;
    white-space: nowrap;
  }
  .punto {
    flex: 0 0 auto;
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    background: #2e9e5b;
  }
  .punto.caido {
    background: #d63a3a;
  }
  .salir {
    width: 2rem;
    height: 2rem;
    border: 2px solid var(--cafe);
    border-radius: 50%;
    background: transparent;
    color: var(--cafe);
    font-weight: bold;
    line-height: 1;
    cursor: pointer;
  }
  .barra-progreso {
    flex: 0 0 auto;
    height: 8px;
    background: var(--arena);
    border-radius: 999px;
    overflow: hidden;
  }
  .barra-progreso div {
    height: 100%;
    background: var(--verde);
    transition: width 0.4s;
  }
  .felicidades {
    flex: 0 0 auto;
    text-align: center;
    font-weight: bold;
    padding: 0.35rem 0.8rem;
    background: var(--arena);
    border: 2px solid var(--verde);
    border-radius: 12px;
  }

  /* Distribución: tarjeta arriba y tablero abajo (celular) */
  .juego {
    flex: 1 1 auto;
    min-height: 0;
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    gap: 0.5rem;
  }
  /* Marco del tablero, como una mesa de lotería */
  .zona {
    position: relative;
    min-height: 0;
    min-width: 0;
    overflow: hidden;
    border: 3px solid var(--arena);
    border-radius: 22px;
    background:
      radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.7), transparent 70%),
      #e8edf4;
    box-shadow: inset 0 3px 10px rgba(15, 53, 87, 0.18);
  }
  .mesa {
    position: absolute;
    inset: 8px;
    display: grid;
    place-items: center;
  }

  /* Tarjeta detectada */
  .panel {
    min-height: 0;
    min-width: 0;
  }
  .actual {
    background: white;
    border: 2px solid var(--arena);
    border-radius: 14px;
    padding: 0.35rem 0.6rem;
  }
  .carta {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    animation: aparecer 0.35s ease-out;
  }
  .carta img {
    height: 64px;
    aspect-ratio: 2 / 3;
    object-fit: cover;
    border-radius: 8px;
    border: 2px solid var(--cafe);
  }
  .datos {
    min-width: 0;
  }
  .etiqueta-chica {
    display: none;
    margin: 0 0 0.2rem;
    font-size: 0.8rem;
    color: #4a5d7a;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .mazahua {
    margin: 0;
    font-size: 1.3rem;
    font-weight: bold;
    line-height: 1.1;
  }
  .espanol {
    margin: 0.1rem 0 0.25rem;
    color: #4a5d7a;
  }
  .etiqueta {
    display: inline-block;
    margin: 0;
    padding: 0.1rem 0.7rem;
    border-radius: 999px;
    background: var(--arena);
    font-size: 0.85rem;
    font-weight: bold;
  }
  .etiqueta.si {
    background: #dcefdc;
    color: #1f6a35;
  }
  .espera {
    margin: 0.5rem 0;
    text-align: center;
    color: #4a5d7a;
  }
  .anteriores {
    display: none; /* en celular no hay espacio; en pantallas grandes sí se ve */
  }
  @keyframes aparecer {
    from {
      opacity: 0;
      transform: scale(0.94);
    }
    to {
      opacity: 1;
      transform: scale(1);
    }
  }

  /* Tablero: el tamaño de cada casilla se calcula en el script */
  .tablero {
    display: grid;
    justify-content: center;
    align-content: center;
  }
  .casilla {
    position: relative;
    min-width: 0;
    min-height: 0;
    padding: 0;
    border: 3px solid white;
    border-radius: 12px;
    background: white;
    overflow: hidden;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(15, 53, 87, 0.2), 0 6px 12px rgba(15, 53, 87, 0.12);
    transition: border-color 0.2s, transform 0.12s, box-shadow 0.12s;
  }
  .casilla img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: opacity 0.3s;
  }
  .casilla:hover {
    transform: translateY(-2px);
  }
  .casilla:active {
    transform: translateY(2px);
    box-shadow: 0 1px 3px rgba(15, 53, 87, 0.2);
  }
  .casilla.marcada {
    border-color: var(--verde);
  }
  .casilla.marcada img {
    opacity: 0.6;
  }
  .sin-imagen {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    padding: 0.2rem;
    font-weight: bold;
    font-size: clamp(0.6rem, 2.5vmin, 1.2rem);
    word-break: break-word;
  }
  .frijol {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    pointer-events: none;
    animation: caer 0.35s ease-out;
    transform: rotate(var(--giro, 0deg));
  }
  .frijol :global(svg) {
    width: 56%;
    height: auto;
    filter: drop-shadow(0 2px 2px rgba(15, 53, 87, 0.45));
  }
  @keyframes caer {
    from {
      opacity: 0;
      transform: translateY(-40%) rotate(var(--giro, 0deg)) scale(1.5);
    }
    to {
      opacity: 1;
      transform: translateY(0) rotate(var(--giro, 0deg)) scale(1);
    }
  }
  .casilla.sacude {
    animation: sacude 0.4s;
    border-color: #d63a3a;
  }
  @keyframes sacude {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(-4px); }
    40% { transform: translateX(4px); }
    60% { transform: translateX(-3px); }
    80% { transform: translateX(3px); }
  }
  .aviso {
    position: absolute;
    bottom: 0.4rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 5;
    padding: 0.45rem 1rem;
    border-radius: 999px;
    background: #0f2a47;
    color: white;
    font-weight: bold;
    font-size: 0.9rem;
    white-space: nowrap;
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.3);
  }

  /* Pantalla final */
  .final {
    flex: 1 1 auto;
    padding: 0.5rem 0 1rem;
  }
  .boton {
    width: 100%;
    margin-top: 1rem;
    padding: 0.9rem;
    border: none;
    border-radius: 14px;
    background: var(--terracota-oscuro);
    color: white;
    font-size: 1.1rem;
    font-weight: bold;
    box-shadow: 0 5px 15px rgba(15, 53, 87, 0.2);
    cursor: pointer;
  }

  /* Computadora o pantalla ancha: tablero a la izquierda, tarjeta e historial a la derecha */
  @media (min-width: 820px) {
    .pantalla {
      padding-left: 1rem;
      padding-right: 1rem;
    }
    .juego {
      width: 100%;
      max-width: 1240px;
      margin: 0 auto;
      grid-template-columns: minmax(0, 1fr) 360px;
      grid-template-rows: minmax(0, 1fr);
      gap: 1rem;
    }
    .zona {
      grid-column: 1;
      grid-row: 1;
    }
    .panel {
      grid-column: 2;
      grid-row: 1;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      overflow: auto;
    }
    .actual {
      padding: 1rem;
      text-align: center;
      box-shadow: 0 5px 15px rgba(15, 53, 87, 0.2);
    }
    .carta {
      flex-direction: column;
    }
    .carta img {
      height: auto;
      width: auto;
      max-width: 100%;
      max-height: 38vh;
      aspect-ratio: 2 / 3;
    }
    .etiqueta-chica {
      display: block;
    }
    .mazahua {
      font-size: 1.7rem;
    }
    .anteriores {
      display: block;
      background: white;
      border: 2px solid var(--arena);
      border-radius: 14px;
      padding: 0.6rem 0.8rem;
      min-height: 0;
    }
    .anteriores h2 {
      font-size: 1rem;
      margin: 0 0 0.5rem;
    }
    .historial {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
    }
    .historial li {
      display: flex;
      flex-direction: column;
      align-items: center;
      width: 64px;
      font-size: 0.7rem;
      text-align: center;
    }
    .historial img {
      width: 48px;
      height: 72px;
      object-fit: cover;
      border-radius: 6px;
    }
  }

  /* Celular en horizontal (poco alto): la tarjeta pasa al lado */
  @media (max-height: 520px) and (min-width: 560px) and (max-width: 819px) {
    .juego {
      grid-template-columns: 210px minmax(0, 1fr);
      grid-template-rows: minmax(0, 1fr);
    }
    .panel {
      grid-column: 1;
      grid-row: 1;
    }
    .zona {
      grid-column: 2;
      grid-row: 1;
    }
  }
</style>