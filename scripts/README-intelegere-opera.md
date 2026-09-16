# Automatizare — Înțelege opera

Comanda stabilă pentru o operă nouă este:

```powershell
.\venv\Scripts\python.exe scripts\intelegere_opera.py --graph "cale\catre\knowledge-graph.json"
```

Graful declară automat calea eseului-model în `sources`, printr-o intrare cu
`source_type: "model_essay"`. El trebuie să declare și opera, autorul, capitolele,
evenimentele, personajele și relațiile. Pentru secvențele relevante,
cel puțin două evenimente trebuie să aibă `evidence_quote` preluat din textul integral.

Pipeline-ul execută, în ordine:

1. generează cu Qwen câte un rezumat pentru fiecare capitol;
2. construiește determinist cele două mind-mapuri de personaje;
3. cere Qwen să selecteze numai ID-urile a două secvențe relevante;
4. construiește textul secvențelor exclusiv din `evidence_quote` din graf;
5. determină curentul literar și explică exact cele două trăsături argumentate
   în eseul-model, cu dovezi din operă;
6. generează schemele pentru relația incipit–final, conflict și titlu.

Knowledge graph-ul este tratat exclusiv ca sursă read-only: pipeline-ul nu îl modifică,
nu adaugă noduri și nu adaugă muchii. Materialul despre curent este publicat numai în
`curent-literar.json`.

Toate apelurile folosesc implicit `qwen/qwen3.7-flash` cu reasoning `medium`.
Fiecare sarcină are o singură încercare. Un rezultat care nu trece validarea locală
este păstrat ca primă variantă și nu produce regenerări. Validarea este diagnostică.
Pentru cele două trăsături, validarea verifică și existența în eseul-model a câte
unui fragment textual justificativ returnat de Qwen.

Qwen nu generează textul secvențelor relevante. Modelul selectează doar ID-uri,
iar pasajele afișate sunt copiate determinist din dovezile verbatim ale grafului.

## Fișiere publicate

```text
data/generated_works/<work_id>/intelegere-opera/
├── rezumat-pe-capitole.md
├── rezumat-pe-capitole.json
├── personaje-mindmaps.json
├── secvente-relevante.json
├── curent-literar.json
├── elemente-compozitionale.json
├── manifest.json
└── */runs/ sau *-runs/
```

UI-ul încarcă automat aceste fișiere pentru opera selectată. Profesorul AI și
dicționarul din toate cele cinci subsecțiuni primesc automat titlul, autorul și
contextul operei curente.

Pentru verificarea planului fără apeluri API:

```powershell
.\venv\Scripts\python.exe scripts\intelegere_opera.py --graph "cale\catre\knowledge-graph.json" --dry-run
```
