# Prompt standardizat pentru reconstruirea rezumatului capitolului I

## Instrucțiuni de utilizare

Acest prompt trebuie oferit identic tuturor modelelor evaluate.

Înlocuiește:

- `SUMMARY_MANIFEST` cu manifestul sarcinii;
- `CHAPTER_01_GRAPH_PACKET` cu subgraful capitolului I.

Subgraful trebuie să conțină toate evenimentele obligatorii ale capitolului, ordinea lor, participanții, locurile, cauzele, consecințele, stările și sursele interne grafului.

Numele modelului, versiunea, temperatura, seed-ul, data execuției și răspunsul brut trebuie înregistrate de aplicația care execută experimentul.

---

## Prompt oferit modelului

Ești participant într-un experiment controlat de reconstruire narativă dintr-un knowledge graph.

Trebuie să reconstruiești rezumatul capitolului I al romanului reprezentat de `CHAPTER_01_GRAPH_PACKET`, folosind exclusiv informațiile din acest subgraf.

Nu ai voie să folosești:

- textul original al operei;
- un rezumat extern;
- un eseu literar extern;
- informații din memoria ta;
- internetul;
- cunoștințe despre operă care nu apar în subgraf.

Chiar dacă recunoști opera, ignoră toate informațiile pe care le-ai putea cunoaște și folosește numai nodurile, muchiile și atributele furnizate.

## Sarcina

Generează două versiuni ale rezumatului pentru `CH_01`:

1. `simple` — limbaj clar și accesibil unui elev;
2. `elevated` — limbaj mai bogat și coerent, potrivit pregătirii pentru Bacalaureat.

Cele două versiuni trebuie să conțină aceleași fapte narative esențiale. Varianta elevată poate modifica vocabularul și tranzițiile, dar nu poate adăuga informații, interpretări sau relații inexistente în graf.

## Selectarea informației

- Include toate evenimentele cu `importance: "major"`.
- Include evenimentele cu `importance: "medium"` necesare pentru continuitatea acțiunii.
- Folosește evenimentele `supporting` numai dacă sunt necesare pentru înțelegerea unui eveniment major sau mediu.
- Respectă `event_sequence`, `chapter_order`, `global_order`, `immediately_precedes`, `occurs_before` și relațiile temporale echivalente.
- Prezintă cauza înaintea consecinței.
- Introdu personajele înainte de folosirea pronumelor care le înlocuiesc.
- Nu combina într-o singură afirmație evenimente care au cauze, participanți sau consecințe incompatibile.
- Nu transforma o interpretare literară într-un fapt narativ.
- Nu prezenta o motivație dedusă drept motivație explicită.
- Dacă informația necesară nu există în graf, omite-o. Nu completa golul prin presupuneri.

## Cerințe pentru varianta simplă

- Lungime: între 180 și 300 de cuvinte.
- Folosește propoziții clare și predominant directe.
- Media recomandată este de maximum 22 de cuvinte pe propoziție.
- Evită termenii academici inutili.
- Explică limpede cine realizează acțiunea.
- Folosește conectori simpli și variați.
- Nu reduce rezumatul la o enumerare mecanică de evenimente.

## Cerințe pentru varianta elevată

- Lungime: între 220 și 350 de cuvinte.
- Păstrează exact aceeași bază factuală precum varianta simplă.
- Folosește tranziții narative coerente și vocabular mai variat.
- Poți integra teme sau conflicte numai dacă acestea apar explicit ca noduri ori relații în subgraf.
- Marchează interpretările prin formulări adecvate, fără a le prezenta drept fapte certe.
- Nu adăuga detalii doar pentru efect stilistic.
- Nu copia mecanic varianta simplă prin înlocuirea câtorva cuvinte.

## Trasabilitatea fiecărei propoziții

Fiecare propoziție trebuie returnată separat și trebuie să conțină:

- indexul propoziției;
- textul exact;
- evenimentele folosite;
- nodurile suplimentare folosite;
- muchiile folosite;
- afirmațiile formale `subject → predicate → object` care susțin propoziția.

Toate afirmațiile formale trebuie să existe în subgraf. Nu declara o muchie aproximativă și nu inventa predicate.

