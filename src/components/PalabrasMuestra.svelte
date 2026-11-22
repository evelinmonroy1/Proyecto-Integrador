<script>
  // Frases para empezar: se escuchan con los mismos audios del juego.
  import { API } from "../lib/config.js";

  const frases = [
    { id: 1, mazahua: "Kjimiji", espanol: "Buenos días" },
    { id: 2, mazahua: "Ja bi chjenzhⱥ", espanol: "Buenas tardes" },
    { id: 3, mazahua: "Chjetji", espanol: "Buenas noches" },
    { id: 4, mazahua: "In chjuzgo e…", espanol: "Mi nombre es…" },
    { id: 5, mazahua: "Na jo'o bi ñ'eje", espanol: "Bienvenidos" },
    { id: 6, mazahua: "Pokjʉ", espanol: "Muchas gracias" },
    { id: 7, mazahua: "Na jo'o gi ñonʉ", espanol: "Buen provecho" },
    { id: 8, mazahua: "Maxkjo", espanol: "Adiós, nos vemos" },
  ];

  let sonando = $state(null);
  let fallo = $state(false);
  let audio = null;

  function escuchar(f) {
    audio?.pause();
    fallo = false;
    sonando = f.id;
    audio = new Audio(`${API}/media/audios/${f.id}.mp3`);
    audio.onended = () => (sonando = null);
    audio.play().catch(() => {
      sonando = null;
      fallo = true;
    });
  }
</script>

<ul class="frases">
  {#each frases as f (f.id)}
    <li>
      <button type="button" class:sonando={sonando === f.id} onclick={() => escuchar(f)}>
        <span class="bocina" aria-hidden="true">{sonando === f.id ? "❚❚" : "▶"}</span>
        <strong>{f.mazahua}</strong>
        <small>{f.espanol}</small>
      </button>
    </li>
  {/each}
</ul>
{#if fallo}
  <p class="aviso">No se pudo reproducir el audio. Revisa que el servidor esté encendido.</p>
{/if}

<style>
  .frases {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    column-gap: 3rem;
    margin: 2.5rem 0 0;
    padding: 0;
    list-style: none;
    border-top: 1px solid var(--arena);
  }
  button {
    width: 100%;
    display: grid;
    grid-template-columns: auto 1fr auto;
    align-items: center;
    column-gap: 1.2rem;
    padding: 1.2rem 0;
    text-align: left;
    background: none;
    border: 0;
    border-bottom: 1px solid var(--arena);
    color: var(--tinta);
  }
  .bocina {
    display: grid;
    place-items: center;
    width: 2.4rem;
    height: 2.4rem;
    border-radius: 50%;
    border: 1px solid var(--arena);
    font-size: 0.7rem;
    color: var(--verde);
    transition: background 0.2s, border-color 0.2s, color 0.2s;
  }
  button:hover .bocina,
  button.sonando .bocina {
    border-color: var(--verde);
    background: var(--verde);
    color: white;
  }
  strong {
    font-family: var(--serif, Georgia, serif);
    font-size: 1.3rem;
    font-weight: 400;
  }
  small {
    font-size: 0.9rem;
    font-style: italic;
    color: var(--cafe);
  }
  button.sonando strong {
    color: var(--verde);
  }
  .aviso {
    margin-top: 1rem;
    color: var(--coral);
  }
  @media (max-width: 640px) {
    .frases {
      grid-template-columns: 1fr;
    }
    button {
      grid-template-columns: auto 1fr;
    }
    small {
      grid-column: 2;
    }
  }
</style>
