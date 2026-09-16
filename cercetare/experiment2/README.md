# Experimentul 2

Experimentul 2 păstrează knowledge graph-ul, cele opt tipologii de întrebări și
runnerul OpenRouter din Experimentul 1, dar introduce două schimbări controlate:

1. detectarea întrebărilor semantic duplicate cu modelul local
   `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`;
2. un profil stilistic măsurat automat pentru rezumatele capitolului I.

Modelul MiniLM nu este un agent și nu generează text. El transformă întrebările în
embeddinguri normalizate, apoi evaluatorul calculează similaritatea cosinus.

## Fișiere importante

- `run_openrouter_experiment.py` — runnerul complet;
- `results/rezultate-experiment.csv` — registrul tehnic actualizat automat după fiecare rulare;
- `evaluator.py` — MiniLM, scorurile de duplicare și penalizarea profilului;
- `text_profile.py` — numără direct indicatorii rezumatului;
- `calibrate_similarity.py` — calibrează pragul pe perechi etichetate;
- `inputs/semantic-similarity.json` — modelul și pragurile semantice;
- `inputs/summary-manifest.json` — marjele stilistice oferite agenților;
- `inputs/reference-style-profile.json` — măsurătorile etalon, neincluse în prompt;
- `prompts/prompt-rezumat-capitolul-1.md` — promptul Experimentului 2;
- `conditii-experiment.md` — protocolul și limitările metodologice.

Promptul nu conține fragmentul-etalon. El conține numai intervalele derivate din
profilul acestuia, pentru a nu introduce fapte externe knowledge graph-ului.

## Instalare

Este recomandat un mediu virtual separat:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r experiment2\requirements.txt
```

La prima comparație, Sentence Transformers descarcă modelul de pe Hugging Face. După
ce modelul se află în cache, evaluarea poate rula local. Pachetul Sentence Transformers
documentează `encode()` și similaritatea embeddingurilor în [documentația oficială](https://www.sbert.net/docs/quickstart.html),
iar checkpointul folosit este publicat în [model card-ul oficial](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).

## Pregătirea subgrafului

Din folderul `cercetare`:

```powershell
python experiment2\prepare_inputs.py
```

Regula de extragere este aceeași ca în Experimentul 1. Rezultatul este scris în
`experiment2/inputs/chapter-01-graph.json`.

## Verificarea MiniLM

```powershell
python experiment2\evaluator.py --compare `
  "De ce îl lovește Ion pe George?" `
  "Care este motivul pentru care Ion îl atacă pe George?"
```

Rezultatul conține `similarity`, `decision` și `same_meaning`.

## Calibrarea pragului

Pragurile `0.74` și `0.82` din configurația inițială sunt provizorii. Ele fac
experimentul executabil, dar nu trebuie prezentate drept praguri universale.

1. Copiază `calibration-pairs.example.csv` într-un fișier de lucru.
2. Adaugă perechi reale de întrebări BAC etichetate independent.
3. Rulează:

```powershell
python experiment2\calibrate_similarity.py perechi-etichete.csv `
  --output experiment2\calibration-report.json
```

După auditarea raportului, configurația poate fi actualizată explicit:

```powershell
python experiment2\calibrate_similarity.py perechi-etichete.csv `
  --output experiment2\calibration-report.json --write-config
```

Pentru raportarea finală trebuie păstrat separat un set de test care nu a fost folosit
la alegerea pragului.

## Configurarea OpenRouter

Copiază `config.local.env.example` ca `config.local.env` și completează cheia și modelul:

```env
OPENROUTER_API_KEY=cheia_ta
OPENROUTER_MODEL=deepseek/deepseek-v4-flash
```

Fișierul local este ignorat de Git.

## Rulare

Preflight OpenRouter, fără generare:

```powershell
python experiment2\run_openrouter_experiment.py --preflight-only
```

Rulare completă:

```powershell
python experiment2\run_openrouter_experiment.py
```

Runnerul salvează aceleași artefacte ca Experimentul 1, însă în `experiment2/`.
`scores.json` și `raport-rulare.md` includ modelul semantic, perechile apropiate,
profilurile celor două rezumate și eventualele penalizări.

## Rezultatele tabelare

După fiecare rulare sau reluare, runnerul actualizează numai
`results/rezultate-experiment.csv`. Fișierul
`results/rezultate-experiment-editabil.xlsx` nu este citit și nu este modificat de
runner, astfel încât observațiile introduse manual rămân sub controlul utilizatorului.

## Cum este limitat rezumatul

Evaluatorul recalculează din text:

- raportul conectorilor discursivi;
- raportul cuvintelor din expresii de umplutură;
- lungimea medie a propoziției;
- raportul cuvintelor care apar în numele personajelor din graf;
- repetarea aceluiași conector;
- proporția propozițiilor care încep cu un conector.

Conjuncțiile și prepozițiile sunt raportate, dar nu sunt penalizate. Conformitatea
stilistică poate scădea scorul fiecărui registru cu maximum 10 puncte. Intervalele,
ponderile și formula sunt înghețate în `inputs/summary-manifest.json`.

## Teste fără descărcarea modelului

```powershell
python -m unittest discover -s experiment2\tests -v
```

Testele folosesc un backend semantic fals, controlat, astfel încât logica evaluatorului
și profilul lexical pot fi verificate fără rețea și fără descărcarea modelului real.
