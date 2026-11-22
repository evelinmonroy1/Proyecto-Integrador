
<script>
import Avatar from "./Avatar.svelte"
  let { ganadores = [], yoId = null, completado = false, grande = false } = $props();

  const medallas = { 1: "🥇", 2: "🥈", 3: "🥉" };
  const nombresLugar = { 1: "primer lugar", 2: "segundo lugar", 3: "tercer lugar" };
  const orden = [2, 1, 3]; // el primer lugar va al centro

  const porLugar = $derived(new Map(ganadores.map((g) => [g.lugar, g.jugador])));
  const miLugar = $derived(ganadores.find((g) => g.jugador.id === yoId)?.lugar ?? null);

  // Confeti con valores fijos (no cambia entre una pantalla y otra)
  const colores = ["#8fb08c", "#d9783f", "#d9534f", "#a9cfd6", "#e9b949", "#4e7452"];
  const confeti = Array.from({ length: 36 }, (_, i) => ({
    izq: (i * 37) % 100,
    retraso: (i % 9) * 0.35,
    duracion: 3 + (i % 5) * 0.6,
    color: colores[i % colores.length],
  }));
</script>

<section class="caja" class:grande>
  {#if ganadores.length > 0}
    <div class="confeti" aria-hidden="true">
      {#each confeti as c}
        <span
          style:left="{c.izq}%"
          style:background={c.color}
          style:animation-delay="{c.retraso}s"
          style:animation-duration="{c.duracion}s"
        ></span>
      {/each}
    </div>
  {/if}

  <h2>🎉 ¡Partida terminada!</h2>

  {#if ganadores.length === 0}
    <p class="mensaje">Se acabaron las tarjetas y nadie completó su tablero.</p>
  {:else if miLugar}
    <p class="mensaje">{medallas[miLugar]} ¡Felicidades! Quedaste en {nombresLugar[miLugar]}</p>
  {:else if completado}
    <p class="mensaje">Completaste tu tablero, pero el podio ya estaba lleno. ¡Muy bien!</p>
  {:else if yoId !== null}
    <p class="mensaje">¡Buen juego! Cada palabra que aprendiste cuenta.</p>
  {:else}
    <p class="mensaje">¡Felicidades a los ganadores!</p>
  {/if}

  {#if ganadores.length > 0}
    <div class="podio" role="list">
      {#each orden as lugar}
        {@const j = porLugar.get(lugar)}
        <div
          class="puesto p{lugar}"
          class:vacio={!j}
          class:mio={j && j.id === yoId}
          role="listitem"
        >
          <div class="persona">
            {#if j}
              <span class="avatar"><Avatar codigo={j.avatar} emoji={j.emoji} /></span>
              <strong class="nombre">{j.nombre}</strong>
            {:else}
              <span class="avatar">·</span>
              <span class="nombre">—</span>
            {/if}
          </div>
          <div class="bloque">
            <span class="medalla">{medallas[lugar]}</span>
            <span class="num">{lugar}</span>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <p class="gracias">Gracias por jugar y aprender mazahua</p>
</section>

<style>
  .caja {
    position: relative;
    overflow: hidden;
    text-align: center;
    padding: 1.5rem 1rem 1.2rem;
    margin-bottom: 1.2rem;
    background: var(--arena);
    border: 2px solid var(--cafe);
    border-radius: var(--radio);
    box-shadow: 0 6px 0 rgba(181, 131, 90, 0.25);
  }
  h2 {
    font-size: clamp(1.5rem, 5vw, 2.1rem);
  }
  .grande h2 {
    font-size: clamp(2rem, 6vw, 3rem);
  }
  .mensaje {
    margin: 0.6rem 0 1.4rem;
    font-size: 1.2rem;
    font-weight: bold;
    color: var(--terracota-oscuro);
  }
  .grande .mensaje {
    font-size: 1.5rem;
  }
  .gracias {
    margin: 1.2rem 0 0;
    color: #6b5a4a;
  }

  /* ----- Podio ----- */
  .podio {
    position: relative;
    z-index: 1;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    gap: 0.6rem;
    max-width: 560px;
    margin: 0 auto;
  }
  .grande .podio {
    max-width: 800px;
  }
  .puesto {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
  }
  .persona {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.2rem;
    width: 100%;
    padding-bottom: 0.4rem;
    opacity: 0;
    animation: aparecer 0.5s ease-out forwards;
  }
  .avatar {
    font-size: clamp(2.2rem, 9vw, 3.4rem);
    line-height: 1;
  }
  .grande .avatar {
    font-size: clamp(3rem, 9vw, 5rem);
  }
  .nombre {
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: clamp(0.9rem, 3.5vw, 1.2rem);
  }
  .grande .nombre {
    font-size: clamp(1.1rem, 3vw, 1.6rem);
  }
  .mio .nombre {
    background: var(--crema);
    border: 2px solid var(--terracota-oscuro);
    border-radius: 999px;
    padding: 0 0.6rem;
  }
  .vacio .persona {
    opacity: 0.35;
    animation: none;
  }

  .bloque {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-start;
    padding-top: 0.5rem;
    border: 3px solid var(--cafe);
    border-bottom: none;
    border-radius: 14px 14px 0 0;
    color: white;
    transform-origin: bottom;
    transform: scaleY(0);
    animation: subir 0.6s ease-out forwards;
  }
  .medalla {
    font-size: clamp(1.5rem, 6vw, 2.2rem);
  }
  .num {
    font-size: clamp(1.6rem, 7vw, 2.6rem);
    font-weight: bold;
  }

  .p1 .bloque {
    height: 170px;
    background: var(--terracota-oscuro);
    animation-delay: 1.5s;
  }
  .p2 .bloque {
    height: 125px;
    background: var(--verde);
    animation-delay: 0.9s;
  }
  .p3 .bloque {
    height: 95px;
    background: var(--cafe);
    animation-delay: 0.3s;
  }
  .grande .p1 .bloque { height: 230px; }
  .grande .p2 .bloque { height: 170px; }
  .grande .p3 .bloque { height: 125px; }

  .p1 .persona { animation-delay: 2.0s; }
  .p2 .persona { animation-delay: 1.4s; }
  .p3 .persona { animation-delay: 0.8s; }

  .vacio .bloque {
    opacity: 0.45;
  }

  @keyframes subir {
    to { transform: scaleY(1); }
  }
  @keyframes aparecer {
    from { opacity: 0; transform: translateY(12px); }
    to { opacity: 1; transform: translateY(0); }
  }

  /* ----- Confeti ----- */
  .confeti {
    position: absolute;
    inset: 0;
    overflow: hidden;
    pointer-events: none;
    z-index: 0;
  }
  .confeti span {
    position: absolute;
    top: -14px;
    width: 10px;
    height: 16px;
    border-radius: 2px;
    opacity: 0.9;
    animation-name: caer;
    animation-timing-function: linear;
    animation-iteration-count: infinite;
  }
  @keyframes caer {
    to {
      transform: translateY(520px) rotate(540deg);
    }
  }

  /* Si la persona prefiere menos movimiento, todo aparece de golpe */
  @media (prefers-reduced-motion: reduce) {
    .bloque,
    .persona {
      animation: none;
      opacity: 1;
      transform: none;
    }
    .confeti {
      display: none;
    }
  }
</style>