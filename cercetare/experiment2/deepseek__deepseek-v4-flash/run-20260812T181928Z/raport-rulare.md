# Raport rulare — DeepSeek: DeepSeek V4 Flash 0423

## Identificarea rulării

- Rulare: `run-20260812T181928Z`
- Data UTC: `2026-08-12T18:19:28.477264+00:00`
- Model solicitat: `deepseek/deepseek-v4-flash`
- Model returnat pentru întrebări: `deepseek/deepseek-v4-flash`
- Model returnat pentru rezumat: `deepseek/deepseek-v4-flash`
- Provider întrebări: SiliconFlow
- Provider rezumat: DeepInfra
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: da
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 8 din 8
- JSON întrebări valid: da
- JSON rezumat valid: da
- Scor întrebări: 84,874 / 100
- Scor rezumat: 95,974 / 100
- Scor general: 90,424 / 100
- Eroare întrebări: —
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | high | 144,086 | 294.728 | 14.322 | 11.510 | 0,042325 |
| Rezumat | high | 451,317 | 30.635 | 33.917 | 18.993 | 0,008858 |

- Durată API cumulată: 595,403 secunde
- Cost total: 0,051182 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|
| Q_001 | SLOT_01 | FACT_1HOP | Cine este tatăl Anei? | 99,000 | Regula formala incalcata: word_count_5_35 |
| Q_002 | SLOT_02 | RELATION_1HOP | Cu cine este căsătorit Ion? | 100,000 | — |
| Q_003 | SLOT_03 | TEMPORAL_ORDER | Care este ordinea evenimentelor: Ion o alege pe Ana la joc, planul pământurilor se conturează, Vasile îl insultă pe Ion? | 63,750 | Rezultate query_plan=['EV_006'], raspuns declarat=['EV_004', 'EV_005', 'EV_006'], expected_result_ids=['EV_006'].; Traseu declarat=2 hop-uri; traseu minim=0.; MiniLM: similaritate semantică maximă 0.765 cu întrebarea 'Q_005'. |
| Q_004 | SLOT_04 | DIRECT_CAUSE | Care este motivația directă pentru care Ion mută hotarul? | 100,000 | — |
| Q_005 | SLOT_05 | DIRECT_EFFECT | Care este consecința directă a faptului că Ion o alege pe Ana la joc? | 97,500 | MiniLM: similaritate semantică maximă 0.765 cu întrebarea 'Q_003'. |
| Q_006 | SLOT_06 | MULTIHOP_CAUSAL | Ce lanț cauzal duce de la observația Savistei la surprinderea lui Ion de către George? | 63,000 | Rezultate query_plan=['EV_112'], raspuns declarat=['EV_107', 'EV_108', 'EV_110', 'EV_112'], expected_result_ids=['EV_112'].; Traseu declarat=4 hop-uri; traseu minim=0. |
| Q_007 | SLOT_07 | STATE_TRANSITION | Cum se schimbă starea Anei de la începutul la sfârșitul capitolului Zece? | 50,000 | Rezultate query_plan=['CON_095'], raspuns declarat=['EV_090', 'EV_091', 'EV_092', 'EV_093', 'EV_094', 'EV_095', 'STATE_CH_10_CLOSE', 'STATE_CH_10_OPEN'], expected_result_ids=['STATE_CH_10_CLOSE'].; Traseu declarat=7 hop-uri; traseu minim=0.; Dificultate recalculata: nivel=3, hop-uri=7, capitole=1; nivel tinta=2. |
| Q_008 | SLOT_08 | CROSS_CHAPTER_COMPARE | În ce locație se desfășoară hora atât în capitolul I, cât și în capitolul XIII? | 93,000 | Dificultate recalculata: nivel=3, hop-uri=2, capitole=2; nivel tinta=3. |

- Media întrebărilor: 83,281 / 100
- Scorul de acoperire și diversitate al setului: 99,213 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 96,545 | 233 | 1,000 | 1,000 | 1,000 | 0,656 | Relatii cauzale declarate: 21 din 32 asteptate.; word_count declarat=186, recalculat=233. |
| elevated | 95,403 | 282 | 1,000 | 1,000 | 1,000 | 0,656 | Relatii cauzale declarate: 21 din 32 asteptate.; word_count declarat=221, recalculat=282.; Profil stilistic în afara marjei: filler_phrases. |

