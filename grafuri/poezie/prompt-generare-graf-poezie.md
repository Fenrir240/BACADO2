# Prompt Standard pentru Generarea Knowledge Graph-ului unei Opere Lirice (Poezie)

---

## ROLUL TĂU

Acționează simultan ca:
1. **Inginer de Knowledge Graph** specializat în reprezentarea structurată a cunoștințelor;
2. **Analist literar** specializat în poezia românească canonică pentru Examenul de Bacalaureat;
3. **Proiectant de ontologii lirice și semiotice**;
4. **Specialist QA** pentru verificarea factuală și eliminarea halucinațiilor.

Trebuie să construiești un **Knowledge Graph complet, autosuficient și verificabil** pentru o operă lirică (poezie/poem) din programa de Bacalaureat (ex: *Luceafărul* de Mihai Eminescu, *Plumb* de George Bacovia, *Testament* de Tudor Arghezi, *Eu nu strivesc corola de minuni a lumii* de Lucian Blaga, *Riga Crypto și Lapona Enigel* de Ion Barbu).

---

## MATERIALE DISPONIBILE ȘI SURSE DE DATE

Vei primi următoarele materiale:
1. **Textul integral al poeziei** (sursa primară absolută pentru citate, strofe, versuri și imagini);
2. **Eseul-model / Comentariul critic normativ** (sursa pentru teme, curente literare, trăsături estetice, semnificații simbolice și interpretări academice);
3. **Opțional: Schema metrică și de prozodie** a textului poetic.

### Reguli stricte privind sursele:
- Textul poetic este sursa factuală principală: orice imagine artistică, figură de stil sau citat trebuie să aibă un corespondent exact în text (`verified_primary: true`).
- Eseul-model stabilește interpretările critice agreate de programa de Bacalaureat.
- **Interzis:** Nu inventa strofe, imagini, semnificații nesusținute sau anacronisme. Dacă o interpretare este ambiguă, marcheaz-o cu `status: "uncertain"`.

---

## OBIECTIVUL PRINCIPAL

Knowledge Graph-ul generat trebuie să fie **complet autosuficient**, permițând algoritmilor downstream din aplicație (`BacApp2-Qwen`) să genereze fără alte surse externe:
1. **Comentariul / Rezumatul semantic pe tablouri și secvențe lirice** (în dublu registru: simplu și elevat);
2. **Cele 3 scheme compoziționale de Bacalaureat**:
   - *Semnificația titlului*;
   - *Relația incipit–final / Simetrii compoziționale*;
   - *Relațiile de opoziție și corespondență (antiteze, planuri lirice)*;
3. **Încadrarea în curentul literar** (Romantism, Simbolism, Modernism, Neomodernism, Tradiționalism) cu cele 2 trăsături fundamentale argumentate prin nodurile grafului;
4. **Banca automată de 96+ itemi de testare** pe cele 8 tipologii cognitive adaptate pentru poezie (de la identificare directă până la sinteză filozofică).

---

## CONSTRÂNGERI CANTITATIVE ȘI DE CALITATE

Graful final trebuie să respecte următoarele standarde:
- **Noduri semantice reale:**
  - Pentru poeme ample (*Luceafărul*): **140 – 220 noduri**;
  - Pentru poezii scurte/medii (*Plumb*, *Testament*, *Corola*): **70 – 130 noduri**;
- **Relații semantice:** minimum **150 – 300 de relații controlate**;
- **Conectivitate:** minimum **95%** dintre noduri conectate la componenta principală;
- **Acoperire integrală:** 100% din strofe/tablouri trebuie să fie acoperite;
- **Ancorare primară:** 100% din nodurile `PoeticImage` și `FigureOfSpeech` trebuie să conțină citate exacte din text;
- **Zero noduri duplicate semantic** și zero relații către noduri inexistente.

---

## ONTOLOGIA GRAFULUI LIRIC (TIPURI DE NODURI)

Graful va fi compus din următoarele tipuri de entități:

