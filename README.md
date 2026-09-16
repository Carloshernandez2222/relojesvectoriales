# Simulación de relojes vectoriales

Sistema distribuido de **mínimo tres nodos independientes**. Cada nodo mantiene un reloj vectorial y expone una API REST en HTTP/JSON para consultar estado, generar eventos locales, enviar mensajes, recibir mensajes y confirmar recepciones con **ACK**.

Otros documentos:

- [README.codespaces.md](README.codespaces.md): cómo abrirlo y ejecutarlo en GitHub Codespaces.
- [README.explicacion.md](README.explicacion.md): cómo está construido y qué hace cada parte.

## Cómo ejecutar

```bash
python -m pip install -r requirements.txt
python test_vector_clock.py
python simulate.py
```

`simulate.py` arranca los nodos A, B y C (puertos 5001, 5002 y 5003), ejecuta un escenario de eventos y comunicaciones, imprime la tabla de relojes y guarda evidencia en `logs/`.

Para levantar un nodo a mano:

```bash
python nodo.py --id A --port 5001 --peers A=http://127.0.0.1:5001,B=http://127.0.0.1:5002,C=http://127.0.0.1:5003
```

## API REST (JSON)

| Método | Ruta | Uso |
|--------|------|-----|
| GET | `/state` | Reloj actual, estadísticas y historial |
| POST | `/event` | Evento local. Cuerpo: `{"descripcion": "..."}` |
| POST | `/send` | Envío a otro nodo. Cuerpo: `{"destino": "B", "payload": "..."}` |
| POST | `/receive` | Recepción de un mensaje (lo usan los otros nodos) |
| POST | `/ack` | Confirmación de recepción (callback del receptor) |

Ejemplo de envío:

```bash
curl -X POST http://127.0.0.1:5001/send -H "Content-Type: application/json" -d "{\"destino\":\"B\",\"payload\":\"hola\"}"
```

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

## Causalidad

Un evento **e sucede-antes que f** si el reloj de e es ≤ componente a componente y estrictamente menor en al menos una posición. Si no hay relación en ningún sentido, los eventos son **concurrentes**.

La simulación deja esa clasificación en `logs/causalidad.txt` y la tabla antes/después en `logs/tabla_relojes.md`.

## Archivos

- `vector_clock.py`: reglas del reloj y comparación de eventos.
- `nodo.py`: proceso independiente + API REST.
- `simulate.py`: escenario de prueba con tres nodos.
- `test_vector_clock.py`: pruebas de incremento, `max()` y concurrencia.
