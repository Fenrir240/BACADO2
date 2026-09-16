# Experimentul 3 — protocol inițial

> Stare: schelet inițial derivat din Experimentul 2. Înaintea rulărilor oficiale,
> documentează aici ipoteza Experimentului 3 și variabila independentă modificată.
> Până atunci, infrastructura reproduce condițiile tehnice ale Experimentului 2.

## Scop

Experimentul măsoară aceleași două sarcini ca Experimentul 1: generarea a opt întrebări
din knowledge graph și reconstruirea capitolului I în registrele simplu și elevat.

Mecanismele de control moștenite din Experimentul 2 sunt:

- înlocuirea similarității lexicale/Jaccard pentru duplicarea întrebărilor cu o
  reprezentare semantică MiniLM;
- introducerea acelorași marje stilistice în promptul tuturor agenților;
- recalcularea automată a profilului stilistic după generare.

## Sursa factuală

Sursa factuală unică rămâne `../graf1/knowledge-graph.json`. Fragmentul-etalon folosit
la estimarea profilului nu este furnizat agenților și nu este utilizat pentru a completa
fapte absente din graf.

Subgraful capitolului I este extras prin exact aceeași funcție ca în Experimentul 1.
Hash-ul grafului, al subgrafului, al promptului și al evaluatorului este salvat în metadate.

## Similaritatea întrebărilor

Modelul înghețat este:

`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

Fiecare întrebare este codificată o singură dată cu `normalize_embeddings=True`.
Matricea de similaritate este produsul scalar al embeddingurilor normalizate, echivalent
similarității cosinus.

Decizia are trei zone:

- sub `review_threshold`: întrebări considerate distincte;
- între `review_threshold` și `duplicate_threshold`: caz marcat pentru revizuire;
- cel puțin `duplicate_threshold`: aceeași semnificație operațională, deci duplicat.

Definiția operațională este: „solicită aceeași informație și ar trebui să primească în
esență același răspuns”. Aceeași temă sau aceeași structură nu sunt suficiente.

Pragurile inițiale sunt provizorii și trebuie calibrate înaintea seriei oficiale. După
începerea rulărilor oficiale, modelul, versiunea bibliotecii, pragurile și setul de
calibrare nu se modifică.

## Profilul rezumatului

Fragmentul-etalon are 212 cuvinte, 12 propoziții și o medie de 17,667 cuvinte pe
propoziție. Conectorii discursivi și de ancorare reprezintă aproximativ 2,36%.

Pentru indicatorul personajelor, implementarea numără numai numele care corespund
nodurilor `Character` din graf. Din acest motiv, profilul automat reproductibil este
11,32%, nu procentul manual mai larg care include persoane absente din graf.

Marjele oficiale sunt cele din `inputs/summary-manifest.json`. Ele sunt intenționat
mai largi decât valorile fragmentului-etalon. Prepozițiile și conjuncțiile sunt doar
raportate, deoarece limitarea lor ar deteriora gramatica limbii române.

Evaluatorul nu folosește procente declarate de agent. El tokenizează `summary_text` și
calculează fiecare indicator. Abaterea produce o penalizare graduală de maximum 10
puncte pentru fiecare registru.

## Condiții identice

Toate modelele comparate primesc:

- același graph packet;
- același prompt și același manifest;
- aceleași intervale stilistice;
- aceleași limite de cuvinte;
- aceeași schemă JSON;
- aceiași parametri OpenRouter comuni;
- nicio ieșire sau corecție de la o rulare anterioară.

MiniLM este folosit după generare și nu oferă feedback agentului în timpul unei rulări.

## Rulări și raportare

Se recomandă minimum trei rulări independente pentru fiecare model. Se raportează
scorurile individuale, media, mediana, abaterea standard, rata JSON valid, toate
perechile ajunse în zona de revizuire și profilurile stilistice complete.

Outputul brut nu se repară înaintea evaluării. O eroare API și o eroare de încărcare a
modelului semantic sunt păstrate ca erori tehnice, nu transformate în scoruri valide.

## Limitări

- Scorul cosinus nu este o probabilitate calibrată.
- MiniLM poate confunda aceeași temă cu aceeași cerere informațională.
- Lexiconul conectorilor nu acoperă orice formulare posibilă și trebuie înghețat înainte
  de rulările oficiale.
- Raportul numelor nu include pronume și depinde de calitatea nodurilor `Character`.
- Un agent poate respecta formal profilul și totuși produce un rezumat factual slab;
  de aceea profilul este numai o penalizare limitată, nu scorul principal.

## Metrică RQUGE-Ro în pregătire

În `rquge_ro/` există o adaptare experimentală a arhitecturii RQUGE pentru română:
`mT5-small` reconstruiește răspunsul din întrebare și context, iar un regresor bazat pe
`XLM-RoBERTa-base` atribuie scorul 1–5. Regresorul trebuie antrenat pe judecăți umane
românești agregate și validat prin Spearman/Pearson pe un test neatins.

Până la îndeplinirea acestor condiții, scorul nu este inclus în rezultatul oficial și
este etichetat `experimental_unvalidated`. Baseline-ul română→engleză se raportează
separat, deoarece eroarea de traducere este o variabilă suplimentară.
