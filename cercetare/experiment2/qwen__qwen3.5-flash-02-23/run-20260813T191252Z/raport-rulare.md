# Raport rulare — Qwen: Qwen3.5-Flash

## Identificarea rulării

- Rulare: `run-20260813T191252Z`
- Data UTC: `2026-08-13T19:12:52.368766+00:00`
- Model solicitat: `qwen/qwen3.5-flash-02-23`
- Model returnat pentru întrebări: `qwen/qwen3.5-flash-02-23`
- Model returnat pentru rezumat: `qwen/qwen3.5-flash-02-23`
- Provider întrebări: Alibaba
- Provider rezumat: Alibaba
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: da
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 8 din 8
- JSON întrebări valid: da
- JSON rezumat valid: da
- Scor întrebări: 75,973 / 100
- Scor rezumat: 87,426 / 100
- Scor general: 81,700 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | none | 59,911 | 286.471 | 3.101 | 0 | 0,019427 |
| Rezumat | none | 33,446 | 29.650 | 6.265 | 0 | 0,003556 |

- Durată API cumulată: 93,357 secunde
- Cost total: 0,022983 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Cine este autorul romanului Ion? | 100,000 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Care este relația dintre personajul Ion al Glanetașului și Florica? | 72,778 | Rezultate query_plan=['CHAR_003'], raspuns declarat=['CHAR_001', 'CHAR_003'], expected_result_ids=['CHAR_003'].; Traseu declarat=1 hop-uri; traseu minim=0. |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | În ce ordine cronologică au loc evenimentele: Ion o alege pe Ana la joc, Vasile îl insultă pe Ion și Ion îl lovește pe George? | 70,500 | Rezultate query_plan=['EV_006'], raspuns declarat=['EV_004', 'EV_006', 'EV_010'], expected_result_ids=['EV_004', 'EV_006', 'EV_010'].; Traseu declarat=2 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=2, hop-uri=3, capitole=1; nivel tinta=2. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Ce motivație directă stă la baza evenimentului în care Ion decide să o lase însărcinată pe Ana? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Care este consecința directă a evenimentului în care Ion mută hotarul tăind brazda lui Simion Lungu? | 100,000 | — |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Urmați lanțul cauzal de la sfatul lui Titu până la moartea Anei: cum duce sfatul la planul compromiterii și apoi la sinucidere? | 49,000 | Rezultate query_plan=['EV_056'], raspuns declarat=['EV_037', 'EV_095', 'MOT_037'], expected_result_ids=['EV_037', 'EV_095', 'MOT_037'].; Traseu declarat=2 hop-uri; traseu minim=0. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Cum se schimbă starea lui Ion între momentul în care își contemplă pământurile și cel în care este ucis de George? | 42,500 | Rezultate query_plan=['CON_081'], raspuns declarat=['EV_080', 'EV_113'], expected_result_ids=['EV_080', 'EV_113'].; Traseu declarat=2 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=2, capitole=2; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Comparați reacția lui Ion față de pământ în Capitolul II (când cosește fâneața) cu cea din Capitolul IX (când sărută pământul). | 52,000 | Rezultate query_plan=[], raspuns declarat=['EV_011', 'EV_082'], expected_result_ids=['EV_011', 'EV_082'].; Traseu declarat=1 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=2, capitole=2; nivel tinta=3.; Regula formala incalcata: ends_with_question_mark |

- Media întrebărilor: 73,347 / 100
- Scorul de acoperire și diversitate al setului: 99,602 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 89,622 | 145 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=198, recalculat=145. |
| elevated | 85,230 | 172 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=238, recalculat=172.; Profil stilistic în afara marjei: filler_phrases, connector_repetition. |

## Rezumatele generate

### Simple

La început, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Apoi, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. Așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. La cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

### Elevated

La începutul secvenței, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Ulterior, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. În continuarea firului narativ, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Pe măsură ce acțiunea înaintează, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. În acest context, Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Ulterior, Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. În continuarea firului narativ, Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. Pe măsură ce acțiunea înaintează, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

## Istoricul reluărilor

1. `2026-08-13T19:18:16.845471+00:00` — retrimise: niciuna; reutilizate valide: niciuna; finalizate ca invalide fără apel API: questions, summary.
2. `2026-08-13T19:39:23.045214+00:00` — retrimise: questions, summary; reutilizate valide: questions, summary; finalizate ca invalide fără apel API: niciuna.

## Fișierele verificabile ale rulării

- `questions.json` și `questions.openrouter-response.json`
- `summary.json` și `summary.openrouter-response.json`
- `scores.json`
- `metadata.json`

Raportul a fost construit determinist din fișierele rulării, fără apel AI suplimentar.

## Verificările specifice Experimentului 2

### Similaritatea semantică a întrebărilor

- Model local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Prag duplicat: `0.82`
- Prag revizuire manuală: `0.74`

### Profilul stilistic al rezumatelor

| Registru | Conformitate | Conectori | Expresii de umplutură | Nume personaje | Penalizare |
|---|---:|---:|---:|---:|---:|
| simple | 100.0% | 1.38% | 0.00% | 14.48% | 0.000 |
| elevated | 71.0% | 2.33% | 3.49% | 12.21% | 2.895 |
