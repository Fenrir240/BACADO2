# Raport rulare — DeepSeek: DeepSeek V4 Flash 0731

## Identificarea rulării

- Rulare: `run-20260806T120214Z`
- Data UTC: `2026-08-06T12:02:14.686191+00:00`
- Model solicitat: `deepseek/deepseek-v4-flash-20260731`
- Model returnat pentru întrebări: `deepseek/deepseek-v4-flash-0731`
- Model returnat pentru rezumat: `deepseek/deepseek-v4-flash-0731`
- Provider întrebări: Fireworks
- Provider rezumat: AtlasCloud
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: da
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 8 din 8
- JSON întrebări valid: da
- JSON rezumat valid: da
- Scor întrebări: 89,486 / 100
- Scor rezumat: 88,945 / 100
- Scor general: 89,215 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | high | 152,057 | 294.777 | 20.396 | 15.702 | 0,046980 |
| Rezumat | low | 52,595 | 30.911 | 5.744 | 277 | 0,005936 |

- Durată API cumulată: 204,652 secunde
- Cost total: 0,052916 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Unde se adună satul la hora duminicală? | 100,000 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Cu cine este căsătorit George Bulbuc? | 100,000 | — |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | Care este ordinea cronologică a următoarelor evenimente: intrarea drumului în Pripas, adunarea satului la horă și vizualizarea ierarhiilor? | 72,500 | Rezultate query_plan=['EV_003'], raspuns declarat=['EV_001', 'EV_002', 'EV_003'], expected_result_ids=['EV_001', 'EV_002', 'EV_003'].; Traseu declarat=2 hop-uri; traseu minim=0. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Care este motivația directă pentru care Ion îl lovește pe George? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Care este consecința directă a faptului că Ion îl lovește pe George? | 100,000 | — |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Ce lanț cauzal duce de la avertismentul Savistei până la moartea lui Ion? | 66,667 | Rezultate query_plan=['EV_114'], raspuns declarat=['EV_108', 'EV_110', 'EV_112', 'EV_113', 'EV_114'], expected_result_ids=['EV_108', 'EV_110', 'EV_112', 'EV_113', 'EV_114'].; Traseu declarat=4 hop-uri; traseu minim=0. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Cum se schimbă starea lui Ion în capitolul IX? | 72,333 | Rezultate query_plan=['CON_082'], raspuns declarat=['CON_082', 'STATE_CH_09_OPEN'], expected_result_ids=['CON_082', 'STATE_CH_09_OPEN'].; Traseu declarat=4 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=5, capitole=1; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Comparați efectul obținerii pământului asupra lui Ion în capitolele VII și IX. | 99,000 | Regula formala incalcata: ends_with_question_mark |

- Media întrebărilor: 88,812 / 100
- Scorul de acoperire și diversitate al setului: 95,549 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 89,765 | 159 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=210, recalculat=159. |
| elevated | 88,125 | 172 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=230, recalculat=172. |

## Rezumatele generate

### Simple

La început, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Apoi, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. După aceea, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. În continuare, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Mai târziu, Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Apoi, Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. După aceea, Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. În continuare, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. Mai târziu, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Apoi, Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

### Elevated

La începutul secvenței, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Ulterior, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. În continuarea firului narativ, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Pe măsură ce acțiunea înaintează, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. În acest context, Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Ulterior, Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. În continuarea firului narativ, Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. Pe măsură ce acțiunea înaintează, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

## Istoricul reluărilor

1. `2026-08-06T12:34:20.904765+00:00` — retrimise: summary; reutilizate fără apel API: questions.

## Fișierele verificabile ale rulării

- `questions.json` și `questions.openrouter-response.json`
- `summary.json` și `summary.openrouter-response.json`
- `scores.json`
- `metadata.json`

Raportul a fost construit determinist din fișierele rulării, fără apel AI suplimentar.
