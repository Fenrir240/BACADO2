# Prompt Qwen — trei întrebări despre cauză și consecință

Ești un generator controlat de întrebări din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Folosește numai informațiile din `GRAPH_PACKET`.

## Particularitatea grafului

Graful poate reprezenta cauzalitatea atât prin muchii (`causes`, `contributes_to`, `enables`, `results_in`), cât și prin atributele evenimentelor:

- `attributes.causes`;
- `attributes.motivations`;
- `attributes.preconditions`;
- `attributes.immediate_effects`;
- `attributes.long_term_effects`.

Citirea unui atribut nu este hop. Declară fiecare atribut utilizat în `evidence.attribute_paths`, împreună cu valoarea exactă folosită.

## Sarcina

Generează exact **3 întrebări despre cauze, motivații și consecințe**.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Urmărește numai
`event_ids` și relațiile alocate. Nu alege alt lanț cauzal.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

## Profilul mid-hop

- între 2 și 6 hop-uri reale;
- între 3 și 8 noduri distincte;
- cel puțin o relație cauzală sau un atribut cauzal relevant;
- maximum trei capitole;
- fiecare traseu trebuie să formeze un lanț cauzal inteligibil.

## Diversitatea obligatorie

1. o întrebare despre cauza sau motivația directă a unui eveniment;
2. o întrebare despre consecința directă ori pe termen lung;
3. o întrebare despre un lanț cauzal cu minimum două etape.

## Reguli de logică

- Nu confunda ordinea temporală cu relația cauzală: faptul că A apare înainte de B nu dovedește singur că A cauzează B.
- Nu folosi `expresses_theme` ca relație cauzală.
- Nu adăuga o cauză din interpretarea proprie.
- Nu concatena evenimente fără legătură pentru a obține high-hop artificial.
- Fiecare hop și atribut trebuie să contribuie la explicația răspunsului.
- Dacă lanțul cauzal nu este suficient de clar, returnează slotul ca imposibil.

## Reguli lingvistice

- 7-35 de cuvinte și semnul `?`.
- Întrebările trebuie să fie naturale și adecvate unui elev.
- Fără ID-uri tehnice, opinii sau răspuns sugerat în întrebare.
- Răspunsul trebuie să diferențieze cauza, evenimentul și consecința.

## Format JSON obligatoriu

```json
{
  "task": "question_generation",
  "category_id": "CAUSE_EFFECT",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "CAUSE_01",
      "status": "generated",
      "question_text": "...?",
      "answer": {
        "text": "...",
        "node_ids": ["..."],
        "ordered_node_ids": ["..."]
      },
      "evidence": {
        "node_ids": ["..."],
        "edge_ids": ["..."],
        "paths": [{"node_ids": ["..."], "edge_ids": ["..."], "predicates": ["..."]}],
        "attribute_paths": [
          {"node_id": "EV_...", "json_path": "attributes.causes", "value_used": "..."}
        ],
        "chapter_ids": ["..."]
      },
      "hop_profile": {
        "class": "midhop",
        "total_edge_hops": 4,
        "longest_continuous_path_hops": 4,
        "distinct_evidence_nodes": 5,
        "chapters_involved": 2
      },
      "declared_difficulty": 2
    }
  ]
}
```

Returnează exclusiv JSON valid. Pentru imposibilitate folosește `status: "impossible"` și `reason`.

## Verificare internă

Verifică exactitatea valorilor din atribute, existența muchiilor, direcția cauzală, continuitatea traseului și lipsa padding-ului semantic.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
