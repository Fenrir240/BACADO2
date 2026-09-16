# GRAPH_PACKET-uri compacte pentru Qwen

Fiecare fișier este derivat automat din `cercetare\graf2\knowledge-graph.json` și păstrează ID-urile canonice ale nodurilor și muchiilor. Fișierele sunt minificate intenționat pentru reducerea numărului de tokenuri.

Estimările folosesc raportul empiric de aproximativ 3,142 caractere/token observat pentru Qwen 3.5 Flash în Experimentul 2. Tokenizarea exactă depinde de model și provider.

| # | Categorie | Prompt | GRAPH_PACKET | Noduri | Muchii | Tokenuri packet | Tokenuri prompt + packet | Reducere față de graful complet |
|---:|---|---|---|---:|---:|---:|---:|---:|
| 1 | `SIMPLE_FACT_LOWHOP` | `../prompturi intrebari/01-intrebari-simple-lowhop.md` | `01-simple-facts.packet.json` | 13 | 12 | 3,956 | 5,250 | 98.2% |
| 2 | `CHARACTER_RELATION` | `../prompturi intrebari/02-relatii-dintre-personaje-lowhop.md` | `02-character-relations.packet.json` | 13 | 24 | 4,890 | 6,177 | 97.7% |
| 3 | `NARRATIVE_ACTION` | `../prompturi intrebari/03-actiune-narativa-lowhop.md` | `03-narrative-actions.packet.json` | 14 | 12 | 4,449 | 5,646 | 97.9% |
| 4 | `TEMPORAL_ORDER` | `../prompturi intrebari/04-ordine-narativa-midhop.md` | `04-temporal-order.packet.json` | 18 | 34 | 8,887 | 10,114 | 95.8% |
| 5 | `CAUSE_EFFECT` | `../prompturi intrebari/05-cauza-si-consecinta-midhop.md` | `05-cause-effect.packet.json` | 20 | 31 | 7,542 | 8,782 | 96.5% |
| 6 | `CHARACTER_EVOLUTION` | `../prompturi intrebari/06-evolutia-personajelor-highhop.md` | `06-character-evolution.packet.json` | 19 | 39 | 9,196 | 10,576 | 95.7% |
| 7 | `LITERARY_INTERPRETATION` | `../prompturi intrebari/07-teme-conflicte-si-simboluri-highhop.md` | `07-literary-concepts.packet.json` | 21 | 27 | 8,638 | 9,979 | 96.0% |
| 8 | `CROSS_CHAPTER_COMPARE` | `../prompturi intrebari/08-comparatii-intre-capitole-highhop.md` | `08-cross-chapter-comparison.packet.json` | 21 | 34 | 7,125 | 8,494 | 96.7% |

Total estimat pentru cele opt rulări separate: **65,018 tokenuri input**.

## Algoritmul determinist de selecție

Versiune: `question-packet-selection-v3-history`.

1. Sunt eligibile numai evenimentele `explicit_fact` cu `verification.status=verified_primary`.
2. Fiecare categorie are exact trei sloturi semantice fixe.
3. Evenimentele rezervate de loturile anterioare sunt excluse înaintea clasării.
4. Candidații rămași sunt clasați stabil după importanță, metoda verificării, scorul dovezii, ordinea globală și ID.
5. Regulile categoriei aleg evenimente, relații, lanțuri sau concepte; egalitățile sunt rupte exclusiv prin cheia stabilă.
6. Pentru fiecare slot se adaugă numai închiderea de o muchie către personaje, capitole, locuri, stări sau concepte permise.
7. Packetul este reuniunea celor trei sloturi și are buget maxim de 40 de noduri și 100 de muchii.
8. Qwen poate folosi numai ID-urile declarate în slotul curent; validatorul verifică separat respectarea contractului.

Nu se folosește randomizare, seed, eșantionare LLM sau selecție manuală de ID-uri. Același graf și aceeași versiune a algoritmului produc JSON identic.

## Utilizare

În promptul categoriei, înlocuiește exact `{{GRAPH_PACKET}}` cu întregul conținut al fișierului `.packet.json` asociat. Nu reformata JSON-ul înainte de trimitere, deoarece indentarea mărește contextul fără beneficiu semantic.

## Regenerare

Rulează din rădăcina proiectului:

```powershell
python cercetare-qwen/build_graph_packets.py
```

Generatorul verifică faptul că toate ID-urile provin din graful canonic, toate muchiile au capete incluse și fiecare packet conține suficient material pentru categoria sa.
