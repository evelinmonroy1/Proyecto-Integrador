from collections import defaultdict
from fastapi import WebSocket


class Salas:
    """Guarda las conexiones WebSocket agrupadas por código de partida."""

    def __init__(self):
        self.salas: dict[str, list[dict]] = defaultdict(list)

    async def conectar(self, codigo: str, ws: WebSocket, rol: str, jugador_id: int | None):
        await ws.accept()
        self.salas[codigo].append({"ws": ws, "rol": rol, "jugador_id": jugador_id})

    def desconectar(self, codigo: str, ws: WebSocket):
        if codigo not in self.salas:
            return
        self.salas[codigo] = [c for c in self.salas[codigo] if c["ws"] is not ws]
        if not self.salas[codigo]:
            del self.salas[codigo]

    def ids_conectados(self, codigo: str) -> set:
        return {
            c["jugador_id"]
            for c in self.salas.get(codigo, [])
            if c["rol"] == "jugador"
        }

    async def difundir(self, codigo: str, mensaje: dict):
        """Envía un mensaje a todos los conectados de esa partida."""
        for c in list(self.salas.get(codigo, [])):
            try:
                await c["ws"].send_json(mensaje)
            except Exception:
                self.desconectar(codigo, c["ws"])


salas = Salas()