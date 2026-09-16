| # | Nodo | Tipo | Reloj antes | Reloj después | Detalle |
|---|------|------|-------------|---------------|---------|
| 1 | A | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:1, B:0, C:0]` | A inicia cálculo local |
| 2 | B | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:0, B:1, C:0]` | B inicia cálculo local |
| 3 | A | ENVIO | `[A:1, B:0, C:0]` | `[A:2, B:0, C:0]` | A envía a B: resultado parcial de A |
| 4 | B | RECEPCION | `[A:0, B:1, C:0]` | `[A:2, B:2, C:0]` | B recibe de A: resultado parcial de A |
| 5 | B | ACK_ENVIADO | `[A:2, B:2, C:0]` | `[A:2, B:2, C:0]` | B confirma recepción e845aad4-2c89-482a-87bd-e7c25843c950 a A |
| 6 | A | ACK_RECIBIDO | `[A:2, B:0, C:0]` | `[A:2, B:0, C:0]` | Recepción confirmada por B (respuesta_http) |
| 7 | C | EVENTO_LOCAL | `[A:0, B:0, C:0]` | `[A:0, B:0, C:1]` | C trabaja en paralelo |
| 8 | B | ENVIO | `[A:2, B:2, C:0]` | `[A:2, B:3, C:0]` | B envía a C: B reenvía lo de A más lo propio |
| 9 | C | RECEPCION | `[A:0, B:0, C:1]` | `[A:2, B:3, C:2]` | C recibe de B: B reenvía lo de A más lo propio |
| 10 | C | ACK_ENVIADO | `[A:2, B:3, C:2]` | `[A:2, B:3, C:2]` | C confirma recepción 8c901b10-3290-4b31-ace3-2cf6fb5b3fc7 a B |
| 11 | B | ACK_RECIBIDO | `[A:2, B:3, C:0]` | `[A:2, B:3, C:0]` | Recepción confirmada por C (respuesta_http) |
| 12 | C | ENVIO | `[A:2, B:3, C:2]` | `[A:2, B:3, C:3]` | C envía a A: C responde a A |
| 13 | A | RECEPCION | `[A:2, B:0, C:0]` | `[A:3, B:3, C:3]` | A recibe de C: C responde a A |
| 14 | A | ACK_ENVIADO | `[A:3, B:3, C:3]` | `[A:3, B:3, C:3]` | A confirma recepción 2173e657-692c-434f-b93d-b13f9cd02300 a C |
| 15 | C | ACK_RECIBIDO | `[A:2, B:3, C:3]` | `[A:2, B:3, C:3]` | Recepción confirmada por A (respuesta_http) |
| 16 | B | EVENTO_LOCAL | `[A:2, B:3, C:0]` | `[A:2, B:4, C:0]` | B hace otro trabajo local |
| 17 | A | ENVIO | `[A:3, B:3, C:3]` | `[A:4, B:3, C:3]` | A envía a C: A avisa a C |
| 18 | C | RECEPCION | `[A:2, B:3, C:3]` | `[A:4, B:3, C:4]` | C recibe de A: A avisa a C |
| 19 | C | ACK_ENVIADO | `[A:4, B:3, C:4]` | `[A:4, B:3, C:4]` | C confirma recepción 6f22fcc1-9e53-4924-956d-a85a8cd7b578 a A |
| 20 | A | ACK_RECIBIDO | `[A:4, B:3, C:3]` | `[A:4, B:3, C:3]` | Recepción confirmada por C (respuesta_http) |
