| # | Nodo | Tipo | Reloj antes | Reloj después | Detalle | Explicación |
|---|------|------|-------------|---------------|---------|-------------|
| 1 | A | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:1, B:0, C:0]` | A inicia cálculo local | Evento local: A incrementa su posición (0 → 1) |
| 2 | B | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:0, B:1, C:0]` | B inicia cálculo local | Evento local: B incrementa su posición (0 → 1) |
| 3 | A | ENVIO | `[A:1, B:0, C:0]` | `[A:2, B:0, C:0]` | A envía a B: resultado parcial de A | Envío (cuenta como evento): A incrementa su posición (1 → 2) y manda [A:2, B:0, C:0] en el JSON a B |
| 4 | B | RECEPCION | `[A:0, B:1, C:0]` | `[A:2, B:2, C:0]` | B recibe de A: resultado parcial de A | max([A:0, B:1, C:0], [A:2, B:0, C:0]) = [A:2, B:1, C:0]; luego B +1 → [A:2, B:2, C:0] |
| 5 | B | ACK_ENVIADO | `[A:2, B:2, C:0]` | `[A:2, B:2, C:0]` | B confirma recepción 360955d7-2b45-40aa-b12e-3e92b7799c96 a A | Confirmación de recepción: el reloj no cambia |
| 6 | A | ACK_RECIBIDO | `[A:2, B:0, C:0]` | `[A:2, B:0, C:0]` | Recepción confirmada por B (respuesta_http) | Confirmación de recepción: el reloj no cambia |
| 7 | C | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:0, B:0, C:1]` | C trabaja en paralelo | Evento local: C incrementa su posición (0 → 1) |
| 8 | B | ENVIO | `[A:2, B:2, C:0]` | `[A:2, B:3, C:0]` | B envía a C: B reenvía lo de A más lo propio | Envío (cuenta como evento): B incrementa su posición (2 → 3) y manda [A:2, B:3, C:0] en el JSON a C |
| 9 | C | RECEPCION | `[A:0, B:0, C:1]` | `[A:2, B:3, C:2]` | C recibe de B: B reenvía lo de A más lo propio | max([A:0, B:0, C:1], [A:2, B:3, C:0]) = [A:2, B:3, C:1]; luego C +1 → [A:2, B:3, C:2] |
| 10 | C | ACK_ENVIADO | `[A:2, B:3, C:2]` | `[A:2, B:3, C:2]` | C confirma recepción b6985a76-a83c-4667-9f67-07251b29b48e a B | Confirmación de recepción: el reloj no cambia |
| 11 | B | ACK_RECIBIDO | `[A:2, B:3, C:0]` | `[A:2, B:3, C:0]` | Recepción confirmada por C (respuesta_http) | Confirmación de recepción: el reloj no cambia |
| 12 | C | ENVIO | `[A:2, B:3, C:2]` | `[A:2, B:3, C:3]` | C envía a A: C responde a A | Envío (cuenta como evento): C incrementa su posición (2 → 3) y manda [A:2, B:3, C:3] en el JSON a A |
| 13 | A | RECEPCION | `[A:2, B:0, C:0]` | `[A:3, B:3, C:3]` | A recibe de C: C responde a A | max([A:2, B:0, C:0], [A:2, B:3, C:3]) = [A:2, B:3, C:3]; luego A +1 → [A:3, B:3, C:3] |
| 14 | A | ACK_ENVIADO | `[A:3, B:3, C:3]` | `[A:3, B:3, C:3]` | A confirma recepción 7d47d41f-ff48-4506-99f4-e418da2dd07b a C | Confirmación de recepción: el reloj no cambia |
| 15 | C | ACK_RECIBIDO | `[A:2, B:3, C:3]` | `[A:2, B:3, C:3]` | Recepción confirmada por A (respuesta_http) | Confirmación de recepción: el reloj no cambia |
| 16 | B | EVENTO_LOCAL | `[A:2, B:3, C:0]` | `[A:2, B:4, C:0]` | B hace otro trabajo local | Evento local: B incrementa su posición (3 → 4) |
| 17 | A | ENVIO | `[A:3, B:3, C:3]` | `[A:4, B:3, C:3]` | A envía a C: A avisa a C | Envío (cuenta como evento): A incrementa su posición (3 → 4) y manda [A:4, B:3, C:3] en el JSON a C |
| 18 | C | RECEPCION | `[A:2, B:3, C:3]` | `[A:4, B:3, C:4]` | C recibe de A: A avisa a C | max([A:2, B:3, C:3], [A:4, B:3, C:3]) = [A:4, B:3, C:3]; luego C +1 → [A:4, B:3, C:4] |
| 19 | C | ACK_ENVIADO | `[A:4, B:3, C:4]` | `[A:4, B:3, C:4]` | C confirma recepción 7f1e0237-6ae2-4d2d-a7b7-9fe8cb9aed6a a A | Confirmación de recepción: el reloj no cambia |
| 20 | A | ACK_RECIBIDO | `[A:4, B:3, C:3]` | `[A:4, B:3, C:3]` | Recepción confirmada por C (respuesta_http) | Confirmación de recepción: el reloj no cambia |
