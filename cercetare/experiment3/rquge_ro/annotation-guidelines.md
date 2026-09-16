# Protocol de adnotare pentru span-scorer-ul RQUGE-Ro

## Ce se evaluează

Adnotatorul vede, în ordine aleatorie și fără numele modelului:

1. contextul;
2. întrebarea candidată;
3. răspunsul corect (`gold_answer`);
4. răspunsul produs de modulul QA (`predicted_answer`).

Se evaluează cât de corect redă răspunsul produs informația din răspunsul corect,
ținând cont de întrebare și context. Nu se notează frumusețea formulării întrebării.
Aceasta urmează rolul setului MOCHA în RQUGE; întrebarea bună trebuie să conducă modulul
QA la un răspuns compatibil cu răspunsul corect.

## Rubrica experimentală 1–5

- **5** — echivalent semantic și complet; diferențele sunt numai de formulare;
- **4** — corect în esență, cu o omisiune sau un adaos minor;
- **3** — parțial corect, dar lipsește ori este greșit un element important;
- **2** — conține un element relevant, însă răspunsul este în mare parte greșit;
- **1** — greșit, contradictoriu, irelevant, gol sau nesusținut de context.

Un răspuns mai lung nu primește automat scor mai mare. Detaliile corecte suplimentare
sunt acceptabile numai dacă nu schimbă sensul cerut.

## Procedură minimă

- minimum trei adnotatori independenți per pereche;
- minimum 30–50 exemple comune în pilot pentru clarificarea rubricii;
- ordinea exemplelor randomizată și identitatea generatorului ascunsă;
- se păstrează scorurile individuale, nu numai media;
- dezacordurile mari (de exemplu, diferență de cel puțin 3 puncte) se auditează;
- se raportează acordul inter-adnotatori și distribuția scorurilor;
- train/validation/test se separă pe întrebare și context, înainte de agregare.

Rubrica este o adaptare românească propusă și trebuie validată. Până atunci,
checkpointul rezultat rămâne `experimental_unvalidated`.
