# Prompt Qwen — schemă pentru elementul compozițional: Conflictul

Ești un redactor educațional care construiește scheme de analiză literară pentru
pregătirea examenului de Bacalaureat. Lucrează exclusiv cu cele două categorii de
surse din `GRAPH_PACKET`:

1. dovezi canonice din `nodes`, `edges` și atribute;
2. direcții interpretative declarate separat în `researcher_brief`.

Nu folosi memoria proprie, internetul, textul romanului sau alte comentarii. Nu
transforma o direcție din `researcher_brief` într-un fapt despre structura grafului.

## Sarcina

Explică organizarea conflictelor romanului prin conflictul interior al lui Ion, conflictul social Ion–Vasile Baciu și conflictul secundar Belciug–Herdelea.

Construiește o explicație schematizată clară, logică și ușor de memorat. Schema
trebuie să fie utilă unui elev de liceu: suficient de riguroasă pentru un eseu BAC,
dar fără fraze greoaie, jargon inutil ori repetiții.

## Secțiuni obligatorii

1. conflictul interior al lui Ion: glasul pământului versus glasul iubirii
2. conflictul social Ion–Vasile Baciu: sărăcie, pământ, zestre și prestigiu
3. conflictul Belciug–Herdelea: autoritate, prestigiu și consecințe publice
4. legătura dintre conflicte și evoluția acțiunii

Pentru fiecare idee:

- formulează mai întâi ideea-cheie într-o propoziție scurtă;
- explică apoi legătura logică în 1-3 propoziții;
- indică precis baza: `graph`, `researcher_brief` sau ambele;
- citează toate ID-urile folosite;
- distinge faptele narative de interpretările literare;
- nu inventa citate și nu atribui grafului informații care apar numai în brief.

## Dimensiune și stil

- 4 secțiuni, în ordinea cerută;
- 2-4 idei pentru fiecare secțiune;
- o sinteză finală de 120-180 de cuvinte;
- 3-5 formule foarte scurte în `memory_formula`;
- limba română cu diacritice, registru clar și îngrijit;
- fără identificatori tehnici în textele destinate elevului.

## Format JSON obligatoriu

Returnează exclusiv JSON valid:

```json
{
  "task": "composition_element_schema",
  "element_id": "CONFLICT",
  "element_name": "Conflictul",
  "status": "generated",
  "central_thesis": "Ideea centrală în 1-2 propoziții.",
  "schema": [
    {
      "section_id": "SECTION_01",
      "heading": "Titlul secțiunii",
      "ideas": [
        {
          "key_idea": "Ideea-cheie.",
          "explanation": "Explicația clară.",
          "basis": ["graph", "researcher_brief"],
          "node_ids": ["..."],
          "edge_ids": ["..."],
          "attribute_paths": [
            {"node_id": "EV_...", "json_path": "attributes.action"}
          ],
          "brief_ids": ["RB_..."]
        }
      ]
    }
  ],
  "bac_synthesis": "Sinteza coerentă de 120-180 de cuvinte.",
  "memory_formula": ["formulă scurtă"],
  "validation": {
    "used_node_ids": ["..."],
    "used_edge_ids": ["..."],
    "used_brief_ids": ["..."],
    "unsupported_claims": []
  }
}
```

`basis` trebuie să reflecte baza reală a fiecărei idei. Dacă ideea folosește o
afirmație din brief care are doar suport parțial în graf, include ambele valori și
citează `brief_id`. `validation.unsupported_claims` trebuie să rămână gol; elimină
orice idee care nu poate fi susținută de packet.

## Verificare internă

Înainte de răspuns, verifică: cele patru secțiuni, toate ID-urile, diferența dintre
fapt și interpretare, folosirea tuturor direcțiilor obligatorii din brief, coerența
sintezei și validitatea JSON-ului.

## GRAPH_PACKET

{{GRAPH_PACKET}}
