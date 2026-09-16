# Prompturi Qwen pentru generarea întrebărilor din graful 2

Directorul conține opt prompturi autonome. Fiecare prompt cere exact trei întrebări dintr-o singură categorie și primește knowledge graph-ul prin înlocuirea variabilei `{{GRAPH_PACKET}}`.

## Ordinea recomandată a rulărilor

1. `01-intrebari-simple-lowhop.md`
2. `02-relatii-dintre-personaje-lowhop.md`
3. `03-actiune-narativa-lowhop.md`
4. `04-ordine-narativa-midhop.md`
5. `05-cauza-si-consecinta-midhop.md`
6. `06-evolutia-personajelor-highhop.md`
7. `07-teme-conflicte-si-simboluri-highhop.md`
8. `08-comparatii-intre-capitole-highhop.md`

Rezultatul complet va conține 24 de întrebări: câte trei pentru fiecare categorie.

Evenimentele nu mai sunt alese de Qwen. Generatorul local construiește determinist
trei `question_slots` pentru fiecare categorie. Modelul primește numai subgraful acestor
sloturi și are voie doar să formuleze întrebarea și răspunsul pe baza ID-urilor alocate.

## Definiția complexității

- `lowhop`: 0-3 muchii și puține noduri apropiate; răspunsul este direct.
- `midhop`: 2-6 muchii care formează un traseu narativ sau cauzal coerent.
- `highhop`: mai multe trasee sau un traseu de 4-10 muchii, cu noduri distribuite în mai multe capitole.

Un hop este traversarea unei muchii reale. Citirea unui atribut al unui nod nu este hop și se declară separat în `attribute_paths`.

Numărul de hop-uri nu poate fi crescut artificial prin:

- traversarea unei muchii și revenirea imediată pe muchia inversă;
- repetarea aceluiași nod;
- folosirea unor relații care nu contribuie la răspuns;
- adăugarea unor teme, personaje sau capitole fără rol semantic.

## Utilizare

Pentru fiecare rulare:

1. se citește promptul categoriei;
2. se înlocuiește `{{GRAPH_PACKET}}` cu fișierul compact asociat din `../graph-packets/`;
3. se trimite promptul complet modelului Qwen;
4. se păstrează răspunsul brut și se validează identificatorii și traseele.

Toate prompturile folosesc aceeași structură JSON, astfel încât rezultatele celor opt rulări pot fi concatenate ulterior.

Tabelul exact prompt–packet, dimensiunile și estimările de tokenuri se află în `../graph-packets/README.md`.
