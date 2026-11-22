<script>
  import { onMount } from "svelte";
  import { API } from "../lib/config.js";

  let estado = $state("comprobando");

  onMount(async () => {
    try {
      const respuesta = await fetch(`${API}/api/salud/bd`);
      estado = respuesta.ok ? "ok" : "error";
    } catch {
      estado = "error";
    }
  });
</script>

<p class="estado {estado}">
  {#if estado === "comprobando"}
    Conectando con el servidor…
  {:else if estado === "ok"}
    Servidor conectado
  {:else}
    Sin conexión con el servidor
  {/if}
</p>

<style>
  .estado {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin: 0;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    background: white;
    font-size: 0.9rem;
  }
  .estado::before {
    content: "";
    width: 0.7rem;
    height: 0.7rem;
    border-radius: 50%;
    background: var(--terracota);
  }
  .ok::before {
    background: #2e9e5b;
  }
  .error::before {
    background: #d63a3a;
  }
</style>