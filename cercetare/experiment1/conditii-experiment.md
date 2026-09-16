# Experimentul 1 — utilizarea knowledge graph-ului de către modele AI
se foloseste graf1, benchmark1

## 1. Scopul experimentului

Experimentul compară capacitatea mai multor modele AI de a utiliza același knowledge graph narativ al romanului *Ion* de Liviu Rebreanu pentru două sarcini:

1. generarea unui set standardizat de întrebări;
2. reconstruirea rezumatului capitolului I în registru simplu și în registru elevat.

Modelele nu răspund ulterior la întrebările generate. Fiecare model generează întrebările, răspunsurile de referință propuse și dovezile din graf. Calitatea rezultatului este calculată ulterior prin funcția deterministă de evaluare.

Obiectivul este măsurarea capacității de extragere, structurare și verbalizare a informației existente în graf, nu verificarea cunoștințelor generale ale modelului despre operă.

## 2. Ipoteza de cercetare

În condițiile în care modelele primesc același knowledge graph, aceleași instrucțiuni și aceleași limite de output, vor exista diferențe măsurabile în:

- corectitudinea referințelor la noduri și muchii;
- posibilitatea de derivare a întrebărilor din graf;
- acoperirea evenimentelor capitolului I;
- păstrarea ordinii și cauzalității narative;
- fidelitatea rezumatelor față de graf;
- respectarea formatului JSON solicitat.

## 3. Sursa factuală unică

Sursa canonică a experimentului este:

`../graf1/knowledge-graph.json`

Fișierele PDF ale operei, rezumatul extern, eseul-model, Wikipedia, internetul și cunoștințele proprii ale modelului nu sunt furnizate agenților și nu pot fi folosite ca surse.

Fișierele de documentație din `../graf1/` nu sunt trimise modelelor. Ele pot fi folosite numai de cercetător pentru auditarea grafului.

Versiunea grafului utilizată într-o rulare trebuie identificată prin hash SHA-256. Același hash trebuie să apară în metadatele tuturor rulărilor comparate.

## 4. Pachetele de graf oferite modelelor

### 4.1. Sarcina de generare a întrebărilor

Modelul primește graful integral din:

`../graf1/knowledge-graph.json`

Graful este introdus ca text JSON integral în `GRAPH_PACKET`. Nu se utilizează `file_search`, RAG, căutare semantică sau selecție dinamică de fragmente.

Înaintea rulării trebuie verificat că graful, promptul și outputul maxim încap în fereastra de context a fiecărui model. Un model care nu poate primi același pachet integral nu este inclus în comparația principală.

### 4.2. Sarcina de reconstruire a capitolului I

Modelul primește un subgraf determinist al capitolului I, denumit:

`inputs/chapter-01-graph.json`

Acest fișier trebuie generat exclusiv din graful canonic și trebuie să conțină:

- nodul capitolului I;
- toate evenimentele și subevenimentele capitolului I;
- participanții, locurile și contextele temporale asociate;
- ordinea narativă completă;
- cauzele și consecințele relevante;
- stările și tranzițiile personajelor;
- muchiile și nodurile suport necesare înțelegerii evenimentelor;
- toate referințele interne utilizate de aceste elemente.

Regula de extragere trebuie să fie identică pentru toate modelele. Fișierul trebuie generat o singură dată, validat și identificat prin hash SHA-256 înaintea experimentului. La momentul redactării acestui protocol, fișierul trebuie încă generat; rulările oficiale pentru rezumat nu încep înainte de existența și validarea lui.

## 5. Fișierele folosite pentru solicitarea outputului

### 5.1. Promptul pentru întrebări

Fișier utilizat:

`../benchmark1/prompts/prompt-generare-intrebari.md`

Înaintea apelului sunt înlocuite variabilele:

- `{{TASK_MANIFEST}}` — manifestul fix al sarcinii;
- `{{QUESTION_BLUEPRINTS}}` — definiția celor opt tipologii;
- `{{GRAPH_PACKET}}` — graful integral sau o indicație neechivocă spre blocul JSON integral inclus în aceeași cerere.

Modelul trebuie să genereze exact opt întrebări, câte una pentru fiecare tipologie:

1. `FACT_1HOP`;
2. `RELATION_1HOP`;
3. `TEMPORAL_ORDER`;
4. `DIRECT_CAUSE`;
5. `DIRECT_EFFECT`;
6. `MULTIHOP_CAUSAL`;
7. `STATE_TRANSITION`;
8. `CROSS_CHAPTER_COMPARE`.

