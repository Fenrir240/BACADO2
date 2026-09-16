# Modele OpenRouter compatibile cu dimensiunea experimentului

Ultima verificare: **13 august 2026**.

Surse OpenRouter:

- catalogul public: `GET https://openrouter.ai/api/v1/models`;
- catalogul autentificat al contului: `GET https://openrouter.ai/api/v1/models/user`.

Lista este un snapshot pentru planificarea experimentului, nu o listă permanentă.
Disponibilitatea, providerii, limitele și prețurile trebuie reverificate înaintea
fiecărei serii oficiale.

## Pragul de context al experimentului

Runnerul estimează conservator inputul cu formula `ceil(număr_caractere / 2,5)` și
adaugă limita comună de 60.000 de tokenuri pentru completare.

| Sarcină | Caractere randate | Input estimat conservator | Context minim cu output de 60k |
|---|---:|---:|---:|
| Întrebări | 900.066 | 360.027 | **420.027** |
| Rezumat | 95.930 | 38.372 | 98.372 |

În rulările stabile deja salvate, cererea de întrebări a consumat aproximativ
294.700–303.500 de tokenuri de input, iar cererea de rezumat aproximativ
30.600–31.400. Pragul de **420.027** rămâne criteriul de includere deoarece este
regula conservatoare implementată de runner, nu doar consumul observat cu un anumit
tokenizer.

Un model trece filtrul dimensional numai dacă:

- `context_length >= 420027`;
- `top_provider.context_length >= 420027` pentru providerul disponibil contului;
- limita de completare este de cel puțin 60.000 de tokenuri sau OpenRouter nu declară
  încă o limită;
- acceptă input text, produce text și suportă `max_tokens`;
- nu este router automat, alias `latest` sau variantă batch.

La verificarea preliminară, **74 de identificatoare** din catalogul contului au trecut
filtrul agregat de mai sus. Numărul nu reprezintă automat modele potrivite cercetării:
limitele de context și output pot proveni de la endpointuri diferite ale aceluiași
model. Înaintea includerii trebuie verificat că un singur endpoint satisface simultan
ambele limite. Au fost eliminate manual și modelele de muzică, modelele de siguranță,
variantele redundante și modelele orientate exclusiv spre cod.

## Coada recomandată de testare

Prețurile sunt cele declarate contului OpenRouter, în USD pentru un milion de tokenuri.
Ele nu includ eventuale praguri speciale de long-context și se pot schimba.

### Faza A — candidați pentru setările curente

Acești candidați au suficient context și output, acceptă JSON prin `response_format`
sau Structured Outputs și nu declară o incompatibilitate cu eforturile implicite
`high` pentru întrebări și `low` pentru rezumat.

| Prioritate | Model OpenRouter | Context provider | Output maxim | Input / 1M | Output / 1M | Motivul includerii |
|---:|---|---:|---:|---:|---:|---|
| 1 | `qwen/qwen3.7-flash` | 1.000.000 | 65.536 | $0,03 | $0,13 | Primul pilot ieftin, cu marjă mare de context |
| 2 | `openai/gpt-5.6-luna` | 1.050.000 | 128.000 | $0,10 | $0,60 | Baseline OpenAI ieftin, cu eforturi `high` și `low` declarate |
| 3 | `xiaomi/mimo-v2.5` | 1.048.576 | 131.072 | $0,14 | $0,28 | Diversitate de furnizor la cost redus |
| 4 | `qwen/qwen3.7-plus` | 1.000.000 | 131.072 | $0,32 | $1,28 | Pereche utilă Flash–Plus în aceeași familie |
| 5 | `google/gemini-3.7-flash` | 1.048.576 | 65.536 | $0,375 | $1,875 | Comparație cu Gemini 2.5 Flash Lite deja rulat |
| 6 | `anthropic/claude-sonnet-5` | 1.000.000 | 128.000 | $2,00 | $10,00 | Baseline premium din altă familie |
| 7 | `openai/gpt-5.4` | 1.050.000 | 128.000 | $2,50 | $15,00 | Baseline premium OpenAI |

`qwen/qwen3.5-flash-02-23` rămâne alternativă de rezervă foarte ieftină
($0,065 / $0,26 per milion), dar este mai puțin informativ să fie rulat înaintea
modelelor din familii încă nereprezentate.

### Faza B — compatibile dimensional, dar cu precauții

| Model OpenRouter | Context provider | Precauție metodologică |
|---|---:|---|
| `nvidia/nemotron-3.5-lightning` | 1.048.576 la DeepInfra / 262.144 la CoreWeave | Niciun endpoint verificat nu satisface simultan promptul mare și outputul de 60k: DeepInfra limitează practic outputul la 28.672, iar CoreWeave nu poate primi integral promptul întrebărilor |
| `upstage/solar-pro4` | 524.288 | Trece pragul cu o marjă conservatoare de numai 104.261 tokenuri; bun pentru test de frontieră, nu primul pilot |
| `thinkingmachines/inkling-small` | 524.288 | Aceeași marjă mică de context; Structured Outputs este declarat, dar `response_format` nu este listat separat |
| `x-ai/grok-4.6` | 500.000 | Marjă de numai 79.973 tokenuri și limită maximă de completare nedeclarată; tariful crește pentru prompturi de peste 200k |
| `deepseek/deepseek-v4-pro` | 1.048.576 | Declară numai eforturile `xhigh` și `high`; setarea implicită `low` a rezumatului este respinsă de runner |
| `z-ai/glm-5.2` | 1.048.576 | Declară numai eforturile `xhigh` și `high`; necesită o serie separată sau schimbarea controlată a protocolului |
| `nvidia/nemotron-3.5-lightning:free` | 1.000.000 | Potrivit pentru smoke test fără cost, dar nu declară `response_format`/Structured Outputs și poate avea limite de disponibilitate |

Pentru `deepseek/deepseek-v4-pro` și `z-ai/glm-5.2`, comanda tehnic posibilă este:

```powershell
..\.venv\Scripts\python.exe experiment1\run_openrouter_experiment.py `
  --model "MODEL_ID" `
  --summary-reasoning-effort high
```

Această schimbare nu trebuie amestecată cu seria principală existentă, în care
rezumatul folosește `low`, decât dacă toate modelele comparate sunt rerulate cu aceeași
setare.

## Ordinea de validare

1. Rulează preflight-ul autentificat pentru modelul ales:

   ```powershell
   ..\.venv\Scripts\python.exe experiment1\run_openrouter_experiment.py `
     --model "qwen/qwen3.7-flash" `
     --preflight-only
   ```

2. Pentru primul apel cu plată, folosește o singură rulare pilot și verifică
   `metadata.json`, `finish_reason`, JSON-ul brut și costul raportat.
3. Înaintea seriei oficiale, fixează intersecția parametrilor și aceeași politică de
   fallback pentru toate modelele.
4. Rulează trei repetări numai după ce pilotul trece validarea de context, format și
   parsing.

Modelele deja prezente în rezultate — variantele DeepSeek V4 Flash și
`google/gemini-2.5-flash-lite` — nu au fost repetate în coada de modele noi.
