# Raport rulare — Google: Gemini 2.5 Flash Lite

## Identificarea rulării

- Rulare: `run-20260814T123038Z`
- Data UTC: `2026-08-14T12:30:38.461552+00:00`
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
- Scor întrebări: 67,949 / 100
- Scor rezumat: 85,398 / 100
- Scor general: 76,673 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | none | 18,052 | 303.458 | 3.822 | 0 | 0,031875 |
| Rezumat | none | 18,263 | 31.152 | 8.875 | 0 | 0,006665 |

- Durată API cumulată: 36,315 secunde
- Cost total: 0,038540 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Cine este autorul romanului "Ion"? | 96,250 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Care este relația dintre Ion și George Bulbuc? | 56,111 | Rezultate query_plan=['CHAR_004'], raspuns declarat=['CHAR_001', 'CHAR_004'], expected_result_ids=['CHAR_004'].; Traseu declarat=1 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=1, capitole=7; nivel tinta=1. |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | Care este ordinea evenimentelor: Ion cosește fâneața, Ana vine pe câmp, George îl surprinde pe Ion? | 31,500 | Rezultate query_plan=[], raspuns declarat=['EV_011', 'EV_015', 'EV_112'], expected_result_ids=['EV_011', 'EV_015', 'EV_112'].; Traseu declarat=0 hop-uri; traseu minim=None.; Dificultate recalculata: nivel=3, hop-uri=0, capitole=3; nivel tinta=2.; Regula formala incalcata: answer_not_copied |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Ce l-a motivat pe Ion să mute hotarul? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Ce consecință a avut confirmarea sarcinii de către Firoana? | 100,000 | — |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Care este lanțul cauzal de la refuzul lui Vasile de a transfera pământurile până la moartea lui Ion? | 50,000 | Rezultate query_plan=[], raspuns declarat=['CON_113', 'EV_057', 'EV_060', 'EV_086', 'EV_105', 'EV_112', 'EV_113'], expected_result_ids=['CON_113'].; Traseu declarat=6 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=7, capitole=4; nivel tinta=3. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Ce stare a suferit Ana după ce Ion a început să o agreseze fizic? | 47,500 | Rezultate query_plan=['CON_065'], raspuns declarat=['CON_066'], expected_result_ids=['CON_066'].; Traseu declarat=1 hop-uri; traseu minim=None. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Cum diferă reacția lui Ion la obținerea pământurilor în Capitolul IX față de reacția sa la nașterea lui Petrișor în Capitolul VIII? | 37,500 | Rezultate query_plan=[], raspuns declarat=['EV_075', 'EV_080', 'EV_081', 'EV_082'], expected_result_ids=['EV_075', 'EV_080', 'EV_081', 'EV_082'].; Traseu declarat=0 hop-uri; traseu minim=None. |

- Media întrebărilor: 64,858 / 100
- Scorul de acoperire și diversitate al setului: 95,775 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 85,255 | 159 | 1,000 | 1,000 | 1,000 | 0,031 | Relatii cauzale declarate: 1 din 32 asteptate.; word_count declarat=219, recalculat=159.; Profil stilistic în afara marjei: discourse_connectors, filler_phrases, connector_repetition, connector_sentence_starts. |
| elevated | 85,542 | 172 | 1,000 | 1,000 | 1,000 | 0,031 | Relatii cauzale declarate: 1 din 32 asteptate.; word_count declarat=259, recalculat=172.; Profil stilistic în afara marjei: filler_phrases, connector_repetition. |

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
