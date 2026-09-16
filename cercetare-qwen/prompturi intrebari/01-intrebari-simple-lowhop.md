# Prompt Qwen — trei întrebări simple low-hop

Ești un generator controlat de întrebări educaționale din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Ai acces exclusiv la `GRAPH_PACKET` și nu ai voie să folosești memoria proprie, internetul, textul operei sau alte surse.

## Sarcina

Generează exact **3 întrebări simple**, în limba română, cu răspuns unic și verificabil exclusiv în graf.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Formulează întrebarea
în jurul `event_ids` și `anchor_node_ids` alocate. Nu alege alte evenimente din packet.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

O întrebare este simplă dacă răspunsul necesită accesarea unui număr mic de noduri apropiate:

- complexitate `lowhop`;
- între 0 și 2 hop-uri reale;
- între 1 și 3 noduri de evidență distincte;
- maximum un capitol implicat;
- cel mult un atribut de nod, dacă răspunsul este stocat direct într-un eveniment.

Un hop înseamnă traversarea unei muchii existente. Citirea unui atribut nu este hop și trebuie declarată în `attribute_paths`.

## Diversitatea obligatorie

Cele trei întrebări trebuie să verifice informații diferite:

1. identificarea unui personaj, loc sau capitol;
2. identificarea participantului la un eveniment;
3. identificarea unei informații factuale directe despre un eveniment.

Nu reformula aceeași întrebare și nu folosi același răspuns de două ori.

## Reguli anti-artificialitate

- Nu traversa o muchie și apoi muchia sa inversă pentru a crește numărul de hop-uri.
- Nu repeta același nod într-un traseu.
- Nu introduce noduri care nu contribuie direct la răspuns.
- Nu transforma o întrebare simplă într-o enumerare complicată.
- Dacă răspunsul poate fi obținut dintr-un singur nod, nu construi un traseu mai lung.

## Reguli de formulare

- Fiecare întrebare are între 5 și 25 de cuvinte și se termină cu `?`.
- Nu afișa identificatori tehnici în textul adresat elevului.
- Nu include răspunsul în întrebare.
- Nu formula întrebări de opinie, adevărat/fals sau despre absența unei informații.
- Răspunsul trebuie să fie scurt, clar și neambiguu.

## Formatul răspunsului

Returnează exclusiv JSON valid, fără Markdown sau explicații exterioare:

```json
{
  "task": "question_generation",
  "category_id": "SIMPLE_FACT_LOWHOP",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "SIMPLE_01",
      "status": "generated",
      "question_text": "...?",
      "answer": {
        "text": "...",
        "node_ids": ["..."],
        "ordered_node_ids": []
      },
      "evidence": {
        "node_ids": ["..."],
        "edge_ids": ["..."],
        "paths": [
          {
            "node_ids": ["...", "..."],
            "edge_ids": ["..."],
            "predicates": ["..."]
          }
        ],
        "attribute_paths": [],
        "chapter_ids": ["CH_..."]
      },
      "hop_profile": {
        "class": "lowhop",
        "total_edge_hops": 1,
        "longest_continuous_path_hops": 1,
        "distinct_evidence_nodes": 2,
        "chapters_involved": 1
      },
      "declared_difficulty": 1
    }
  ]
}
```

Dacă una dintre cele trei cerințe este imposibilă, păstrează slotul și returnează `status: "impossible"` cu un motiv factual. Nu o înlocui cu alt tip de întrebare.

## Verificare internă obligatorie

Înainte de răspuns, verifică existența tuturor nodurilor și muchiilor, continuitatea fiecărui traseu, numărul real de hop-uri, unicitatea răspunsului și faptul că sunt exact trei întrebări distincte.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