### 1. Nivelul Macro-Structural
- `Work`: Opera literară modelată (titlu, autor, an, gen, specie lirică).
- `Author`: Autorul canonic.
- `LiteraryMovement`: Curentul literar principal (ex: Romantism, Simbolism, Modernism).
- `LiteraryTrait`: Trăsătură estetică specifică a curentului argumentată în operă.
- `PoeticSequence` / `LyricalTableau`: Diviziune compozițională majoră (tablou, parte, secvență de strofe).
- `Stanza`: Strofa individuală (număr, versuri, rol compozițional).

### 2. Nivelul Planurilor & Vocii Lirice
- `PoeticPlane`: Planul existențial sau spațial (ex: *planul cosmic*, *planul terestru*, *planul exterior/naturii*, *planul interior/conștiinței*, *planul lumii materiale*, *planul absolutului*).
- `PoeticVoice` / `LyricalEgo`: Instanța lirică (eul confesiv, eul contemplator, eul vizionar, măști lirice precum geniul sau îndrăgostitul).
- `PoeticAttitude`: Starea afectivă/intelectuală dominantă (angoasă, solitudine, extaz, detașare rațională, revoltă metafizică).

### 3. Nivelul Textual & Expresiv (Micro-Structural)
- `PoeticImage`: Imagine artistică senzorială (`sensory_type`: *vizuală, auditivă, olfactivă, tactilă, dinamică/motorie, cromatică, sinestezică*).
- `FigureOfSpeech`: Figură de stil / semantică (`figure_type`: *metaforă revelatorie, metaforă plasticizantă, antiteză, oximoron, epitet cromatic, personificare, sinestezie, alegorie, aliterație*).
- `PoeticMotif`: Laitmotiv sau motiv literar recurent (ex: *noaptea, teiul, luna, marea, plumbul, oglinda, cartea, zborul*).
- `PoeticSymbol`: Simbol polisemantic central (ex: *Luceafărul, sicriul de plumb, corola de minuni, amfora*).

### 4. Nivelul Tematic, Compozițional & Prozodic
- `Theme`: Tema centrală (condiția geniului, iubirea absolută, creația/arta poetică, moartea, timpul bivalent).
- `Conflict` / `IdeationalTension`: Opoziție sau tensiune de idei (ex: efemer vs. etern, materie vs. spirit).
- `CompositionalElement`: Elemente de construcție:
  - `titlul` (semnificație denotativă și conotativă);
  - `incipit_final` (relația dintre deschidere și încheiere, simetria discursului);
  - `relatii_opozitie_simetrie` (antitezele structurale și paralelismele sintactice).
- `ProsodicStructure`: Element de prozodie (măsură metrică, tip de rimă, ritm, refren).

---

## VOCABULARUL CONTROLAT DE RELAȚII (EDGES)

Fiecare muchie din graf trebuie să utilizeze exclusiv relațiile din vocabularul controlat:

### Relații Structurale & Ierarhice:
- `belongs_to_movement`: leagă `Work` de `LiteraryMovement`;
- `manifests_trait`: leagă `PoeticImage` sau `FigureOfSpeech` de `LiteraryTrait`;
- `has_sequence`: leagă `Work` de `PoeticSequence`;
- `contains_stanza`: leagă `PoeticSequence` de `Stanza`;
- `uses_prosodic_element`: leagă `Work` de `ProsodicStructure`.

### Relații Spațiale & ale Vocii Lirice:
- `situates_in_plane`: leagă `PoeticSequence` sau `PoeticImage` de `PoeticPlane`;
- `expressed_by_voice`: leagă `PoeticSequence` de `PoeticVoice`;
- `adopts_attitude`: leagă `PoeticVoice` de `PoeticAttitude`.

### Relații de Conținut Artistic & Simbolic:
- `evokes_image`: leagă `Stanza` sau `PoeticSequence` de `PoeticImage`;
- `realized_through`: leagă `PoeticImage` de `FigureOfSpeech`;
- `embodies_motif`: leagă `PoeticImage` de `PoeticMotif`;
- `anchors_symbol`: leagă `PoeticImage` sau `PoeticMotif` de `PoeticSymbol`;
- `expresses_theme`: leagă `PoeticImage` sau `PoeticSymbol` de `Theme`.

