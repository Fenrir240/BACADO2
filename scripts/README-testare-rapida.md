# Pipeline „Testare rapidă”

Scriptul `testare_rapida.py` este punctul unic de intrare pentru partea de exerciții a
unei opere. Primește knowledge graph-ul, derivă automat titlul, autorul și `work_id`,
apelează Qwen pentru banca de întrebări și construiește fișierele consumate direct de UI.

## Comanda standard

Din rădăcina proiectului:

```powershell
.\venv\Scripts\python.exe scripts\testare_rapida.py --graph "cale\catre\knowledge-graph.json"
```

Implicit sunt generate **96 de întrebări**: patru loturi a câte 24, cu trei întrebări
în fiecare dintre cele opt categorii. Sunt făcute 32 de apeluri Qwen, fiecare exact o
singură dată. `reasoning` este `medium`.

Opțiunea `--batches` rămâne disponibilă doar dacă dorești în mod explicit alt număr de loturi:

```powershell
.\venv\Scripts\python.exe scripts\testare_rapida.py --graph "cale\catre\knowledge-graph.json" --batches 2
```

Aceasta planifică 48 de întrebări. Istoricul se păstrează în
`data/generated_works/<work_id>/testare-rapida/selection-history.json`. La o nouă
execuție pentru aceeași operă, evenimentele rezervate anterior sunt excluse înaintea
selecției; nu sunt reluate de la început.

## Artefacte create

- proiectul sursă: `data/generated_works/<work_id>/testare-rapida/`;
- banca JSON cumulativă: `questions.json`;
- varianta TXT pe categorii: `questions-by-category.txt`;
- flashcarduri UI: `data/flashcards/<work_id>.json`;
- grile, cronologii, completări și asocieri:
  `data/exercises/<work_id>/*.json`;
- contractul rezultatului: `manifest.json`.

Validarea locală este strict informativă pentru întrebări. Un răspuns JSON primit de la
Qwen este păstrat chiar dacă nu trece regulile validatorului. Nu există regenerare,
retry sau al doilea apel pentru o sarcină invalidă. Numai răspunsurile marcate explicit
`impossible` sau fără enunț/răspuns nu pot deveni exerciții, dar rămân în arhiva sursă.
Un răspuns neparsabil este de asemenea păstrat brut și reprezentat prin cele trei sloturi
cerute, după care pipeline-ul continuă; nici acesta nu produce un apel suplimentar.

Dacă furnizorul nu livrează niciun răspuns (de exemplu HTTP 502 sau timeout), aceeași
comandă reia numai sarcina de transport eșuată în același lot. Celelalte categorii sunt
reutilizate local, nu se rezervă alte evenimente și nu se repetă apelurile reușite.
Dacă un apel cu reasoning consumă întreaga limită fără să livreze text final
(`finish_reason=length`), reluarea acelei singure sarcini folosește `reasoning=none`;
modelul, packetul și evenimentele selectate rămân aceleași.

## Contract minim al grafului

Graful trebuie să respecte ontologia folosită în proiect și să conțină:

- `metadata.work`, `metadata.author` și `metadata.version` (titlul poate proveni și
  dintr-un nod `Work`, iar autorul dintr-un nod `Author`);
- listele `nodes`, `edges`, `chapters` și `ontology.assertion_types`;
- evenimente `NarrativeEvent` cu ordine globală, capitol, participanți și verificare
  `verified_primary`;
- relații temporale, cauzale, între personaje și legături către concepte literare
  suficiente pentru cele opt categorii.

Dacă o categorie nu are suficiente date, scriptul se oprește înaintea apelului Qwen și
indică exact categoria pentru care graful trebuie completat.

## Reconstrucție fără apel AI

Pentru a reconstrui doar artefactele UI dintr-o bancă existentă:

```powershell
.\venv\Scripts\python.exe scripts\testare_rapida.py `
  --graph "cale\catre\knowledge-graph.json" `
  --build-only `
  --questions "cale\catre\questions.json"
```

Pentru a verifica configurația fără scrieri sau apeluri API:

```powershell
.\venv\Scripts\python.exe scripts\testare_rapida.py --graph "cale\catre\knowledge-graph.json" --plan-only
```
