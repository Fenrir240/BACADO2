# Raport rulare — Google: Gemini 2.5 Flash Lite

## Identificarea rulării

- Rulare: `run-20260806T140802Z`
- Data UTC: `2026-08-06T14:08:02.334448+00:00`
- Model solicitat: `google/gemini-2.5-flash-lite`
- Model returnat pentru întrebări: `google/gemini-2.5-flash-lite`
- Model returnat pentru rezumat: `google/gemini-2.5-flash-lite`
- Provider întrebări: Google
- Provider rezumat: Google
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: da
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 8 din 8
- JSON întrebări valid: da
- JSON rezumat valid: da
- Scor întrebări: 73,383 / 100
- Scor rezumat: 88,945 / 100
- Scor general: 81,164 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | high | 126,353 | 303.420 | 30.227 | 24.575 | 0,042433 |
| Rezumat | low | 66,329 | 31.314 | 20.224 | 11.997 | 0,011221 |

- Durată API cumulată: 192,682 secunde
- Cost total: 0,053654 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Cine este autorul romanului Ion? | 100,000 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Care este relația maritală dintre Ion și Ana? | 66,111 | Rezultate query_plan=['CHAR_002'], raspuns declarat=['CHAR_001', 'CHAR_002'], expected_result_ids=['CHAR_002'].; Traseu declarat=1 hop-uri; traseu minim=0. |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | Care este ordinea cronologică a evenimentelor: Drumul intră în Pripas, Satul se adună la horă și Ierarhiile devin vizibile? | 49,000 | Rezultate query_plan=[], raspuns declarat=['EV_001', 'EV_002', 'EV_003'], expected_result_ids=['EV_001', 'EV_002', 'EV_003'].; Traseu declarat=2 hop-uri; traseu minim=None.; Dificultate recalculata: nivel=3, hop-uri=7, capitole=1; nivel tinta=2. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Ce l-a motivat pe Ion să aleagă pe Ana la joc, deși o iubea pe Florica? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Ce consecință a avut alegerea Anei de către Ion la joc? | 100,000 | — |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Ce lanț cauzal duce la condamnarea lui Ion la închisoare? | 50,000 | Rezultate query_plan=[], raspuns declarat=['EV_026', 'EV_051', 'EV_053'], expected_result_ids=['EV_026', 'EV_051', 'EV_053'].; Traseu declarat=2 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=142, capitole=2; nivel tinta=3. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Ce stare a lui Ion este descrisă înainte de a deveni proprietar și care este starea sa după? | 46,250 | Rezultate query_plan=[], raspuns declarat=['STATE_CH_02_OPEN', 'STATE_CH_07_CLOSE'], expected_result_ids=['STATE_CH_02_OPEN', 'STATE_CH_07_CLOSE'].; Traseu declarat=2 hop-uri; traseu minim=None.; Dificultate recalculata: nivel=3, hop-uri=2, capitole=2; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Cum diferă motivația lui Ion pentru pământ în Capitolul I față de Capitolul IX? | 53,000 | Rezultate query_plan=[], raspuns declarat=['EV_005', 'EV_080', 'EV_081', 'EV_082'], expected_result_ids=['EV_005', 'EV_080', 'EV_081', 'EV_082'].; Traseu declarat=2 hop-uri; traseu minim=None.; Dificultate recalculata: nivel=3, hop-uri=12, capitole=2; nivel tinta=3. |

- Media întrebărilor: 70,545 / 100
- Scorul de acoperire și diversitate al setului: 98,928 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 89,765 | 159 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=245, recalculat=159. |
| elevated | 88,125 | 172 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=250, recalculat=172. |

## Rezumatele generate

### Simple

La început, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Apoi, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. După aceea, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. În continuare, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Mai târziu, Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Apoi, Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. După aceea, Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. În continuare, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. Mai târziu, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Apoi, Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

### Elevated

La începutul secvenței, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Ulterior, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. În continuarea firului narativ, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Pe măsură ce acțiunea înaintează, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. În acest context, Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Ulterior, Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. În continuarea firului narativ, Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. Pe măsură ce acțiunea înaintează, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

## Istoricul reluărilor

Rularea nu a fost reluată.

## Fișierele verificabile ale rulării

- `questions.json` și `questions.openrouter-response.json`
- `summary.json` și `summary.openrouter-response.json`
- `scores.json`
- `metadata.json`

Raportul a fost construit determinist din fișierele rulării, fără apel AI suplimentar.
