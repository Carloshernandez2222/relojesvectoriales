"""Simulación de tres nodos independientes con relojes vectoriales.

Levanta los nodos A, B y C, genera eventos locales y mensajes HTTP/JSON,
registra la evolución de los relojes y clasifica causalidad vs concurrencia.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import time
from pathlib import Path

import requests

from vector_clock import VectorClock

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"

PEERS = {
    "A": "http://127.0.0.1:5001",
    "B": "http://127.0.0.1:5002",
    "C": "http://127.0.0.1:5003",
}


def wait_ready(timeout: float = 15.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if all(requests.get(url + "/state", timeout=1).ok for url in PEERS.values()):
                return
        except requests.RequestException:
            time.sleep(0.3)
    raise RuntimeError("Los nodos no arrancaron a tiempo")


def post(nodo: str, ruta: str, cuerpo: dict) -> dict:
    respuesta = requests.post(PEERS[nodo] + ruta, json=cuerpo, timeout=8)
    try:
        data = respuesta.json()
    except ValueError:
        data = {"ok": False, "error": respuesta.text}
    if not respuesta.ok:
        raise RuntimeError(f"{nodo}{ruta} falló ({respuesta.status_code}): {data}")
    return data


def get_state(nodo: str) -> dict:
    return requests.get(PEERS[nodo] + "/state", timeout=5).json()


def start_nodes() -> list[subprocess.Popen]:
    archivos = ["nodo_a.py", "nodo_b.py", "nodo_c.py"]
    procesos = []
    for archivo in archivos:
        proc = subprocess.Popen([sys.executable, str(ROOT / archivo)], cwd=str(ROOT))
        procesos.append(proc)
    return procesos


def collect_history() -> list[dict]:
    eventos = []
    for nodo in PEERS:
        eventos.extend(get_state(nodo)["historial"])
    eventos.sort(key=lambda e: e["marca_tiempo"])
    return eventos


def relevant_events(historial: list[dict]) -> list[dict]:
    tipos = {"EVENTO_LOCAL", "ENVIO", "RECEPCION"}
    return [e for e in historial if e["tipo"] in tipos]


def write_table(historial: list[dict], csv_path: Path, md_path: Path) -> None:
    campos = ["nodo", "tipo", "detalle", "reloj_antes", "reloj_despues", "message_id"]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=campos)
        writer.writeheader()
        for evento in historial:
            writer.writerow(
                {
                    "nodo": evento["nodo"],
                    "tipo": evento["tipo"],
                    "detalle": evento["detalle"],
                    "reloj_antes": json.dumps(evento["reloj_antes"], ensure_ascii=False),
                    "reloj_despues": json.dumps(evento["reloj_despues"], ensure_ascii=False),
                    "message_id": evento.get("message_id", ""),
                }
            )

    lineas = [
        "| # | Nodo | Tipo | Reloj antes | Reloj después | Detalle |",
        "|---|------|------|-------------|---------------|---------|",
    ]
    for i, evento in enumerate(historial, start=1):
        lineas.append(
            f"| {i} | {evento['nodo']} | {evento['tipo']} | "
            f"`{format_clock(evento['reloj_antes'])}` | "
            f"`{format_clock(evento['reloj_despues'])}` | {evento['detalle']} |"
        )
    md_path.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def format_clock(clock: dict) -> str:
    return "[" + ", ".join(f"{k}:{clock[k]}" for k in sorted(clock)) + "]"


def print_table(historial: list[dict]) -> None:
    print("\n=== Evolución de relojes vectoriales ===")
    encabezado = f"{'#':<4}{'Nodo':<6}{'Tipo':<14}{'Antes':<22}{'Después':<22}Detalle"
    print(encabezado)
    print("-" * len(encabezado) + "-" * 24)
    for i, evento in enumerate(historial, start=1):
        print(
            f"{i:<4}{evento['nodo']:<6}{evento['tipo']:<14}"
            f"{format_clock(evento['reloj_antes']):<22}"
            f"{format_clock(evento['reloj_despues']):<22}"
            f"{evento['detalle']}"
        )


def analyze_causality(eventos: list[dict]) -> str:
    lineas = ["=== Relaciones de causalidad y concurrencia ===", ""]
    lineas.append("Cada evento de interés queda etiquetado con el reloj DESPUÉS de ocurrir.")
    lineas.append("e -> f si el reloj de e es menor o igual componente a componente y estrictamente")
    lineas.append("menor en al menos una posicion. Si no hay e -> f ni f -> e, son concurrentes.")
    lineas.append("")

    etiquetados = []
    for i, evento in enumerate(eventos, start=1):
        etiqueta = f"E{i}"
        etiquetados.append((etiqueta, evento))
        lineas.append(
            f"{etiqueta}  nodo={evento['nodo']}  tipo={evento['tipo']}  "
            f"VC={format_clock(evento['reloj_despues'])}  {evento['detalle']}"
        )

    lineas.append("")
    lineas.append("--- Comparaciones ---")
    for i, (a_id, a) in enumerate(etiquetados):
        for b_id, b in etiquetados[i + 1 :]:
            va, vb = a["reloj_despues"], b["reloj_despues"]
            if VectorClock.happens_before(va, vb):
                relacion = f"{a_id} -> {b_id}  (causal: {a_id} sucede-antes que {b_id})"
            elif VectorClock.happens_before(vb, va):
                relacion = f"{b_id} -> {a_id}  (causal: {b_id} sucede-antes que {a_id})"
            else:
                relacion = f"{a_id} || {b_id}  (concurrentes)"
            lineas.append(relacion)
    return "\n".join(lineas) + "\n"


def print_stats() -> None:
    print("\n=== Conteos (recepciones solo confirmadas con ACK) ===")
    for nodo in PEERS:
        stats = get_state(nodo)["estadisticas"]
        print(
            f"Nodo {nodo}: locales={stats['eventos_locales']} "
            f"enviados={stats['mensajes_enviados']} "
            f"recibidos={stats['mensajes_recibidos']} "
            f"acks_enviados={stats['acks_enviados']} "
            f"acks_recibidos={stats['acks_recibidos']} "
            f"recepciones_confirmadas={stats['recepciones_confirmadas']}"
        )


def run_scenario() -> None:
    """Secuencia pensada para mostrar causalidad y concurrencia."""
    post("A", "/event", {"descripcion": "A inicia cálculo local"})
    post("B", "/event", {"descripcion": "B inicia cálculo local"})
    post("A", "/send", {"destino": "B", "payload": "resultado parcial de A"})
    time.sleep(0.2)
    post("C", "/event", {"descripcion": "C trabaja en paralelo"})
    post("B", "/send", {"destino": "C", "payload": "B reenvía lo de A más lo propio"})
    time.sleep(0.2)
    post("C", "/send", {"destino": "A", "payload": "C responde a A"})
    time.sleep(0.2)
    post("B", "/event", {"descripcion": "B hace otro trabajo local"})
    post("A", "/send", {"destino": "C", "payload": "A avisa a C"})
    time.sleep(0.3)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    LOGS.mkdir(exist_ok=True)
    procesos = start_nodes()
    try:
        wait_ready()
        print("Nodos A, B y C en ejecución.")
        run_scenario()
        time.sleep(0.5)

        historial = collect_history()
        print_table(historial)
        print_stats()

        write_table(historial, LOGS / "evolucion_relojes.csv", LOGS / "tabla_relojes.md")

        analisis = analyze_causality(relevant_events(historial))
        print("\n" + analisis)
        (LOGS / "causalidad.txt").write_text(analisis, encoding="utf-8")

        estados = {nodo: get_state(nodo) for nodo in PEERS}
        (LOGS / "estados.json").write_text(
            json.dumps(estados, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Evidencia guardada en {LOGS}")
    finally:
        for proc in procesos:
            proc.terminate()
        for proc in procesos:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
