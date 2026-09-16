# Prompt Qwen — trei întrebări despre acțiunea narativă

Ești un generator controlat de întrebări din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Folosește numai `GRAPH_PACKET`; nu utiliza memoria, internetul, textul integral sau rezumate externe.

## Sarcina

Generează exact **3 întrebări despre acțiune**: ce face un personaj, cine realizează o acțiune sau ce se întâmplă într-un moment precis al narațiunii.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Formulează întrebarea
numai despre `event_ids` alocate. Nu alege alte acțiuni din packet.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

## Profilul de complexitate

- complexitate `lowhop` sau `low-midhop`;
- între 1 și 3 hop-uri reale;
- între 2 și 5 noduri distincte;
- un singur eveniment central pentru fiecare întrebare;
- maximum două evenimente auxiliare, numai dacă sunt necesare pentru context.

Poți utiliza nodul `NarrativeEvent`, muchiile de participare, capitolul, locul și câmpurile `action` sau `canonical_description`. Accesarea unui atribut nu este hop și trebuie consemnată în `attribute_paths`.

## Diversitatea obligatorie

1. o întrebare de tip „cine realizează acțiunea?”;
2. o întrebare de tip „ce face personajul într-un context precis?”;
3. o întrebare de tip „ce eveniment se produce într-un loc sau capitol precis?”.

Folosește trei evenimente centrale diferite și, pe cât posibil, trei capitole diferite.

## Reguli de coerență

- Răspunsul trebuie să descrie acțiunea, nu interpretarea ei.
- Nu include în răspuns cauze sau consecințe care nu sunt cerute.
- Nu mări traseul prin muchii inverse, noduri repetate sau concepte tematice inutile.
- Nu formula întrebări prea generale precum „Ce se întâmplă în roman?”.
- Întrebarea trebuie să poată fi înțeleasă fără identificatori tehnici.

## Reguli lingvistice

- 5-30 de cuvinte și semnul `?`.
- Limba română cu diacritice.
- Răspuns unic sau o acțiune precis delimitată.
- Fără opinie, adevărat/fals sau informații absente din graf.

## Format JSON obligatoriu

```json
{
  "task": "question_generation",
  "category_id": "NARRATIVE_ACTION",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "ACTION_01",
      "status": "generated",
      "question_text": "...?",
      "answer": {"text": "...", "node_ids": ["..."], "ordered_node_ids": []},
      "evidence": {
        "node_ids": ["..."],
        "edge_ids": ["..."],
        "paths": [{"node_ids": ["..."], "edge_ids": ["..."], "predicates": ["..."]}],
        "attribute_paths": [
          {"node_id": "EV_...", "json_path": "attributes.action", "value_used": "..."}
        ],
        "chapter_ids": ["CH_..."]
      },
      "hop_profile": {
        "class": "lowhop",
        "total_edge_hops": 2,
        "longest_continuous_path_hops": 2,
        "distinct_evidence_nodes": 3,
        "chapters_involved": 1
      },
      "declared_difficulty": 1
    }
  ]
}
```

Returnează exclusiv JSON valid. Dacă un slot nu poate fi satisfăcut, folosește `status: "impossible"` și `reason`, fără a schimba categoria.

## Verificare internă

Verifică cele trei evenimente, participanții, atributele citate, muchiile, traseele și numărul real de hop-uri.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