### Relații de Opoziție, Simetrie & Corespondență:
- `opposes` / `contrasts_with`: opoziție structurală (ex: *planul cosmic* $\leftrightarrow$ *planul terestru*);
- `mirrors_in_symmetry`: corespondență de simetrie (ex: *incipit* $\leftrightarrow$ *final*);
- `corresponds_to`: corespondență simbolică / sinestezică (ex: *decorul funerar exterior* $\leftrightarrow$ *vidul sufletesc interior*).

---

## STRUCTURA FORMALĂ A JSON-ULUI DE IEȘIRE

Rezultatul trebuie să fie un JSON valid, organizat după următorul contract strict:

```json
{
  "metadata": {
    "work": "Titlul Operei",
    "author": "Numele Autorului",
    "genre": "Liric",
    "species": "Specia Lirică (ex: Poem filozofic / Artă poetică / Elegie)",
    "movement": "Curentul Literar (ex: Romantism / Simbolism / Modernism)",
    "version": "2.0.0",
    "total_stanzas": 0,
    "total_sequences": 0
  },
  "ontology": {
    "node_types": [
      "Work", "Author", "LiteraryMovement", "LiteraryTrait", "PoeticSequence", 
      "Stanza", "PoeticPlane", "PoeticVoice", "PoeticAttitude", "PoeticImage", 
      "FigureOfSpeech", "PoeticMotif", "PoeticSymbol", "Theme", "CompositionalElement", "ProsodicStructure"
    ],
    "assertion_types": [
      "explicit_fact", 
      "literary_interpretation", 
      "symbolic_interpretation", 
      "prosodic_fact"
    ]
  },
  "sequences": [
    {
      "id": "SEQ_001",
      "number": 1,
      "title": "Titlul / Tema secvenței lirice",
      "stanza_range": [1, 7],
      "simple_verbalization": "Reconstituirea clară și accesibilă a ideii poetice.",
      "elevated_verbalization": "Interpretarea critică și academică a tabloului pentru eseul de Bacalaureat.",
      "dominant_plane": "PLANE_ID",
      "dominant_voice": "VOICE_ID"
    }
  ],
  "nodes": [
    {
      "id": "IMG_001",
      "type": "PoeticImage",
      "label": "Descriere scurtă a imaginii",
      "sensory_type": "vizuala / auditiva / sinestezie / motorie / cromatica",
      "quote": "Citatul exact din textul poeziei",
      "stanza": 1,
      "verified_primary": true,
      "importance": "high"
    },
    {
      "id": "FIG_001",
      "type": "FigureOfSpeech",
      "label": "Denumirea figurii (ex: Oximoronul naturii geniului)",
      "figure_type": "oximoron / metafora / antiteza / epitet",
      "quote": "Citatul exact",
      "literary_effect": "Efectul expresiv și semnificația critică.",
      "verified_primary": true,
      "importance": "high"
    }
  ],
  "edges": [
    {
      "source": "SEQ_001",
      "target": "IMG_001",
      "relation": "evokes_image",
      "assertion_type": "explicit_fact"
    },
    {
      "source": "IMG_001",
      "target": "FIG_001",
      "relation": "realized_through",
      "assertion_type": "literary_interpretation"
    },
    {
      "source": "PLANE_COSMIC",
      "target": "PLANE_TERESTRU",
      "relation": "opposes",
      "assertion_type": "literary_interpretation"
    }
  ]
}
```

---

## CHECKLIST DE VALIDARE ÎNAINTE DE FINALIZARE

1. ✅ **Ancorare Factuală:** Toate imaginile și figurile au asociat un citat direct din poezie?
2. ✅ **Acoperire Bacalaureat:** Sunt prezente cele 2 trăsături ale curentului literar? Sunt definite nodurile pentru Titlu, Incipit-Final și Relațiile de Opoziție?
3. ✅ **Dualitate de Limbaj:** Fiecare secvență lirică conține atât `simple_verbalization`, cât și `elevated_verbalization`?
4. ✅ **Validitate Grafică:** Toate identificatorii `source` și `target` din `edges` există în `nodes`?
5. ✅ **Fără Halucinații:** Nu există interpretări fanteziste sau nesusținute de textul primar și eseul-model critic?