Outputul trebuie să fie JSON valid și să includă întrebarea, răspunsul propus, nodurile, muchiile și planul de interogare care justifică rezultatul.

### 5.2. Promptul pentru rezumatul capitolului I

Fișier utilizat:

`../benchmark1/prompts/prompt-rezumat-capitolul-1.md`

Înaintea apelului sunt înlocuite variabilele:

- `{{SUMMARY_MANIFEST}}` — manifestul fix al sarcinii;
- `{{CHAPTER_01_GRAPH_PACKET}}` — conținutul integral al subgrafului validat pentru capitolul I sau o indicație neechivocă spre blocul JSON inclus în aceeași cerere.

Modelul trebuie să genereze:

- rezumatul simplu al capitolului I;
- rezumatul elevat al capitolului I;
- segmentarea pe propoziții;
- evenimentele și afirmațiile graf care susțin fiecare propoziție;
- muchiile cauzale declarate;
- lista evenimentelor utilizate.

Outputul trebuie să fie JSON valid.

## 6. Modelele și modalitatea de apelare

Modelele sunt apelate prin OpenRouter. Lista efectivă este obținută din endpointul autentificat:

`GET https://openrouter.ai/api/v1/models/user`

Pentru fiecare model se salvează identificatorul OpenRouter exact. Nu se folosesc routere automate care ar putea selecta alt model de la o rulare la alta.

În comparația principală sunt acceptate numai modelele care:

- pot primi pachetul de graf stabilit;
- pot produce suficient output pentru schema solicitată;
- acceptă parametrii comuni stabiliți pentru experiment;
- sunt disponibile conform politicilor contului OpenRouter al organizației.

Providerul efectiv, endpointul, modelul returnat și eventualele fallback-uri trebuie înregistrate când informația este disponibilă. Pentru o comparație strictă, fallback-urile între modele diferite trebuie dezactivate.

## 7. Condiții identice pentru toate modelele

Fiecare model primește:

- același graf sau același subgraf, verificat prin hash;
- același prompt, verificat prin hash;
- același manifest;
- aceleași tipologii de întrebări;
- aceeași schemă de output;
- aceeași limită maximă de output;
- aceeași limbă de lucru: româna;
- nicio unealtă externă;
- fără acces la internet;
- fără istoricul altei rulări;
- fără outputurile celorlalte modele;
- fără feedback din partea evaluatorului înaintea predării rezultatului.

Fiecare sarcină este executată într-o cerere independentă. Nu se folosește conversația de la generarea întrebărilor pentru generarea rezumatului.

Parametrii precum `temperature`, `seed`, `reasoning` și `response_format` se folosesc numai dacă sunt acceptați de toate modelele din comparația respectivă. Intersecția parametrilor suportați se stabilește înaintea rulărilor și nu se schimbă pe parcursul experimentului.

Dacă un model nu acceptă Structured Outputs, comparația principală trebuie fie restrânsă la modele compatibile, fie executată fără această funcție pentru toate modelele. Nu se oferă avantaje de format numai anumitor modele.

## 8. Numărul de rulări

Se efectuează trei rulări independente pentru fiecare combinație model–sarcină.

Rulările nu folosesc response caching. Prompt caching este permis, deoarece poate reduce costul procesării fără să reutilizeze răspunsul final.

Pentru fiecare model se raportează:

- scorul fiecărei rulări;
- media aritmetică;
- mediana;
- scorul minim și maxim;
- abaterea standard;
- rata outputurilor JSON valide.

## 9. Evaluarea deterministă

Fișierul de evaluare este:

`../benchmark1/scoring/evaluator.py`

Funcțiile publice utilizate sunt:

- `score_question_generation(...)`;
- `score_chapter_1_summary(...)`;
- `score_agent_submission(...)`.

Evaluatorul primește outputul modelului și knowledge graph-ul canonic. Niciun alt model AI nu acordă scorul.

### 9.1. Scorul întrebărilor

Fiecare întrebare primește maximum 100 de puncte:

- validitatea schemei: 5;
- respectarea blueprintului: 15;
- validitatea referințelor: 15;
- derivabilitatea din graf: 25;
- unicitatea răspunsului: 10;
- minimalitatea traseului: 10;
- nivelul de dificultate: 10;
- reguli formale: 5;
- lipsa duplicării: 5.

Scorul setului de întrebări este:

`QGS = 0,90 × media celor 8 întrebări + 0,10 × scorul de diversitate al setului`

