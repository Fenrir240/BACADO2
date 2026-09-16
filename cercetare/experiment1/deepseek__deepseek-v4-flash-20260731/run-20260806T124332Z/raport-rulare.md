# Raport rulare — DeepSeek: DeepSeek V4 Flash 0731

## Identificarea rulării

- Rulare: `run-20260806T124332Z`
- Data UTC: `2026-08-06T12:43:32.214688+00:00`
- Model solicitat: `deepseek/deepseek-v4-flash-20260731`
- Model returnat pentru întrebări: `deepseek/deepseek-v4-flash-0731`
- Model returnat pentru rezumat: `deepseek/deepseek-v4-flash-0731`
- Provider întrebări: Cloudflare
- Provider rezumat: Together
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: da
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 8 din 8
- JSON întrebări valid: da
- JSON rezumat valid: da
- Scor întrebări: 80,284 / 100
- Scor rezumat: 95,195 / 100
- Scor general: 87,739 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | high | 847,048 | 294.756 | 39.314 | 27.856 | 0,052274 |
| Rezumat | low | 57,131 | 30.911 | 7.508 | 0 | 0,006430 |

- Durată API cumulată: 904,179 secunde
- Cost total: 0,058704 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Unde se adună satul la hora duminicală? | 100,000 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Ce este Ion pentru Ana? | 100,000 | — |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | În ce ordine se petrec alegerea Anei la joc, conturarea planului pământurilor și insulta lui Vasile? | 72,500 | Rezultate query_plan=['EV_006'], raspuns declarat=['EV_004', 'EV_005', 'EV_006'], expected_result_ids=['EV_004', 'EV_005', 'EV_006'].; Traseu declarat=2 hop-uri; traseu minim=0. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | De ce o alege Ion pe Ana la joc? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Ce consecință are lovirea lui George de către Ion? | 100,000 | — |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Ce lanț de evenimente duce de la intrarea drumului în Pripas până la conturarea planului pentru pământuri? | 52,000 | Rezultate query_plan=[], raspuns declarat=['EV_001', 'EV_002', 'EV_003', 'EV_004', 'EV_005'], expected_result_ids=['EV_001', 'EV_002', 'EV_003', 'EV_004', 'EV_005'].; Traseu declarat=4 hop-uri; traseu minim=0. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Cum se transformă starea narativă în capitolul al XII-lea? | 52,727 | Rezultate query_plan=['CON_110', 'STATE_CH_12_CLOSE'], raspuns declarat=['EV_104', 'EV_105', 'EV_106', 'EV_107', 'EV_108', 'EV_109', 'EV_110', 'STATE_CH_12_CLOSE', 'STATE_CH_12_OPEN'], expected_result_ids=['STATE_CH_12_CLOSE'].; Traseu declarat=8 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=8, capitole=1; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Cine este participantul principal în confruntarea din capitolul I și cine în cea din capitolul XIII? | 58,000 | Rezultate query_plan=[], raspuns declarat=['CHAR_001', 'CHAR_004'], expected_result_ids=['CHAR_001', 'CHAR_004'].; Traseu declarat=2 hop-uri; traseu minim=1.; Dificultate recalculata: nivel=3, hop-uri=3, capitole=2; nivel tinta=3. |

- Media întrebărilor: 79,403 / 100
- Scorul de acoperire și diversitate al setului: 88,211 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 96,015 | 159 | 1,000 | 1,000 | 1,000 | 0,625 | Relatii cauzale declarate: 20 din 32 asteptate.; word_count declarat=0, recalculat=159. |
| elevated | 94,375 | 172 | 1,000 | 1,000 | 1,000 | 0,625 | Relatii cauzale declarate: 20 din 32 asteptate.; word_count declarat=0, recalculat=172. |

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
