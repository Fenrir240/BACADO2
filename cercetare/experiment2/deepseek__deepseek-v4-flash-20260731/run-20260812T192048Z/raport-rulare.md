# Raport rulare — DeepSeek: DeepSeek V4 Flash 0731

## Identificarea rulării

- Rulare: `run-20260812T192048Z`
- Data UTC: `2026-08-12T19:20:48.557808+00:00`
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
- Scor întrebări: 89,768 / 100
- Scor rezumat: 87,421 / 100
- Scor general: 88,595 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | high | 349,402 | 294.807 | 30.003 | 23.169 | 0,049674 |
| Rezumat | none | 42,609 | 30.635 | 5.208 | 0 | 0,005747 |

- Durată API cumulată: 392,011 secunde
- Cost total: 0,055421 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Ce consecință are faptul că Ion mută hotarul? | 100,000 | — |
| Q_002 | SLOT_02 | RELATION_1HOP | Ce relație există între Ion și Florica? | 100,000 | — |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | În ce ordine se petrec evenimentele: Ion o alege pe Ana la joc, planul pământurilor se conturează și Vasile îl insultă pe Ion? | 72,500 | Rezultate query_plan=['EV_006'], raspuns declarat=['EV_004', 'EV_005', 'EV_006'], expected_result_ids=['EV_004', 'EV_005', 'EV_006'].; Traseu declarat=2 hop-uri; traseu minim=0. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Care este motivația directă pentru care Ion îl lovește pe George? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Care este consecința directă a bătăii de la cârciumă dintre Ion și George? | 100,000 | — |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Ce lanț cauzal leagă compromiterea Anei de amânarea transferului pământurilor? | 66,667 | Rezultate query_plan=['CON_057'], raspuns declarat=['CON_056', 'CON_057', 'EV_037', 'EV_056', 'EV_057'], expected_result_ids=['CON_056', 'CON_057', 'EV_037', 'EV_056', 'EV_057'].; Traseu declarat=4 hop-uri; traseu minim=0. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Cum se schimbă starea lui Ion în capitolul al VII-lea? | 94,250 | Dificultate recalculata: nivel=2, hop-uri=3, capitole=1; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | Ce relație există între evenimentul de deschidere și cel de închidere al romanului? | 76,333 | Rezultate query_plan=['EV_122'], raspuns declarat=['EV_001', 'EV_122'], expected_result_ids=['EV_001', 'EV_122'].; Traseu declarat=1 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=3, capitole=2; nivel tinta=3. |

- Media întrebărilor: 88,719 / 100
- Scorul de acoperire și diversitate al setului: 99,209 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 89,612 | 144 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=180, recalculat=144. |
| elevated | 85,230 | 172 | 1,000 | 1,000 | 1,000 | 0,000 | Relatii cauzale declarate: 0 din 32 asteptate.; word_count declarat=220, recalculat=172.; Profil stilistic în afara marjei: filler_phrases, connector_repetition. |

## Rezumatele generate

### Simple

La început, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. În curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. Așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. Afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. La cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

### Elevated

La începutul secvenței, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Ulterior, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. În continuarea firului narativ, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Pe măsură ce acțiunea înaintează, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. În acest context, Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Ulterior, Vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. În continuarea firului narativ, Vasile îl preferă pe George Bulbuc, flăcău înstărit și potrivit rangului familiei sale. Pe măsură ce acțiunea înaintează, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, Ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

## Istoricul reluărilor

1. `2026-08-12T19:56:47.760794+00:00` — retrimise: summary; reutilizate fără apel API: questions.

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
| simple | 100.0% | 0.69% | 0.00% | 14.58% | 0.000 |
| elevated | 71.0% | 2.33% | 3.49% | 12.21% | 2.895 |
