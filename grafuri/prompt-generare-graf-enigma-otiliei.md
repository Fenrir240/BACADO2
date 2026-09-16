
ROLUL TĂU

Acționează simultan ca:

1. inginer de knowledge graph;
2. analist literar specializat în literatura română;
3. specialist în modelarea narațiunilor;
4. proiectant de ontologii;
5. specialist QA pentru verificarea datelor.

Trebuie să construiești un knowledge graph complet, autosuficient și verificabil pentru opera:

ENIGMA OTILIEI
de
GEORGE CĂLINESCU

MATERIALE DISPONIBILE

Materialele concrete pentru această rulare sunt:

- `opere_pdf/enigma-otiliei.pdf` — textul integral și sursa factuală principală;
- `modele_eseuri/enigma_otiliei.md` — eseul-model și sursa normativă pentru trăsăturile curentului literar abordate în eseu;
- `cercetare/graf2/knowledge-graph.json` — model structural pentru dimensiunea și ontologia grafului 2 al operei „Ion”, fără a fi folosit ca sursă factuală pentru „Enigma Otiliei”.


Vei primi următoarele materiale:

- textul integral al operei în format PDF;
- un rezumat al operei;
- un eseu-model;
- opțional, un knowledge graph realizat anterior;
- opțional, acces la structura vizuală a unei alte opere deja implementate în aplicație.

Rolurile surselor sunt:

1. Textul integral al operei este sursa factuală principală.
2. Rezumatul este folosit pentru verificarea firului narativ și identificarea evenimentelor importante.
3. Eseul-model este folosit pentru teme, conflicte, simboluri, relații și interpretări literare.
4. Graful anterior poate fi folosit ca punct de pornire, dar trebuie verificat integral.
5. Implementarea existentă poate fi folosită doar ca model structural și vizual, nu ca sursă factuală.

Nu folosi informații din memoria ta dacă acestea nu pot fi confirmate din materialele furnizate.

Dacă o informație nu apare clar în surse:

- nu o inventa;
- marcheaz-o cu `status: "uncertain"`;
- precizează motivul incertitudinii;
- indică sursa sau pasajul care produce ambiguitatea.

OBIECTIVUL PRINCIPAL

Construiește un knowledge graph narativ care să permită reconstruirea completă, exclusiv din graf, a rezumatului fiecărui capitol:

- într-un limbaj simplu, clar și accesibil unui elev;
- într-un limbaj elevat, potrivit pentru pregătirea examenului de Bacalaureat.

Graful trebuie să fie autosuficient.

După construirea lui, un alt algoritm trebuie să poată genera rezumatele fără să mai citească PDF-ul, rezumatul sau eseul inițial.

Nu introduce rezumatul complet al capitolului într-un singur nod. Rezumatul trebuie să poată fi reconstruit prin parcurgerea ordonată a evenimentelor, stărilor, cauzelor și consecințelor din graf.

CONSTRÂNGERI CANTITATIVE

Graful final trebuie să conțină:

- minimum 200 de noduri semantice reale si maxim 300 noduri semantice reale;
- toate capitolele operei;
- toate evenimentele importante;
- suficiente subevenimente pentru reconstruirea narațiunii;
- minimum 300 de relații semantice;
- minimum 95% dintre noduri conectate la componenta principală;
- zero noduri duplicate semantic;
- zero relații care indică noduri inexistente;
- zero capitole fără evenimente;
- zero evenimente fără sursă;
- zero evenimente fără poziție în ordinea narativă.

 Nodurile trebuie să conțină informație reală. Este interzisă atingerea pragului prin:

- duplicarea personajelor;
- reformularea aceleiași informații în noduri diferite;
- crearea unor noduri fără utilitate narativă;
- transformarea fiecărui cuvânt sau fiecărei propoziții într-un nod;
- folosirea excesivă a identificatorilor sau metadatelor;
- inventarea unor evenimente secundare.

