"""Nodo independiente con reloj vectorial y API REST.

Cada proceso de este módulo es un nodo del sistema distribuido. Expone
endpoints HTTP/JSON para consultar estado, generar eventos locales,
enviar mensajes, recibir mensajes y confirmar recepciones (ACK).

El conteo de recepciones solo se considera confirmado cuando llega el ACK.
"""

from __future__ import annotations

import argparse
import logging
import threading
import uuid
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, request

from vector_clock import VectorClock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("nodo")


class DistributedNode:
    """Estado y reglas de un nodo del sistema distribuido."""

    def __init__(self, node_id: str, peers: dict[str, str]) -> None:
        self.node_id = node_id
        self.peers = peers
        self.clock = VectorClock(list(peers.keys()), node_id)
        self.lock = threading.Lock()
        self.history: list[dict] = []
        self.pending_acks: dict[str, dict] = {}
        self.stats = {
            "eventos_locales": 0,
            "mensajes_enviados": 0,
            "mensajes_recibidos": 0,
            "acks_enviados": 0,
            "acks_recibidos": 0,
            "recepciones_confirmadas": 0,
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

        with self.lock:
            antes = self.clock.copy()
            despues = self.clock.on_receive(reloj_remoto)
            self.stats["mensajes_recibidos"] += 1
            self._record(
                "RECEPCION",
                f"{self.node_id} recibe de {origen}: {payload}",
                antes,
                despues,
                extra={"message_id": message_id, "origen": origen},
            )
            ack = {
                "recibido": True,
                "message_id": message_id,
                "origen_ack": self.node_id,
                "destino_ack": origen,
                "reloj_receptor": despues,
                "mensajes_recibidos": self.stats["mensajes_recibidos"],
            }
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
            if pendiente and pendiente.get("confirmado"):
                return pendiente
            self.stats["acks_recibidos"] += 1
            self.stats["recepciones_confirmadas"] += 1
            if pendiente:
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


def create_app(node: DistributedNode) -> Flask:
    app = Flask(__name__)

    @app.get("/")
    @app.get("/state")
    def state():
        return jsonify(node.snapshot())

    @app.post("/event")
    def event():
        data = request.get_json(silent=True) or {}
        descripcion = data.get("descripcion", "evento local")
        return jsonify({"ok": True, "evento": node.local_event(descripcion)})

    @app.post("/send")
    def send():
        data = request.get_json(silent=True) or {}
        destino = data.get("destino")
        payload = data.get("payload", "")
        if not destino:
            return jsonify({"ok": False, "error": "Falta 'destino'"}), 400
        try:
            resultado = node.send_message(destino, payload)
        except ValueError as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400
        codigo = 200 if resultado.get("ok") else 502
        return jsonify(resultado), codigo

    @app.post("/receive")
    def receive():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": False, "error": "JSON requerido"}), 400
        return jsonify(node.receive_message(data))

    @app.post("/ack")
    def ack():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"ok": False, "error": "JSON requerido"}), 400
        return jsonify(node.receive_ack(data))

    return app


def parse_peers(raw: str) -> dict[str, str]:
    pares = {}
    for item in raw.split(","):
        nombre, url = item.split("=", 1)
        pares[nombre.strip()] = url.strip()
    return pares


def main() -> None:
    parser = argparse.ArgumentParser(description="Nodo con reloj vectorial")
    parser.add_argument("--id", required=True, help="Identificador del nodo, por ejemplo A")
    parser.add_argument("--port", required=True, type=int, help="Puerto HTTP del nodo")
    parser.add_argument(
        "--peers",
        required=True,
        help="Pares id=url separados por coma. Ejemplo: A=http://127.0.0.1:5001,B=http://127.0.0.1:5002",
    )
    args = parser.parse_args()
    peers = parse_peers(args.peers)
    if args.id not in peers:
        raise SystemExit("El --id debe aparecer también en --peers")

    node = DistributedNode(args.id, peers)
    app = create_app(node)
    logger.info("Nodo %s escuchando en puerto %s", args.id, args.port)
    app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