Lipsa unei întrebări din cele opt produce implicit scor zero pentru poziția respectivă.

### 9.2. Scorul rezumatului

Fiecare registru, simplu și elevat, primește maximum 100 de puncte:

- acoperirea evenimentelor: 30;
- susținerea afirmațiilor prin graf: 25;
- ordinea evenimentelor: 20;
- păstrarea cauzalității: 10;
- disciplina dovezilor: 5;
- concizia: 5;
- respectarea registrului: 5.

Scorul rezumatului este:

`SRS = media(scor simplu, scor elevat) − penalizarea pentru inconsistența evenimentelor`

### 9.3. Scorul general

Dacă cele două sarcini au ponderi egale:

`SCOR_GENERAL = 0,50 × QGS + 0,50 × SRS`

Ponderile nu se modifică după observarea rezultatelor.

## 10. Rezultatele care trebuie salvate

Pentru fiecare rulare se păstrează:

- outputul brut al modelului;
- outputul JSON parsat, dacă este valid;
- raportul complet produs de evaluator;
- erorile de parsare sau de apel;
- identificatorul exact al modelului;
- providerul și endpointul efectiv, dacă sunt disponibile;
- data și ora;
- durata apelului;
- numărul de tokenuri de input, output și cache;
- costul raportat de OpenRouter;
- parametrii cererii;
- hash-ul grafului;
- hash-ul promptului;
- numărul rulării.

Structura recomandată este:

```text
experiment1/
  conditii-experiment.md
  inputs/
    chapter-01-graph.json
  runs/
    <model-id-normalizat>/
      run-01/
        questions.raw.json
        summary.raw.json
        scores.json
        metadata.json
      run-02/
      run-03/
  results/
    rezultate-experiment.csv
    rezultate-experiment.json
```

Tabelul final trebuie să permită identificarea exactă a:

- modelului;
- numărului rulării;
- întrebărilor generate;
- rezumatului simplu;
- rezumatului elevat;
- scorului întrebărilor;
- scorului rezumatului;
- scorului general;
- erorilor și observațiilor tehnice.

## 11. Tratarea erorilor

- Un output care nu poate fi parsat nu este reparat de alt model AI.
- Răspunsul brut este păstrat integral.
- O reluare cauzată de eroare API este marcată separat și nu înlocuiește silențios o rulare.
- Un refuz al modelului este păstrat și punctat conform regulilor evaluatorului.
- Un output trunchiat este marcat `incomplete`.
- Nu se modifică manual nodurile, muchiile sau dovezile declarate de model înaintea evaluării.

## 12. Validări obligatorii înaintea rulării oficiale

Experimentul poate începe numai după ce sunt îndeplinite toate condițiile:

- `knowledge-graph.json` trece validarea existentă;
- `chapter-01-graph.json` a fost generat și validat;
- manifestele și blueprinturile au fost materializate în forme fixe;
- placeholder-ele din prompturi sunt complet înlocuite;
- evaluatorul este înghețat și identificat prin hash sau versiune;
- fiecare model trece un test de context și parametri;
- cheia OpenRouter este furnizată prin variabilă de mediu, nu este salvată în proiect;
- politica organizației permite trimiterea datelor către modelele și providerii aleși;
- o rulare de test completă a produs output, scor și metadate fără intervenție manuală.

## 13. Limitări metodologice cunoscute

Versiunea curentă a evaluatorului verifică riguros structurile declarate de model, însă nu poate demonstra singură că fiecare formulare liberă din rezumat are exact aceeași semantică precum tripletele declarate.

De asemenea, lista curentă de relații cauzale a capitolului I trebuie normalizată înaintea rulării oficiale pentru a evita punctarea dublă a relațiilor semantic echivalente și includerea accidentală a relațiilor între capitole.

Aceste limitări trebuie corectate sau înghețate și declarate explicit înainte de colectarea rezultatelor. Evaluatorul nu se modifică după începerea experimentului.

## 14. Starea protocolului

Acesta este protocolul inițial al Experimentului 1. Documentul descrie condițiile care trebuie îndeplinite, dar nu declară încă experimentul pregătit pentru rulări oficiale.

Elementele care mai trebuie create sau finalizate sunt:

- subgraful determinist al capitolului I;
- manifestul întrebărilor;
- definițiile blueprinturilor într-un fișier de input;
- manifestul rezumatului;
- runnerul OpenRouter;
- schema tabelului final;
- corecțiile și înghețarea evaluatorului.
