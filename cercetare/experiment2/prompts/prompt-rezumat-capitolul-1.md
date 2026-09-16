# Prompt standardizat pentru reconstruirea rezumatului capitolului I — Experimentul 2

Ești participant într-un experiment controlat de reconstruire narativă dintr-un
knowledge graph. Reconstruiește rezumatul capitolului `CH_01` folosind exclusiv
informațiile din subgraful furnizat.

Nu folosi textul original, rezumate externe, internetul, memoria despre operă sau
informații care nu apar în graf. Dacă o informație lipsește, omite-o.

## Sarcina

Generează două versiuni:

1. `simple` — limbaj clar și accesibil unui elev, între 180 și 300 de cuvinte;
2. `elevated` — limbaj mai bogat, potrivit pregătirii pentru Bacalaureat, între
   220 și 350 de cuvinte.

Versiunile trebuie să păstreze aceeași bază factuală. Varianta elevată poate schimba
vocabularul și ritmul, dar nu poate adăuga fapte, motivații sau interpretări inexistente.

## Selectarea și ordonarea informației

- Include toate evenimentele `major`.
- Include evenimentele `medium` necesare continuității.
- Folosește evenimentele `supporting` numai dacă explică un eveniment important.
- Respectă ordinea din `event_sequence` și relațiile temporale explicite.
- Prezintă cauza înaintea consecinței.
- Introdu personajul înaintea pronumelui care îl înlocuiește.
- Nu combina evenimente cu participanți sau cauze incompatibile.
- Nu transforma o interpretare într-un fapt.

## Profil stilistic obligatoriu

Respectă marjele din `SUMMARY_MANIFEST.style_constraints`. Acestea sunt intervale,
nu ținte exacte. Nu sacrifica gramatica sau fidelitatea factuală pentru un procent.

În mod special:

- nu introduce un conector pentru fiecare muchie ori eveniment din graf;
- folosește un conector numai pentru o relație temporală, cauzală, concesivă sau
  pentru o schimbare de scenă care altfel ar fi neclară;
- evită formulele de umplutură precum „de asemenea”, „mai apoi”, „în continuare”,
  „în acest context” și „în ceea ce privește”;
- nu începe propoziții consecutive cu formule de tranziție;
- alternează natural numele personajelor și pronumele, fără repetiție mecanică;
- preferă acțiunile și relațiile concrete unor tranziții decorative;
- prepozițiile și conjuncțiile necesare gramatical nu trebuie eliminate.

Nu raporta tu procentele. Evaluatorul le recalculează direct din `summary_text`.

## Trasabilitatea propozițiilor

Returnează fiecare propoziție separat cu:

- `sentence_index` consecutiv, începând de la 1;
- textul exact;
- evenimentele folosite;
- nodurile suplimentare;
- muchiile folosite;
- afirmațiile formale `subject → predicate → object` care o susțin.

Toate ID-urile și toate tripletele trebuie să existe în subgraf. ID-urile tehnice
apar numai în dovezi, nu în textul rezumatului.

Pentru fiecare versiune, `summary_text` trebuie să fie concatenarea, în ordine, a
valorilor `sentences[].text`. `used_event_ids` trebuie să urmeze prima apariție în
rezumat. Un eveniment nu poate fi simultan folosit și omis.

## Formatul rezultatului

Returnează exclusiv un obiect JSON valid, fără Markdown și fără explicații exterioare:

```json
{
  "benchmark_id": "valoarea din SUMMARY_MANIFEST",
  "task": "chapter_summary_reconstruction",
  "graph_version": "valoarea din SUMMARY_MANIFEST",
  "chapter_id": "CH_01",
  "summaries": {
    "simple": {
      "register": "simple",
      "summary_text": "Textul integral.",
      "word_count": 0,
      "used_event_ids": ["EV_001"],
      "omitted_event_ids": [],
      "omissions": [],
      "sentences": [
        {
          "sentence_index": 1,
          "text": "Textul exact al propoziției.",
          "event_ids": ["EV_001"],
          "supporting_node_ids": ["NODE_ID"],
          "edge_ids": ["EDGE_ID"],
          "claims": [
            {"subject": "NODE_ID", "predicate": "predicate", "object": "NODE_ID"}
          ]
        }
      ]
    },
    "elevated": {
      "register": "elevated",
      "summary_text": "Textul integral.",
      "word_count": 0,
      "used_event_ids": ["EV_001"],
      "omitted_event_ids": [],
      "omissions": [],
      "sentences": [
        {
          "sentence_index": 1,
          "text": "Textul exact al propoziției.",
          "event_ids": ["EV_001"],
          "supporting_node_ids": ["NODE_ID"],
          "edge_ids": ["EDGE_ID"],
          "claims": [
            {"subject": "NODE_ID", "predicate": "predicate", "object": "NODE_ID"}
          ]
        }
      ]
    }
  }
}
```

## Verificare înaintea răspunsului

Verifică intern că ambele versiuni există, că toate evenimentele majore sunt incluse,
că ordinea și cauzalitatea sunt păstrate, că fiecare propoziție are dovezi valide,
că limitele de cuvinte și marjele stilistice sunt respectate și că rezultatul este JSON.

## SUMMARY_MANIFEST

{{SUMMARY_MANIFEST}}

## CHAPTER_01_GRAPH_PACKET

{{CHAPTER_01_GRAPH_PACKET}}
