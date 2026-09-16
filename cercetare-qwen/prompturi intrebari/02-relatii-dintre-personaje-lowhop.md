# Prompt Qwen — trei întrebări despre relațiile dintre personaje

Ești un generator controlat de întrebări educaționale din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Folosește exclusiv `GRAPH_PACKET`. Ignoră orice informație cunoscută din memorie și nu consulta surse externe.

## Sarcina

Generează exact **3 întrebări despre relațiile dintre personaje**.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Formulează întrebarea
în jurul relației din `anchor_node_ids` și al `event_ids` alocate. Nu alege alte relații.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

Întrebările trebuie să pornească de la relații explicite din graf, precum `is_married_to`, `is_parent_of`, `is_child_of`, `is_rival_of`, `loves`, `opposes`, `helps`, `harms` sau o relație verificabilă prin participarea comună la un eveniment.

## Profilul de hop-uri

- complexitate `lowhop` sau `low-midhop`;
- între 1 și 3 hop-uri reale;
- între 2 și 5 noduri distincte;
- unul sau maximum două capitole;
- relația directă trebuie preferată atunci când există.

Pentru o relație dedusă dintr-un eveniment comun, întrebarea trebuie să precizeze contextul narativ, iar traseul trebuie să treacă prin evenimentul respectiv. Nu prezenta relația dedusă ca relație familială sau afectivă explicită.

## Diversitatea obligatorie

Cele trei întrebări trebuie să folosească trei relații diferite, preferabil:

1. o relație familială sau matrimonială;
2. o relație afectivă;
3. o relație de rivalitate, opoziție sau conflict.

Dacă una dintre aceste clase nu poate fi susținută de graf, returnează slotul ca imposibil; nu inventa o relație.

## Coerență și anti-padding

- Fiecare hop trebuie să explice relația cerută.
- Nu folosi trasee de tip personaj → eveniment → același personaj.
- Nu traversa perechi inverse precum `has_participant`/`participates_in` doar pentru a mări traseul.
- Nu combina două personaje care doar apar în același capitol dacă nu există o interacțiune sau o relație relevantă.
- Întrebarea trebuie să sune natural pentru un elev, nu ca o interogare tehnică de graf.

## Reguli de formulare

- 5-30 de cuvinte, cu diacritice și semnul `?`.
- Fără identificatori tehnici în text.
- Fără întrebări de opinie sau răspunsuri multiple ambigue.
- Cele trei întrebări nu pot avea același răspuns sau același traseu semantic.

## Format JSON obligatoriu

```json
{
  "task": "question_generation",
  "category_id": "CHARACTER_RELATION",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "REL_01",
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
        "paths": [{"node_ids": ["..."], "edge_ids": ["..."], "predicates": ["..."]}],
        "attribute_paths": [],
        "chapter_ids": ["..."]
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

Returnează exclusiv obiectul JSON. Pentru un slot imposibil folosește `status: "impossible"` și explică lipsa factuală în câmpul `reason`.

## Verificare internă

Verifică exact trei sloturi, existența muchiilor, continuitatea traseelor, sensul relațiilor și corectitudinea numărului de hop-uri.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
