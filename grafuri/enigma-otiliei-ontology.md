# Ontologia knowledge graph-ului «Enigma Otiliei»

Ontologia păstrează vocabularul promptului folosit pentru graful 2 al operei «Ion» și îl extinde explicit cu `LiteraryMovement`, `LiteraryTrait` și `CompositionElement`.

## Tipuri de noduri

- `Action` - definit pentru extensie.
- `Author` - instanțiat.
- `Chapter` - instanțiat.
- `Character` - instanțiat.
- `CharacterState` - definit pentru extensie.
- `CompositionElement` - instanțiat.
- `Conflict` - instanțiat.
- `Consequence` - definit pentru extensie.
- `Decision` - definit pentru extensie.
- `Emotion` - definit pentru extensie.
- `Evidence` - definit pentru extensie.
- `Family` - definit pentru extensie.
- `Institution` - definit pentru extensie.
- `LiteraryMovement` - instanțiat.
- `LiteraryTechnique` - instanțiat.
- `LiteraryTrait` - instanțiat.
- `Location` - instanțiat.
- `Motif` - instanțiat.
- `Motivation` - definit pentru extensie.
- `NarrativeEvent` - instanțiat.
- `NarrativePerspective` - instanțiat.
- `NarrativeState` - instanțiat.
- `NarrativeSubevent` - definit pentru extensie.
- `Object` - definit pentru extensie.
- `Part` - definit pentru extensie.
- `Relationship` - definit pentru extensie.
- `SocialGroup` - definit pentru extensie.
- `SocialStatus` - definit pentru extensie.
- `SourceFragment` - definit pentru extensie.
- `Symbol` - instanțiat.
- `Theme` - instanțiat.
- `TimeContext` - definit pentru extensie.
- `Value` - definit pentru extensie.
- `Work` - instanțiat.

## Relații

- `authored_by` - folosită în graf.
- `belongs_to_literary_movement` - folosită în graf.
- `causes` - rezervată de vocabularul controlat.
- `changes_state_of` - folosită în graf.
- `chapter_of` - rezervată de vocabularul controlat.
- `communicates_to` - rezervată de vocabularul controlat.
- `contains` - folosită în graf.
- `contrasts_with` - folosită în graf.
- `contributes_to` - folosită în graf.
- `derived_from_source` - rezervată de vocabularul controlat.
- `desires` - rezervată de vocabularul controlat.
- `discovers` - rezervată de vocabularul controlat.
- `enables` - folosită în graf.
- `experiences` - rezervată de vocabularul controlat.
- `expresses_motif` - folosită în graf.
- `expresses_theme` - folosită în graf.
- `foreshadows` - rezervată de vocabularul controlat.
- `harms` - rezervată de vocabularul controlat.
- `has_chapter` - rezervată de vocabularul controlat.
- `has_characteristic` - folosită în graf.
- `has_closing_state` - folosită în graf.
- `has_composition_element` - folosită în graf.
- `has_concept` - folosită în graf.
- `has_consequence` - rezervată de vocabularul controlat.
- `has_elevated_verbalization` - rezervată de vocabularul controlat.
- `has_motivation` - rezervată de vocabularul controlat.
- `has_opening_state` - folosită în graf.
- `has_part` - rezervată de vocabularul controlat.
- `has_participant` - folosită în graf.
- `has_setting` - folosită în graf.
- `has_simple_verbalization` - rezervată de vocabularul controlat.
- `helps` - rezervată de vocabularul controlat.
- `hides_from` - rezervată de vocabularul controlat.
- `illustrated_by` - rezervată de vocabularul controlat.
- `illustrates` - folosită în graf.
- `immediately_follows` - folosită în graf.
- `immediately_precedes` - folosită în graf.
- `initiates` - rezervată de vocabularul controlat.
- `instance_of` - rezervată de vocabularul controlat.
- `intensifies` - folosită în graf.
- `involves` - folosită în graf.
- `is_child_of` - rezervată de vocabularul controlat.
- `is_friend_of` - folosită în graf.
- `is_married_to` - folosită în graf.
- `is_parent_of` - folosită în graf.
- `is_rival_of` - folosită în graf.
- `is_sibling_of` - folosită în graf.
- `is_uncle_of` - folosită în graf.
- `loves` - folosită în graf.
- `manipulates` - rezervată de vocabularul controlat.
- `motivates` - rezervată de vocabularul controlat.
- `observes` - rezervată de vocabularul controlat.
- `occurs_after` - folosită în graf.
- `occurs_at` - folosită în graf.
- `occurs_before` - folosită în graf.
- `occurs_in_chapter` - folosită în graf.
- `opposes` - rezervată de vocabularul controlat.
- `parallels` - rezervată de vocabularul controlat.
- `part_of` - rezervată de vocabularul controlat.
- `participates_in` - rezervată de vocabularul controlat.
- `prepares` - folosită în graf.
- `prevents` - rezervată de vocabularul controlat.
- `protects` - rezervată de vocabularul controlat.
- `resolves` - rezervată de vocabularul controlat.
- `results_in` - folosită în graf.
- `subclass_of` - rezervată de vocabularul controlat.
- `supported_by` - folosită în graf.
- `symbolizes` - rezervată de vocabularul controlat.

## Reguli de extensie

- ID-urile trebuie să fie unice și stabile.
- Un nod narativ trebuie să indice capitolul, ordinea, sursa și verbalizările simplă și elevată.
- O muchie trebuie să folosească ID-uri existente și minimum o referință-sursă.
- Interpretările nu pot fi marcate drept fapte explicite.
- Pentru o altă operă se păstrează ontologia, dar se înlocuiesc toate instanțele și dovezile factuale.
