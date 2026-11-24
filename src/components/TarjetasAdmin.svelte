<script>
  import "../lib/auth.js";
  import { onMount } from "svelte";
  import { API } from "../lib/config.js";

  // ---------- Datos ----------
  let palabras = $state([]);
  let tarjetas = $state({}); // palabra_id -> uid
  let cargando = $state(true);
  let error = $state("");
  let busqueda = $state("");
  let soloSin = $state(false);
  let version = $state(Date.now());

  // Estado del lector
  let ultima = $state(null);

  // Vinculación
  let vinculando = $state(null);
  let reg = $state(null);
  let hecho = $state(null);
  let fallo = $state("");

  let sondeoRegistro;
  let sondeoLector;

  const conTarjeta = $derived(palabras.filter((p) => tarjetas[p.id]).length);
  const visibles = $derived(
    palabras.filter((p) => {
      const q = busqueda.trim().toLowerCase();
      const coincide =
        !q || p.mazahua.toLowerCase().includes(q) || p.espanol.toLowerCase().includes(q);
      return coincide && (!soloSin || !tarjetas[p.id]);
    })
  );

  const urlMedia = (ruta) => (ruta ? `${API}${ruta}?v=${version}` : null);

  function mensaje(d) {
    if (typeof d?.detail === "string") return d.detail;
    if (Array.isArray(d?.detail)) return d.detail.map((x) => x.msg).join(". ");
    return "Ocurrió un error inesperado";
  }

  function tiempo(s) {
    if (s === null || s === undefined) return "";
    if (s < 5) return "ahora mismo";
    if (s < 60) return `hace ${s} s`;
    return "hace más de un minuto";
  }

  // ---------- Cargar ----------
  async function cargar() {
    try {
      const [rp, rt] = await Promise.all([
        fetch(`${API}/api/palabras`),
        fetch(`${API}/api/tarjetas`),
      ]);
      if (!rp.ok || !rt.ok) throw new Error();
      palabras = await rp.json();
      tarjetas = Object.fromEntries((await rt.json()).map((t) => [t.palabra_id, t.uid]));
      version = Date.now();
      error = "";
    } catch {
      error = "No se pudo conectar con el servidor";
    } finally {
      cargando = false;
    }
  }

  async function revisarLector() {
    try {
      const r = await fetch(`${API}/api/tarjetas/ultima`);
      if (r.ok) ultima = await r.json();
    } catch {}
  }

  // ---------- Vincular una tarjeta ----------
  async function vincular(p) {
    error = "";
    hecho = null;
    fallo = "";
    try {
      const r = await fetch(`${API}/api/tarjetas/registro`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ palabra_id: p.id }),
      });
      const d = await r.json();
      if (!r.ok) {
        error = mensaje(d);
        return;
      }
      vinculando = p;
      reg = { activo: true, restan: d.segundos, aviso: null, resultado: null };
      clearInterval(sondeoRegistro);
      sondeoRegistro = setInterval(sondear, 1000);
    } catch {
      error = "No se pudo conectar con el servidor";
    }
  }

  // Pregunta cada segundo si ya llegó la tarjeta
  async function sondear() {
    if (!vinculando) return;
    try {
      const r = await fetch(`${API}/api/tarjetas/registro`);
      if (!r.ok) return;
      const d = await r.json();
      reg = d;
      if (!d.activo) {
        clearInterval(sondeoRegistro);
        if (d.resultado?.ok && d.resultado.palabra_id === vinculando.id) {
          hecho = d.resultado.uid;
          await cargar();
        } else {
          fallo = "Se acabó el tiempo sin leer ninguna tarjeta.";
        }
      }
    } catch {}
  }

  async function cerrar() {
    clearInterval(sondeoRegistro);
    if (reg?.activo) {
      try {
        await fetch(`${API}/api/tarjetas/registro`, { method: "DELETE" });
      } catch {}
    }
    vinculando = null;
    reg = null;
    hecho = null;
    fallo = "";
  }

  async function quitar(p) {
    if (!confirm(`¿Quitar la tarjeta vinculada a "${p.mazahua}"?`)) return;
    error = "";
    try {
      const r = await fetch(`${API}/api/tarjetas/${p.id}`, { method: "DELETE" });
      if (!r.ok) {
        error = mensaje(await r.json());
        return;
      }
      await cargar();
    } catch {
      error = "No se pudo conectar con el servidor";
    }
  }

  onMount(() => {
    cargar();
    revisarLector();
    sondeoLector = setInterval(revisarLector, 2000);
    return () => {
      clearInterval(sondeoRegistro);
      clearInterval(sondeoLector);
    };
  });
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && vinculando && cerrar()} />

