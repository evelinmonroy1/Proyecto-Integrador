<script>
  import Avatar from "./Avatar.svelte";
  import {
    ANIMALES, CABEZA, CARA, FONDOS, NOMBRES_FONDO,
    esAvatar, leer, cambiar, aleatorio,
  } from "../lib/avatar.js";

  // Uso: <AvatarEditor bind:valor={avatar} />
  let { valor = $bindable("") } = $props();

  // clave = posición dentro del texto del avatar (0 animal, 1 cabeza, 2 cara, 3 fondo)
  const pestanas = [
    { clave: 0, nombre: "Animal", icono: "🐾" },
    { clave: 1, nombre: "Cabeza", icono: "👒" },
    { clave: 2, nombre: "Cara", icono: "🕶️" },
    { clave: 3, nombre: "Fondo", icono: "🎨" },
  ];
  const listas = [
    ANIMALES.map((a) => a.nombre),
    CABEZA,
    CARA,
    NOMBRES_FONDO,
  ];
  let activa = $state(0);

  // Si no hay avatar todavía (o es uno antiguo), arranca con uno al azar
  $effect(() => {
    if (!esAvatar(valor)) valor = aleatorio();
  });

  const actual = $derived(leer(valor));
  const elegir = (posicion, i) => (valor = cambiar(valor, posicion, i));
  // Vista previa: el mismo avatar con SOLO esa opción cambiada
  const probar = (posicion, i) => cambiar(valor, posicion, i);
</script>

<div class="editor">
  <div class="vista">
    <div class="grande"><Avatar codigo={valor} /></div>
    <button type="button" class="azar" onclick={() => (valor = aleatorio())}>🎲 Sorpréndeme</button>
  </div>

  <div class="pestanas" role="tablist">
    {#each pestanas as p (p.clave)}
      <button
        type="button"
        role="tab"
        class:activa={activa === p.clave}
        aria-selected={activa === p.clave}
        onclick={() => (activa = p.clave)}
      >
        <span class="icono">{p.icono}</span>{p.nombre}
      </button>
    {/each}
  </div>

  <div class="opciones" role="radiogroup" aria-label={pestanas[activa].nombre}>
    {#each listas[activa] as nombre, i}
      <button
        type="button"
        role="radio"
        class="op"
        class:elegida={actual[activa] === i}
        aria-checked={actual[activa] === i}
        aria-label={nombre}
        title={nombre}
        onclick={() => elegir(activa, i)}
      >
        <span class="mini"><Avatar codigo={probar(activa, i)} /></span>
        <span class="etiqueta">{nombre}</span>
      </button>
    {/each}
  </div>
</div>

<style>
  .editor {
    display: flex;
    flex-direction: column;
    gap: 0.9rem;
  }
  .vista {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
  }
  .grande {
    font-size: 8rem;
    line-height: 1;
  }
  .azar {
    padding: 0.5rem 1.1rem;
    font-size: 1rem;
    font-weight: bold;
    color: #4e7452;
    background: #fff;
    border: 2px solid #4e7452;
    border-radius: 999px;
    cursor: pointer;
  }
  .azar:hover {
    background: #4e7452;
    color: #fff;
  }
  .pestanas {
    display: flex;
    gap: 0.35rem;
    background: #efe5d0;
    padding: 0.3rem;
    border-radius: 14px;
  }
  .pestanas button {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.1rem;
    padding: 0.45rem 0.2rem;
    font-size: 0.85rem;
    font-weight: bold;
    color: #5a4636;
    background: transparent;
    border: none;
    border-radius: 11px;
    cursor: pointer;
  }
  .pestanas .icono {
    font-size: 1.25rem;
  }
  .pestanas button.activa {
    background: #fff;
    color: #4e7452;
    box-shadow: 0 1px 3px rgba(90, 70, 54, 0.25);
  }
  .opciones {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.55rem;
  }
  .op {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.2rem;
    padding: 0.5rem 0.25rem;
    background: #fff;
    border: 2px solid #e2d5bd;
    border-radius: 16px;
    cursor: pointer;
    transition: transform 0.12s, border-color 0.12s, box-shadow 0.12s;
  }
  .op:hover {
    transform: translateY(-2px);
  }
  .op.elegida {
    border-color: #4e7452;
    box-shadow: 0 0 0 3px rgba(78, 116, 82, 0.25);
    background: #f2f7ef;
  }
  .mini {
    font-size: 3.6rem;
    line-height: 1;
  }
  .etiqueta {
    font-size: 0.8rem;
    font-weight: bold;
    color: #5a4636;
    text-align: center;
  }
  @media (min-width: 520px) {
    .opciones {
      grid-template-columns: repeat(6, 1fr);
    }
    .mini {
      font-size: 3rem;
    }
  }
</style>
