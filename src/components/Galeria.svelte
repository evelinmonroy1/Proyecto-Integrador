<script>
  import { onMount } from "svelte";
  import { API } from "../lib/config.js";

  let estado = $state("cargando"); // cargando | listo | error
  let categorias = $state([]);
  let palabras = $state([]);
  let filtro = $state(0); // 0 = todas
  let busqueda = $state("");
  let abierta = $state(-1); // índice dentro de "visibles" de la tarjeta ampliada

  // Tarjetas que se voltean y modo práctica
  let volteadas = $state({}); // { idPalabra: true }
  let practica = $state(false);
  let mezcla = $state(null); // orden al azar en modo práctica
  let audio = null;

  const url = (ruta) => (ruta ? `${API}${ruta}` : null);

  // Quita acentos para que "nariz" encuentre "Nariz" y "dia" encuentre "días"
  const normal = (t) =>
    (t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  let visibles = $derived.by(() => {
    const q = normal(busqueda.trim());
    const lista = palabras.filter((p) => {
      if (filtro && p.categoria_id !== filtro) return false;
      return !q || normal(p.mazahua).includes(q) || normal(p.espanol).includes(q);
    });
    if (mezcla) lista.sort((a, b) => (mezcla[a.id] ?? 0) - (mezcla[b.id] ?? 0));
    return lista;
  });

  let actual = $derived(abierta >= 0 ? visibles[abierta] : null);
  let descubiertas = $derived(visibles.filter((p) => volteadas[p.id]).length);

  function cuantas(id) {
    return id ? palabras.filter((p) => p.categoria_id === id).length : palabras.length;
  }

  async function cargar() {
    estado = "cargando";
    try {
      const r = await fetch(`${API}/api/galeria`);
      if (!r.ok) throw new Error();
      const datos = await r.json();
      categorias = datos.categorias;
      palabras = datos.palabras.filter((p) => p.imagen_url);
      estado = "listo";
    } catch {
      estado = "error";
    }
  }

  function escuchar(p) {
    if (!p?.audio_url) return;
    audio?.pause();
    audio = new Audio(url(p.audio_url));
    audio.play().catch(() => {});
  }

  function voltear(p) {
    const ahora = !volteadas[p.id];
    volteadas[p.id] = ahora;
    // En modo práctica, al descubrir la tarjeta suena la palabra
    if (ahora && practica) escuchar(p);
  }

  function cambiarModo() {
    practica = !practica;
    volteadas = {};
    mezcla = null;
  }

  function barajar() {
    const ids = palabras.map((p) => p.id);
    for (let i = ids.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [ids[i], ids[j]] = [ids[j], ids[i]];
    }
    const orden = {};
    ids.forEach((id, k) => (orden[id] = k));
    mezcla = orden;
    volteadas = {};
  }

  function ocultarTodas() {
    volteadas = {};
  }

  function abrir(i) {
    abierta = i;
  }
  function cerrar() {
    audio?.pause();
    abierta = -1;
  }
  function mover(paso) {
    if (!visibles.length) return;
    abierta = (abierta + paso + visibles.length) % visibles.length;
  }

  function teclas(e) {
    if (abierta < 0) return;
    if (e.key === "Escape") cerrar();
    else if (e.key === "ArrowRight") mover(1);
    else if (e.key === "ArrowLeft") mover(-1);
  }

  onMount(cargar);
</script>

<svelte:window onkeydown={teclas} />

{#if estado === "cargando"}
  <p class="aviso">Cargando las tarjetas…</p>
{:else if estado === "error"}
  <div class="aviso error">
    <p>No se pudieron cargar las imágenes. Revisa que el servidor esté encendido.</p>
    <button type="button" onclick={cargar}>Intentar de nuevo</button>
  </div>
{:else}
  <div class="controles">
    <div class="filtros" role="group" aria-label="Filtrar por categoría">
      <button type="button" class:activo={filtro === 0} onclick={() => (filtro = 0)}>
        Todas <small>{cuantas(0)}</small>
      </button>
      {#each categorias as c (c.id)}
        {#if cuantas(c.id)}
          <button type="button" class:activo={filtro === c.id} onclick={() => (filtro = c.id)}>
            {c.nombre} <small>{cuantas(c.id)}</small>
          </button>
        {/if}
      {/each}
    </div>
    <input
      type="search"
      placeholder="Buscar en mazahua o español…"
      bind:value={busqueda}
      aria-label="Buscar palabra"
    />
  </div>

  <!-- Barra de modo -->
  <div class="modo">
    <button type="button" class="interruptor" class:encendido={practica} onclick={cambiarModo} aria-pressed={practica}>
      <span class="perilla"></span>
      Modo práctica
    </button>
    {#if practica}
      <p class="ayuda">Lee la palabra en español, piensa cómo se dice en mazahua y voltea la tarjeta.</p>
      <div class="botones-modo">
        <span class="contador-practica">{descubiertas} / {visibles.length}</span>
        <button type="button" class="chico" onclick={barajar}>🔀 Barajar</button>
        <button type="button" class="chico" onclick={ocultarTodas}>↺ Ocultar todas</button>
      </div>
    {:else}
      <p class="ayuda">Toca una tarjeta para voltearla y escuchar la palabra.</p>
    {/if}
  </div>

  {#if visibles.length === 0}
    <p class="aviso">No hay tarjetas que coincidan con «{busqueda}».</p>
  {:else}
    <ul class="rejilla">
      {#each visibles as p, i (p.id)}
        <li>
          <div class="giro" class:volteada={volteadas[p.id]}>
            <!-- Frente -->
            <button
              type="button"
              class="cara frente"
              class:pregunta={practica}
              onclick={() => voltear(p)}
              inert={volteadas[p.id]}
              aria-label={practica ? `¿Cómo se dice ${p.espanol}? Voltear` : `${p.mazahua}, ${p.espanol}. Voltear`}
            >
              {#if practica}
                <small>¿Cómo se dice…?</small>
                <strong>{p.espanol}</strong>
                <span class="pista">Toca para descubrir</span>
              {:else}
                <img src={url(p.imagen_url)} alt="{p.mazahua} ({p.espanol})" loading="lazy" />
              {/if}
            </button>

            <!-- Reverso -->
            <div class="cara reverso" class:con-imagen={practica} inert={!volteadas[p.id]}>
              {#if practica}
                <img src={url(p.imagen_url)} alt="{p.mazahua} ({p.espanol})" loading="lazy" />
              {:else}
                <span class="adorno" aria-hidden="true">✿</span>
                <strong>{p.mazahua}</strong>
                <span class="espanol">{p.espanol}</span>
              {/if}
              <div class="acciones">
                {#if p.audio_url}
                  <button type="button" onclick={() => escuchar(p)} title="Escuchar" aria-label="Escuchar">🔊</button>
                {/if}
                <button type="button" onclick={() => abrir(i)} title="Ver en grande" aria-label="Ver en grande">⤢</button>
                <button type="button" onclick={() => voltear(p)} title="Voltear" aria-label="Voltear">↺</button>
              </div>
            </div>
          </div>
        </li>
      {/each}
    </ul>
  {/if}
{/if}

{#if actual}
  <div class="fondo" onclick={cerrar} role="presentation">
    <div
      class="visor"
      role="dialog"
      aria-modal="true"
      aria-label="{actual.mazahua} · {actual.espanol}"
      onclick={(e) => e.stopPropagation()}
      onkeydown={() => {}}
      tabindex="-1"
    >
      <button type="button" class="cerrar" onclick={cerrar} aria-label="Cerrar">✕</button>
      <button type="button" class="flecha izq" onclick={() => mover(-1)} aria-label="Anterior">‹</button>
      <img src={url(actual.imagen_url)} alt="{actual.mazahua} ({actual.espanol})" />
      <button type="button" class="flecha der" onclick={() => mover(1)} aria-label="Siguiente">›</button>

      <div class="pie">
        <div>
          <strong>{actual.mazahua}</strong>
          <span>{actual.espanol}</span>
        </div>
        {#if actual.audio_url}
          <button type="button" class="escuchar" onclick={() => escuchar(actual)}>🔊 Escuchar</button>
        {/if}
      </div>
      <p class="contador">{abierta + 1} / {visibles.length}</p>
    </div>
  </div>
{/if}

<style>
  .aviso {
    padding: 3rem 0;
    color: var(--cafe);
    font-size: 1.05rem;
  }
  .aviso.error {
    color: var(--coral);
  }
  .aviso button,
  .escuchar {
    padding: 0.75rem 1.5rem;
    border: 0;
    border-radius: 999px;
    background: var(--verde);
    color: white;
    font-weight: 500;
  }

  /* Filtros como pestañas de texto */
  .controles {
    display: flex;
    flex-wrap: wrap;
    gap: 1.5rem 2rem;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    border-bottom: 1px solid var(--arena);
  }
  .filtros {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem 1.8rem;
  }
  .filtros button {
    padding: 0.8rem 0;
    margin-bottom: -1px;
    border: 0;
    border-bottom: 1px solid transparent;
    background: none;
    color: var(--cafe);
    font-size: 0.78rem;
    font-weight: 500;
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .filtros button small {
    margin-left: 0.3rem;
    letter-spacing: 0;
    opacity: 0.6;
  }
  .filtros button:hover {
    color: var(--tinta);
  }
  .filtros button.activo {
    color: var(--verde);
    border-bottom-color: var(--verde);
  }
  input[type="search"] {
    flex: 0 1 260px;
    margin-bottom: 0.5rem;
    padding: 0.5rem 0;
    border: 0;
    border-bottom: 1px solid var(--arena);
    font: inherit;
    font-size: 0.95rem;
    background: transparent;
    color: var(--tinta);
  }
  input[type="search"]:focus {
    outline: none;
    border-bottom-color: var(--verde);
  }

  /* ---------- Modo práctica ---------- */
  .modo {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.8rem 1.4rem;
    margin-bottom: 2rem;
    padding: 0.9rem 1.2rem;
    border-radius: 16px;
    background: white;
    box-shadow: 0 6px 18px -12px rgba(20, 59, 97, 0.4);
  }
  .interruptor {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0;
    border: 0;
    background: none;
    font-weight: 700;
    color: var(--tinta);
  }
  .perilla {
    position: relative;
    width: 2.8rem;
    height: 1.6rem;
    border-radius: 999px;
    background: var(--arena);
    transition: background 0.2s;
  }
  .perilla::after {
    content: "";
    position: absolute;
    top: 0.2rem;
    left: 0.2rem;
    width: 1.2rem;
    height: 1.2rem;
    border-radius: 50%;
    background: white;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
    transition: transform 0.2s;
  }
  .encendido .perilla {
    background: var(--verde);
  }
  .encendido .perilla::after {
    transform: translateX(1.2rem);
  }
  .ayuda {
    flex: 1 1 260px;
    margin: 0;
    font-size: 0.92rem;
    color: var(--cafe);
  }
  .botones-modo {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .contador-practica {
    margin-right: 0.3rem;
    font-weight: 700;
    color: var(--verde);
  }
  .chico {
    padding: 0.45rem 0.9rem;
    border: 1px solid var(--arena);
    border-radius: 999px;
    background: white;
    color: var(--tinta);
    font-size: 0.85rem;
    font-weight: 700;
  }
  .chico:hover {
    border-color: var(--verde);
  }

  /* ---------- Rejilla de tarjetas que se voltean ---------- */
  .rejilla {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(165px, 1fr));
    gap: 2rem 1.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
    perspective: 1200px;
  }
  .giro {
    position: relative;
    aspect-ratio: 2 / 3;
    transform-style: preserve-3d;
    transition: transform 0.55s cubic-bezier(0.3, 0.7, 0.3, 1);
  }
  .giro.volteada {
    transform: rotateY(180deg);
  }
  .cara {
    position: absolute;
    inset: 0;
    border-radius: 12px;
    overflow: hidden;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    box-shadow: 0 8px 20px -12px rgba(20, 59, 97, 0.45);
  }
  .frente {
    display: block;
    width: 100%;
    padding: 0;
    border: 0;
    background: white;
    transition: transform 0.25s, box-shadow 0.25s;
  }
  .giro:not(.volteada) .frente:hover,
  .giro:not(.volteada) .frente:focus-visible {
    transform: translateY(-5px);
    box-shadow: 0 18px 30px -16px rgba(20, 59, 97, 0.55);
  }
  .frente img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  /* Frente en modo práctica: solo la palabra en español */
  .frente.pregunta {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    padding: 1rem;
    background: linear-gradient(160deg, var(--marino, #143b61), var(--medio, #457caa));
    color: white;
    text-align: center;
  }
  .pregunta small {
    font-size: 0.75rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.8;
  }
  .pregunta strong {
    font-family: var(--serif, inherit);
    font-size: 1.35rem;
    line-height: 1.15;
    color: white;
  }
  .pista {
    margin-top: 0.6rem;
    padding: 0.25rem 0.7rem;
    border-radius: 999px;
    background: var(--mostaza, #f2c14e);
    color: var(--marino, #143b61);
    font-size: 0.72rem;
    font-weight: 700;
  }

  /* Reverso */
  .reverso {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
    padding: 1rem 0.8rem 3.6rem;
    background: white;
    border: 3px solid var(--mostaza, #f2c14e);
    text-align: center;
    transform: rotateY(180deg);
  }
  .adorno {
    font-size: 1.6rem;
    color: var(--cielo, #589ac4);
  }
  .reverso strong {
    font-family: var(--serif, inherit);
    font-size: 1.5rem;
    line-height: 1.1;
    color: var(--tinta);
    word-break: break-word;
  }
  .espanol {
    font-size: 0.95rem;
    color: var(--cafe);
  }
  .reverso.con-imagen {
    padding: 0;
    border-width: 0;
  }
  .reverso.con-imagen img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .acciones {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0.6rem;
    display: flex;
    justify-content: center;
    gap: 0.4rem;
  }
  /* En modo práctica los botones van arriba para no tapar la palabra de la tarjeta */
  .con-imagen .acciones {
    top: 0.5rem;
    bottom: auto;
    justify-content: flex-end;
    padding-right: 0.5rem;
  }
  .acciones button {
    width: 2.3rem;
    height: 2.3rem;
    border: 0;
    border-radius: 50%;
    background: var(--marino, #143b61);
    color: white;
    font-size: 1rem;
    box-shadow: 0 4px 10px -4px rgba(0, 0, 0, 0.4);
    transition: transform 0.15s, background 0.15s;
  }
  .acciones button:hover {
    transform: scale(1.1);
    background: var(--verde);
  }

  /* ---------- Visor ---------- */
  .fondo {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: rgba(248, 251, 253, 0.9);
    backdrop-filter: blur(14px);
  }
  .visor {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.4rem;
    max-height: 100%;
    outline: none;
  }
  .visor img {
    max-height: min(68vh, 700px);
    max-width: min(86vw, 460px);
    border-radius: 8px;
    box-shadow: 0 30px 60px -25px rgba(15, 34, 51, 0.45);
  }
  .pie {
    display: flex;
    align-items: center;
    gap: 2rem;
  }
  .pie strong {
    display: block;
    font-family: var(--serif, Georgia, serif);
    font-size: 1.8rem;
    font-weight: 400;
    color: var(--tinta);
    line-height: 1.1;
  }
  .pie span {
    font-family: var(--serif, Georgia, serif);
    font-style: italic;
    color: var(--cafe);
  }
  .contador {
    margin: 0;
    color: var(--cafe);
    font-size: 0.75rem;
    letter-spacing: 0.25em;
  }
  .cerrar,
  .flecha {
    position: absolute;
    border: 1px solid var(--arena);
    border-radius: 50%;
    background: white;
    color: var(--tinta);
  }
  .cerrar {
    top: -0.8rem;
    right: -0.8rem;
    width: 2.4rem;
    height: 2.4rem;
    z-index: 1;
  }
  .flecha {
    top: 38%;
    width: 3rem;
    height: 3rem;
    font-size: 1.6rem;
    line-height: 1;
  }
  .flecha:hover,
  .cerrar:hover {
    background: var(--tinta);
    color: white;
  }
  .izq {
    left: -4.2rem;
  }
  .der {
    right: -4.2rem;
  }

  @media (prefers-reduced-motion: reduce) {
    .giro {
      transition: none;
    }
  }
  @media (max-width: 640px) {
    .izq {
      left: 0.4rem;
    }
    .der {
      right: 0.4rem;
    }
    .rejilla {
      grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
      gap: 1.2rem 0.8rem;
    }
    .reverso strong {
      font-size: 1.2rem;
    }
    .pregunta strong {
      font-size: 1.1rem;
    }
    .acciones button {
      width: 2rem;
      height: 2rem;
      font-size: 0.85rem;
    }
    .pie {
      flex-direction: column;
      gap: 0.8rem;
      text-align: center;
    }
  }
</style>