Cel puțin 55% dintre noduri trebuie să fie legate direct de narațiune: evenimente, subevenimente, stări, decizii, schimbări, cauze sau consecințe.

MODELUL ONTOLOGIC

Folosește un model inspirat de Wikidata, dar adaptat unei opere literare.

Fiecare nod trebuie să aibă:

- identificator unic și stabil;
- tip;
- etichetă;
- descriere autosuficientă;
- capitol sau capitole asociate;
- surse;
- nivel de importanță;
- nivel de certitudine;
- eventuale denumiri alternative.

Tipurile minime de noduri trebuie să includă:

- `Work`;
- `Author`;
- `Part`;
- `Chapter`;
- `NarrativeEvent`;
- `NarrativeSubevent`;
- `Character`;
- `CharacterState`;
- `Decision`;
- `Motivation`;
- `Action`;
- `Consequence`;
- `Location`;
- `TimeContext`;
- `Object`;
- `Family`;
- `Institution`;
- `SocialGroup`;
- `Relationship`;
- `Conflict`;
- `Theme`;
- `Motif`;
- `Symbol`;
- `Value`;
- `Emotion`;
- `SocialStatus`;
- `NarrativePerspective`;
- `LiteraryTechnique`;
- `LiteraryMovement`;
- `LiteraryTrait`;
- `CompositionElement`;
- `Evidence`;
- `SourceFragment`.

Poți introduce și alte tipuri dacă sunt necesare, dar trebuie definite în schema grafului.



DELIMITAREA OBLIGATORIE A CAPITOLELOR PENTRU „ENIGMA OTILIEI”

Opera trebuie modelată în exact 20 de capitole, în ordinea I-XX. Nu deduce granițele exclusiv din schimbarea paginii și nu confunda anexele critice cu textul romanului.

În PDF-ul furnizat, delimitarea verificată este:

- Capitolul I: paginile PDF 11-30;
- Capitolul II: paginile PDF 31-45;
- Capitolul III: paginile PDF 46-61;
- Capitolul IV: paginile PDF 62-72;
- Capitolul V: paginile PDF 73-82;
- Capitolul VI: paginile PDF 83-102;
- Capitolul VII: paginile PDF 103-119;
- Capitolul VIII: paginile PDF 120-154;
- Capitolul IX: paginile PDF 155-173;
- Capitolul X: paginile PDF 174-190;
- Capitolul XI: paginile PDF 191-213;
- Capitolul XII: paginile PDF 214-233;
- Capitolul XIII: paginile PDF 234-254;
- Capitolul XIV: paginile PDF 255-282;
- Capitolul XV: paginile PDF 283-306;
- Capitolul XVI: paginile PDF 307-326;
- Capitolul XVII: paginile PDF 327-364;
- Capitolul XVIII: paginile PDF 365-403;
- Capitolul XIX: paginile PDF 404-445;
- Capitolul XX: paginile PDF 446-485.

Paginile PDF 486-500 conțin aparatul critic și nu fac parte din narațiunea romanului. Fiecare eveniment trebuie atribuit capitolului în care apare efectiv, iar pagina de început și pagina de sfârșit trebuie păstrate în metadatele capitolului.

MODELAREA CAPITOLELOR

Pentru fiecare capitol creează obligatoriu:

1. un nod `Chapter`;
2. o stare inițială a capitolului;
3. o stare finală a capitolului;
4. o listă total ordonată de evenimente;
5. subevenimentele necesare;
6. personajele participante;
7. locurile;
8. contextul temporal;
9. cauzele fiecărui eveniment;
10. consecințele fiecărui eveniment;
11. schimbările de stare ale personajelor;
12. motivațiile explicite;
13. motivațiile deduse, marcate separat;
14. conflictele active;
15. temele, motivele și simbolurile relevante;
16. conexiuni cu evenimente din capitolele anterioare;
17. evenimentele care pregătesc capitolele următoare;
18. importanța evenimentului pentru firul narativ general.

Fiecare eveniment trebuie să conțină cel puțin:

