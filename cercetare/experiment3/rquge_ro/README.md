# RQUGE-Ro-KG

Acest submodul reproduce în română arhitectura RQUGE: un model QA generează răspunsul
la întrebarea candidată folosind contextul, apoi un al doilea model estimează pe scala
1–5 cât de bine se aliniază răspunsul generat cu răspunsul corect. Implementarea este
**experimentală** până când span-scorer-ul este validat pe un set românesc ținut separat.

## Modelele alese

- QA: `google/mt5-small` (multilingv, aproximativ 300M parametri);
- span scorer: `FacebookAI/xlm-roberta-base` (multilingv, aproximativ 280M parametri);
- baseline prin traducere: `Helsinki-NLP/opus-mt-roa-en`.

Paper-ul original folosește `allenai/unifiedqa-v2-t5-large-1363200` pentru QA și
`alirezamsh/quip-512-mocha` pentru span scoring. Aceste checkpointuri sunt în engleză;
paper-ul menționează explicit engleza drept limitare. Alegerea mT5-small + XLM-R base
reduce ansamblul la aproximativ 580M parametri și permite antrenarea componentelor pe
rând, inclusiv cu LoRA.

Pentru un pilot minim există combinația configurabilă `google-t5/t5-small` (60M) +
`distilbert/distilbert-base-multilingual-cased` (134M), aproximativ 194M parametri în
total. Este mai ușoară, dar T5-small nu este un model multilingv comparabil cu mT5 și
calitatea QA în română trebuie demonstrată separat. De aceea presetul implicit rămâne
mT5-small + XLM-R base.

## Ce date sunt necesare

1. Pentru QA: exemple `question`, `context`, `answer`. XQuAD-ro poate servi drept set
   de validare general, iar RoITD și exemplele din domeniul BAC drept antrenare.
2. Pentru span scorer: `question`, `context`, `gold_answer`, `predicted_answer` și o
   evaluare umană `score` în `[1, 5]`. Ideal, fiecare caz este evaluat de minimum trei
   adnotatori, iar scorul-țintă este media lor.
3. Un test românesc neatins la antrenare pentru Spearman/Pearson și comparația cu
   evaluatori umani. Fără acest pas, numele corect este „RQUGE-Ro experimental”, nu o
   metrică oficial validată.

Exemplele de schemă sunt în `../inputs/rquge-ro-*.example.jsonl`. Conform arhitecturii
paper-ului, adnotatorul notează corectitudinea semantică a `predicted_answer` față de
`gold_answer`, condiționat de întrebare și context; calitatea întrebării este măsurată
indirect prin capacitatea QA de a recupera răspunsul. Rubrica propusă este în
`annotation-guidelines.md` și trebuie înghețată după un pilot de adnotare.

Evaluările individuale se agregă înainte de antrenare:

```powershell
python experiment3\rquge_ro\aggregate_ratings.py `
  ratings-individuale.jsonl ratings-ro.jsonl --minimum-annotators 3
```

## Instalare

Din folderul `cercetare`:

```powershell
python -m venv .venv-rquge
.venv-rquge\Scripts\python.exe -m pip install -r experiment3\rquge_ro\requirements.txt
```

## Pregătirea datelor QA

XQuAD/SQuAD JSON:

```powershell
python experiment3\rquge_ro\prepare_qa_data.py squad xquad.ro.json qa-ro.jsonl
```

CSV (numele coloanelor pot fi schimbate din opțiuni):

```powershell
python experiment3\rquge_ro\prepare_qa_data.py csv roitd.csv qa-roitd.jsonl `
  --context-column context --question-column question --answer-column answer
```

Pentru RoITD trebuie inspectată versiunea descărcată înainte de filtrarea câmpului
`is_impossible`; scriptul nu îi presupune semantica. Filtrarea explicită se face cu
`--filter-column is_impossible --keep-value VALOAREA_VERIFICATA`.

## Antrenarea QA

Configurație prudentă pentru GPU de laptop:

```powershell
python experiment3\rquge_ro\train_qa.py qa-ro.jsonl `
  --validation-jsonl qa-validation.jsonl `
  --output-dir experiment3\models\rquge-ro-qa `
  --batch-size 1 --gradient-accumulation 8 --gradient-checkpointing --fp16 --use-lora
```

Pe CPU poate rula, dar fine-tuning-ul va fi lent. Un GPU de 8 GB poate fi suficient
pentru LoRA cu batch 1 și checkpointing; memoria exactă depinde de lungimea contextului,
versiunile bibliotecilor și placă. Full fine-tuning este mai realist de la 12–16 GB VRAM.

## Antrenarea span-scorer-ului

```powershell
python experiment3\rquge_ro\train_span_scorer.py ratings-ro.jsonl `
  --validation-jsonl ratings-validation.jsonl `
  --output-dir experiment3\models\rquge-ro-span `
  --batch-size 1 --gradient-accumulation 8 --gradient-checkpointing --fp16 --use-lora
```

Pentru pilotul minimal se pot adăuga
`--base-model distilbert/distilbert-base-multilingual-cased`; scriptul adaptează automat
modulele LoRA la DistilBERT.

Setul de validare și testul trebuie împărțite după întrebare/context, nu după simpla
linie, ca evaluările aceleiași întrebări să nu ajungă în ambele subseturi. Dacă nu este
dat un fișier de validare, scriptul păstrează automat grupurile împreună.

## Scorare

```powershell
python experiment3\rquge_ro\score.py `
  experiment3\inputs\rquge-ro-score-input.example.jsonl `
  --qa-model experiment3\models\rquge-ro-qa `
  --span-model experiment3\models\rquge-ro-span `
  --qa-adapter --span-adapter `
  --output-jsonl experiment3\outputs\rquge-ro-scores.jsonl
```

Flagurile `--qa-adapter` și `--span-adapter` se folosesc numai pentru checkpointuri
LoRA. Ieșirea păstrează separat scorul brut, scorul limitat la `[1,5]`, exact match și
token-F1 pentru audit.

## Baseline prin traducere

```powershell
python experiment3\rquge_ro\translate_baseline.py `
  experiment3\inputs\rquge-ro-score-input.example.jsonl translated-en.jsonl
```

Acest baseline ajută la comparație cu RQUGE englezesc, dar traducerea întrebării,
contextului și răspunsului poate modifica dificultatea. De aceea nu este recomandat ca
metrica principală și trebuie raportat distinct.

Surse: [RQUGE (Findings of ACL 2023)](https://aclanthology.org/2023.findings-acl.428/),
[codul autorilor](https://github.com/alirezamshi/RQUGE),
[mT5-small](https://huggingface.co/google/mt5-small),
[XLM-RoBERTa-base](https://huggingface.co/FacebookAI/xlm-roberta-base),
[XQuAD](https://github.com/google-deepmind/xquad),
[RoITD](https://huggingface.co/datasets/dragosnicolae555/RoITD) și
[OPUS-MT roa-en](https://huggingface.co/Helsinki-NLP/opus-mt-roa-en).
