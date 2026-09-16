# Cum rulezi un model AI în Experimentul 1

## Fișierele importante

- `config.local.env` — cheia OpenRouter și modelul ales; este ignorat de Git.
- `prepare_inputs.py` — construiește determinist subgraful capitolului I.
- `run_openrouter_experiment.py` — verifică modelul, trimite cele două cereri, salvează outputurile și acordă scorurile.
- `modele-openrouter-compatibile.md` — snapshotul modelelor cu context suficient și coada recomandată de testare.
- `inputs/question-manifest.json` — cele opt sloturi de întrebări.
- `inputs/question-blueprints.json` — regulile tipologiilor.
- `inputs/summary-manifest.json` — condițiile rezumatului.
- `../benchmark1/prompts/` — prompturile standardizate.
- `../benchmark1/scoring/evaluator.py` — evaluatorul determinist.

## Alegerea modelului

Editează numai fișierul local `config.local.env`:

```env
OPENROUTER_API_KEY=cheia_ta
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
```

Nu pune cheia între ghilimele și nu o copia în alte fișiere.

## Verificare fără cost

Din rădăcina proiectului:

```powershell
python cercetare/experiment1/run_openrouter_experiment.py --preflight-only
```

Această comandă verifică dacă cheia permite accesul la model și afișează contextul și parametrii suportați. Nu cere modelului să genereze conținut.

## Rulare completă

```powershell
python cercetare/experiment1/run_openrouter_experiment.py
```

Runnerul folosește implicit:

- maximum 60.000 de tokenuri de completare;
- reasoning `high` pentru întrebări și `low` pentru rezumat;
- fallback între provideri activat;
- verificarea strictă a modelului returnat.

Runnerul inserează fiecare pachet dinamic exact o singură dată în prompt: graful,
subgraful capitolului I, manifestele și blueprinturile. Dacă un placeholder lipsește
sau apare de mai multe ori în template, rularea se oprește înainte de apelul API,
pentru a preveni dublarea accidentală a tokenurilor de intrare.

Dacă vrei să dezactivezi fallback-ul între provideri pentru o anumită rulare:

```powershell
python cercetare/experiment1/run_openrouter_experiment.py --no-provider-fallbacks
```

Această alegere trebuie folosită identic pentru toate modelele din aceeași comparație,
iar providerul efectiv este păstrat în metadate.

## Reluarea unei rulări eșuate

Închide mai întâi `results/rezultate-experiment.csv` dacă este deschis în Excel.
Apoi indică folderul rulării existente:

```powershell
python cercetare/experiment1/run_openrouter_experiment.py --resume-run "cercetare/experiment1/deepseek__deepseek-v4-flash-20260731/run-20260806T120214Z"
```

Runnerul încarcă de pe disc sarcinile care au deja JSON valid și nu le mai trimite
către API. Sunt retrimise exclusiv sarcinile eșuate. Pentru rularea de mai sus,
`questions` este reutilizat, iar către model este trimis numai `summary`.

Modelul este preluat din `metadata.json` al rulării reluate. Runnerul refuză reluarea
cu alt model. Încercarea eșuată este arhivată în `previous-attempts/`, iar rândul CSV
este inserat sau actualizat după `run_id`, fără duplicate.

Poți schimba explicit nivelurile de reasoning, dacă protocolul experimentului o cere:

```powershell
python cercetare/experiment1/run_openrouter_experiment.py --summary-reasoning-effort minimal
```

Fallback-ul de provider nu introduce modele alternative în cerere. Runnerul trimite un
singur câmp `model`, nu trimite parametrul `models`, și respinge automat răspunsul dacă
identificatorul returnat nu coincide cu modelul cerut sau cu identificatorul său canonic.

Poți testa temporar alt model fără să modifici configurația:

```powershell
python cercetare/experiment1/run_openrouter_experiment.py --model "openai/gpt-5.4"
```

## Unde apar rezultatele

Caracterul `/` din identificatorul OpenRouter este înlocuit cu `__`, deoarece `/` separă folderele. Pentru modelul `deepseek/deepseek-v4-flash`, rezultatele apar în:

```text
experiment1/
  deepseek__deepseek-v4-flash/
    run-AAAALLZZThhmmssZ/
      questions.raw.txt
      questions.json
      questions.openrouter-response.json
      summary.raw.txt
      summary.json
      summary.openrouter-response.json
      scores.json
      metadata.json
      raport-rulare.md
```

Fiecare rulare primește alt folder, astfel încât rezultatele vechi nu sunt suprascrise.

Tabelul cumulativ este `results/rezultate-experiment.csv`.

`raport-rulare.md` este creat automat, fără apel AI suplimentar, din JSON-urile,
scorurile și metadatele salvate. Conține identificarea modelului și providerilor,
scorurile, întrebările exacte, rezumatele, tokenurile, costurile, diagnosticele și
istoricul eventualelor reluări.

## Ce se întâmplă într-o rulare

1. Cheia și modelul sunt citite din fișierul local ignorat de Git.
2. Endpointul `/models/user` confirmă că modelul este disponibil contului.
3. Se verifică aproximativ dacă inputul și outputul încap în context.
4. Graful integral este introdus în promptul întrebărilor.
5. Subgraful capitolului I este introdus în promptul rezumatului.
6. Se aplică setarea aleasă pentru fallback-ul între providerii aceluiași model.
7. Răspunsurile brute sunt salvate înaintea evaluării.
8. JSON-ul este parsat fără reparații automate.
9. `evaluator.py` calculează scorurile.
10. Metadatele și rezultatele sunt salvate fără cheia API.
11. Se generează automat `raport-rulare.md`.

## Reguli pentru o comparație corectă

- Nu modifica prompturile între două modele comparate.
- Nu modifica graful sau evaluatorul după începerea seriei de rulări.
- Folosește același număr de rulări pentru fiecare model.
- Nu repara manual outputurile înainte de punctare.
- Păstrează folderele cu răspunsurile brute și metadatele.
