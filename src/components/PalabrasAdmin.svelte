<script>
  import "../lib/auth.js";;
  import { onMount } from "svelte";
  import { API } from "../lib/config.js";

  const EXT_IMG = [".png", ".jpg", ".jpeg", ".webp"];
  const EXT_AUDIO = [".mp3", ".ogg", ".wav"];
  const MAX_MB = 5;

  // ---------- Datos ----------
  let palabras = $state([]);
  let categorias = $state([]);
  let total = $state(0);
  let busqueda = $state("");
  let filtroCategoria = $state("");
  let cargando = $state(true);
  let error = $state("");
  let aviso = $state("");
  // Las imágenes y audios se guardan con el mismo nombre al reemplazarlos;
  // este número obliga al navegador a pedirlos de nuevo.
  let version = $state(Date.now());

  // ---------- Formulario ----------
  let formAbierto = $state(false);
  let editando = $state(null);
  let fMazahua = $state("");
  let fEspanol = $state("");
  let fCategoria = $state("");
  let fImagen = $state(null);
  let fAudio = $state(null);
  let previaImagen = $state(null);
  let previaAudio = $state(null);
  let guardando = $state(false);
  let errorForm = $state("");
  let nuevaCategoria = $state("");

  const maxLado = $derived(Math.min(6, Math.floor(Math.sqrt(total))));
  const filtrando = $derived(busqueda.trim() !== "" || filtroCategoria !== "");

  let temporizador;
  let pedido = 0;
  let audio = null;

  const urlMedia = (ruta) => (ruta ? `${API}${ruta}?v=${version}` : null);
  const nombreCategoria = (id) => categorias.find((c) => c.id === id)?.nombre ?? null;

  function mensaje(d) {
    if (typeof d?.detail === "string") return d.detail;
    if (Array.isArray(d?.detail)) return d.detail.map((x) => x.msg).join(". ");
    return "Ocurrió un error inesperado";
  }

  function mostrarAviso(texto) {
    aviso = texto;
    setTimeout(() => (aviso = ""), 3500);
  }

  // ---------- Cargar ----------
  async function cargar() {
    const miPedido = ++pedido;
    try {
      const params = new URLSearchParams();
      if (busqueda.trim()) params.set("q", busqueda.trim());
      if (filtroCategoria) params.set("categoria_id", filtroCategoria);

      const [rp, rt] = await Promise.all([
        fetch(`${API}/api/palabras?${params}`),
        fetch(`${API}/api/salud/bd`),
      ]);
      if (!rp.ok) throw new Error();
      const lista = await rp.json();
      if (miPedido !== pedido) return; // llegó una respuesta más nueva
      palabras = lista;
      if (rt.ok) total = (await rt.json()).palabras;
      version = Date.now();
      error = "";
    } catch {
      if (miPedido === pedido) error = "No se pudieron cargar las palabras. ¿Está encendido el servidor?";
    } finally {
      if (miPedido === pedido) cargando = false;
    }
  }

  async function cargarCategorias() {
    try {
      const r = await fetch(`${API}/api/categorias`);
      if (r.ok) categorias = await r.json();
    } catch {}
  }

  function alEscribir() {
    clearTimeout(temporizador);
    temporizador = setTimeout(cargar, 300);
  }

  function limpiarFiltros() {
    busqueda = "";
    filtroCategoria = "";
    cargar();
  }

  // ---------- Audio de la lista ----------
  function escuchar(p) {
    audio?.pause();
    audio = new Audio(urlMedia(p.audio_url));
    audio.play().catch(() => (error = "No se pudo reproducir el audio"));
  }

  // ---------- Formulario ----------
  function soltarPrevias() {
    if (previaImagen) URL.revokeObjectURL(previaImagen);
    if (previaAudio) URL.revokeObjectURL(previaAudio);
    previaImagen = null;
    previaAudio = null;
    fImagen = null;
    fAudio = null;
  }

  function abrirNueva() {
    soltarPrevias();
    editando = null;
    fMazahua = "";
    fEspanol = "";
    fCategoria = "";
    errorForm = "";
    nuevaCategoria = "";
    formAbierto = true;
  }

  function abrirEditar(p) {
    soltarPrevias();
    editando = p;
    fMazahua = p.mazahua;
    fEspanol = p.espanol;
    fCategoria = p.categoria_id ?? "";
    errorForm = "";
    nuevaCategoria = "";
    formAbierto = true;
  }

  function cerrarForm() {
    soltarPrevias();
    formAbierto = false;
    editando = null;
  }

  function validar(archivo, extensiones) {
    const ext = "." + archivo.name.split(".").pop().toLowerCase();
    if (!extensiones.includes(ext)) {
      return `Formato no permitido (${ext}). Usa: ${extensiones.join(", ")}`;
    }
    if (archivo.size > MAX_MB * 1024 * 1024) {
      return `El archivo pesa más de ${MAX_MB} MB. Redúcelo antes de subirlo.`;
    }
    return "";
  }

  function elegirImagen(e) {
    errorForm = "";
    const entrada = e.currentTarget;
    const archivo = entrada.files[0];
    if (previaImagen) URL.revokeObjectURL(previaImagen);
    previaImagen = null;
    fImagen = null;
    if (!archivo) return;
    const problema = validar(archivo, EXT_IMG);
    if (problema) {
      errorForm = problema;
      entrada.value = "";
      return;
    }
    fImagen = archivo;
    previaImagen = URL.createObjectURL(archivo);
  }

  function elegirAudio(e) {
    errorForm = "";
    const entrada = e.currentTarget;
    const archivo = entrada.files[0];
    if (previaAudio) URL.revokeObjectURL(previaAudio);
    previaAudio = null;
    fAudio = null;
    if (!archivo) return;
    const problema = validar(archivo, EXT_AUDIO);
    if (problema) {
      errorForm = problema;
      entrada.value = "";
      return;
    }
    fAudio = archivo;
    previaAudio = URL.createObjectURL(archivo);
  }

  async function crearCategoria() {
    const nombre = nuevaCategoria.trim();
    if (!nombre) return;
    errorForm = "";
    try {
      const r = await fetch(`${API}/api/categorias?nombre=${encodeURIComponent(nombre)}`, {
        method: "POST",
      });
      const d = await r.json();
      if (!r.ok) {
        errorForm = mensaje(d);
        return;
      }
      categorias = [...categorias, d].sort((a, b) => a.nombre.localeCompare(b.nombre));
      fCategoria = d.id;
      nuevaCategoria = "";
    } catch {
      errorForm = "No se pudo conectar con el servidor";
    }
  }

  async function guardar() {
    errorForm = "";
    if (!fMazahua.trim() || !fEspanol.trim()) {
      errorForm = "Escribe la palabra en mazahua y su traducción al español";
      return;
    }

    const datos = new FormData();
    datos.append("mazahua", fMazahua.trim());
    datos.append("espanol", fEspanol.trim());
    if (fCategoria !== "") datos.append("categoria_id", String(fCategoria));
    if (fImagen) datos.append("imagen", fImagen);
    if (fAudio) datos.append("audio", fAudio);

    guardando = true;
    try {
      const url = editando ? `${API}/api/palabras/${editando.id}` : `${API}/api/palabras`;
      const r = await fetch(url, { method: editando ? "PUT" : "POST", body: datos });
      const d = await r.json();
      if (!r.ok) {
        errorForm = mensaje(d);
        return;
      }
      const eraNueva = !editando;
      cerrarForm();
      mostrarAviso(eraNueva ? `Se agregó "${d.mazahua}"` : `Se guardaron los cambios de "${d.mazahua}"`);
      await cargar();
    } catch {
      errorForm = "No se pudo conectar con el servidor";
    } finally {
      guardando = false;
    }
  }

  async function eliminar(p) {
    if (!confirm(`¿Eliminar "${p.mazahua}" (${p.espanol})?\nTambién se borrarán su imagen y su audio.`)) return;
    error = "";
    try {
      const r = await fetch(`${API}/api/palabras/${p.id}`, { method: "DELETE" });
      if (!r.ok) {
        error = mensaje(await r.json());
        return;
      }
      mostrarAviso(`Se eliminó "${p.mazahua}"`);
      await cargar();
    } catch {
      error = "No se pudo conectar con el servidor";
    }
  }

  onMount(() => {
    cargarCategorias();
    cargar();
    return () => {
      clearTimeout(temporizador);
      audio?.pause();
      soltarPrevias();
    };
  });