- `event_id`;
- `chapter_id`;
- `chapter_order`;
- `global_order`;
- `title`;
- `canonical_description`;
- `participants`;
- `location`;
- `time_context`;
- `preconditions`;
- `causes`;
- `action`;
- `immediate_effects`;
- `long_term_effects`;
- `state_transitions`;
- `motivations`;
- `conflicts`;
- `themes`;
- `importance`;
- `source_refs`;
- `confidence`;
- `simple_narration`;
- `elevated_narration`;
- `simple_transition`;
- `elevated_transition`.

`simple_narration` trebuie să exprime evenimentul:

- în propoziții clare;
- cu vocabular accesibil;
- fără formulări academice inutile;
- fără pierderea informației importante.

`elevated_narration` trebuie să exprime exact același fapt:

- într-un limbaj mai bogat și coerent;
- potrivit unui elev care se pregătește pentru Bacalaureat;
- fără exagerări;
- fără informații suplimentare care nu există în graf;
- fără interpretări prezentate drept fapte.

Cele două formulări trebuie să păstreze același conținut factual.



MODELAREA CURENTULUI LITERAR

Creează obligatoriu:

1. un nod `LiteraryMovement` pentru curentul în care se încadrează opera;
2. noduri `LiteraryTrait` distincte pentru trăsăturile curentului;
3. muchii explicite între operă, curent, trăsături și dovezile narative;
4. explicații autosuficiente, dovezi din operă și utilizarea fiecărei trăsături în eseu.

Pentru „Enigma Otiliei”, curentul trebuie determinat din surse și modelat ca realism balzacian. Eseul-model este sursa normativă pentru trăsăturile care vor fi abordate în eseu. Creează și evidențiază exact aceste două trăsături:

- verosimilitatea evenimentelor prin cronotopul precis;
- tipologiile umane, în special avarul și parvenitul balzacian.

Pot exista și alte trăsături documentate pentru explicarea curentului, dar ele trebuie marcate separat și nu trebuie prezentate drept trăsături alese pentru eseul-model. Leagă fiecare trăsătură de evenimente, personaje, locuri sau tehnici literare care o demonstrează.

MODELAREA ELEMENTELOR COMPOZIȚIONALE

Creează obligatoriu noduri semantice distincte de tip `CompositionElement` pentru:

1. `Titlul`;
2. `Conflictul`;
3. `Relația incipit-final`.

Fiecare element compozițional trebuie să conțină:

- definiția și rolul său în operă;
- componentele schemei explicative;
- minimum două dovezi sau legături către evenimentele relevante;
- explicația relației dintre dovezi și interpretare;
- formulare potrivită pentru utilizarea într-un eseu de Bacalaureat;
- surse și tipul afirmației.

Leagă opera de cele trei elemente prin `has_composition_element`. Leagă elementele de evenimente prin `supported_by` sau `illustrated_by`, iar interpretările de faptele narative care le justifică. Conflictul ca element compozițional poate agrega nodurile de conflict particulare, dar nu trebuie confundat cu un singur conflict narativ.

STĂRILE PERSONAJELOR

Pentru personajele importante, modelează evoluția lor pe capitole.

O stare trebuie să poată descrie, unde este relevant:

- starea emoțională;
- situația familială;
- situația socială;
- situația materială;
- relațiile active;
- obiectivele;
- dorințele;
- temerile;
- conflictele interioare;
- conflictele exterioare;
- informațiile cunoscute personajului;
- informațiile necunoscute personajului;
- schimbarea produsă de un eveniment.

Folosește relații de forma:

- `has_state_before`;
- `has_state_after`;
- `changes_state_of`;
- `gains`;
- `loses`;
- `discovers`;
- `believes`;
- `desires`;
- `fears`;
- `decides`;
- `abandons_goal`;
- `adopts_goal`.

Nu presupune că naratorul, cititorul și personajele cunosc aceleași informații.

RELAȚII OBLIGATORII

