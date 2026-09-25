# Simulación de relojes vectoriales

Sistema distribuido de **mínimo tres nodos independientes**. Cada nodo mantiene un reloj vectorial y expone una API REST en HTTP/JSON para consultar estado, generar eventos locales, enviar mensajes, recibir mensajes y confirmar recepciones con **ACK**.

## Cómo ejecutar

```bash
python -m pip install -r requirements.txt
python test_vector_clock.py
python simulate.py
```

Para arrancar con vectores elegidos por ti (JSON en línea o ruta a un `.json`; las posiciones que no pongas quedan en 0):

```bash
python simulate.py --relojes '{"A": {"A": 3, "B": 0, "C": 1}, "C": {"C": 5}}'
```

`simulate.py` arranca **tres archivos independientes**: `nodo_a.py`, `nodo_b.py` y `nodo_c.py` (puertos 5001, 5002 y 5003), ejecuta un escenario de eventos y comunicaciones, imprime la tabla de relojes y guarda evidencia en `logs/`.

Para levantar cada nodo a mano (una terminal por archivo):

```bash
python nodo_a.py
python nodo_b.py
python nodo_c.py
```

## API REST (JSON)

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/state` | Reloj actual, estadísticas y historial |
| GET | `/clock` | Solo el vector actual |
| PUT / PATCH | `/clock` | Editar el vector a mano. Cuerpo: `{"reloj": {"A": 5, "C": 2}}` |
| POST | `/event` | Evento local. Cuerpo: `{"descripcion": "..."}` |
| POST | `/send` | Envío a otro nodo. Cuerpo: `{"destino": "B", "payload": "..."}` |
| POST | `/receive` | Recepción de un mensaje (lo usan los otros nodos) |
| POST | `/ack` | Confirmación de recepción (callback del receptor) |

Ejemplo de envío:

```bash
curl -X POST http://127.0.0.1:5001/send -H "Content-Type: application/json" -d "{\"destino\":\"B\",\"payload\":\"hola\"}"
```

Ejemplo de edición del vector de B (solo cambia las posiciones indicadas):

```bash
curl -X PUT http://127.0.0.1:5002/clock -H "Content-Type: application/json" -d "{\"reloj\":{\"A\":4,\"B\":7}}"
```

Solo se aceptan nodos conocidos (`A`, `B`, `C`) y enteros `>= 0`; si no, responde `400`. Cada edición queda en el historial como `EDICION_MANUAL` con el reloj antes y después.

## Reloj vectorial

- **Evento local** y **envío**: se incrementa solo la posición propia.
- **Recepción**: `max()` componente a componente con el reloj del mensaje y después se incrementa la posición propia.

## ACK y conteo de recepciones

Un envío no cuenta como recepción confirmada solo por haber llamado a `/send`. El receptor:

1. Actualiza su reloj.
2. Incrementa `mensajes_recibidos`.
3. Devuelve un **ACK** en la respuesta HTTP de `/receive`.
4. Además envía un callback POST a `/ack` del emisor.

El emisor incrementa `acks_recibidos` y `recepciones_confirmadas` **solo cuando llega el ACK**. Si el HTTP falla, el mensaje queda pendiente y no se cuenta la recepción.

Como el ACK llega por dos vías (respuesta HTTP y callback), el emisor lo cuenta **una sola vez** por `message_id`. Un ACK de un mensaje que el nodo no envió, o que viene de un nodo distinto al destino, se descarta y se suma a `acks_ignorados`. Si el receptor recibe dos veces el mismo `message_id`, no vuelve a tocar su reloj: reenvía el mismo ACK y suma `mensajes_duplicados`.

## Causalidad

Un evento **e sucede-antes que f** si el reloj de e es ≤ componente a componente y estrictamente menor en al menos una posición. Si no hay relación en ningún sentido, los eventos son **concurrentes**.

## Evidencia generada (`logs/`)

- `tabla_relojes.md` / `evolucion_relojes.csv`: reloj antes y después de cada evento, con una columna que explica la regla aplicada (por ejemplo `max([A:0, B:1, C:0], [A:2, B:0, C:0]) = [A:2, B:1, C:0]; luego B +1`).
- `causalidad.txt`: resumen con el número de pares causales y concurrentes, la lista de pares concurrentes y todas las comparaciones.
- `ejecucion.txt`: la salida completa de consola de la última ejecución.
- `estados.json`: estado final de cada nodo (reloj, estadísticas, ACK e historial).

## Archivos

- `nodo_a.py`: nodo A independiente (puerto 5001).
- `nodo_b.py`: nodo B independiente (puerto 5002).
- `nodo_c.py`: nodo C independiente (puerto 5003).
- `vector_clock.py`: reglas del reloj y comparación de eventos.
- `simulate.py`: escenario de prueba que arranca los tres archivos.
- `test_vector_clock.py`: pruebas de incremento, `max()` y concurrencia.
