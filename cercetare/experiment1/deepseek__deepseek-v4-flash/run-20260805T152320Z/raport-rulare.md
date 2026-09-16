# Raport pilot — DeepSeek V4 Flash

## Identificarea rulării

- Rulare: `run-20260805T152320Z`
- Model solicitat: `deepseek/deepseek-v4-flash`
- Model returnat pentru întrebări: `deepseek/deepseek-v4-flash`
- Model returnat pentru rezumat: `deepseek/deepseek-v4-flash`
- Verificarea identității modelului: reușită
- Provider întrebări: Novita
- Provider rezumat: DeepInfra
- Fallback între modele: inexistent
- Fallback între provideri ai aceluiași model: permis

## Rezultate

- Întrebări generate: 8 din 8
- JSON întrebări valid: da
- JSON rezumat valid: da
- Scor întrebări: 82,818 / 100
- Scor rezumat: 93,161 / 100
- Scor general: 87,989 / 100

## Performanță și cost

### Întrebări

- Durată: 211,422 secunde
- Tokenuri prompt: 586.785
- Tokenuri completare: 20.975
- Tokenuri de reasoning: 17.108
- Cost: 0,0880229 USD

### Rezumat

- Durată: 568,248 secunde
- Tokenuri prompt: 59.483
- Tokenuri completare: 25.876
- Tokenuri de reasoning: 13.816
- Cost: 0,010006542 USD

### Total

- Durată API cumulată: 779,670 secunde
- Cost total: 0,098029442 USD

## Scorurile întrebărilor

| Slot | Tipologie | Scor |
|---|---|---:|
| SLOT_01 | FACT_1HOP | 99,000 |
| SLOT_02 | RELATION_1HOP | 99,000 |
| SLOT_03 | TEMPORAL_ORDER | 65,250 |
| SLOT_04 | DIRECT_CAUSE | 100,000 |
| SLOT_05 | DIRECT_EFFECT | 100,000 |
| SLOT_06 | MULTIHOP_CAUSAL | 61,111 |
| SLOT_07 | STATE_TRANSITION | 50,909 |
| SLOT_08 | CROSS_CHAPTER_COMPARE | 72,778 |

Scorul de diversitate al setului a fost 99,13 / 100. Pierderile principale provin din planurile de interogare pentru întrebările temporale, multihop, de tranziție de stare și de comparație între capitole.

## Scorurile rezumatelor

| Registru | Scor | Cuvinte recalculate | Acoperire evenimente | Afirmații valide | Ordine corectă | Recall cauzal |
|---|---:|---:|---:|---:|---:|---:|
| simplu | 92,697 | 227 | 1,000 | 1,000 | 1,000 | 0,375 |
| elevat | 93,625 | 291 | 1,000 | 1,000 | 1,000 | 0,406 |

Ambele rezumate au acoperit toate evenimentele capitolului I, au folosit afirmații valide și au păstrat ordinea narativă. Principala pierdere este la relațiile cauzale declarate. Modelul a declarat greșit propriul număr de cuvinte: 198 în loc de 227 pentru varianta simplă și 232 în loc de 291 pentru varianta elevată.

## Observație metodologică

Aceasta este o rulare pilot, nu una dintre cele trei repetări oficiale. Prima încercare tehnică, `run-20260805T143832Z`, a eșuat din cauza unui rate limit al providerului DigitalOcean și nu trebuie interpretată ca performanță a modelului.

Evaluatorul folosit are încă limitarea documentată privind normalizarea relațiilor cauzale ale capitolului I. Scorurile trebuie considerate rezultate ale versiunii curente a evaluatorului.