Definește un vocabular controlat de relații. Acesta trebuie să includă cel puțin:

- `instance_of`;
- `subclass_of`;
- `part_of`;
- `has_part`;
- `has_chapter`;
- `chapter_of`;
- `occurs_in_chapter`;
- `occurs_at`;
- `occurs_before`;
- `occurs_after`;
- `immediately_precedes`;
- `immediately_follows`;
- `causes`;
- `contributes_to`;
- `enables`;
- `prevents`;
- `motivates`;
- `results_in`;
- `foreshadows`;
- `resolves`;
- `intensifies`;
- `contrasts_with`;
- `parallels`;
- `participates_in`;
- `initiates`;
- `experiences`;
- `observes`;
- `discovers`;
- `communicates_to`;
- `hides_from`;
- `helps`;
- `opposes`;
- `manipulates`;
- `harms`;
- `protects`;
- `loves`;
- `desires`;
- `is_married_to`;
- `is_parent_of`;
- `is_child_of`;
- `is_rival_of`;
- `has_motivation`;
- `has_consequence`;
- `changes_state_of`;
- `expresses_theme`;
- `expresses_motif`;
- `symbolizes`;
- `supported_by`;
- `derived_from_source`;
- `has_simple_verbalization`;
- `has_elevated_verbalization`;
- `belongs_to_literary_movement`;
- `has_characteristic`;
- `has_composition_element`;
- `illustrated_by`.

Pentru ordine, cauzalitate și relațiile dintre personaje, folosește muchii explicite. Nu lăsa informațiile importante ascunse doar în descrierile textuale.

DISTINCȚIA DINTRE FAPT ȘI INTERPRETARE

Separă strict:

- faptele narative explicite;
- motivațiile explicite;
- motivațiile deduse;
- interpretările literare;
- simbolurile;
- ipotezele;
- informațiile incerte.

Fiecare afirmație trebuie să aibă un câmp:

`assertion_type`, cu una dintre valorile:

- `explicit_fact`;
- `explicit_motivation`;
- `inferred_motivation`;
- `literary_interpretation`;
- `symbolic_interpretation`;
- `uncertain`.

Pentru afirmațiile deduse sau interpretative explică în câmpul `reasoning_note` ce fapte din graf susțin interpretarea.

Nu transforma interpretările din eseul-model în evenimente narative.

SURSE ȘI TRASABILITATE

Fiecare nod narativ și fiecare relație importantă trebuie să conțină minimum o referință.

Referința trebuie să includă, când informația este disponibilă:

- `source_id`;
- tipul sursei;
- titlul sursei;
- numărul paginii PDF;
- capitolul;
- un fragment scurt sau o parafrază de identificare;
- nivelul de certitudine.

Exemplu:

{
  "source_id": "SRC_PDF_001",
  "source_type": "primary_text",
  "page": 127,
  "chapter": "Capitolul IV",
  "evidence": "Fragmentul în care personajul intră noaptea în casă",
  "confidence": 1.0
}

Dacă numerotarea PDF-ului diferă de numerotarea tipărită, păstrează ambele valori.

SCHEMA JSON

Creează un fișier JSON cu următoarea structură generală:

{
  "metadata": {},
  "sources": [],
  "ontology": {
    "node_types": [],
    "relationship_types": [],
    "assertion_types": []
  },
  "nodes": [],
  "edges": [],
  "chapters": [],
  "reconstruction_profiles": {},
  "validation": {}
}

Structura unui nod trebuie să respecte aproximativ forma:

{
  "id": "EV_CH04_007",
  "type": "NarrativeEvent",
  "label": "...",
  "description": "...",
  "chapter_ids": ["CH04"],
  "importance": "major",
  "confidence": 1.0,
  "assertion_type": "explicit_fact",
  "source_refs": ["REF_00451"],
  "attributes": {}
}

Structura unei relații trebuie să respecte aproximativ forma:

