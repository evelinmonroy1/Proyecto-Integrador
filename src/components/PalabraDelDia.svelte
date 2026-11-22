<script>
  // "Palabra del día": cada día muestra una tarjeta distinta, con su audio.
  import { onMount } from "svelte";
  import { API } from "../lib/config.js";

  let palabra = $state(null);
  let error = $state(false);
  let sonando = $state(false);
  let audio = null;

  onMount(async () => {
    try {
      const r = await fetch(`${API}/api/galeria`);
      if (!r.ok) throw new Error();
      const { palabras } = await r.json();
      const conImagen = palabras.filter((p) => p.imagen_url);
      if (!conImagen.length) throw new Error();
      // Número de día (cambia a medianoche, hora local)
      const hoy = new Date();
      const dia = Math.floor(
        Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()) / 86400000
      );
      palabra = conImagen[(dia * 7) % conImagen.length];
    } catch {
      error = true;
    }
  });

  function escuchar() {
    if (!palabra?.audio_url) return;
    audio?.pause();
    audio = new Audio(`${API}${palabra.audio_url}`);
    sonando = true;
    audio.onended = () => (sonando = false);
    audio.play().catch(() => (sonando = false));
  }

  const fecha = new Date().toLocaleDateString("es-MX", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
</script>

{#if palabra}
  <div class="palabra-dia">
    <img class="carta" src={`${API}${palabra.imagen_url}`} alt="{palabra.mazahua} ({palabra.espanol})" />
    <div class="info">
      <span class="etiqueta">✿ Palabra del día · {fecha}</span>
      <strong class="mazahua">{palabra.mazahua}</strong>
      <span class="espanol">{palabra.espanol}</span>
      <div class="acciones">
        {#if palabra.audio_url}
          <button type="button" class="escuchar" class:sonando onclick={escuchar}>
            {sonando ? "🔊 Escuchando…" : "🔈 Escuchar"}
          </button>
        {/if}
        <a class="ver" href="/galeria">Ver todas las tarjetas →</a>
      </div>
    </div>
  </div>
{:else if !error}
  <div class="palabra-dia cargando" aria-hidden="true"></div>
{/if}

<style>
  .palabra-dia {
    position: relative;
    display: flex;
    align-items: center;
    gap: clamp(1.2rem, 4vw, 2.8rem);
    max-width: 880px;
    margin: 0 auto;
    padding: 1.6rem clamp(1.2rem, 4vw, 2.6rem);
    border-radius: 26px;
    background: linear-gradient(135deg, #143b61 0%, #1f5c94 60%, #457caa 100%);
    color: white;
    box-shadow: 0 18px 36px -20px rgba(20, 59, 97, 0.7);
    overflow: hidden;
  }
  .palabra-dia::after {
    content: "";
    position: absolute;
    right: -60px;
    top: -60px;
    width: 220px;
    height: 220px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.07);
  }
  .cargando {
    height: 210px;
    opacity: 0.4;
  }
  .carta {
    flex: none;
    width: 120px;
    border-radius: 10px;
    border: 4px solid white;
    box-shadow: 0 12px 24px -10px rgba(0, 0, 0, 0.5);
    transform: rotate(-6deg);
    transition: transform 0.3s;
  }
  .palabra-dia:hover .carta {
    transform: rotate(0deg) scale(1.04);
  }
  .info {
    position: relative;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .etiqueta {
    align-self: flex-start;
    margin-bottom: 0.4rem;
    padding: 0.25rem 0.8rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.14);
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.04em;
  }
  .mazahua {
    font-family: "Baloo 2", "Nunito", system-ui, sans-serif;
    font-size: clamp(2.2rem, 5vw, 3.2rem);
    font-weight: 800;
    line-height: 1;
  }
  .espanol {
    font-size: 1.15rem;
    color: #d2dee7;
  }
  .acciones {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.8rem 1.4rem;
    margin-top: 1rem;
  }
  .escuchar {
    padding: 0.65rem 1.4rem;
    border: 0;
    border-radius: 999px;
    background: #f2c14e;
    color: #143b61;
    font: inherit;
    font-weight: 700;
    transition: transform 0.15s;
  }
  .escuchar:hover {
    transform: translateY(-2px);
  }
  .escuchar.sonando {
    background: white;
  }
  .ver {
    font-weight: 700;
    color: white;
    border-bottom: 2px solid #f2c14e;
  }
  @media (max-width: 560px) {
    .palabra-dia {
      flex-direction: column;
      text-align: center;
    }
    .etiqueta {
      align-self: center;
    }
    .acciones {
      justify-content: center;
    }
  }
</style>