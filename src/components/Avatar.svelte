
<script>
  import { esAvatar, leer, ANIMALES, FONDOS, nombre } from "../lib/avatar.js";

  // codigo: "k-2-1-0-3". emoji: se usa solo con avatares antiguos.
  let { codigo = "", emoji = "🙂" } = $props();

  const valido = $derived(esAvatar(codigo));
  const partes = $derived(leer(codigo));
  const an = $derived(ANIMALES[partes[0]]);
  const cabeza = $derived(partes[1]);
  const cara = $derived(partes[2]);
  const fondo = $derived(FONDOS[partes[3]]);

  // El animalito ocupa el 80 % del cuadro para dejar sitio a los sombreros
  const K = 0.8;
  const OX = 10;
  const OY = 17;
  const px = (x) => OX + x * K;
  const py = (y) => OY + y * K;
  // Los accesorios se dibujan en "unidades de cara": 100 unidades = ancho de la cara
  const esc = $derived((an.ancho * K) / 100);
  const posCabeza = $derived(`translate(${px(an.cx)} ${py(an.top)}) scale(${esc})`);
  const posLado = (dx, dy) =>
    `translate(${px(an.cx + (an.ancho * dx) / 100)} ${py(an.top + (an.ancho * dy) / 100)}) scale(${esc})`;
  const posOjos = $derived(`translate(${px(an.ex)} ${py(an.ey)}) scale(${esc})`);
  const sep = $derived((an.sep / an.ancho) * 100); // separación de los ojos en unidades de cara
  const r = $derived(sep * 0.33);                  // radio de un lente
</script>

