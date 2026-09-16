# Ontologia knowledge graph-ului «Ion» - graful 2

## Principii de modelare

Graful separă faptele narative de interpretări, păstrează ordinea locală și globală a evenimentelor și atașează fiecărei afirmații cel puțin o referință. Pentru a respecta limita de 200-300 de noduri fără pierdere narativă, motivațiile și consecințele repetitive sunt stocate în atributele evenimentelor, nu ca noduri auxiliare distincte.

## Tipuri de noduri

- `Work`: opera literară modelată (instanțe în graful 2: 1).
- `Author`: autorul operei (instanțe în graful 2: 1).
- `Part`: diviziune majoră a operei (instanțe în graful 2: 2).
- `Chapter`: unitate narativă cu stare inițială, stare finală și evenimente ordonate (instanțe în graful 2: 13).
- `NarrativeEvent`: eveniment factual ordonat și verbalizat în registru simplu și elevat (instanțe în graful 2: 124).
- `NarrativeSubevent`: componentă atomică a unui eveniment complex (instanțe în graful 2: 0).
- `Character`: agent uman sau personaj participant la narațiune (instanțe în graful 2: 24).
- `CharacterState`: stare contextuală a unui personaj (instanțe în graful 2: 0).
- `NarrativeState`: starea generală de deschidere sau închidere a unui capitol (instanțe în graful 2: 26).
- `Decision`: alegere explicită ori dedusă a unui personaj (instanțe în graful 2: 0).
- `Motivation`: cauză internă a unei acțiuni; în graful 2 este de regulă atribut textual al evenimentului (instanțe în graful 2: 0).
- `Action`: acțiune atomică desprinsă dintr-un eveniment (instanțe în graful 2: 0).
- `Consequence`: efect imediat sau de durată; în graful 2 este de regulă atribut textual al evenimentului (instanțe în graful 2: 0).
- `Location`: spațiu în care are loc un eveniment (instanțe în graful 2: 14).
- `TimeContext`: reper temporal explicit sau relativ (instanțe în graful 2: 0).
- `Object`: obiect cu funcție narativă (instanțe în graful 2: 0).
- `Family`: grup familial relevant (instanțe în graful 2: 0).
- `Institution`: instituție socială, administrativă sau religioasă (instanțe în graful 2: 2).
- `SocialGroup`: categorie sau comunitate socială (instanțe în graful 2: 0).
- `Relationship`: relație reificată între personaje (instanțe în graful 2: 0).
- `Conflict`: opoziție interioară sau exterioară care organizează acțiunea (instanțe în graful 2: 5).
- `Theme`: temă literară susținută prin evenimente (instanțe în graful 2: 9).
- `Motif`: element recurent cu funcție compozițională (instanțe în graful 2: 1).
- `Symbol`: element cu semnificație simbolică argumentată (instanțe în graful 2: 0).
- `Value`: valoare socială, morală sau materială urmărită de personaje (instanțe în graful 2: 4).
- `Emotion`: stare afectivă relevantă (instanțe în graful 2: 0).
- `SocialStatus`: poziție socială contextuală (instanțe în graful 2: 0).
- `NarrativePerspective`: mod de organizare a perspectivei narative (instanțe în graful 2: 0).
- `LiteraryTechnique`: procedeu literar confirmat de sursele interpretative (instanțe în graful 2: 1).
- `Evidence`: unitate de probă; disponibilă în ontologie, dar compactată în referințe în graful 2 (instanțe în graful 2: 0).
- `SourceFragment`: fragment-sursă; disponibil în ontologie, compactat în referințele pe capitole (instanțe în graful 2: 0).
- `SourceDocument`: document-sursă canonic (instanțe în graful 2: 0).
- `OntologyClass`: clasă a vocabularului; declarată în ontologie fără noduri artificiale de instanțiere (instanțe în graful 2: 0).

## Relații controlate

Relațiile structurale (`part_of`, `has_part`, `has_chapter`, `chapter_of`) descriu ierarhia operei. Relațiile temporale (`occurs_before`, `immediately_precedes`, `immediately_follows`) fixează ordinea. Relațiile cauzale (`causes`, `contributes_to`, `enables`, `results_in`) explică dependențele dintre evenimente. Relațiile de participare și stare leagă personajele de acțiune. Relațiile tematice și simbolice sunt marcate ca interpretări.

- `instance_of`
- `subclass_of`
- `created_by`
- `part_of`
- `has_part`
- `has_chapter`
- `chapter_of`
- `occurs_in_chapter`
- `occurs_at`
- `occurs_before`
- `occurs_after`
- `immediately_precedes`
- `immediately_follows`
- `causes`
- `contributes_to`
- `enables`
- `prevents`
- `motivates`
- `results_in`
- `foreshadows`
- `resolves`
- `intensifies`
- `contrasts_with`
- `parallels`
- `has_participant`
- `participates_in`
- `initiates`
- `experiences`
- `observes`
- `discovers`
- `communicates_to`
- `hides_from`
- `helps`
- `opposes`
- `manipulates`
- `harms`
- `protects`
- `loves`
- `desires`
- `is_married_to`
- `is_parent_of`
- `is_child_of`
- `is_rival_of`
- `has_motivation`
- `has_consequence`
- `has_state_before`
- `has_state_after`
- `changes_state_of`
- `gains`
- `loses`
- `believes`
- `fears`
- `decides`
- `abandons_goal`
- `adopts_goal`
- `expresses_theme`
- `expresses_motif`
- `symbolizes`
- `supported_by`
- `derived_from_source`
- `has_simple_verbalization`
- `has_elevated_verbalization`
- `has_opening_state`
- `has_closing_state`
- `documents`
- `mentions`
- `has_evidence`
- `evokes_symbol`
- `expresses_value`
- `uses_technique`

## Tipuri de afirmații

- `explicit_fact`: fapt prezent direct în text sau rezumat.
- `explicit_motivation`: motivație formulată direct de narațiune/personaj.
- `inferred_motivation`: motivație dedusă, care necesită justificare contextuală.
- `literary_interpretation`: interpretare susținută de eseu și de fapte.
- `symbolic_interpretation`: semnificație simbolică argumentată.
- `uncertain`: informație ambiguă, niciodată prezentată drept certitudine.

## Exemple

- `EV_004 occurs_in_chapter CH_01` fixează apartenența unui eveniment.
- `EV_004 expresses_theme CONCEPT_001` leagă faptul de o temă, cu `assertion_type: literary_interpretation`.
- `EV_001 immediately_precedes EV_002` permite reconstrucția cronologică.
- `EV_037 causes EV_056` descrie o dependență cauzală între capitole.

## Reguli de extensie pentru alte opere

1. Se păstrează identificatori stabili și unici.
2. Orice eveniment are capitol, ordine locală/globală, cauză, efect, sursă și două verbalizări factualmente echivalente.
3. O relație poate indica numai noduri existente și folosește vocabularul controlat.
4. Interpretările nu sunt transformate în fapte și trebuie susținute de evenimente explicite.
5. Tipurile noi se adaugă simultan în ontologie și schemă, cu definiție și exemplu.
6. Pragurile cantitative se ating numai prin informație semantică utilă, fără duplicate sau noduri de umplutură.
