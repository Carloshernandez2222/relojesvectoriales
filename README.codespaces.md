# Cómo correrlo en GitHub Codespaces

Esta guía es solo para Codespaces. El manual completo del proyecto está en [README.md](README.md).

## 1. Abrir el Codespace

1. Entra al repositorio en GitHub.
2. Pulsa **Code** → **Codespaces** → **Create codespace on main** (o en `master` si esa es la rama principal).
3. Espera a que termine de crear el entorno. El archivo `.devcontainer/devcontainer.json` instala solo las dependencias de `requirements.txt`.

## 2. Comprobar Python

En la terminal del Codespace:

```bash
python3 --version
python3 -m pip install -r requirements.txt
```

## 3. Ejecutar la simulación completa

Esto levanta los nodos A, B y C, genera eventos, imprime la tabla de relojes y apaga los procesos al terminar:

```bash
python3 test_vector_clock.py
python3 simulate.py
```

La evidencia queda en `logs/`.

## 4. Dejar los tres nodos corriendo (para probar la API a mano)

Abre **tres terminales** en el Codespace.

Terminal 1:

```bash
python3 nodo.py --id A --port 5001 --peers A=http://127.0.0.1:5001,B=http://127.0.0.1:5002,C=http://127.0.0.1:5003
```

Terminal 2:

```bash
python3 nodo.py --id B --port 5002 --peers A=http://127.0.0.1:5001,B=http://127.0.0.1:5002,C=http://127.0.0.1:5003
```

Terminal 3:

```bash
python3 nodo.py --id C --port 5003 --peers A=http://127.0.0.1:5001,B=http://127.0.0.1:5002,C=http://127.0.0.1:5003
```

Codespaces reenvía los puertos 5001, 5002 y 5003. Para pruebas **entre nodos** usa siempre `127.0.0.1` (comunicación interna del contenedor).

## 5. Probar endpoints

En una cuarta terminal:

```bash
curl -s http://127.0.0.1:5001/state

curl -s -X POST http://127.0.0.1:5001/event \
  -H "Content-Type: application/json" \
  -d '{"descripcion":"evento local en A"}'

curl -s -X POST http://127.0.0.1:5001/send \
  -H "Content-Type: application/json" \
  -d '{"destino":"B","payload":"hola desde A"}'

curl -s http://127.0.0.1:5002/state
```

En el JSON del emisor revisa `recepciones_confirmadas` y `acks_recibidos`. En el receptor revisa `mensajes_recibidos`. Sin ACK no se cuenta la recepción confirmada.

## 6. Si un puerto ya está ocupado

```bash
pkill -f nodo.py || true
```

Luego vuelve a lanzar los tres nodos.

## 7. Qué no hace falta

- No necesitas Docker extra: el Codespace ya es el entorno.
- No cambies las URLs a `localhost` público de GitHub para que un nodo hable con otro; entre ellos debe ser `127.0.0.1`.
- `simulate.py` no deja los servidores encendidos. Si quieres inspeccionar con `curl`, usa el paso 4.