{#if valido}
  <span class="avatar-dibujo" role="img" aria-label={nombre(codigo)} style:background-color={fondo}>
    <img class="animal" src={an.archivo} alt="" loading="lazy" decoding="async" draggable="false" />
    <svg class="capa" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <!-- ================= CARA ================= -->
      {#if cara === 1}
        <g transform={posOjos} stroke-linecap="round">
          <path d={`M${-sep / 2 + r} -1 Q0 -${r * 0.45} ${sep / 2 - r} -1`} fill="none" stroke="#2c4a6e" stroke-width="2.4" />
          <circle cx={-sep / 2} cy="0" r={r} fill="#ffffff" fill-opacity="0.22" stroke="#2c4a6e" stroke-width="2.6" />
          <circle cx={sep / 2} cy="0" r={r} fill="#ffffff" fill-opacity="0.22" stroke="#2c4a6e" stroke-width="2.6" />
          <path d={`M${-sep / 2 - r * 0.6} ${-r * 0.55} Q${-sep / 2 - r * 0.2} ${-r * 0.85} ${-sep / 2 + r * 0.3} ${-r * 0.75}`} fill="none" stroke="#fff" stroke-opacity="0.85" stroke-width="2" />
          <path d={`M${sep / 2 - r * 0.6} ${-r * 0.55} Q${sep / 2 - r * 0.2} ${-r * 0.85} ${sep / 2 + r * 0.3} ${-r * 0.75}`} fill="none" stroke="#fff" stroke-opacity="0.85" stroke-width="2" />
        </g>
      {:else if cara === 2}
        <g transform={posOjos} stroke-linecap="round">
          <path d={`M${-sep / 2 + r} -2 Q0 -${r * 0.5} ${sep / 2 - r} -2`} fill="none" stroke="#1f1f2b" stroke-width="3" />
          <rect x={-sep / 2 - r * 1.15} y={-r * 0.8} width={r * 2.3} height={r * 1.7} rx={r * 0.7} fill="#23232f" stroke="#111" stroke-width="1.6" />
          <rect x={sep / 2 - r * 1.15} y={-r * 0.8} width={r * 2.3} height={r * 1.7} rx={r * 0.7} fill="#23232f" stroke="#111" stroke-width="1.6" />
          <path d={`M${-sep / 2 - r * 0.7} ${-r * 0.35} L${-sep / 2 - r * 0.15} ${-r * 0.65}`} stroke="#fff" stroke-opacity="0.7" stroke-width="2.4" />
          <path d={`M${sep / 2 - r * 0.7} ${-r * 0.35} L${sep / 2 - r * 0.15} ${-r * 0.65}`} stroke="#fff" stroke-opacity="0.7" stroke-width="2.4" />
        </g>
      {/if}

      <!-- ================= CABEZA ================= -->
      {#if cabeza === 1}
        <!-- sombrero charro -->
        <g transform={posCabeza} stroke-linejoin="round">
          <g transform="translate(0 5)">
            <ellipse cx="0" cy="2" rx="68" ry="13" fill="#a87a3e" />
            <ellipse cx="0" cy="-3" rx="68" ry="12" fill="#e8c274" stroke="#8a5a2b" stroke-width="1.8" />
            <path d="M-30 -6 C-33 -40 -19 -58 0 -58 C19 -58 33 -40 30 -6 Q0 3 -30 -6 Z" fill="#f0cc84" stroke="#8a5a2b" stroke-width="1.8" />
            <path d="M-30.4 -9 Q0 0 30.4 -9 L30.8 -22 Q0 -13 -30.8 -22 Z" fill="#d9534f" stroke="#8a2f2c" stroke-width="1.2" />
            <path d="M-18 -17 l5 5 l-5 5 l-5 -5 Z" fill="#f5c542" transform="translate(0 -1)" />
            <path d="M0 -15 l5 5 l-5 5 l-5 -5 Z" fill="#4fb3a9" transform="translate(0 0)" />
            <path d="M18 -17 l5 5 l-5 5 l-5 -5 Z" fill="#f5c542" transform="translate(0 -1)" />
            <ellipse cx="-12" cy="-42" rx="5" ry="11" fill="#fff" fill-opacity="0.4" transform="rotate(-16 -12 -42)" />
          </g>
        </g>
      {:else if cabeza === 2}
        <!-- corona -->
        <g transform={posCabeza} stroke-linejoin="round">
          <g transform="translate(0 6)">
            <path d="M-36 0 L-41 -36 L-21 -19 L0 -46 L21 -19 L41 -36 L36 0 Z" fill="#f7c948" stroke="#a8741a" stroke-width="1.8" />
            <rect x="-36" y="-9" width="72" height="9" rx="2.5" fill="#eaa92d" stroke="#a8741a" stroke-width="1.6" />
            <circle cx="0" cy="-45" r="4.2" fill="#e5484d" stroke="#8f1d22" stroke-width="1.2" />
            <circle cx="-41" cy="-36" r="3.8" fill="#4aa3df" stroke="#235e8a" stroke-width="1.2" />
            <circle cx="41" cy="-36" r="3.8" fill="#4aa3df" stroke="#235e8a" stroke-width="1.2" />
            <circle cx="0" cy="-4.5" r="2.6" fill="#e5484d" />
            <circle cx="-16" cy="-4.5" r="2.2" fill="#fff" fill-opacity="0.85" />
            <circle cx="16" cy="-4.5" r="2.2" fill="#fff" fill-opacity="0.85" />
            <path d="M-26 -8 L-30 -26" stroke="#fff" stroke-opacity="0.55" stroke-width="2.6" stroke-linecap="round" />
          </g>
        </g>
      {:else if cabeza === 3}
        <!-- moño de lado -->
        <g transform={posLado(32, 8) + " rotate(14)"} stroke-linejoin="round">
          <path d="M-3 0 L-30 -19 Q-36 0 -30 19 Z" fill="#ee5f9d" stroke="#a8336a" stroke-width="1.8" />
          <path d="M3 0 L30 -19 Q36 0 30 19 Z" fill="#ee5f9d" stroke="#a8336a" stroke-width="1.8" />
          <circle cx="-20" cy="-4" r="2.6" fill="#fff" fill-opacity="0.9" />
          <circle cx="-22" cy="7" r="2.2" fill="#fff" fill-opacity="0.9" />
          <circle cx="20" cy="-4" r="2.6" fill="#fff" fill-opacity="0.9" />
          <circle cx="22" cy="7" r="2.2" fill="#fff" fill-opacity="0.9" />
          <ellipse cx="0" cy="0" rx="7" ry="9" fill="#d63f85" stroke="#a8336a" stroke-width="1.6" />
          <ellipse cx="-2" cy="-3" rx="2.2" ry="3.2" fill="#fff" fill-opacity="0.5" />
        </g>
      {:else if cabeza === 4}
        <!-- flor de lado -->
        <g transform={posLado(-30, 10)}>
          {#each [0, 72, 144, 216, 288] as giro}
            <ellipse cx="0" cy="-13" rx="9" ry="12" fill="#ff90ba" stroke="#c55a86" stroke-width="1.6" transform={`rotate(${giro})`} />
          {/each}
          <circle cx="0" cy="0" r="8" fill="#ffd43f" stroke="#c99600" stroke-width="1.6" />
          <circle cx="-2.4" cy="-2.6" r="2.4" fill="#fff" fill-opacity="0.65" />
        </g>
      {:else if cabeza === 5}
        <!-- gorra -->
        <g transform={posCabeza} stroke-linejoin="round">
          <g transform="translate(0 6)">
            <path d="M-35 0 C-37 -44 37 -44 35 0 Z" fill="#4584d6" stroke="#234f8f" stroke-width="1.8" />
            <path d="M0 -40 C-6 -26 -6 -12 0 0" fill="none" stroke="#2e65ad" stroke-width="1.6" />
            <path d="M-10 -3 C20 -6 48 -2 58 8 C42 14 10 12 -10 7 Z" fill="#2f62a8" stroke="#234f8f" stroke-width="1.8" />
            <circle cx="0" cy="-40" r="3.4" fill="#2e65ad" stroke="#234f8f" stroke-width="1.2" />
            <ellipse cx="-14" cy="-26" rx="5" ry="10" fill="#fff" fill-opacity="0.35" transform="rotate(-18 -14 -26)" />
            <path d="M10 -22 l3 6 l6.5 1 l-4.8 4.4 l1.2 6.4 l-5.9 -3.2 l-5.9 3.2 l1.2 -6.4 l-4.8 -4.4 l6.5 -1 Z" fill="#ffd43f" transform="translate(2 2) scale(0.8)" />
          </g>
        </g>
      {/if}
    </svg>
  </span>
{:else}
  <span class="avatar-emoji">{emoji}</span>
{/if}

<style>
  /* Se ajusta al tamaño de letra del lugar donde se use (font-size) */
  .avatar-dibujo {
    position: relative;
    display: inline-block;
    width: 1.15em;
    height: 1.15em;
    border-radius: 28%;
    overflow: hidden;
    vertical-align: middle;
    border: 0.04em solid #2c4a6e;
    box-sizing: border-box;
    line-height: 0;
    background-image: radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0) 62%);
  }
  .animal {
    position: absolute;
    left: 10%;
    top: 17%;
    width: 80%;
    height: 80%;
    object-fit: contain;
    pointer-events: none;
    user-select: none;
    filter: drop-shadow(0 0.02em 0.02em rgba(15, 53, 87, 0.3));
  }
  .capa {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    filter: drop-shadow(0 0.012em 0.012em rgba(15, 53, 87, 0.3));
  }
</style>
