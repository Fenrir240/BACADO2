# Prompt standardizat pentru generarea întrebărilor

## Instrucțiuni de utilizare

Acest prompt trebuie oferit identic tuturor modelelor evaluate.

Înlocuiește numai cele trei variabile de la final:

- `TASK_MANIFEST` cu manifestul experimentului;
- `QUESTION_BLUEPRINTS` cu definițiile tipologiilor;
- `GRAPH_PACKET` cu knowledge graph-ul sau subgraful folosit în experiment.

Numele și versiunea modelului, temperatura, seed-ul, data execuției și răspunsul brut trebuie înregistrate de aplicația care execută experimentul. Nu trebuie cerute modelului.

---

## Prompt oferit modelului

Ești participant într-un experiment controlat de generare a întrebărilor dintr-un knowledge graph narativ.

Ai acces exclusiv la informațiile din `GRAPH_PACKET`. Nu ai voie să folosești PDF-ul operei, un rezumat extern, informații din memoria ta sau informații de pe internet.

Chiar dacă recunoști opera literară, ignoră toate informațiile pe care le-ai putea cunoaște despre aceasta și lucrează numai cu nodurile, muchiile și atributele furnizate.

## Sarcina

Generează exact câte o întrebare pentru fiecare slot din `TASK_MANIFEST`.

Pentru fiecare întrebare trebuie să furnizezi:

1. textul exact al întrebării;
2. răspunsul propus;
3. nodurile care susțin răspunsul;
4. muchiile care susțin răspunsul;
5. un traseu verificabil prin graf;
6. planul formal al interogării;
7. dificultatea declarată;
8. capitolele utilizate.

Funcția de evaluare va verifica automat toate nodurile, muchiile, traseele și rezultatele declarate. Nu inventa identificatori și nu aproxima relațiile.

## Tipologiile obligatorii

Respectă blueprint-ul indicat în fiecare slot.

### `FACT_1HOP`

- folosește exact o relație semantică relevantă;
- răspunsul trebuie să fie un fapt, un nod sau o valoare identificabilă fără ambiguitate;
- întrebarea trebuie să aibă un răspuns unic.

### `RELATION_1HOP`

- întreabă despre relația directă dintre două entități;
- traseul formal trebuie să conțină o singură muchie relevantă;
- nu transforma întrebarea într-o întrebare cauzală sau temporală.

### `TEMPORAL_ORDER`

- folosește minimum trei evenimente;
- evenimentele trebuie să poată fi ordonate prin `chapter_order`, `global_order`, `occurs_before`, `immediately_precedes` sau relații echivalente existente în graf;
- răspunsul trebuie să conțină ordinea completă a evenimentelor.

### `DIRECT_CAUSE`

- întreabă despre cauza sau motivația directă a unui eveniment;
- folosește `has_motivation`, `motivates`, `causes` sau o relație cauzală directă disponibilă în graf;
- nu adăuga explicații care nu apar în traseul declarat.

### `DIRECT_EFFECT`

- întreabă despre efectul sau consecința directă a unui eveniment;
- folosește `has_consequence`, `results_in` sau o relație echivalentă disponibilă în graf;
- răspunsul trebuie să fie derivabil direct din muchiile indicate.

### `MULTIHOP_CAUSAL`

- folosește minimum patru hop-uri;
- include minimum trei evenimente sau stări narative;
- traseul trebuie să conțină minimum două relații cauzale;
- fiecare pas trebuie să fie conectat de următorul printr-o muchie existentă;
- răspunsul trebuie să prezinte lanțul cauzal în ordinea sa corectă.

### `STATE_TRANSITION`

- include o stare inițială, un eveniment sau o succesiune de evenimente transformatoare și o stare finală;
- folosește `has_state_before`, `has_state_after`, `changes_state_of`, `gains`, `loses` sau relații echivalente disponibile în graf;
- precizează personajul sau entitatea a cărei stare se schimbă.

### `CROSS_CHAPTER_COMPARE`

- folosește minimum două capitole;
- construiește două trasee comparabile;
- precizează criteriul comparației;
- răspunsul trebuie să includă informația relevantă din ambele capitole;
- nu formula întrebări de opinie sau interpretări care nu pot fi verificate.

## Reguli pentru formularea întrebărilor