</script>

<svelte:window onkeydown={(e) => e.key === "Escape" && formAbierto && !guardando && cerrarForm()} />

<!-- ===== Herramientas ===== -->
<section class="tarjeta herramientas">
  <input
    class="buscador"
    type="search"
    placeholder="Buscar en mazahua o español…"
    bind:value={busqueda}
    oninput={alEscribir}
    aria-label="Buscar palabras"
  />
  <select bind:value={filtroCategoria} onchange={cargar} aria-label="Filtrar por categoría">
    <option value="">Todas las categorías</option>
    {#each categorias as c (c.id)}
      <option value={c.id}>{c.nombre}</option>
    {/each}
  </select>
  <button class="boton" onclick={abrirNueva}>＋ Nueva palabra</button>
</section>

<p class="resumen">
  {#if total < 4}
    Tienes <strong>{total}</strong> palabra{total === 1 ? "" : "s"}. Necesitas al menos 4 para jugar.
  {:else}
    Tienes <strong>{total}</strong> palabras: alcanzan para tableros de hasta
    <strong>{maxLado}×{maxLado}</strong>. Para que los tableros sean distintos entre jugadores,
    registra más palabras que casillas.
  {/if}
</p>

{#if aviso}<p class="exito">✓ {aviso}</p>{/if}
{#if error}<p class="error">{error}</p>{/if}

<!-- ===== Lista ===== -->
{#if cargando}
  <p class="vacio">Cargando palabras…</p>
{:else if palabras.length === 0}
  <section class="tarjeta">
    <p class="vacio">
      {#if filtrando}
        No hay palabras con esos filtros.
        <button class="enlace" onclick={limpiarFiltros}>Quitar filtros</button>
      {:else}
        Aún no hay palabras. Pulsa <strong>＋ Nueva palabra</strong> para agregar la primera.
      {/if}
    </p>
  </section>
{:else}
  <p class="contador">
    {filtrando ? `${palabras.length} resultado${palabras.length === 1 ? "" : "s"}` : `${palabras.length} palabras`}
  </p>
  <ul class="lista">
    {#each palabras as p (p.id)}
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
          <span class="etiquetas">
            {#if nombreCategoria(p.categoria_id)}
              <span class="etiqueta">{nombreCategoria(p.categoria_id)}</span>
            {/if}
            {#if !p.imagen_url}<span class="etiqueta falta">⚠ sin imagen</span>{/if}
            {#if !p.audio_url}<span class="etiqueta falta">⚠ sin audio</span>{/if}
          </span>
        </div>

        <div class="acciones">
          {#if p.audio_url}
            <button class="icono" onclick={() => escuchar(p)} title="Escuchar" aria-label="Escuchar {p.mazahua}">🔊</button>
          {/if}
          <button class="icono" onclick={() => abrirEditar(p)} title="Editar" aria-label="Editar {p.mazahua}">✏️</button>
          <button class="icono peligro" onclick={() => eliminar(p)} title="Eliminar" aria-label="Eliminar {p.mazahua}">🗑️</button>
        </div>
      </li>
    {/each}
  </ul>
{/if}

<!-- ===== Formulario (agregar / editar) ===== -->
{#if formAbierto}
  <div class="modal" role="dialog" aria-modal="true" aria-label={editando ? "Editar palabra" : "Nueva palabra"}>
    <button class="fondo" aria-label="Cerrar" onclick={() => !guardando && cerrarForm()}></button>

    <div class="contenido">
      <h2>{editando ? "Editar palabra" : "Nueva palabra"}</h2>

      <label>
        Palabra en mazahua
        <input bind:value={fMazahua} maxlength="100" autocomplete="off" />
      </label>

      <label>
        Traducción al español
        <input bind:value={fEspanol} maxlength="100" autocomplete="off" />
      </label>

      <label>
        Categoría
        <select bind:value={fCategoria}>
          <option value="">Sin categoría</option>
          {#each categorias as c (c.id)}
            <option value={c.id}>{c.nombre}</option>
          {/each}
        </select>
      </label>

      <div class="nueva-categoria">
        <input
          bind:value={nuevaCategoria}
          placeholder="¿Otra categoría? Escríbela aquí"
          maxlength="80"
          onkeydown={(e) => e.key === "Enter" && (e.preventDefault(), crearCategoria())}
        />
        <button class="secundario chico" onclick={crearCategoria} disabled={!nuevaCategoria.trim()}>
          Crear
        </button>
      </div>

      <div class="archivo">
        <span class="titulo-campo">Imagen de la tarjeta (PNG, JPG o WEBP, máx. {MAX_MB} MB)</span>
        {#if previaImagen || editando?.imagen_url}
          <img class="previa" src={previaImagen ?? urlMedia(editando.imagen_url)} alt="Vista previa" />
        {/if}
        <input type="file" accept=".png,.jpg,.jpeg,.webp,image/*" onchange={elegirImagen} />
        {#if editando?.imagen_url && !fImagen}
          <small>Deja vacío para conservar la imagen actual.</small>
        {/if}
      </div>

      <div class="archivo">
        <span class="titulo-campo">Audio en mazahua (MP3, OGG o WAV, máx. {MAX_MB} MB)</span>
        {#if previaAudio || editando?.audio_url}
          <audio controls src={previaAudio ?? urlMedia(editando.audio_url)}></audio>
        {/if}
        <input type="file" accept=".mp3,.ogg,.wav,audio/*" onchange={elegirAudio} />
        {#if editando?.audio_url && !fAudio}
          <small>Deja vacío para conservar el audio actual.</small>
        {/if}
      </div>

      {#if errorForm}<p class="error">{errorForm}</p>{/if}

      <div class="botones">
        <button class="secundario" onclick={cerrarForm} disabled={guardando}>Cancelar</button>
        <button class="boton" onclick={guardar} disabled={guardando}>
          {guardando ? "Guardando…" : editando ? "Guardar cambios" : "Agregar palabra"}
        </button>
      </div>
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

  /* Herramientas */
  .herramientas {
    display: flex;
    flex-wrap: wrap;
    gap: 0.7rem;
    align-items: center;
  }
  .buscador {
    flex: 1 1 220px;
  }
  input,
  select {
    font: inherit;
    padding: 0.6rem 0.9rem;
    border: 2px solid var(--cafe);
    border-radius: 12px;
    background: var(--crema);
    min-width: 0;
  }
  input:focus,
  select:focus {
    outline: 3px solid var(--salvia);
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
  .boton:active {
    transform: translateY(2px);
    box-shadow: 0 2px 6px rgba(15, 53, 87, 0.2);
  }
  .boton:disabled {
    opacity: 0.55;
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
  .enlace {
    border: none;
    background: none;
    color: var(--terracota-oscuro);
    font-weight: bold;
    text-decoration: underline;
  }

  .resumen {
    margin: 0 0 1rem;
    color: #4a5d7a;
  }
  .contador {
    margin: 0 0 0.6rem;
    font-weight: bold;
    color: var(--cafe);
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
    border: none;
  }
  .textos {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .mazahua {
    font-size: 1.2rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .espanol {
    color: #4a5d7a;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .etiquetas {
    display: flex;
    flex-wrap: wrap;
    gap: 0.3rem;
    margin-top: 0.2rem;
  }
  .etiqueta {
    padding: 0.05rem 0.6rem;
    border-radius: 999px;
    background: var(--salvia);
    color: white;
    font-size: 0.75rem;
    font-weight: bold;
  }
  .etiqueta.falta {
    background: #fff1cf;
    color: #8a5a00;
    border: 1px solid var(--terracota);
  }
  .acciones {
    display: flex;
    gap: 0.2rem;
  }
  .icono {
    border: none;
    background: transparent;
    font-size: 1.3rem;
    padding: 0.4rem;
    border-radius: 10px;
  }
  .icono:hover {
    background: var(--crema);
  }
  .icono.peligro:hover {
    background: #fbe3e1;
  }

  /* Formulario */
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
    width: min(100%, 480px);
    max-height: 94vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
    padding: 1.3rem;
    background: var(--crema);
    border: 3px solid var(--cafe);
    border-radius: var(--radio);
  }
  label {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
    font-weight: bold;
  }
  label input,
  label select {
    font-weight: normal;
  }
  .nueva-categoria {
    display: flex;
    gap: 0.5rem;
  }
  .nueva-categoria input {
    flex: 1;
    font-size: 0.9rem;
  }
  .archivo {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    padding: 0.7rem;
    border: 2px dashed var(--arena);
    border-radius: 12px;
    background: white;
  }
  .titulo-campo {
    font-weight: bold;
    font-size: 0.9rem;
  }
  .archivo input[type="file"] {
    padding: 0.4rem;
    font-size: 0.85rem;
  }
  .archivo small {
    color: #4a5d7a;
  }
  .previa {
    max-width: 120px;
    max-height: 180px;
    object-fit: contain;
    border-radius: 8px;
    border: 2px solid var(--cafe);
    align-self: center;
  }
  audio {
    width: 100%;
  }
  .botones {
    display: flex;
    justify-content: flex-end;
    gap: 0.6rem;
  }

  @media (max-width: 480px) {
    .lista {
      grid-template-columns: 1fr;
    }
  }
</style>