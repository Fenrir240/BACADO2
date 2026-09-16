# Prompt Qwen — trei întrebări high-hop despre evoluția personajelor

Ești un generator controlat de întrebări din knowledge graph-ul operei declarate în `GRAPH_PACKET.metadata.work_title`. Lucrează exclusiv cu `GRAPH_PACKET`, fără cunoștințe din memorie sau surse externe.

## Sarcina

Generează exact **3 întrebări despre evoluția unor personaje** de-a lungul narațiunii.

## Selecția deterministă obligatorie

`GRAPH_PACKET.selection.question_slots` conține exact cele trei sloturi, în ordinea răspunsului.
Pentru fiecare slot, copiază exact `slot_id` în `question_id` și folosește exclusiv
`allowed_node_ids`, `allowed_edge_ids` și `chapter_ids` din acel slot. Personajul este fixat
prin `anchor_node_ids`, iar etapele sunt fixate prin `event_ids`. Nu alege alt personaj.
`hop_profile` trebuie să respecte `hop_bounds` al slotului, care are prioritate față de profilul generic.

O întrebare trebuie să urmărească o succesiune coerentă de stări sau evenimente care schimbă situația personajului: obiective, relații, poziție socială, stare afectivă, câștiguri, pierderi sau conflicte.

## Profilul high-hop

- între 4 și 8 hop-uri reale relevante;
- între 5 și 10 noduri distincte;
- minimum două evenimente transformatoare;
- minimum două capitole;
- cel puțin o muchie `changes_state_of` sau o legătură explicită între personaj și evenimentele transformatoare;
- traseul trebuie să aibă un început, o transformare și un rezultat final.

Poți folosi stările de deschidere/închidere ale capitolelor și atributele `state_transitions`, `immediate_effects` și `long_term_effects`. Atributele se declară separat și nu se numără ca hop-uri.

## Diversitatea obligatorie

- folosește trei personaje diferite;
- cel puțin o întrebare trebuie să urmărească o evoluție socială sau materială;
- cel puțin una trebuie să urmărească o evoluție afectivă ori relațională;
- cel puțin una trebuie să urmărească degradarea, pierderea sau schimbarea unui obiectiv.

## Reguli pentru high-hop coerent

- Fiecare eveniment inclus trebuie să schimbe sau să explice evoluția personajului.
- Nu adăuga apariții episodice doar pentru a atinge pragul de hop-uri.
- Nu folosi dus-întors `has_participant`/`participates_in`.
- Nu repeta același nod și nu număra de două ori aceeași legătură semantică.
- Traseul trebuie să poată fi rezumat într-o întrebare naturală de maximum 40 de cuvinte.
- Dacă pragul high-hop produce o întrebare lipsită de sens, returnează `impossible`; nu construi o „abominație” tehnică.

## Reguli de formulare

- 10-40 de cuvinte, cu diacritice și `?`.
- Formularea trebuie să precizeze personajul și criteriul evoluției.
- Fără opinii libere; se cer numai schimbări reprezentate în graf.
- Răspunsul trebuie să prezinte etapele în ordine narativă.

## Format JSON obligatoriu

```json
{
  "task": "question_generation",
  "category_id": "CHARACTER_EVOLUTION",
  "graph_version": "valoarea din GRAPH_PACKET.metadata.version",
  "questions": [
    {
      "question_id": "EVOLUTION_01",
      "status": "generated",
      "question_text": "Cum evoluează ... de la ... la ...?",
      "answer": {
        "text": "...",
        "node_ids": ["..."],
        "ordered_node_ids": ["EV_...", "EV_...", "EV_..."]
      },
      "evidence": {
        "node_ids": ["..."],
        "edge_ids": ["..."],
        "paths": [{"node_ids": ["..."], "edge_ids": ["..."], "predicates": ["..."]}],
        "attribute_paths": [
          {"node_id": "EV_...", "json_path": "attributes.state_transitions", "value_used": "..."}
        ],
        "chapter_ids": ["CH_...", "CH_..."]
      },
      "hop_profile": {
        "class": "highhop",
        "total_edge_hops": 6,
        "longest_continuous_path_hops": 6,
        "distinct_evidence_nodes": 7,
        "chapters_involved": 3
      },
      "declared_difficulty": 3
    }
  ]
}
```

Returnează exclusiv JSON valid. Un slot imposibil rămâne în listă cu `status: "impossible"` și `reason`.

## Verificare internă

Verifică identitatea personajului în toate etapele, ordinea evenimentelor, legăturile de stare, numărul real de hop-uri și contribuția fiecărui nod la răspuns.

În fiecare slot, `focus_event_id` este evenimentul-subiect principal al întrebării. Celelalte `event_ids` sunt context sau etape necesare și nu trebuie transformate în subiecte alternative.

## GRAPH_PACKET

{{GRAPH_PACKET}}
