# Pachete Qwen pentru elementele compoziționale

Fiecare element are un prompt, un GRAPH_PACKET compact și un fișier `.qwen.txt` gata de trimis.

Interpretările solicitate de cercetător care nu sunt complet explicite în graful 2 sunt păstrate separat în `researcher_brief`. Qwen trebuie să le citeze prin `brief_id`, fără să le prezinte drept muchii canonice.

| # | Element | Noduri | Muchii | Tokenuri packet | Tokenuri prompt + packet |
|---:|---|---:|---:|---:|---:|
| 1 | Titlul | 60 | 197 | 18,744 | 19,804 |
| 2 | Relația incipit–final | 43 | 126 | 12,814 | 13,901 |
| 3 | Conflictul | 90 | 470 | 39,842 | 40,936 |

Total estimat pentru cele trei apeluri: **74,641 tokenuri input**.

Estimarea folosește raportul empiric de aproximativ 3,142 caractere/token pentru Qwen 3.5 Flash.

## Fișiere

- `.prompt.md` — prompt reutilizabil cu `{{GRAPH_PACKET}}`;
- `.graph-packet.json` — subgraful și brief-ul cercetătorului;
- `.qwen.txt` — promptul și packetul deja combinate.

## Regenerare

```powershell
python cercetare-qwen/build_composition_packets.py
```
