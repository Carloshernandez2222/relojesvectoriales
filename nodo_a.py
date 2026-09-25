"""Nodo A independiente.

Proceso propio, reloj vectorial propio y API REST en el puerto 5001.
Se comunica con B y C solo por HTTP/JSON. No comparte memoria con los otros nodos.
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

from vector_clock import VectorClock

NODO_ID = "A"
PUERTO = 5001
PARES = {
    "A": "http://127.0.0.1:5001",
    "B": "http://127.0.0.1:5002",
    "C": "http://127.0.0.1:5003",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("nodo_a")


class NodoA:
    def __init__(self) -> None:
        self.node_id = NODO_ID
        self.peers = PARES
        self.clock = VectorClock(list(PARES.keys()), NODO_ID)
        self.lock = threading.Lock()
        self.history: list[dict] = []
        self.pending_acks: dict[str, dict] = {}
        self.received: dict[str, dict] = {}
        self.stats = {
            "eventos_locales": 0,
            "mensajes_enviados": 0,
            "mensajes_recibidos": 0,
            "acks_enviados": 0,
            "acks_recibidos": 0,
            "recepciones_confirmadas": 0,
            "acks_ignorados": 0,
            "mensajes_duplicados": 0,
            "ediciones_manuales": 0,
        }

    def _record(self, tipo: str, detalle: str, antes: dict, despues: dict, extra: dict | None = None) -> dict:
        entrada = {
            "marca_tiempo": datetime.now(timezone.utc).isoformat(),
            "nodo": self.node_id,
            "tipo": tipo,
            "detalle": detalle,
            "reloj_antes": antes,
            "reloj_despues": despues,
        }
        if extra:
            entrada.update(extra)
        self.history.append(entrada)
        logger.info("%s | %s | %s -> %s | %s", self.node_id, tipo, antes, despues, detalle)
        return entrada

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "nodo": self.node_id,
                "archivo": "nodo_a.py",
                "reloj": self.clock.copy(),
                "pares": self.peers,
                "estadisticas": dict(self.stats),
                "pendientes_ack": list(self.pending_acks.values()),
                "historial": list(self.history),
            }

    def local_event(self, descripcion: str = "evento local") -> dict:
        with self.lock:
            antes = self.clock.copy()
            despues = self.clock.increment()
            self.stats["eventos_locales"] += 1
            return self._record("EVENTO_LOCAL", descripcion, antes, despues)

    def edit_clock(self, valores: dict, motivo: str = "edición manual") -> dict:
        with self.lock:
            antes = self.clock.copy()
            despues = self.clock.set_values(valores)
            self.stats["ediciones_manuales"] += 1
            return self._record("EDICION_MANUAL", motivo, antes, despues)

    def send_message(self, destino: str, payload: str) -> dict:
        if destino not in self.peers or destino == self.node_id:
            raise ValueError(f"Destino inválido: {destino}")
        message_id = str(uuid.uuid4())
        with self.lock:
            antes = self.clock.copy()
            despues = self.clock.increment()
            self.stats["mensajes_enviados"] += 1
            mensaje = {
                "message_id": message_id,
                "origen": self.node_id,
                "destino": destino,
                "payload": payload,
                "reloj": despues,
                "ack_url": self.peers[self.node_id].rstrip("/") + "/ack",
            }
            self.pending_acks[message_id] = {
                "message_id": message_id,
                "destino": destino,
                "payload": payload,
                "reloj_envio": despues,
                "confirmado": False,
            }
            self._record(
                "ENVIO",
                f"{self.node_id} envía a {destino}: {payload}",
                antes,
                despues,
                extra={"message_id": message_id, "destino": destino},
            )
        url = self.peers[destino].rstrip("/") + "/receive"
        try:
            respuesta = requests.post(url, json=mensaje, timeout=5)
            respuesta.raise_for_status()
            cuerpo = respuesta.json()
        except requests.RequestException as exc:
            with self.lock:
                return {
                    "ok": False,
                    "error": f"No se obtuvo ACK de {destino}: {exc}",
                    "message_id": message_id,
                    "pendiente": True,
                    "estadisticas": dict(self.stats),
                }
        ack = cuerpo.get("ack", {})
        confirmado = bool(cuerpo.get("ok")) and bool(ack.get("recibido"))
        if confirmado:
            self._apply_ack(ack, via="respuesta_http")
        with self.lock:
            return {
                "ok": confirmado,
                "message_id": message_id,
                "reloj_local": self.clock.copy(),
                "ack": ack,
                "estadisticas": dict(self.stats),
            }

    def receive_message(self, body: dict) -> dict:
        origen = body.get("origen")
        payload = body.get("payload", "")
        reloj_remoto = body.get("reloj") or {}
        message_id = body.get("message_id") or str(uuid.uuid4())
        ack_url = body.get("ack_url")
        if not isinstance(reloj_remoto, dict):
            raise ValueError("'reloj' debe ser un objeto JSON")
        with self.lock:
            if message_id in self.received:
                self.stats["mensajes_duplicados"] += 1
                return {"ok": True, "duplicado": True, "ack": self.received[message_id]}
            antes = self.clock.copy()
            despues = self.clock.on_receive(reloj_remoto)
            self.stats["mensajes_recibidos"] += 1
            self._record(
                "RECEPCION",
                f"{self.node_id} recibe de {origen}: {payload}",
                antes,
                despues,
                extra={"message_id": message_id, "origen": origen, "reloj_mensaje": reloj_remoto},
            )
            ack = {
                "recibido": True,
                "message_id": message_id,
                "origen_ack": self.node_id,
                "destino_ack": origen,
                "reloj_receptor": despues,
                "mensajes_recibidos": self.stats["mensajes_recibidos"],
            }
            self.received[message_id] = ack
            self.stats["acks_enviados"] += 1
            self._record(
                "ACK_ENVIADO",
                f"{self.node_id} confirma recepción {message_id} a {origen}",
                despues,
                despues,
                extra={"message_id": message_id, "origen": origen},
            )
        if ack_url:
            threading.Thread(target=self._deliver_ack, args=(ack_url, ack), daemon=True).start()
        return {"ok": True, "ack": ack}

    def _deliver_ack(self, ack_url: str, ack: dict) -> None:
        try:
            requests.post(ack_url, json=ack, timeout=5)
        except requests.RequestException as exc:
            logger.warning("No se pudo entregar ACK asíncrono: %s", exc)

    def _apply_ack(self, ack: dict, via: str) -> dict:
        message_id = ack.get("message_id")
        with self.lock:
            pendiente = self.pending_acks.get(message_id)
            if pendiente is None or ack.get("origen_ack") != pendiente["destino"]:
                self.stats["acks_ignorados"] += 1
                logger.warning("ACK ignorado (mensaje desconocido o emisor incorrecto): %s", ack)
                return {"ignorado": True, "message_id": message_id}
            if pendiente.get("confirmado"):
                return pendiente
            self.stats["acks_recibidos"] += 1
            self.stats["recepciones_confirmadas"] += 1
            pendiente["confirmado"] = True
            pendiente["via"] = via
            pendiente["reloj_receptor"] = ack.get("reloj_receptor")
            antes = self.clock.copy()
            return self._record(
                "ACK_RECIBIDO",
                f"Recepción confirmada por {ack.get('origen_ack')} ({via})",
                antes,
                antes,
                extra={"message_id": message_id, "ack": ack},
            )

    def receive_ack(self, ack: dict) -> dict:
        entrada = self._apply_ack(ack, via="callback")
        return {"ok": True, "evento": entrada, "estadisticas": dict(self.stats)}


nodo = NodoA()
app = Flask(__name__)


@app.get("/")
@app.get("/state")
def state():
    return jsonify(nodo.snapshot())


@app.get("/clock")
def get_clock():
    with nodo.lock:
        return jsonify({"nodo": nodo.node_id, "reloj": nodo.clock.copy()})


@app.route("/clock", methods=["PUT", "PATCH"])
def edit_clock():
    data = request.get_json(silent=True) or {}
    valores = data.get("reloj")
    if not isinstance(valores, dict) or not valores:
        return jsonify({"ok": False, "error": "Cuerpo esperado: {\"reloj\": {\"A\": 3, ...}}"}), 400
    try:
        entrada = nodo.edit_clock(valores, data.get("motivo", "edición manual"))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify({"ok": True, "evento": entrada, "reloj": entrada["reloj_despues"]})


@app.post("/event")
def event():
    data = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "evento": nodo.local_event(data.get("descripcion", "evento local en A"))})


@app.post("/send")
def send():
    data = request.get_json(silent=True) or {}
    destino = data.get("destino")
    if not destino:
        return jsonify({"ok": False, "error": "Falta 'destino'"}), 400
    try:
        resultado = nodo.send_message(destino, data.get("payload", ""))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(resultado), (200 if resultado.get("ok") else 502)


@app.post("/receive")
def receive():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "JSON requerido"}), 400
    try:
        return jsonify(nodo.receive_message(data))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.post("/ack")
def ack():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False, "error": "JSON requerido"}), 400
    return jsonify(nodo.receive_ack(data))


if __name__ == "__main__":
    logger.info("Nodo A (nodo_a.py) escuchando en puerto %s", PUERTO)
    app.run(host="127.0.0.1", port=PUERTO, debug=False, use_reloader=False)
