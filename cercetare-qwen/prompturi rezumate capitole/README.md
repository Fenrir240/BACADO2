# Prompturi și GRAPH_PACKET-uri pentru rezumatele capitolelor

Directorul conține câte trei fișiere pentru fiecare dintre cele 13 capitole:

- `.prompt.md` — prompt reutilizabil, cu placeholderul `{{GRAPH_PACKET}}`;
- `.graph-packet.json` — subgraful compact al capitolului;
- `.qwen.txt` — promptul și packetul deja combinate, gata de trimis modelului.

Fișierele `.qwen.txt` sunt varianta recomandată pentru rulare.

Estimările folosesc raportul empiric de aproximativ 3,142 caractere/token observat pentru Qwen 3.5 Flash în Experimentul 2.

| Capitol | Evenimente sursă | Verificate | Excluse | Tokenuri GRAPH_PACKET | Tokenuri fișier Qwen |
|---|---:|---:|---:|---:|---:|
| Capitolul I - Începutul | 10 | 10 | 0 | 2,754 | 3,488 |
| Capitolul II - Zvârcolirea | 12 | 11 | 1 | 2,751 | 3,487 |
| Capitolul III - Iubirea | 15 | 15 | 0 | 3,775 | 4,509 |
| Capitolul IV - Noaptea | 9 | 9 | 0 | 2,256 | 2,988 |
| Capitolul V - Rușinea | 9 | 9 | 0 | 2,711 | 3,443 |
| Capitolul VI - Nunta | 8 | 8 | 0 | 2,600 | 3,331 |
| Capitolul VII - Vasile | 8 | 8 | 0 | 2,311 | 3,044 |
| Capitolul VIII - Copilul | 9 | 9 | 0 | 2,467 | 3,200 |
| Capitolul IX - Sărutarea | 9 | 9 | 0 | 2,352 | 3,086 |
| Capitolul X - Ștreangul | 6 | 6 | 0 | 1,673 | 2,406 |
| Capitolul XI - Blestemul | 8 | 8 | 0 | 2,193 | 2,927 |
| Capitolul XII - George | 8 | 8 | 0 | 2,174 | 2,907 |
| Capitolul XIII - Sfârșitul | 13 | 13 | 0 | 3,391 | 4,126 |

Total estimat pentru toate cele 13 rulări: **42,942 tokenuri input**.

## Garanții ale packeturilor

- evenimentele sunt împărțite explicit în verificate și excluse;
- fiecare eveniment verificat are pagină PDF sau locator de sursă și citat din textul integral;
- modelul returnează numai event_ids; citatele nu sunt duplicate în output și sunt verificate local;
- packetul nu conține evenimente din capitole vecine, teme sau muchii inutile;
- evenimentele interpretative sau cu aliniere insuficientă sunt păstrate numai pentru audit și nu pot fi verbalizate.

## Regenerare

```powershell
python cercetare-qwen/build_chapter_summary_packets.py
```
