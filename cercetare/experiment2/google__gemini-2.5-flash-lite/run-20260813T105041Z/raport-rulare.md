# Raport rulare — Google: Gemini 2.5 Flash Lite

## Identificarea rulării

- Rulare: `run-20260813T105041Z`
- Data UTC: `2026-08-13T10:50:41.853150+00:00`
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
- Scor întrebări: 76,189 / 100
- Scor rezumat: 85,087 / 100
- Scor general: 80,638 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | high | 100,124 | 303.458 | 28.754 | 24.572 | 0,041847 |
| Rezumat | high | 46,111 | 31.152 | 23.014 | 14.709 | 0,012321 |

- Durată API cumulată: 146,235 secunde
- Cost total: 0,054168 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Cine este autorul romanului "Ion"? | 100,000 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Care este relația dintre Ion și Ana? | 90,000 | Dificultate recalculata: nivel=3, hop-uri=1, capitole=3; nivel tinta=1. |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | Care este ordinea cronologică a evenimentelor: Drumul intră în Pripas, Satul se adună la horă și Ierarhiile devin vizibile? | 78,333 | Rezultate query_plan=['EV_002', 'EV_003', 'EV_004'], raspuns declarat=['EV_001', 'EV_002', 'EV_003'], expected_result_ids=['EV_001', 'EV_002', 'EV_003'].; Traseu declarat=2 hop-uri; traseu minim=0. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Ce l-a motivat pe Ion să cosească fâneața? | 50,000 | Rezultate query_plan=['EV_011'], raspuns declarat=['MOT_011'], expected_result_ids=['EV_011'].; Traseu declarat=1 hop-uri; traseu minim=0.; MiniLM: similaritate semantică maximă 0.873 cu întrebarea 'Q_005'. |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Care a fost consecința faptului că Ion a cosit fâneața? | 95,000 | MiniLM: similaritate semantică maximă 0.873 cu întrebarea 'Q_004'. |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Cum a dus sfatul lui Titu la acceptarea căsătoriei de către Vasile Baciu? | 60,000 | Rezultate query_plan=[], raspuns declarat=[], expected_result_ids=['EV_056'].; Traseu declarat=9 hop-uri; traseu minim=None.; Dificultate recalculata: nivel=3, hop-uri=14, capitole=3; nivel tinta=3. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Care a fost starea lui Ion înainte și după evenimentele din Capitolul I, unde a luptat cu George? | 53,000 | Rezultate query_plan=[], raspuns declarat=['CHAR_001', 'STATE_CH_01_CLOSE', 'STATE_CH_01_OPEN'], expected_result_ids=['CHAR_001'].; Traseu declarat=2 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=2, hop-uri=3, capitole=1; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Cum diferă obsesia lui Ion pentru pământ în Capitolul I față de Capitolul II? | 63,000 | Rezultate query_plan=[], raspuns declarat=[], expected_result_ids=['CH_01', 'CH_02'].; Traseu declarat=2 hop-uri; traseu minim=None.; Dificultate recalculata: nivel=3, hop-uri=4, capitole=2; nivel tinta=3. |

- Media întrebărilor: 73,667 / 100
- Scorul de acoperire și diversitate al setului: 98,894 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 84,943 | 159 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=219, recalculat=159.; Profil stilistic în afara marjei: discourse_connectors, filler_phrases, connector_repetition, connector_sentence_starts. |
| elevated | 85,230 | 172 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=259, recalculat=172.; Profil stilistic în afara marjei: filler_phrases, connector_repetition. |

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

## Verificările specifice Experimentului 2

### Similaritatea semantică a întrebărilor

- Model local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Prag duplicat: `0.82`
- Prag revizuire manuală: `0.74`

### Profilul stilistic al rezumatelor

| Registru | Conformitate | Conectori | Expresii de umplutură | Nume personaje | Penalizare |
|---|---:|---:|---:|---:|---:|
| simple | 51.8% | 5.03% | 2.52% | 13.21% | 4.822 |
| elevated | 71.0% | 2.33% | 3.49% | 12.21% | 2.895 |
