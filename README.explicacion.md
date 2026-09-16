# Cómo está hecho y qué hace

Este documento explica el diseño del proyecto, no los comandos de instalación. Para ejecutar en local usa [README.md](README.md). Para Codespaces usa [README.codespaces.md](README.codespaces.md).

## Qué problema resuelve

En un sistema distribuido no hay un reloj global confiable. Cada nodo tiene su propio orden de eventos. Un **reloj vectorial** sirve para responder dos preguntas:

1. ¿El evento X **causó** (sucedió-antes que) el evento Y?
2. ¿X e Y ocurrieron **en paralelo** (concurrentes), sin que uno dependiera del otro?

Esta simulación lo muestra con **tres procesos independientes** que se hablan por HTTP y JSON, como pide la práctica.

## Qué hace el sistema, en una frase

Tres nodos (A, B y C) mantienen cada uno un vector `[A, B, C]`. Cuando pasa algo, actualizan ese vector con reglas fijas. Al final se puede comparar esos vectores y decir qué eventos son causales y cuáles concurrentes. Las recepciones **solo se cuentan si llegó un ACK**.

## Piezas del código

| Archivo | Rol |
|---------|-----|
| `vector_clock.py` | El reloj: incrementar, `max()` al recibir, y comparar dos eventos. |
| `nodo.py` | Un proceso Flask: estado, evento local, envío, recepción y ACK. |
| `simulate.py` | Arranca A, B y C, dispara un escenario y escribe tablas/logs. |
| `test_vector_clock.py` | Comprueba las reglas del reloj sin red. |
| `logs/` | Evidencia de una corrida: tabla antes/después y causalidad. |

Cada nodo se lanza como proceso aparte (`python nodo.py --id A --port 5001 ...`). No comparten memoria: solo se enteran de los demás por HTTP.

## Cómo se construyó

1. **Reloj vectorial primero.** Un diccionario `{A:0, B:0, C:0}` por nodo. Evento local o envío: `vector[yo] += 1`. Recepción: para cada componente `vector[i] = max(local[i], remoto[i])` y después `vector[yo] += 1`.
2. **API REST encima.** Flask expone `/state`, `/event`, `/send`, `/receive` y `/ack`. El cuerpo es JSON.
3. **Envío real entre nodos.** `/send` en A hace `POST` a `/receive` de B con el payload y el reloj de A ya incrementado.
4. **ACK para poder contar recepciones.** El enunciado extra pedía acknowledge si se iban a contar recepciones. Por eso un `POST /send` no suma `recepciones_confirmadas` hasta que el destino responde `ack.recibido = true`. Hay dos caminos de ACK:
   - la respuesta HTTP de `/receive` (inmediata);
   - un callback `POST /ack` al emisor (por si se quiere ver el ACK como mensaje aparte).
   El segundo no vuelve a contar si el primero ya confirmó el mismo `message_id`.
5. **Simulación y evidencia.** `simulate.py` levanta los tres servidores, genera eventos locales y mensajes A→B, B→C, C→A, A→C, imprime la tabla reloj-antes / reloj-después y clasifica pares de eventos.

## Qué hace cada endpoint

- `GET /state`: reloj actual, estadísticas (locales, enviados, recibidos, acks, recepciones confirmadas) e historial.
- `POST /event`: simula trabajo interno. Solo sube la posición propia.
- `POST /send`: incrementa el reloj, marca el mensaje como pendiente de ACK y llama a `/receive` del destino.
- `POST /receive`: aplica `max()` + incremento, suma `mensajes_recibidos` y arma el ACK.
- `POST /ack`: el emisor marca el `message_id` como confirmado y suma `recepciones_confirmadas`.

El ACK **no vuelve a cambiar el reloj**. Solo sirve para confirmar entrega y poder contar. Si el HTTP de envío falla, el mensaje queda en `pendientes_ack` y no se cuenta.

## Cómo se leen los relojes (para la revisión)

Sean dos eventos e y f, con los vectores **después** de ocurrir:

- **e sucede-antes que f** si todas las posiciones de e son ≤ las de f y al menos una es estrictamente menor.
- **Concurrentes** si no se cumple en ningún sentido (ni e antes que f, ni f antes que e).

Ejemplo de la simulación:

- Evento local de A `[A:1, B:0, C:0]` y evento local de B `[A:0, B:1, C:0]` son **concurrentes**: ninguno “sabe” del otro.
- El envío de A a B `[A:2, B:0, C:0]` **sucede-antes** que la recepción en B `[A:2, B:2, C:0]`: B fusionó el reloj de A y luego incrementó el suyo.
- El trabajo local tardío de B `[A:2, B:4, C:0]` es **concurrente** con el último envío de A `[A:4, B:3, C:3]`: cada uno avanzó componentes que el otro no tiene.

La cadena A envía a B, B envía a C, C responde a A es **causal**: el reloj va arrastrando el conocimiento de los anteriores.

## Conteos que deben cuadrar en una corrida buena

En el escenario de `simulate.py`:

- A envía 2 mensajes y confirma 2 recepciones (ACKs de B y de C).
- B envía 1 y confirma 1 (ACK de C).
- C envía 1 y confirma 1 (ACK de A).
- En el lado receptor: B recibió 1, C recibió 2, A recibió 1.

Si `mensajes_enviados` del origen no coincide con `recepciones_confirmadas` de ese mismo origen, algún ACK no llegó.

## Qué no es este proyecto

No es un cluster real ni usa gRPC, colas ni base de datos. Es una simulación didáctica: procesos locales, HTTP y las reglas clásicas de Lamport/Fidge-Mattern para relojes vectoriales, más ACK para no contar recepciones a ciegas.
