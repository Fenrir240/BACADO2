# Runner Qwen pentru întrebări și rezumate

`run_qwen_packets.py` apelează secvențial cele opt GRAPH_PACKET-uri pentru întrebări,
cele treisprezece pachete pentru rezumatele capitolelor și cele trei pachete pentru
elementele compoziționale. Fiecare rezultat este salvat imediat și poate fi
reutilizat la reluarea rulării.

## Ce se păstrează

În `rulari/<model>/<run-id>/` sunt create:

- `questions.all.json` — cele 24 de întrebări, grupate pe categorii;
- `intrebari-pe-categorii.txt` — rezultatul unic disponibil pentru fiecare categorie;
- `question-selection.json` — lotul, evenimentele rezervate și istoricul exclus;
- `inputs/question-packets/` — snapshoturile packeturilor folosite numai de această rulare;
- `raport-cost-intrebari.md` — costul total al setului de întrebări;
- `questions-cost-report.json` — costul și încercările setului într-un format prelucrabil automat;
- `raport-cost-rezumate.md` — costul total al celor 13 rezumate, inclusiv toate reluările;
- `summaries-cost-report.json` — costurile și încercările rezumatelor într-un format prelucrabil automat;
- `summaries.all.json` — prima variantă parseabilă pentru toate cele 13 capitole, indiferent de validare;
- `summaries.all.txt` — prima bucată pentru toate cele 13 capitole, cu titlul și statutul fiecăreia;
- `summaries.validated.txt` — numai rezumatele validate, gata de folosit;
- `rezumate-pe-capitole.txt` — prima bucată generată pentru fiecare dintre cele 13 capitole, cu titlul și statutul validatorului;
- `compositions.all.json` — schemele pentru titlu, incipit–final și conflict;
- `results.json` — progresul și totalurile;
- `token-usage.csv` — un rând pentru fiecare apel, inclusiv reluările;
- `raport-rulare.md` — raport lizibil, după modelul Experimentului 2;
- `manifest.json` — hash-urile exacte ale prompturilor și packeturilor;
- câte un director per sarcină, cu promptul trimis, requestul fără cheia API,
  răspunsul OpenRouter complet, textul brut, JSON-ul extras și validarea locală.

În plus, `cercetare-qwen/toate-intrebarile-pe-categorii.txt` este registrul cumulativ
al tuturor rulărilor. Este reconstruit automat după fiecare rezultat, grupează
întrebările în cele opt categorii și păstrează pentru fiecare grup lotul, rularea,
modelul și diagnosticul validării. Reconstrucția din artefacte împiedică dublarea
aceleiași categorii atunci când o rulare este doar reluată sau raportul este refăcut.
Fișierul `cercetare-qwen/toate-intrebarile.json` păstrează aceeași bancă în format
prelucrabil, inclusiv răspunsurile, dovezile, nodurile, profilul de hop-uri și
proveniența fiecărei întrebări.

Pentru fiecare rezumat parseabil, inclusiv unul respins semantic, runnerul creează și
`summaries/<capitol>/summary.txt`, care conține numai textul rezumatului. Fișierele
`rezumate-pe-capitole.txt` și `summaries.all.txt` includ prima variantă a tuturor
capitolelor. `summaries.validated.txt` rămâne separat și conține numai rezumatele care
au trecut validatorul, pentru audit.

## Protecția factuală a rezumatelor

Modelul implicit este `qwen/qwen3.7-flash`. Pentru rezumate, fiecare pachet expune
numai evenimentele verificate în textul primar, împreună cu pagina PDF sau locatorul
sursei și un citat scurt. Evenimentele interpretative sau insuficient aliniate sunt trecute
separat în `excluded_events` și nu pot fi verbalizate.

Validatorul nu mai verifică doar lista de ID-uri. El cere reproducerea exactă a
fiecărei propoziții, acoperirea unică a evenimentelor și verifică local propozițiile
față de citatele primare păstrate în pachet. Modelul nu mai recopiază citatele în output,
ceea ce reduce costul și elimină o sursă inutilă de erori de formatare. Validatorul cere
aliniere lexicală între propoziție și dovezi și respinge intensificări nesusținute
precum „instantaneu”, „definitiv”, „complet” sau „exclusiv”. Configurația implicită
folosește reasoning `medium` și maximum 12.000 de tokeni de ieșire pentru rezumate.

Pentru întrebări, configurația implicită folosește reasoning `medium` și exact un apel
per categorie. Rezultatul JSON este păstrat chiar dacă validatorul semantic găsește
probleme. Erorile validatorului rămân în `validation.json` și în metadate doar ca
diagnostic; ele nu mai produc feedback, retry sau înlocuirea rezultatului. Dacă modelul
returnează JSON imposibil de citit, răspunsul brut este tot păstrat și sarcina nu este
retrimisă automat.

