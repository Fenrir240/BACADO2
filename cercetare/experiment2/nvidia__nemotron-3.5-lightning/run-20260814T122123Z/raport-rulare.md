# Raport rulare — NVIDIA: Nemotron 3.5 Lightning

## Identificarea rulării

- Rulare: `run-20260814T122123Z`
- Data UTC: `2026-08-14T12:21:23.597225+00:00`
- Model solicitat: `nvidia/nemotron-3.5-lightning`
- Model returnat pentru întrebări: `—`
- Model returnat pentru rezumat: `nvidia/nemotron-3.5-lightning`
- Provider întrebări: —
- Provider rezumat: DeepInfra
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: nu
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 0 din 0
- JSON întrebări valid: nu
- JSON rezumat valid: da
- Scor întrebări: 0,000 / 100
- Scor rezumat: 81,767 / 100
- Scor general: 40,883 / 100
- Eroare întrebări: OpenRouter API 502: Upstream error from DeepInfra: This model's maximum context length is 262144 tokens. However, you requested 26000 output tokens and your prompt contains at least 236145 input tokens, for a total of at least 262145 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=236145)
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | — | — | — | — | — | — |
| Rezumat | none | 14,995 | 33.107 | 4.051 | 0 | 0,003459 |

- Durată API cumulată: 14,995 secunde
- Cost total: 0,003459 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|

- Media întrebărilor: 0,000 / 100
- Scorul de acoperire și diversitate al setului: 0,000 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 82,480 | 130 | 1,000 | 0,889 | 1,000 | 0,000 | Afirmatii invalide: 2 din 18.; Relatii cauzale declarate: 0 din 32 asteptate.; Propozitii cu dovezi integral valide: 6 din 8.; word_count declarat=201, recalculat=130.; Profil stilistic în afara marjei: discourse_connectors, filler_phrases, connector_repetition, connector_sentence_starts. |
| elevated | 81,054 | 139 | 1,000 | 0,889 | 1,000 | 0,000 | Afirmatii invalide: 2 din 18.; Relatii cauzale declarate: 0 din 32 asteptate.; Propozitii cu dovezi integral valide: 6 din 8.; word_count declarat=235, recalculat=139.; Profil stilistic în afara marjei: filler_phrases, connector_repetition, connector_sentence_starts. |

## Rezumatele generate

### Simple

La început, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Apoi, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. După aceea, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. În continuare, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Ulterior, vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. În continuare, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

### Elevated

La începutul secvenței, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Ulterior, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. În continuarea firului narativ, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Pe măsură ce acțiunea înaintează, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Ulterior, vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. Pe măsură ce acțiunea înaintează, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

## Istoricul reluărilor

Rularea nu a fost reluată.

## Fișierele verificabile ale rulării

- `questions.json` și `questions.openrouter-response.json`
- `summary.json` și `summary.openrouter-response.json`
- `scores.json`
- `metadata.json`

Raportul a fost construit determinist din fișierele rulării, fără apel AI suplimentar.

## Verificările specifice Experimentului 2

### Similaritatea semantică a întrebărilor

- Model local: `indisponibil`
- Prag duplicat: `—`
- Prag revizuire manuală: `—`

### Profilul stilistic al rezumatelor

| Registru | Conformitate | Conectori | Expresii de umplutură | Nume personaje | Penalizare |
|---|---:|---:|---:|---:|---:|
| simple | 67.6% | 3.85% | 5.38% | 10.77% | 3.242 |
| elevated | 67.4% | 2.88% | 2.16% | 10.07% | 3.262 |