{
  "id": "EDGE_000451",
  "source": "EV_CH04_007",
  "predicate": "causes",
  "target": "EV_CH04_008",
  "qualifiers": {
    "chapter": "CH04",
    "certainty": 1.0
  },
  "assertion_type": "explicit_fact",
  "source_refs": ["REF_00451"]
}

Nu stoca referințele dintre noduri doar sub formă de text. `source` și `target` trebuie să fie identificatori valizi.

RECONSTRUIREA REZUMATELOR

Definește două profiluri de reconstrucție.

Profilul `simple`:

- folosește evenimentele majore și medii;
- respectă ordinea narativă;
- folosește `simple_narration`;
- include cauzele necesare pentru înțelegere;
- explică clar cine face acțiunea;
- evită vocabularul dificil;
- produce un text coerent, nu o listă de propoziții independente.

Profilul `elevated`:

- folosește aceleași evenimente factuale;
- folosește `elevated_narration`;
- include tranziții mai elaborate;
- poate integra teme și conflicte confirmate;
- diferențiază faptele de interpretări;
- nu introduce informații care nu există în graf;
- produce un rezumat potrivit pentru pregătirea la Bacalaureat.

Pentru fiecare capitol trebuie să poată fi generate cel puțin:

- un rezumat simplu scurt;
- un rezumat simplu complet;
- un rezumat elevat scurt;
- un rezumat elevat complet.

Rezumatul complet trebuie să includă toate evenimentele cu importanță `major` și `medium`.

Rezumatul scurt trebuie să includă toate evenimentele `major` și doar evenimentele `medium` necesare pentru continuitate.

REGULI DE COERENȚĂ NARATIVĂ

La reconstruirea rezumatului:

- introdu personajele înainte de folosirea pronumelor;
- nu utiliza un personaj înainte de prima lui apariție;
- păstrează ordinea evenimentelor;
- include cauza înaintea consecinței;
- precizează locul numai când este relevant;
- evită repetarea informației;
- păstrează continuitatea dintre capitole;
- explică schimbările bruște de stare;
- nu combina evenimente care au participanți sau cauze diferite;
- nu prezenta o motivație dedusă drept fapt explicit.

FIȘIERELE DE LIVRAT

Lucrează într-un director separat și nu modifica aplicația existentă.

Livrează:

1. `knowledge-graph.json`
   - graful complet;
   - minimum 200 de noduri si maxim 300;
   - minimum 300 de relații.

2. `knowledge-graph.schema.json`
   - schema JSON;
   - tipurile permise;
   - câmpurile obligatorii;
   - enumerările;
   - regulile de validare.

3. `ontology.md`
   - explicația tipurilor de noduri;
   - explicația relațiilor;
   - exemple de folosire;
   - regulile de extensie pentru alte opere.

4. `chapter-reconstructions.md`
   - pentru fiecare capitol:
     - rezumat simplu complet;
     - rezumat elevat complet;
     - lista nodurilor folosite pentru fiecare propoziție.

5. `coverage-matrix.md`
   - fiecare capitol;
   - paginile-sursă;
   - numărul de evenimente;
   - numărul de personaje;
   - numărul de relații cauzale;
   - numărul de schimbări de stare;
   - problemele sau incertitudinile detectate.

6. `validation-report.md`
   - numărul exact de noduri;
   - numărul exact de relații;
   - distribuția nodurilor pe tipuri;
   - nodurile orfane;
   - relațiile invalide;
   - duplicatele;
   - capitolele incomplete;
   - evenimentele fără sursă;
   - rezultatul testului de reconstruire.

7. `knowledge-graph.html`
   - vizualizare interactivă autosuficientă;
   - fără dependențe externe obligatorii;
   - căutare după nod;
   - filtrare după capitol;
   - filtrare după tip;
   - filtrare după personaj;
   - filtrare după importanță;
   - afișarea surselor;
   - vizualizarea cronologică a evenimentelor;
   - generarea rezumatului simplu sau elevat exclusiv din graf.

