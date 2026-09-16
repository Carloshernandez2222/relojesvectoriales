| # | Nodo | Tipo | Reloj antes | Reloj después | Detalle |
|---|------|------|-------------|---------------|---------|
| 1 | A | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:1, B:0, C:0]` | A inicia cálculo local |
| 2 | B | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:0, B:1, C:0]` | B inicia cálculo local |
| 3 | A | ENVIO | `[A:1, B:0, C:0]` | `[A:2, B:0, C:0]` | A envía a B: resultado parcial de A |
| 4 | B | RECEPCION | `[A:0, B:1, C:0]` | `[A:2, B:2, C:0]` | B recibe de A: resultado parcial de A |
| 5 | B | ACK_ENVIADO | `[A:2, B:2, C:0]` | `[A:2, B:2, C:0]` | B confirma recepción b1987cca-1bb9-42e3-8c1d-504a160edfbd a A |
| 6 | A | ACK_RECIBIDO | `[A:2, B:0, C:0]` | `[A:2, B:0, C:0]` | Recepción confirmada por B (respuesta_http) |
| 7 | C | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:0, B:0, C:1]` | C trabaja en paralelo |
| 8 | B | ENVIO | `[A:2, B:2, C:0]` | `[A:2, B:3, C:0]` | B envía a C: B reenvía lo de A más lo propio |
| 9 | C | RECEPCION | `[A:0, B:0, C:1]` | `[A:2, B:3, C:2]` | C recibe de B: B reenvía lo de A más lo propio |
| 10 | C | ACK_ENVIADO | `[A:2, B:3, C:2]` | `[A:2, B:3, C:2]` | C confirma recepción e0484e85-c3da-427e-9ace-9caad33942aa a B |
| 11 | B | ACK_RECIBIDO | `[A:2, B:3, C:0]` | `[A:2, B:3, C:0]` | Recepción confirmada por C (respuesta_http) |
| 12 | C | ENVIO | `[A:2, B:3, C:2]` | `[A:2, B:3, C:3]` | C envía a A: C responde a A |
| 13 | A | RECEPCION | `[A:2, B:0, C:0]` | `[A:3, B:3, C:3]` | A recibe de C: C responde a A |
| 14 | A | ACK_ENVIADO | `[A:3, B:3, C:3]` | `[A:3, B:3, C:3]` | A confirma recepción 5db67ac1-f83e-4e21-bf11-eb8191e8c302 a C |
| 15 | C | ACK_RECIBIDO | `[A:2, B:3, C:3]` | `[A:2, B:3, C:3]` | Recepción confirmada por A (respuesta_http) |
| 16 | B | EVENTO_LOCAL | `[A:2, B:3, C:0]` | `[A:2, B:4, C:0]` | B hace otro trabajo local |
| 17 | A | ENVIO | `[A:3, B:3, C:3]` | `[A:4, B:3, C:3]` | A envía a C: A avisa a C |
| 18 | C | RECEPCION | `[A:2, B:3, C:3]` | `[A:4, B:3, C:4]` | C recibe de A: A avisa a C |
| 19 | C | ACK_ENVIADO | `[A:4, B:3, C:4]` | `[A:4, B:3, C:4]` | C confirma recepción 2e1aaa7d-c879-4aa0-bbeb-4d69cd425a68 a A |
| 20 | A | ACK_RECIBIDO | `[A:4, B:3, C:3]` | `[A:4, B:3, C:3]` | Recepción confirmada por C (respuesta_http) |