<!-- ===== Estado del lector ===== -->
<section class="tarjeta lector">
  <span class="punto" class:vivo={ultima?.hace !== null && ultima?.hace !== undefined && ultima.hace < 30}></span>
  {#if ultima?.uid}
    <span>
      Última tarjeta leída: <code>{ultima.uid}</code> · {tiempo(ultima.hace)} ·
      {#if ultima.palabra}<strong>{ultima.palabra}</strong>{:else}<em>sin vincular</em>{/if}
    </span>
  {:else}
    <span>El lector todavía no ha enviado ninguna tarjeta.</span>
  {/if}
</section>

<p class="resumen">
  <strong>{conTarjeta}</strong> de <strong>{palabras.length}</strong> palabras tienen tarjeta.
  Las palabras sin tarjeta no se pueden cantar con el lector.
</p>

<section class="tarjeta herramientas">
  <input
    class="buscador"
    type="search"
    placeholder="Buscar palabra…"
    bind:value={busqueda}
    aria-label="Buscar palabra"
  />
  <label class="check">
    <input type="checkbox" bind:checked={soloSin} />
    Solo las que no tienen tarjeta
  </label>
</section>

{#if error}<p class="error">{error}</p>{/if}

<!-- ===== Lista ===== -->
{#if cargando}
  <p class="vacio">Cargando…</p>
{:else if visibles.length === 0}
  <section class="tarjeta">
    <p class="vacio">
      {palabras.length === 0
        ? "Aún no hay palabras. Agrégalas primero en «Administrar palabras»."
        : "No hay palabras con esos filtros."}
    </p>
  </section>
{:else}
  <ul class="lista">
    {#each visibles as p (p.id)}
      <li class="fila">
        <div class="miniatura">
          {#if p.imagen_url}
            <img src={urlMedia(p.imagen_url)} alt="" loading="lazy" />
          {:else}
            <span>Sin imagen</span>
          {/if}
        </div>

        <div class="textos">
          <strong class="mazahua">{p.mazahua}</strong>
          <span class="espanol">{p.espanol}</span>
          {#if tarjetas[p.id]}
            <span class="etiqueta ok">📡 <code>{tarjetas[p.id]}</code></span>
          {:else}
            <span class="etiqueta falta">⚠ sin tarjeta</span>
          {/if}
        </div>

        <div class="acciones">
          <button class="secundario chico" onclick={() => vincular(p)}>
            {tarjetas[p.id] ? "Cambiar" : "Vincular"}
          </button>
          {#if tarjetas[p.id]}
            <button class="icono" onclick={() => quitar(p)} title="Quitar tarjeta" aria-label="Quitar tarjeta de {p.mazahua}">🗑️</button>
          {/if}
        </div>
      </li>
    {/each}
  </ul>
{/if}

<!-- ===== Ventana para vincular ===== -->
{#if vinculando}
  <div class="modal" role="dialog" aria-modal="true" aria-label="Vincular tarjeta">
    <button class="fondo" aria-label="Cerrar" onclick={cerrar}></button>

    <div class="contenido">
      <h2>Vincular tarjeta</h2>
      <p class="palabra"><strong>{vinculando.mazahua}</strong> · {vinculando.espanol}</p>

      {#if hecho}
        <p class="exito">✓ ¡Listo! La tarjeta <code>{hecho}</code> quedó vinculada.</p>
        <button class="boton" onclick={cerrar}>Terminar</button>
      {:else if fallo}
        <p class="error">{fallo}</p>
        <div class="botones">
          <button class="secundario" onclick={cerrar}>Cerrar</button>
          <button class="boton" onclick={() => vincular(vinculando)}>Intentar de nuevo</button>
        </div>
      {:else}
        <div class="espera">
          <span class="onda">📡</span>
          <p>Acerca la tarjeta al lector…</p>
          <p class="ayuda">Quedan {reg?.restan ?? 0} segundos</p>
        </div>
        {#if reg?.aviso}<p class="error">{reg.aviso}</p>{/if}
        <button class="secundario" onclick={cerrar}>Cancelar</button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .tarjeta {
    background: white;
    border: 2px solid var(--arena);
    border-radius: var(--radio);
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 6px 18px rgba(15, 53, 87, 0.2);
  }
  h2 {
    font-size: 1.4rem;
    margin-bottom: 0.4rem;
  }
  code {
    background: var(--crema);
    padding: 0.05rem 0.4rem;
    border-radius: 6px;
    font-size: 0.9em;
  }

  .lector {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }
  .punto {
    flex: none;
    width: 0.8rem;
    height: 0.8rem;
    border-radius: 50%;
    background: #a7b9cd;
  }
  .punto.vivo {
    background: #2e9e5b;
  }

  .resumen {
    margin: 0 0 1rem;
    color: #4a5d7a;
  }
  .herramientas {
    display: flex;
    flex-wrap: wrap;
    gap: 0.9rem;
    align-items: center;
  }
  .buscador {
    flex: 1 1 220px;
  }
  input[type="search"] {
    font: inherit;
    padding: 0.6rem 0.9rem;
    border: 2px solid var(--cafe);
    border-radius: 12px;
    background: var(--crema);
    min-width: 0;
  }
  input[type="search"]:focus {
    outline: 3px solid var(--salvia);
  }
  .check {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: bold;
  }

  .vacio {
    text-align: center;
    color: #4a5d7a;
    padding: 1.5rem 0;
    margin: 0;
  }
  .error {
    background: #fbe3e1;
    color: #8f2a26;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0 0 1rem;
  }
  .exito {
    background: #dcefdc;
    color: #1f6a35;
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin: 0 0 1rem;
    font-weight: bold;
  }

  /* Lista */
  .lista {
    list-style: none;
    margin: 0;
    padding: 0;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 0.8rem;
  }
  .fila {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.6rem;
    background: white;
    border: 2px solid var(--arena);
    border-radius: 14px;
  }
  .miniatura {
    flex: none;
    width: 54px;
    height: 81px;
    display: grid;
    place-items: center;
    overflow: hidden;
    border-radius: 8px;
    border: 2px dashed var(--arena);
    background: var(--crema);
    font-size: 0.65rem;
    text-align: center;
    color: #7b8aa3;
  }
  .miniatura img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  .textos {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.15rem;
  }
  .mazahua {
    font-size: 1.2rem;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .espanol {
    color: #4a5d7a;
  }
  .etiqueta {
    margin-top: 0.2rem;
    padding: 0.05rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: bold;
  }
  .etiqueta.ok {
    background: #dcefdc;
    color: #1f6a35;
  }
  .etiqueta.falta {
    background: #fff1cf;
    color: #8a5a00;
    border: 1px solid var(--terracota);
  }
  .acciones {
    display: flex;
    align-items: center;
    gap: 0.3rem;
  }
  .icono {
    border: none;
    background: transparent;
    font-size: 1.3rem;
    padding: 0.4rem;
    border-radius: 10px;
  }
  .icono:hover {
    background: #fbe3e1;
  }

  .boton {
    padding: 0.7rem 1.3rem;
    border: none;
    border-radius: 12px;
    background: var(--verde);
    color: white;
    font-size: 1rem;
    font-weight: bold;
    box-shadow: 0 4px 12px rgba(15, 53, 87, 0.2);
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

  /* Ventana */
  .modal {
    position: fixed;
    inset: 0;
    z-index: 50;
    display: grid;
    place-items: center;
    padding: 1rem;
  }
  .fondo {
    position: absolute;
    inset: 0;
    border: none;
    background: rgba(15, 53, 87, 0.65);
  }
  .contenido {
    position: relative;
    width: min(100%, 420px);
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    padding: 1.4rem;
    text-align: center;
    background: var(--crema);
    border: 3px solid var(--cafe);
    border-radius: var(--radio);
  }
  .palabra {
    margin: 0;
    font-size: 1.2rem;
  }
  .espera {
    padding: 0.5rem 0;
  }
  .espera p {
    margin: 0.3rem 0;
  }
  .ayuda {
    color: #4a5d7a;
  }
  .onda {
    display: inline-block;
    font-size: 3.5rem;
    animation: latido 1.2s ease-in-out infinite;
  }
  @keyframes latido {
    50% {
      transform: scale(1.2);
      opacity: 0.6;
    }
  }
  .botones {
    display: flex;
    justify-content: center;
    gap: 0.6rem;
  }
  @media (prefers-reduced-motion: reduce) {
    .onda {
      animation: none;
    }
  }
  @media (max-width: 480px) {
    .lista {
      grid-template-columns: 1fr;
    }
  }
</style>