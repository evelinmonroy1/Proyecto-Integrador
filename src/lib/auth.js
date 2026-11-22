// Sesión del administrador en el navegador.
// Se importa SOLO en las páginas y componentes de /admin (no en los del jugador).
import { API } from "./config.js";

const CLAVE = "loteria_admin_token";

// La sesión vive en sessionStorage: se borra sola al cerrar la pestaña o el navegador.
// (Se limpia también cualquier sesión vieja que haya quedado guardada en localStorage.)
try { localStorage.removeItem(CLAVE); } catch {}

export function obtenerToken() {
  try { return sessionStorage.getItem(CLAVE); } catch { return null; }
}
export function guardarToken(t) {
  try { sessionStorage.setItem(CLAVE, t); } catch {}
}
export function cerrarSesion() {
  try { sessionStorage.removeItem(CLAVE); } catch {}
  window.location.href = "/admin/login";
}

// Todo lo siguiente solo corre en el navegador (en el servidor de Astro no existe "window")
if (typeof window !== "undefined") {
  const enLogin = window.location.pathname.startsWith("/admin/login");

  // 1) Sin sesión no se ve ninguna página de administrador
  if (!enLogin && !obtenerToken()) {
    window.location.replace("/admin/login");
  }

  // 2) Todas las llamadas a la API llevan la sesión automáticamente
  if (!window.__authFetch) {
    window.__authFetch = true;
    const original = window.fetch.bind(window);
    window.fetch = async (entrada, init = {}) => {
      const url = typeof entrada === "string" ? entrada : entrada.url;
      const token = obtenerToken();
      if (token && url.startsWith(API)) {
        const headers = new Headers(init.headers || (typeof entrada === "string" ? undefined : entrada.headers));
        headers.set("Authorization", `Bearer ${token}`);
        init = { ...init, headers };
      }
      const r = await original(entrada, init);
      // Sesión vencida o inválida: volver al login
      if (r.status === 401 && url.startsWith(API) && !url.includes("/api/auth/login") && !enLogin) {
        try { sessionStorage.removeItem(CLAVE); } catch {}
        window.location.replace("/admin/login");
      }
      return r;
    };
  }
}