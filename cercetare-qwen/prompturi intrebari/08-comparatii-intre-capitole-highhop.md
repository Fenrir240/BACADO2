# Prompt Qwen — trei întrebări high-hop de comparație între capitole

Ești un generator controlat de întrebări comparative din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Folosește numai `GRAPH_PACKET` și nu completa informații din memorie.

## Sarcina

Generează exact **3 întrebări care compară informații din capitole diferite**.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Compară toate și numai
ramurile din `event_ids`, după criteriul fixat de `anchor_node_ids`. Nu alege alte capitole.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

Fiecare întrebare trebuie să precizeze un criteriu unic de comparație, de exemplu:

- acțiunile sau alegerile aceluiași personaj;
- schimbarea unei relații;
- două stări narative;
- manifestarea aceleiași teme sau a aceluiași conflict;
- paralelismul ori contrastul dintre două evenimente.

## Profilul high-hop ramificat

- minimum două capitole;
- două trasee comparabile, câte unul pentru fiecare termen al comparației;
- între 5 și 10 hop-uri totale relevante;
- cel puțin 2 hop-uri pe fiecare ramură;
- între 6 și 12 noduri distincte;
- minimum două evenimente centrale diferite.

Pentru comparație, `total_edge_hops` este suma hop-urilor din ramurile distincte. `longest_continuous_path_hops` este lungimea celei mai lungi ramuri, nu suma lor.

## Diversitatea obligatorie

1. comparație privind evoluția sau acțiunile unui personaj;
2. comparație privind o relație ori un conflict;
3. comparație tematică, simbolică sau compozițională.

Folosește perechi de capitole și criterii diferite.

## Reguli pentru comparații cu sens

- Cele două ramuri trebuie să fie comparabile după același criteriu explicit.
- Nu compara evenimente doar fiindcă apar în capitole diferite.
- Răspunsul trebuie să prezinte întâi dovezile pentru fiecare capitol și apoi asemănarea sau diferența.
- Nu introduce o concluzie care nu este susținută de nodurile și muchiile declarate.
- Nu mări hop-urile prin muchii inverse, noduri repetate sau ocoluri tematice inutile.
- Dacă nu există două trasee comparabile și coerente, marchează slotul imposibil.

## Reguli lingvistice

- 12-40 de cuvinte și semnul `?`.
- Menționează în limbaj natural momentele sau capitolele comparate.
- Fără ID-uri tehnice, opinii sau întrebări excesiv de încărcate.
- Întrebarea trebuie să poată fi înțeleasă la prima citire.

## Format JSON obligatoriu

```json
{
  "task": "question_generation",
  "category_id": "CROSS_CHAPTER_COMPARE",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "COMPARE_01",
      "status": "generated",
      "question_text": "Cum diferă ... între ... și ...?",
      "comparison_criterion": "...",
      "answer": {
        "text": "...",
        "node_ids": ["..."],
        "ordered_node_ids": ["..."]
      },
      "evidence": {
        "node_ids": ["..."],
        "edge_ids": ["..."],
        "paths": [
          {"path_id": "BRANCH_A", "node_ids": ["..."], "edge_ids": ["..."], "predicates": ["..."]},
          {"path_id": "BRANCH_B", "node_ids": ["..."], "edge_ids": ["..."], "predicates": ["..."]}
        ],
        "attribute_paths": [],
        "chapter_ids": ["CH_...", "CH_..."]
      },
      "hop_profile": {
        "class": "highhop",
        "total_edge_hops": 8,
        "longest_continuous_path_hops": 4,
        "distinct_evidence_nodes": 9,
        "chapters_involved": 2
      },
      "declared_difficulty": 3
    }
  ]
}
```

Returnează exclusiv JSON valid. Pentru imposibilitate păstrează slotul cu `status: "impossible"` și `reason`.

## Verificare internă

Verifică cele două ramuri, criteriul comun, capitolele, continuitatea muchiilor, numărul real de hop-uri și faptul că răspunsul nu depășește dovezile declarate.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
