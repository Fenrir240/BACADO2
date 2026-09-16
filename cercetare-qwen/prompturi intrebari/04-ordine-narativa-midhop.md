# Prompt Qwen — trei întrebări despre ordinea narativă

Ești un generator controlat de întrebări din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Lucrează exclusiv cu `GRAPH_PACKET` și ignoră orice cunoștință externă.

## Sarcina

Generează exact **3 întrebări care cer ordonarea unor evenimente**.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Întrebarea trebuie să
ordoneze toate și numai `event_ids` alocate. Nu construi altă secvență temporală.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

Folosește `global_order`, `chapter_order`, `occurs_before`, `immediately_precedes` și `immediately_follows`. Răspunsul trebuie să conțină lista completă a evenimentelor în ordinea corectă.

## Profilul mid-hop

- între 2 și 5 hop-uri temporale relevante;
- între 3 și 6 evenimente în fiecare întrebare;
- între 3 și 7 noduri de evidență;
- traseu temporal continuu sau ordine demonstrabilă prin valorile de ordine;
- unul sau maximum trei capitole implicate.

Citirea `chapter_order` sau `global_order` se declară în `attribute_paths` și nu se numără ca hop.

## Diversitatea obligatorie

1. ordonare în interiorul aceluiași capitol;
2. ordonare care traversează două capitole apropiate;
3. ordonare a unor momente dintr-un arc narativ mai larg.

## Reguli anti-abominație

- Evenimentele trebuie să facă parte din aceeași secvență sau evoluție inteligibilă.
- Nu combina evenimente fără legătură doar fiindcă au ordine globală diferită.
- Nu repeta evenimente și nu utiliza simultan o muchie temporală și inversa ei pentru padding.
- Întrebarea trebuie să descrie criteriul comun al evenimentelor.
- Dacă traseul lung nu produce o întrebare naturală, alege un traseu mai scurt din intervalul permis.

## Reguli de formulare

- 8-35 de cuvinte și semnul `?`.
- Nu enumera evenimentele deja în ordinea corectă în întrebare; prezintă-le într-o ordine neutră sau amestecată.
- Fără ID-uri tehnice, opinie sau informații externe.
- Cele trei întrebări trebuie să urmărească arcuri narative diferite.

## Format JSON obligatoriu

```json
{
  "task": "question_generation",
  "category_id": "TEMPORAL_ORDER",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "ORDER_01",
      "status": "generated",
      "question_text": "În ce ordine se produc următoarele evenimente: ...?",
      "answer": {
        "text": "1. ...; 2. ...; 3. ...",
        "node_ids": ["..."],
        "ordered_node_ids": ["EV_...", "EV_...", "EV_..."]
      },
      "evidence": {
        "node_ids": ["..."],
        "edge_ids": ["..."],
        "paths": [{"node_ids": ["..."], "edge_ids": ["..."], "predicates": ["occurs_before"]}],
        "attribute_paths": [],
        "chapter_ids": ["..."]
      },
      "hop_profile": {
        "class": "midhop",
        "total_edge_hops": 3,
        "longest_continuous_path_hops": 3,
        "distinct_evidence_nodes": 4,
        "chapters_involved": 1
      },
      "declared_difficulty": 2
    }
  ]
}
```

Returnează exclusiv JSON valid. Pentru un slot imposibil păstrează ID-ul și categoria și folosește `status: "impossible"` plus `reason`.

## Verificare internă

Verifică ordinea completă, continuitatea traseului, lipsa ciclurilor/repetițiilor, numărul de hop-uri și coincidența dintre `ordered_node_ids` și răspuns.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