O propoziție fără dovezi valide va fi tratată de evaluator ca afirmație nesusținută.

Identificatorii tehnici trebuie să apară numai în secțiunea de dovezi, nu în textul rezumatului.

## Evenimente folosite și omise

Pentru fiecare versiune returnează:

- `used_event_ids`, în ordinea primei apariții în rezumat;
- `omitted_event_ids`;
- pentru fiecare eveniment omis, un motiv structural scurt;
- `word_count`, calculat de tine și reverificat automat de evaluator.

Nu marca un eveniment drept folosit dacă acesta nu susține nicio propoziție.

## Formatul obligatoriu al rezultatului

Returnează exclusiv un obiect JSON valid. Nu folosi blocuri Markdown și nu scrie explicații înainte sau după JSON.

```json
{
  "benchmark_id": "valoarea din SUMMARY_MANIFEST",
  "task": "chapter_summary_reconstruction",
  "graph_version": "valoarea din SUMMARY_MANIFEST",
  "chapter_id": "CH_01",
  "summaries": {
    "simple": {
      "register": "simple",
      "summary_text": "Textul integral al rezumatului simplu.",
      "word_count": 0,
      "used_event_ids": ["EV_001"],
      "omitted_event_ids": [],
      "omissions": [],
      "sentences": [
        {
          "sentence_index": 1,
          "text": "Textul exact al primei propoziții.",
          "event_ids": ["EV_001"],
          "supporting_node_ids": ["NODE_ID"],
          "edge_ids": ["EDGE_ID"],
          "claims": [
            {
              "subject": "NODE_ID",
              "predicate": "predicate",
              "object": "NODE_ID"
            }
          ]
        }
      ]
    },
    "elevated": {
      "register": "elevated",
      "summary_text": "Textul integral al rezumatului elevat.",
      "word_count": 0,
      "used_event_ids": ["EV_001"],
      "omitted_event_ids": [],
      "omissions": [],
      "sentences": [
        {
          "sentence_index": 1,
          "text": "Textul exact al primei propoziții.",
          "event_ids": ["EV_001"],
          "supporting_node_ids": ["NODE_ID"],
          "edge_ids": ["EDGE_ID"],
          "claims": [
            {
              "subject": "NODE_ID",
              "predicate": "predicate",
              "object": "NODE_ID"
            }
          ]
        }
      ]
    }
  }
}
```

## Reguli de consistență JSON

- `summary_text` trebuie să fie concatenarea, în aceeași ordine, a valorilor `sentences[].text`.
- Fiecare `sentence_index` trebuie să fie unic, consecutiv și să înceapă de la 1.
- Fiecare ID din `used_event_ids` trebuie să apară în minimum o valoare `sentences[].event_ids`.
- Fiecare eveniment declarat în `sentences[].event_ids` trebuie să apară în `used_event_ids`.
- Un eveniment nu poate apărea simultan în `used_event_ids` și `omitted_event_ids`.
- Fiecare `edge_id` trebuie să existe în subgraf.
- Pentru fiecare afirmație, combinația `subject`, `predicate`, `object` trebuie să corespundă unei muchii existente.
- Toate nodurile trebuie să aparțină subgrafului furnizat.
- Ordinea primei apariții a evenimentelor trebuie să respecte ordinea narativă, cu excepția unei retrospective reprezentate explicit în graf.

## Verificare înainte de răspuns

Înainte de a returna JSON-ul, verifică intern:

1. că ai generat ambele versiuni;
2. că ai inclus toate evenimentele majore;
3. că evenimentele sunt în ordine;
4. că fiecare propoziție are dovezi;
5. că toate nodurile și muchiile există;
6. că toate afirmațiile formale corespund grafului;
7. că variantele respectă limitele de cuvinte;
8. că varianta elevată nu adaugă fapte;
9. că nu ai folosit informații externe;
10. că rezultatul este JSON valid.

## Datele experimentului

### SUMMARY_MANIFEST

{{SUMMARY_MANIFEST}}

### CHAPTER_01_GRAPH_PACKET

{{CHAPTER_01_GRAPH_PACKET}}