Vizualizarea HTML este doar o reprezentare. Sursa canonică a datelor trebuie să rămână fișierul JSON.

PROCESUL OBLIGATORIU

Execută sarcina în următoarea ordine:

Etapa 1 — Auditul surselor

- citește integral materialele;
- identifică structura operei;
- identifică toate capitolele;
- verifică paginile lipsă sau imposibil de citit;
- raportează eventualele probleme înainte de generare dacă acestea blochează completitudinea.

Etapa 2 — Proiectarea ontologiei

- definește tipurile de noduri;
- definește relațiile;
- definește regulile de identificare;
- definește regulile de proveniență.

Etapa 3 — Extragerea faptelor

- extrage personajele, locurile, evenimentele, obiectele și instituțiile;
- separă faptele de interpretări;
- atașează sursele.

Etapa 4 — Modelarea narațiunii

- ordonează evenimentele în interiorul fiecărui capitol;
- creează legături cauzale;
- creează tranziții de stare;
- creează legături între capitole.

Etapa 5 — Extinderea semantică

- adaugă teme, motive, simboluri, conflicte și tehnici literare;
- leagă fiecare interpretare de faptele care o susțin.

Etapa 6 — Verificarea pragului

- verifică minimum 200 de noduri si maxim 300;
- dacă sunt mai puține, identifică informații reale care nu au fost încă modelate;
- nu adăuga umplutură;
- nu opri procesul până când pragul nu este atins în mod semantic justificat.

Etapa 7 — Testul de autosuficiență

Simulează că nu mai ai acces la materialele originale.

Folosind exclusiv graful:

- reconstruiește rezumatul fiecărui capitol în limbaj simplu;
- reconstruiește același rezumat în limbaj elevat;
- verifică dacă toate personajele, cauzele și consecințele sunt inteligibile;
- identifică informațiile lipsă;
- completează graful din surse;
- repetă testul până când rezumatele sunt coerente și complete.

Etapa 8 — Validarea finală

Rulează verificări automate pentru:

- identificatori unici;
- noduri duplicate;
- noduri orfane;
- muchii invalide;
- surse inexistente;
- ordine narativă incompletă;
- cicluri imposibile în relațiile temporale;
- evenimente fără participanți;
- evenimente fără capitol;
- evenimente fără verbalizare simplă;
- evenimente fără verbalizare elevată;
- contradicții între stările personajelor;
- afirmații interpretative marcate greșit drept fapte.

CRITERII DE ACCEPTARE

Nu declara sarcina finalizată până când toate condițiile sunt îndeplinite:

- există minimum 200 de noduri semantice reale si maxim 300 noduri semantice reale;
- există minimum 300 de relații;
- toate capitolele sunt reprezentate;
- fiecare capitol are o ordine completă a evenimentelor;
- toate evenimentele importante au cauze și consecințe;
- fiecare eveniment are sursă;
- fiecare eveniment are verbalizare simplă și elevată;
- rezumatul fiecărui capitol poate fi generat exclusiv din graf;
- nicio propoziție din rezumatele de validare nu conține informații absente din graf;
- fiecare propoziție generată indică nodurile și relațiile care o susțin;
- graful nu conține umplutură sau duplicate;
- toate fișierele trec validarea.

RAPORTAREA FINALĂ

La final, răspunde concis și precizează:

- directorul în care ai salvat fișierele;
- numărul exact de noduri;
- numărul exact de relații;
- numărul capitolelor;
- numărul evenimentelor și subevenimentelor;
- numărul afirmațiilor cu sursă;
- numărul eventualelor incertitudini;
- rezultatul testelor;
- dacă rezumatele simple și elevate au fost reconstruite exclusiv din graf.

Nu pretinde că validarea a reușit dacă nu ai rulat efectiv verificările.
Nu reduce dimensiunea grafului pentru a economisi timp sau spațiu.
Nu modifica proiectul existent.
Nu te opri după realizarea unei demonstrații sau a câtorva capitole.
Livrează graful complet pentru întreaga operă.