## Rezumatele generate

### Simple

Capitolul I, intitulat Începutul, face parte din romanul Ion de Liviu Rebreanu. La începutul capitolului, drumul care intră în Pripas introduce treptat satul, cu casele sale și semnele unei comunități aparent liniștite. Apoi, în curtea văduvei Todosia, jocul duminical adună țăranii din tot satul și eliberează energiile acumulate peste săptămână, într-o atmosferă de sărbătoare și voie bună. Așezarea participanților la horă separă clar săracii, bogații și intelectualitatea, cum ar fi învățătorul Zaharia Herdelea, preotul Belciug și Toma Bulbuc, arătând astfel ordinea socială strictă și ierarhia satului. Deși o iubește pe Florica, o fată săracă și frumoasă, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu, demonstrând că alegerea afectivă este subordonată averii. Planul pământurilor se conturează clar și hotărât: Ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Vasile Baciu, beat fiind și furios, îl numește public pe Ion sărăntoc și refuză categoric să îl accepte ca ginere, preferându-l pe George Bulbuc, un flăcău înstărit și respectat. Acest afront îl face pe Ion să caute o ocazie de a-și afirma superioritatea și de a se răzbuna pe Vasile. La cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării directe și violente dintre Ion și George. Ion îl bate pe George cu un par, dovedindu-și forța fizică și câștigând respectul flăcăilor. Astfel, Ion își consolidează prestigiul fizic, dar conflictul social și erotic rămâne deschis și nerezolvat.

### Elevated

Capitolul I, intitulat sugestiv Începutul, deschide romanul Ion, capodopera realistă a lui Liviu Rebreanu. La debutul secvenței narative, drumul care străbate câmpia pătrunde treptat în satul Pripas, dezvăluind casele modeste și indiciile unei colectivități aparent pașnice. Ulterior, în ograda văduvei Todosia, hora duminicală adună obștea sătească, eliberând energiile acumulate de-a lungul săptămânii, într-o atmosferă de sărbătoare și exuberanță colectivă. Dispunerea participanților la joc separă net categoriile sociale: săracii, înstăriții și intelectualitatea, reprezentată de învățătorul Zaharia Herdelea, preotul Belciug și Toma Bulbuc, relevând astfel ierarhia riguroasă și stratificarea comunității. Această ordine socială este dictată de avere și prestigiu. Cu toate că nutrește sentimente sincere pentru Florica, o fată săracă și plăpândă, Ion o neglijează ostentativ și o alege la dans pe Ana, fiica prosperului Vasile Baciu, dovedind că aspirațiile afective sunt subordonate interesului material și setei de pământ. Alegerea Anei relevă conflictul interior al lui Ion între iubire și interes. În acest context, se conturează cu claritate planul lui Ion de a obține pământurile lui Vasile Baciu prin căsătoria cu Ana. Vasile Baciu, aflat sub influența băuturii și mânat de mânie și dispreț, îl stigmatizează public pe Ion, numindu-l sărăntoc și refuzând categoric să-l primească drept ginere, preferându-l pe George Bulbuc, un flăcău înstărit și bine văzut în sat. Această umilință publică profundă transformă setea de pământ a lui Ion într-o pornire irezistibilă și mistuitoare de răzbunare și afirmare socială, intensificându-i ambiția. La cârciuma lui Avrum, plata lăutarilor prilejuiește confruntarea directă și violentă dintre Ion și George. Ion îl lovește pe George cu un par, demonstrându-și forța brută și câștigând admirația și respectul flăcăilor. Astfel, Ion își consolidează prestigiul fizic, însă conflictul social și cel erotic rămân deschise, prefigurând tensiunile și evenimentele viitoare.

## Istoricul reluărilor

1. `2026-08-12T18:30:28.338763+00:00` — retrimise: summary; reutilizate fără apel API: questions.

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
| simple | 100.0% | 1.72% | 0.00% | 12.88% | 0.000 |
| elevated | 88.4% | 1.42% | 1.06% | 10.64% | 1.159 |