- Scrie întrebările în limba română, cu diacritice.
- Fiecare întrebare trebuie să se termine cu semnul întrebării.
- Fiecare întrebare trebuie să conțină între 5 și 35 de cuvinte.
- Nu include identificatori tehnici precum `EV_001`, `CHAR_001` sau `EDGE_00001` în textul adresat elevului.
- Nu include răspunsul complet în întrebare.
- Nu formula întrebări de opinie.
- Nu folosi expresii precum „ce crezi”, „cum consideri” sau „după părerea ta”.
- Nu formula întrebări despre absența unei informații. Knowledge graph-ul este tratat ca o lume deschisă: absența unei afirmații nu demonstrează că aceasta este falsă.
- Nu folosi întrebări de tip adevărat/fals în această etapă.
- Nu genera două întrebări cu același răspuns și același traseu.
- Nu reformula aceeași întrebare pentru două sloturi diferite.
- Nu utiliza o informație doar pentru că apare în eticheta experimentului sau în instrucțiuni. Informația trebuie să existe în `GRAPH_PACKET`.

## Reguli pentru răspunsul propus

- Răspunsul trebuie să fie derivabil exclusiv din `query_plan` și `evidence`.
- `answer.node_ids` trebuie să conțină numai nodurile care reprezintă răspunsul.
- Pentru o listă ordonată, folosește și `answer.ordered_node_ids`.
- Pentru un lanț cauzal, răspunsul trebuie să păstreze ordinea traseului.
- Nu introduce în `answer.text` fapte care nu sunt reprezentate de nodurile și muchiile declarate.

## Reguli pentru planul formal

`query_plan` reprezintă sensul formal al întrebării și va fi executat automat pe knowledge graph.

- `start_node_ids` conține punctele de pornire.
- `predicates` conține relațiile traversate, în ordine.
- `intermediate_node_ids` conține nodurile intermediare, în ordine.
- `expected_result_ids` trebuie să coincidă cu rezultatul declarat în `answer.node_ids` sau `answer.ordered_node_ids`.
- `required_hops` trebuie să fie egal cu numărul real de muchii parcurse.
- Toate perechile consecutive din `evidence.path_node_ids` trebuie să fie conectate prin muchiile declarate.

## Situație imposibilă

Dacă un slot nu poate fi satisfăcut din graful furnizat, nu inventa informații. Returnează pentru acel slot:

```json
{
  "slot_id": "SLOT_XX",
  "blueprint_id": "...",
  "status": "impossible",
  "reason": "Explicație factuală despre relațiile sau nodurile care lipsesc."
}
```

Nu înlocui slotul imposibil cu o întrebare din altă categorie.

## Formatul obligatoriu al rezultatului

Returnează exclusiv un obiect JSON valid. Nu folosi blocuri Markdown și nu scrie explicații înainte sau după JSON.

```json
{
  "benchmark_id": "valoarea din TASK_MANIFEST",
  "task": "question_generation",
  "graph_version": "valoarea din TASK_MANIFEST",
  "questions": [
    {
      "question_id": "Q_001",
      "slot_id": "SLOT_01",
      "blueprint_id": "FACT_1HOP",
      "status": "generated",
      "question_text": "Textul exact al întrebării?",
      "answer": {
        "answer_type": "entity",
        "text": "Răspunsul exact propus.",
        "node_ids": ["NODE_ID"],
        "ordered_node_ids": []
      },
      "query_plan": {
        "start_node_ids": ["NODE_ID"],
        "predicates": ["predicate"],
        "intermediate_node_ids": [],
        "expected_result_ids": ["NODE_ID"]
      },
      "evidence": {
        "node_ids": ["NODE_ID", "NODE_ID"],
        "edge_ids": ["EDGE_ID"],
        "path_node_ids": ["NODE_ID", "NODE_ID"]
      },
      "scope": {
        "chapter_ids": ["CH_01"]
      },
      "declared_difficulty": {
        "level": 1,
        "required_hops": 1,
        "required_nodes": 2,
        "chapters_involved": 1
      }
    }
  ]
}
```

## Verificare înainte de răspuns

Înainte de a returna JSON-ul, verifică intern:

1. că ai produs exact un rezultat pentru fiecare slot;
2. că toate identificatoarele există în `GRAPH_PACKET`;
3. că toate muchiile declarate conectează nodurile indicate;
4. că `expected_result_ids` coincide cu răspunsul;
5. că numărul de hop-uri este corect;
6. că blueprint-ul este respectat;
7. că întrebările nu sunt duplicate;
8. că nu ai folosit informații externe;
9. că rezultatul este JSON valid.

## Datele experimentului

### TASK_MANIFEST

{{TASK_MANIFEST}}

### QUESTION_BLUEPRINTS

{{QUESTION_BLUEPRINTS}}

### GRAPH_PACKET

{{GRAPH_PACKET}}
