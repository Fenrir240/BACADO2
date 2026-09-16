# Raport de validare - graful 2

- Rezultat general: **TRECUT**
- Validare JSON Schema: **TRECUT**
- Noduri: **227** (prag acceptat: 200-300)
- Relații: **1674** (minimum: 300)
- Capitole: **13**
- Evenimente: **124**
- Subevenimente distincte: **0**
- Noduri narative: **150** (66.1%)
- Conectate la componenta principală: **227** (100.0%)
- Afirmații cu sursă: **1901**
- Incertitudini: **0**

## Verificări structurale

- ID-uri duplicate: 0
- Duplicate semantice după etichetă normalizată: 0
- Noduri orfane: 0
- Muchii invalide: 0
- Referințe-sursă inexistente: 0
- Afirmații fără sursă: 0
- Capitole incomplete: 0
- Erori de ordine locală: 0
- Contradicții temporale: 0
- Noduri implicate în cicluri temporale: 0
- Erori de ordine globală: 0
- Interpretări marcate greșit drept fapte: 0
- Contradicții detectate între stări: 0

## Auditul surselor

- Rezultat audit: **TRECUT**
- Pagini PDF: 550
- Pagini cu text extractibil: 549
- Supliment final canonic Wikisource: **TRECUT**
- Fișiere-sursă lipsă: 0
- Fișiere-sursă goale: 0
- Titluri de capitol neconfirmate la pagina de început: 0

## Verificări narative

- Evenimente fără sursă: 0
- Evenimente fără ordine: 0
- Evenimente fără verbalizare simplă: 0
- Evenimente fără verbalizare elevată: 0
- Evenimente fără cauză: 80
- Evenimente fără consecință: 79
- Evenimente fără participant uman explicit: 2

Evenimentele fără participant uman sunt secvențe-cadru sau observații narative: `EV_001`, `EV_121`. Ele păstrează locul, ordinea, cauza, consecința și sursa.

## Distribuția nodurilor

- Author: 1
- Chapter: 13
- Character: 24
- Conflict: 5
- Institution: 2
- LiteraryTechnique: 1
- Location: 14
- Motif: 1
- NarrativeEvent: 124
- NarrativeState: 26
- Part: 2
- Theme: 9
- Value: 4
- Work: 1

## Distribuția relațiilor

- causes: 12
- changes_state_of: 45
- chapter_of: 13
- contrasts_with: 2
- contributes_to: 5
- created_by: 1
- enables: 25
- expresses_motif: 4
- expresses_theme: 152
- expresses_value: 24
- has_chapter: 13
- has_closing_state: 13
- has_opening_state: 13
- has_part: 2
- has_participant: 291
- immediately_follows: 111
- immediately_precedes: 111
- intensifies: 104
- is_child_of: 12
- is_married_to: 8
- is_parent_of: 12
- is_rival_of: 2
- loves: 3
- occurs_at: 124
- occurs_before: 123
- occurs_in_chapter: 124
- parallels: 3
- part_of: 15
- participates_in: 291
- results_in: 13
- uses_technique: 3

## Test de autosuficiență

Cele patru variante de rezumat pentru fiecare capitol au fost regenerate programatic numai din `chapters[].event_sequence` și din verbalizările nodurilor `NarrativeEvent`. Fiecare propoziție este asociată evenimentului și referințelor care o susțin.

## Concluzie

Graful respectă limitele cantitative, păstrează toate capitolele și evenimentele valide ale grafului 1, adaugă evenimentele factuale lipsă, elimină nodurile auxiliare redundante și trece verificările automate descrise mai sus.
