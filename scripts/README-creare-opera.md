# Automatizarea completă a unei opere

Comanda unică este:

```powershell
.\venv\Scripts\python.exe scripts\creeaza_opera.py "cale\catre\graf-opera curenta.json"
```

Calea trebuie pusă între ghilimele dacă numele grafului conține spații. Numele
fișierului poate avea forma `graf-opera curenta.json`, însă titlul și autorul sunt
citite din knowledge graph.

## Ce construiește

Scriptul rulează automat, în această ordine:

1. `Înțelege opera` — rezumate pe capitole și personaje pentru proză, respectiv
   text pe tablouri, voci lirice și imagini pentru poezie; în ambele cazuri sunt
   generate curentul literar, secvențele și elementele compoziționale;
2. `Testare rapidă` — implicit patru loturi, adică 96 de întrebări, plus toate
   băncile de flashcarduri și exerciții pentru UI;
3. `Construiește eseul` — schema integrală bazată pe eseul-model;
4. înregistrarea operei în `data/works.json`, astfel încât să apară în aplicație.

Eseul-model este găsit automat în `sources`, în intrarea cu
`source_type: "model_essay"`. Același eseu-model stabilește exact cele două
trăsături explicate la „Înțelege opera” și folosite la „Construiește eseul”, astfel
încât secțiunile să fie coerente. Pentru proză, knowledge graph-ul trebuie să conțină
capitole, evenimente, personaje și cel puțin două evenimente cu `evidence_quote`
verbatim. Pentru poezie trebuie să conțină strofe, secvențe lirice și vocile/planurile
poetice relevante. Ambele variante declară eseul-model în `sources`.

Graful primit nu este modificat. O copie canonică este păstrată în:

```text
data/generated_works/<work_id>/knowledge-graph.json
```

Toate apelurile folosesc implicit `qwen/qwen3.7-flash` și o singură încercare per
sarcină; fișa lirică folosește reasoning `none`, iar băncile `medium`. Pentru o operă
epică cu 13 capitole sunt planificate
51 de apeluri Qwen: 18 pentru „Înțelege opera”, 32 pentru cele 96 de întrebări și
unul pentru „Construiește eseul”. Pentru o operă lirică sunt planificate 6 apeluri:
un apel pentru fișa pedagogică-sursă și cinci apeluri separate pentru flashcarduri și
fiecare tip de exercițiu. Lectura pe tablouri, curentul
literar, vocile, imaginile și schemele compoziționale sunt derivate din sursele deja
validate, iar secvențele relevante și blueprint-ul sunt extrase direct din eseul-model.
Toate artefactele sunt validate într-o zonă de staging înainte de publicare.

## Rerulare sigură

O rerulare normală detectează secțiunile deja finalizate și nu mai generează încă
96 de întrebări. Opera este înregistrată idempotent, fără duplicate.

Pentru a regenera intenționat toate cele trei secțiuni:

```powershell
.\venv\Scripts\python.exe scripts\creeaza_opera.py "cale\catre\graf-opera curenta.json" --force
```

`--force` produce încă patru loturi de întrebări și suprascrie artefactele publicate
cu cele mai noi variante, păstrând directoarele istorice ale rulărilor.

Pentru verificarea planului fără apeluri API și fără înregistrarea operei:

```powershell
.\venv\Scripts\python.exe scripts\creeaza_opera.py "cale\catre\graf-opera curenta.json" --dry-run
```

Manifestul final este:

```text
data/generated_works/<work_id>/manifest.json
```

La finalul comenzii sunt afișate costul rulării curente, costul total acumulat
pentru operă și tokenurile consumate. Sumele sunt cele raportate efectiv de
OpenRouter prin `usage.cost`, în USD. Defalcarea pe cele trei secțiuni și istoricul
cumulativ sunt păstrate în:

```text
data/generated_works/<work_id>/cost-report.json
```

O rerulare care sare peste toate secțiunile are costul curent zero. O rulare cu
`--force` adaugă costurile noilor apeluri la totalul istoric, fără să dubleze
rulările anterioare.

Dacă aplicația este deja pornită, reîncarcă pagina după finalizarea scriptului pentru
ca noua operă să apară în meniul lateral.