La începutul fiecărei rulări noi, runnerul citește `question-selection.json` din
rulările anterioare, exclude toate evenimentele deja rezervate și construiește următorul
lot în ordinea deterministă a importanței. Rulările vechi, create înaintea acestui
mecanism, sunt recunoscute împreună drept primul lot. Selecția este rezervată înaintea
apelurilor API, astfel încât nici o rulare întreruptă să nu permită reutilizarea ei.
La epuizarea candidaților necesari unei categorii, runnerul se oprește explicit în loc
să repete în tăcere evenimente vechi.

Pentru rezumate se face exact un apel per capitol. Prima variantă JSON este păstrată și
publicată chiar dacă validatorul semantic o respinge; erorile rămân numai pentru audit.
Nu se generează feedback de corecție și nu există retry automat. La reluarea rulării,
un capitol care are deja o variantă parseabilă, validă sau invalidă, este sărit.

Raportul distinge ultima încercare a fiecărei sarcini de consumul tuturor
încercărilor facturabile. Astfel, tokenii unei reluări nu dispar din total.
Raportul separat pentru întrebări nu include costul rezumatelor sau al elementelor
compoziționale și marchează setul drept generat când au fost păstrate toate cele 8
categorii. Numărul de rezultate validate este raportat separat, fără să afecteze
păstrarea lor.

Fișierul `intrebari-pe-categorii.txt` este destinat citirii directe. El conține
răspunsul unic al fiecărei categorii și indică separat dacă validarea diagnostică a
trecut sau a semnalat probleme.

## Configurare

Copiază `config.local.env.example` ca `config.local.env` și completează cheia. Dacă
fișierul nu există, runnerul poate reutiliza cheia din
`../cercetare/experiment2/config.local.env`, dar păstrează implicit modelul Qwen.

## Comenzi

Inventar local, fără cheie și fără API:

```powershell
python cercetare-qwen/run_qwen_packets.py --plan-only
```

Verificarea disponibilității modelului:

```powershell
python cercetare-qwen/run_qwen_packets.py --preflight-only
```

Rularea completă, în ordinea 8 categorii + 13 capitole + 3 elemente compoziționale:

```powershell
python cercetare-qwen/run_qwen_packets.py
```

Doar întrebările, cu valorile implicite recomandate (`reasoning=medium`, un singur
apel per categorie):

```powershell
python cercetare-qwen/run_qwen_packets.py --tasks questions
```

Pentru mai mult reasoning, fără a activa retry-uri de validare:

```powershell
python cercetare-qwen/run_qwen_packets.py --tasks questions `
  --questions-reasoning-effort high
```

Grupurile pot fi rulate în aceeași sesiune persistentă. Prima comandă
creează folderul rulării; a doua continuă acel folder:

```powershell
python cercetare-qwen/run_qwen_packets.py --tasks questions
python cercetare-qwen/run_qwen_packets.py --resume-run <folder-rulare> --tasks summaries
```

Elementele compoziționale pot fi generate separat într-o rulare nouă:

```powershell
python cercetare-qwen/run_qwen_packets.py --tasks compositions
```

Sau unul câte unul în aceeași rulare:

```powershell
python cercetare-qwen/run_qwen_packets.py --only 01-titlul
python cercetare-qwen/run_qwen_packets.py --resume-run <folder-rulare> --only 02-relatia-incipit-final
python cercetare-qwen/run_qwen_packets.py --resume-run <folder-rulare> --only 03-conflictul
```

Rulările create înainte de adăugarea elementelor compoziționale rămân reluabile,
dar nu pot primi noile sarcini; pentru acestea se pornește o rulare nouă.

Pentru o singură sarcină, folosește cheia afișată de `--plan-only`:

```powershell
python cercetare-qwen/run_qwen_packets.py --only 01-simple-facts
```

Reluarea unei rulări întrerupte sare peste orice răspuns de întrebări deja generat,
indiferent de diagnosticul validatorului. Sunt retrimise numai categoriile fără răspuns
din cauza unei erori de apel:

```powershell
python cercetare-qwen/run_qwen_packets.py --resume-run `
  cercetare-qwen/rulari/qwen__qwen3.7-flash/run-AAAALLZZThhmmssZ
```

Reconstruirea raportului fără API:

```powershell
python cercetare-qwen/run_qwen_packets.py --resume-run <folder-rulare> --finalize-only
```

Inputurile unei rulări sunt înghețate prin hash. Dacă un prompt sau packet este
modificat, runnerul cere pornirea unei rulări noi pentru a evita amestecarea unor
rezultate obținute în condiții diferite.
