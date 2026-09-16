# Automatizare — Construiește eseul

Comanda stabilă pentru o operă nouă este:

```powershell
.\venv\Scripts\python.exe scripts\eseu.py --graph "cale\catre\knowledge-graph.json" --model-essay "cale\catre\eseu-model.md"
```

Pipeline-ul face un singur apel către `qwen/qwen3.7-flash`, cu reasoning `medium`,
și nu reîncearcă generarea. Eseul-model este obligatoriu și reprezintă autoritatea
pentru structura eseului.

## Regula trăsăturilor curentului

Schema are exact două noduri de trăsături. Sunt acceptate numai cele două trăsături
dezvoltate explicit în paragrafele argumentative ale eseului-model. Trăsăturile doar
enumerate în introducere nu sunt preluate.

Pentru fiecare trăsătură, scriptul verifică determinist că:

- denumirea apare exact în fragmentul-sursă;
- fragmentul-sursă este o porțiune continuă din eseul-model;
- fragmentul-model este o porțiune continuă din eseul-model.

Dacă una dintre verificări eșuează, prima variantă Qwen rămâne salvată în directorul
rulării pentru diagnostic, însă nu înlocuiește blueprint-ul valid folosit de UI. Nu se
face nicio regenerare. În evaluarea elevului, orice trăsătură care nu apare în lista
închisă din blueprint este tratată drept incorectă.

## Fișiere rezultate

- `data/generated_works/<work_id>/construieste-eseu/eseu.json` — blueprint-ul complet al UI-ului;
- `data/generated_works/<work_id>/construieste-eseu/eseu-model.md` — copia canonică folosită ulterior de UI și profesorul AI;
- `data/generated_works/<work_id>/construieste-eseu/manifest.json` — surse, model, validare și rezultat;
- `data/generated_works/<work_id>/construieste-eseu/runs/run-*/` — packet, prompt, cerere, răspuns și validare.

Blueprint-ul conține introducerea, cele două trăsături, tema, două secvențe, cele trei
elemente compoziționale și concluzia. Alegerea celor două elemente compoziționale rămâne
făcută de elev în „Înțelege opera”, iar selecția este reflectată automat în schema eseului.

Pentru a pregăti cererea fără apel API:

```powershell
.\venv\Scripts\python.exe scripts\eseu.py --graph "cale\catre\knowledge-graph.json" --model-essay "cale\catre\eseu-model.md" --dry-run
```
