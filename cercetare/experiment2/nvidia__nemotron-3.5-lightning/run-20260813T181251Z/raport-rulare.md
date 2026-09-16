# Raport rulare — NVIDIA: Nemotron 3.5 Lightning

## Identificarea rulării

- Rulare: `run-20260813T181251Z`
- Data UTC: `2026-08-13T18:12:51.488145+00:00`
- Model solicitat: `nvidia/nemotron-3.5-lightning`
- Model returnat pentru întrebări: `—`
- Model returnat pentru rezumat: `nvidia/nemotron-3.5-lightning`
- Provider întrebări: —
- Provider rezumat: CoreWeave
- Fallback între modele: inexistent; runnerul trimite un singur model și îi verifică identitatea
- Fallback între providerii aceluiași model — întrebări: nu
- Fallback între providerii aceluiași model — rezumat: da

## Rezultate generale

- Întrebări generate: 0 din 0
- JSON întrebări valid: nu
- JSON rezumat valid: da
- Scor întrebări: 0,000 / 100
- Scor rezumat: 81,198 / 100
- Scor general: 40,599 / 100
- Eroare întrebări: OpenRouter HTTP 400: {"error":{"message":"Provider returned error","code":400,"metadata":{"raw":"{\"error\":{\"message\":\"This model's maximum context length is 262144 tokens. However, you requested 27000 output tokens and your prompt contains at least 235145 input tokens, for a total of at least 262145 tokens. Please reduce the length of the input prompt or the number of requested output tokens. (parameter=input_tokens, value=235145)\",\"type\":\"invalid_request_error\",\"param\":\"messages\",\"code\":\"context_length_exceeded\"}}","provider_name":"Venice","is_byok":false,"provider_error_code":"context_length_exceeded","retry_after_seconds":29,"retry_after_seconds_raw":28.873,"headers":{"Retry-After":"29"}}},"user_id":"org_3HOxRiTX7Q4sWxrepTeWRDvBnNr"}
- Eroare rezumat: —

## Performanță și cost

| Sarcină | Reasoning | Durată (s) | Tokenuri prompt | Tokenuri completare | Tokenuri reasoning | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| Întrebări | — | — | — | — | — | — |
| Rezumat | high | 16,121 | 33.107 | 3.887 | 0 | 0,004282 |

- Durată API cumulată: 16,121 secunde
- Cost total: 0,004282 USD

## Scorurile întrebărilor

| ID | Slot | Tipologie | Întrebare | Scor | Diagnostic |
|---|---|---|---|---:|---|

- Media întrebărilor: 0,000 / 100
- Scorul de acoperire și diversitate al setului: 0,000 / 100

## Scorurile rezumatelor

| Registru | Scor | Cuvinte | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal | Diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| simple | 81,368 | 144 | 1,000 | 0,875 | 1,000 | 0,000 | Afirmatii invalide: 2 din 16.; Relatii cauzale declarate: 0 din 32 asteptate.; Propozitii cu dovezi integral valide: 7 din 9.; word_count declarat=287, recalculat=144.; Profil stilistic în afara marjei: discourse_connectors, filler_phrases, connector_repetition, connector_sentence_starts. |
| elevated | 81,029 | 155 | 1,000 | 0,875 | 1,000 | 0,000 | Afirmatii invalide: 2 din 16.; Relatii cauzale declarate: 0 din 32 asteptate.; Propozitii cu dovezi integral valide: 7 din 9.; word_count declarat=324, recalculat=155.; Profil stilistic în afara marjei: filler_phrases, connector_repetition. |

## Rezumatele generate

### Simple

La început, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Apoi, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. După aceea, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. În continuare, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. Mai târziu, ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Ulterior, vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. În continuare, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. Mai târziu, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

### Elevated

La începutul secvenței, drumul introduce treptat satul Pripas, casele și semnele unei comunități aparent liniștite. Ulterior, în curtea Todosiei, jocul duminical adună țăranii și eliberează energiile acumulate peste săptămână. În continuarea firului narativ, așezarea participanților la horă separă săracii, bogații și intelectualitatea și arată ordinea socială a satului. Pe măsură ce acțiunea înaintează, deși o iubește pe Florica, Ion o ignoră ostentativ și dansează cu Ana, fiica bogată a lui Vasile Baciu. În acest context, ion urmărește căsătoria cu Ana pentru a ajunge la pământurile lui Vasile Baciu. Ulterior, vasile Baciu, beat, îl numește public pe Ion sărăntoc și refuză să îl accepte ca ginere. Pe măsură ce acțiunea înaintează, afrontul lui Vasile transformă dorința de pământ într-o nevoie de răzbunare și validare. În acest context, la cârciuma lui Avrum, plata lăutarilor devine pretextul confruntării dintre Ion și George. Ulterior, ion îl bate pe George cu un par și își dovedește forța în fața flăcăilor.

## Istoricul reluărilor

1. `2026-08-13T18:18:30.884879+00:00` — retrimise: questions; reutilizate fără apel API: summary.
2. `2026-08-13T18:20:35.525264+00:00` — retrimise: questions; reutilizate fără apel API: summary.
3. `2026-08-13T18:22:16.616768+00:00` — retrimise: questions; reutilizate fără apel API: summary.
4. `2026-08-13T18:29:15.594340+00:00` — retrimise: questions; reutilizate fără apel API: summary.
5. `2026-08-13T18:31:35.587072+00:00` — retrimise: questions; reutilizate fără apel API: summary.

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
| simple | 57.7% | 4.86% | 2.78% | 12.50% | 4.230 |
| elevated | 69.5% | 2.58% | 3.87% | 11.61% | 3.048 |
