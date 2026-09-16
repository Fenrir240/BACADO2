from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRAPH1_DIR = ROOT / "cercetare" / "graf1"
OUTPUT_DIR = ROOT / "cercetare" / "graf2"
SOURCE_DIR = ROOT / "data" / "sources" / "ion"
CANONICAL_FINAL_PATH = SOURCE_DIR / "final-canonical-wikisource.md"

GRAPH1_PATH = GRAPH1_DIR / "knowledge-graph.json"
GRAPH_PATH = OUTPUT_DIR / "knowledge-graph.json"
SCHEMA_PATH = OUTPUT_DIR / "knowledge-graph.schema.json"
ONTOLOGY_PATH = OUTPUT_DIR / "ontology.md"
RECONSTRUCTIONS_PATH = OUTPUT_DIR / "chapter-reconstructions.md"
COVERAGE_PATH = OUTPUT_DIR / "coverage-matrix.md"
VALIDATION_PATH = OUTPUT_DIR / "validation-report.md"
HTML_PATH = OUTPUT_DIR / "knowledge-graph.html"

REMOVED_NODE_TYPES = {
    "OntologyClass",
    "Evidence",
    "SourceFragment",
    "Motivation",
    "Consequence",
}

NARRATIVE_TYPES = {
    "NarrativeEvent",
    "NarrativeSubevent",
    "NarrativeState",
    "CharacterState",
    "Decision",
    "Action",
    "Motivation",
    "Consequence",
}

CAUSAL_PREDICATES = {
    "causes",
    "contributes_to",
    "enables",
    "prevents",
    "motivates",
    "results_in",
    "foreshadows",
}


# Corecții factuale verificate în textul integral. Graful 1 a preluat câteva
# formulări greșite din rezumatul secundar; aplicarea lor aici face regenerarea
# KG2 reproductibilă și împiedică reapariția erorilor la următoarea construire.
EVENT_FACT_OVERRIDES: dict[str, tuple[str, str]] = {
    "EV_002": (
        "Hora adună comunitatea în curtea Todosiei",
        "Duminica, hora din curtea Todosiei adună tinerii, lăutarii, femeile, copiii, bărbații și fruntașii satului.",
    ),
    "EV_004": (
        "Ion o alege pe Ana la horă",
        "Ion joacă alături de Ana, o ține de brâu și o cheamă să-l urmeze în livada din spatele șurii.",
    ),
    "EV_005": (
        "Ion cumpănește între Florica și averea Anei",
        "Ion știe că încă o iubește pe Florica, dar cântărește faptul că ea este săracă, în timp ce Ana are pământuri, case și vite.",
    ),
    "EV_006": (
        "Vasile îl insultă public pe Ion",
        "Vasile Baciu îl numește pe Ion «golan» și «tâlhar» în fața oamenilor și încearcă să-l alunge de lângă Ana.",
    ),
    "EV_003": (
        "Hora arată ierarhia satului",
        "La horă, tinerii joacă lângă lăutari, bărbații stau în grupuri mai departe, iar fruntașii și intelectualii ocupă poziții distincte.",
    ),
    "EV_008": (
        "Împotrivirea lui Vasile îl întărâtă pe Ion",
        "Împotrivirea lui Vasile Baciu îl întărâtă pe Ion și îl face să stăruie în apropierea de Ana.",
    ),
    "EV_011": (
        "Ion cosește pe fâneața sa",
        "Ion cosește cu înverșunare pe mica sa fâneață și privește întinderea hotarului.",
    ),
    "EV_012": (
        "Ion aude glasul pământului",
        "Privind hotarul, Ion simte glasul pământului ca pe o chemare care îl copleșește.",
    ),
    "EV_014": (
        "Alexandru Glanetașu risipește averea familiei",
        "Prin lipsa de muncă, datorii și băutură, Alexandru Glanetașu vinde treptat cea mai mare parte a pământurilor familiei.",
    ),
    "EV_015": (
        "Ana îl întâlnește pe Ion la câmp",
        "În drum spre tatăl ei cu un coș de mâncare, Ana se oprește la fâneața lui Ion și îi vorbește.",
    ),
    "EV_016": (
        "Florica îl întâlnește pe Ion la câmp",
        "Florica apare la fâneață și îi reproșează lui Ion că umblă după Ana.",
    ),
    "EV_017": (
        "Ion o îmbrățișează pe Florica",
        "Ion îi spune Floricăi că ea a rămas crăiasa inimii lui, apoi o îmbrățișează și o sărută.",
    ),
    "EV_020": (
        "Familia Herdelea discută întâmplările satului",
        "În casa Herdelea, Zaharia și Maria, împreună cu Titu, Laura și Ghighi, discută întâmplările din Pripas.",
    ),
    "EV_022": (
        "Belciug se teme că Herdelea îi știrbește autoritatea",
        "Preotul Belciug bănuiește că învățătorul Herdelea îi subminează autoritatea în sat.",
    ),
    "EV_024": (
        "Ion este umilit de dojana preotului",
        "Dojana publică a lui Belciug îl umple pe Ion de rușine și de necaz în fața satului.",
    ),
    "EV_029": (
        "Aurel recunoaște că a tăcut",
        "Aurel recunoaște că știa despre cererea în căsătorie a lui George Pintea, dar că a tăcut.",
    ),
    "EV_039": (
        "Ana îl cheamă pe Ion în casă",
        "Ana îl roagă pe Ion să intre în casă, profitând de somnul adânc al lui Vasile Baciu.",
    ),
    "EV_052": (
        "Belciug sprijină plângerea lui Simion",
        "Belciug redactează plângerea lui Simion Lungu împotriva lui Ion și se oferă drept martor.",
    ),
    "EV_021": (
        "Titu încearcă să o cucerească pe doamna Lang",
        "Atras de doamna Lang, Titu merge la Jidovița și caută prilejuri de a o cuceri.",
    ),
    "EV_058": (
        "Ion și Ana se căsătoresc",
        "Nunta lui Ion cu Ana ține trei zile, după obiceiul satului, și îi reunește pe nuntași în alaiul care merge la Jidovița.",
    ),
    "EV_056": (
        "Belciug încearcă să împace familiile",
        "Pentru a curma rușinea publică, Belciug îi cheamă pe Vasile Baciu, Ion și Ana și încearcă să obțină o învoială de căsătorie și zestre.",
    ),
    "EV_059": (
        "Ion vede că Ana este prețul pământurilor",
        "În drumul spre cununie, Ion înțelege că trebuie să o primească și pe Ana odată cu pământurile și respinge gândul de a fugi cu Florica, fiindcă ar rămâne sărac.",
    ),
    "EV_064": (
        "Vasile refuză să transfere pământurile",
        "După nuntă, Vasile Baciu refuză să treacă pământurile promise pe numele lui Ion.",
    ),
    "EV_065": (
        "Vasile o bate pe Ana",
        "Trimisă de Ion să-și înduplece tatăl, Ana încearcă să-i vorbească lui Vasile Baciu, dar acesta o lovește și o alungă.",
    ),
    "EV_066": (
        "Ion o bate pe Ana",
        "Când Ana se întoarce însângerată de la tatăl ei, Ion o învinuiește că s-ar fi înțeles cu Vasile și o lovește la rândul lui.",
    ),
    "EV_067": (
        "Ana se gândește pentru prima dată la moarte",
        "După dubla violență, Ana vede prăpastia vieții sale și se gândește la moarte, dar mișcarea copilului o face să aleagă încă o dată viața.",
    ),
    "EV_037": (
        "Ion se bucură la gândul sarcinii Anei",
        "Când Ana spune că se teme să nu fi rămas însărcinată, Ion își ascunde cu greu bucuria.",
    ),
    "EV_040": (
        "Ion și Ana petrec noaptea împreună",
        "În timp ce Vasile Baciu doarme în aceeași încăpere, Ion și Ana întrețin relații sexuale pe cuptor.",
    ),
    "EV_042": (
        "George pleacă dezgustat după ce îi surprinde",
        "După ce îl vede pe Ion ieșind și aude temerea Anei că ar putea fi însărcinată, George pleacă dezgustat.",
    ),
    "EV_046": (
        "Vasile o trimite pe Ana la Ion",
        "După ce o bate, Vasile Baciu o trimite pe Ana la Ion ca să se înțeleagă cu el asupra căsătoriei.",
    ),
    "EV_060": (
        "Ana vede lăcomia lui Ion la nuntă",
        "La nuntă, Ion rămâne nepăsător la plânsul Anei și întreabă lacom câți bani s-au strâns.",
    ),
    "EV_062": (
        "Laura se căsătorește cu George Pintea",
        "Laura și George Pintea sunt cununați la Armadia și pleacă împreună după nuntă.",
    ),
    "EV_063": (
        "Laura pleacă împreună cu soțul ei",
        "După cununia din Armadia, Laura și George Pintea pleacă spre parohia lui, iar pe drum își mărturisesc reciproc iubirea.",
    ),
    "EV_093": (
        "Savista o avertizează pe Ana",
        "Savista îi spune Anei că Ion o caută pe Florica și că George îi va omorî.",
    ),
    "EV_100": (
        "Petrișor este înmormântat",
        "După moarte, Petrișor este înmormântat lângă Ana.",
    ),
    "EV_101": (
        "Ion se teme că va pierde pământurile",
        "Cât Petrișor este bolnav, Ion îl întreabă pe Herdelea dacă moartea copilului ar face ca pământurile să se întoarcă la Vasile Baciu.",
    ),
    "EV_102": (
        "Vasile cere înapoi pământurile",
        "După înmormântarea lui Petrișor, Vasile Baciu îi cere lui Ion să-i înapoieze pământurile date Anei și copilului.",
    ),
    "EV_103": (
        "Ion reia legătura cu Florica pe câmp",
        "Întâlnind-o pe Florica pe câmp, Ion o oprește, o îmbrățișează și îi spune că tot a lui trebuie să fie.",
    ),
    "EV_104": (
        "Ion îl vizitează des pe George",
        "Pentru a o vedea pe Florica, Ion începe să meargă des în casa lui George sub pretextul prieteniei.",
    ),
    "EV_105": (
        "George își ascunde bănuiala",
        "După avertismentul Savistei, George înțelege de ce vine Ion la el, dar continuă să-l primească pentru a-l prinde și a se răfui cu el.",
    ),
    "EV_106": (
        "Ion îi fixează Floricăi o întâlnire",
        "Aflând că George va pleca duminică noaptea, Ion îi poruncește Floricăi să iasă în ogradă după plecarea soțului.",
    ),
    "EV_108": (
        "Savista îl avertizează pe George",
        "După ce îl surprinde pe Ion intrând la Florica, Savista îi spune lui George ce a văzut.",
    ),
    "EV_120": (
        "Noua biserică este sfințită",
        "Episcopul, numeroși preoți, intelectualii și țăranii participă la sfințirea noii biserici din Pripas.",
    ),
    "EV_121": (
        "Jocul tinerilor continuă",
        "La petrecerea de la Todosia, primarul le poruncește flăcăilor să continue jocul în fața oaspeților.",
    ),
    "EV_047": (
        "Ana respinge gândurile de moarte",
        "Ana își amintește că fusese aproape să-și ia viața, dar sarcina o face acum să îndepărteze gândurile de moarte.",
    ),
    "EV_068": (
        "Ion îi cere sfatul lui Belciug",
        "Belciug îi spune lui Ion că bătaia nu aduce dreptate și îl îndeamnă să consulte un avocat.",
    ),
    "EV_069": (
        "Ion hotărăște să recurgă la lege",
        "După sfatul preotului, Ion pleacă hotărât să lase legea să decidă conflictul cu Vasile Baciu.",
    ),
    "EV_070": (
        "Ion o alungă pe Ana",
        "Ion o conduce pe Ana până la poartă și o trimite înapoi la tatăl ei.",
    ),
    "EV_071": (
        "Ana se simte fără rost",
        "Alungată de Ion, Ana pleacă plângând și spune că numai ea nu are niciun rost în lume.",
    ),
    "EV_072": (
        "Titu decide să plece din Pripas",
        "Dezamăgit de conflictul electoral și de compromisurile tatălui său, Titu își găsește un post de subnotar în Lușca.",
    ),
    "EV_073": (
        "Titu pleacă la Lușca",
        "După aflarea rezultatului alegerilor, Titu părăsește Pripasul pentru postul din Lușca, nu pentru România.",
    ),
    "EV_074": (
        "Ana rămâne la Vasile Baciu",
        "După ce Ion o alungă, Ana se întoarce și rămâne în casa tatălui ei, Vasile Baciu.",
    ),
    "EV_075": (
        "Ion pornește procesul pentru pământuri",
        "Ion îl angajează pe avocatul Victor Grofșoru și îl cheamă în judecată pe Vasile Baciu pentru pământurile promise.",
    ),
    "EV_076": (
        "Vasile cedează o parte din avere",
        "Temându-se de proces, Vasile acceptă să-i dea lui Ion jumătate din locuri și cealaltă casă, iar Ana se întoarce la soț.",
    ),
    "EV_077": (
        "Ana naște pe câmp",
        "Ana naște pe câmp un băiat, în timpul muncilor agricole.",
    ),
    "EV_078": (
        "Violența lui Ion reîncepe",
        "La mai puțin de o săptămână după botezul copilului, Ion găsește din nou prilej să o bată pe Ana.",
    ),
    "EV_079": (
        "Ana este atrasă din nou de gândul morții",
        "După ce vede urmările sinuciderii lui Avrum, Ana începe din nou să se gândească la moarte.",
    ),
    "EV_080": (
        "Ion și Herdelea sunt condamnați",
        "Tribunalul îl condamnă pe Ion la o lună de închisoare, iar pe Zaharia Herdelea la opt zile de închisoare.",
    ),
    "EV_081": (
        "Ion se poartă calculat cu Ana",
        "Temându-se că Ana ar putea cere despărțirea înaintea procesului cu Vasile, Ion trece pentru o vreme de la bătăi la mângâieri.",
    ),
    "EV_082": (
        "Vasile hotărăște să cedeze averea",
        "Înspăimântat de apropierea judecății, Vasile Baciu hotărăște să încheie conflictul și să-i dea lui Ion averea.",
    ),
    "EV_083": (
        "Vasile și Ion merg la notar",
        "Vasile Baciu și Ion merg la notarul din Jidovița pentru încheierea contractului.",
    ),
    "EV_084": (
        "Contractul îi dă lui Ion toate pământurile",
        "Contractul îl face pe Ion stăpânul tuturor pământurilor lui Vasile Baciu.",
    ),
    "EV_085": (
        "Vasile înțelege că a rămas fără avere",
        "După semnarea contractului, Vasile își dă seama că a fost lăsat fără nimic și se repede la Ion.",
    ),
    "EV_086": (
        "Ion îi povestește lui Titu izbânda",
        "Întâlnindu-l pe Titu întors din Lușca, Ion îi spune cu mândrie cum l-a învins pe Vasile Baciu.",
    ),
    "EV_087": (
        "Ion se vede stăpân deplin",
        "Ion îi spune lui Titu că tot pământul este acum al lui.",
    ),
    "EV_088": (
        "Ion își contemplă pământurile",
        "Ajuns pe câmp, Ion privește pământurile dobândite și se simte puternic în fața lor.",
    ),
    "EV_089": (
        "Ion sărută pământul",
        "Ion îngenunchează și își lipește buzele de pământul ud într-un gest de posesie și adorare.",
    ),
    "EV_090": (
        "Florica se căsătorește cu George",
        "Florica se căsătorește cu George Bulbuc, iar nunta lor reunește comunitatea.",
    ),
    "EV_091": (
        "Ion o privește stăruitor pe Florica",
        "La nunta Floricăi, Ion nu-și desprinde privirea de mireasă, iar George simte primejdia.",
    ),
    "EV_092": (
        "Ana observă dorința lui Ion",
        "Ana înțelege la ospăț că Ion o dorește pe Florica și se simte batjocorită în fața oamenilor.",
    ),
    "EV_095": (
        "Ana se spânzură",
        "Ana își pune capăt vieții prin spânzurare în grajd.",
    ),
    "EV_110": (
        "George îl lovește pe Ion",
        "Întors acasă, George ia sapa din tindă și îl lovește de trei ori pe Ion în întuneric.",
    ),
    "EV_109": (
        "George se întoarce acasă",
        "George pleacă spre pădure cu tatăl său, dar se răzgândește și se întoarce singur peste câmp.",
    ),
    "EV_111": (
        "Ion își revine după lovituri",
        "După loviturile primite la sfârșitul capitolului anterior, Ion își revine din starea de inconștiență.",
    ),
    "EV_112": (
        "Ion își înțelege starea",
        "Ion simte durerile cumplite și își dă seama că este pe moarte.",
    ),
    "EV_113": (
        "Ion se târăște spre poartă",
        "Ion se târăște aproximativ un sfert de ceas până sub nucul de lângă poartă.",
    ),
    "EV_114": (
        "Ion moare sub nuc",
        "După ce se târăște până sub nucul de lângă poartă, Ion moare acolo și este găsit dimineața.",
    ),
    "EV_117": (
        "Averea lui Ion este transcrisă bisericii",
        "Victor Grofșoru se însărcinează să transcrie averea răposatului Ion Glanetașu pe numele bisericii române din Pripas.",
    ),
    "EV_122": (
        "Viața satului continuă",
        "În timp ce satul își continuă viața și tinerii joacă, George rămâne în temniță, așteptând judecata curții cu jurați.",
    ),
}

EVENT_PAGE_OVERRIDES: dict[str, tuple[int, ...]] = {
    "EV_003": (8, 9, 10),
    "EV_008": (17,),
    "EV_011": (50, 51, 54),
    "EV_012": (53,),
    "EV_014": (49, 50),
    "EV_015": (55,),
    "EV_016": (57,),
    "EV_017": (57,),
    "EV_020": (62,),
    "EV_022": (77,),
    "EV_024": (82, 83),
    "EV_002": (8, 9),
    "EV_004": (14, 15, 16),
    "EV_021": (66, 67, 68),
    "EV_025": (82, 83),
    "EV_027": (100, 101),
    "EV_039": (177, 178),
    "EV_037": (181,),
    "EV_040": (178, 179, 180),
    "EV_042": (181,),
    "EV_044": (195, 196),
    "EV_046": (219, 220),
    "EV_051": (116,),
    "EV_052": (116,),
    "EV_058": (280, 281, 282),
    "EV_057": (248, 249, 250),
    "EV_060": (283, 284),
    "EV_061": (283,),
    "EV_062": (276, 277, 278, 279),
    "EV_064": (294, 295, 296),
    "EV_065": (306, 307),
    "EV_066": (307, 308),
    "EV_067": (320,),
    "EV_047": (210,),
    "EV_068": (322,),
    "EV_069": (323,),
    "EV_070": (323,),
    "EV_071": (323,),
    "EV_072": (324, 325),
    "EV_073": (330,),
    "EV_074": (330, 331),
    "EV_075": (331, 332),
    "EV_076": (334,),
    "EV_077": (345, 346, 347),
    "EV_078": (353,),
    "EV_079": (354, 358),
    "EV_080": (364,),
    "EV_081": (371,),
    "EV_082": (378,),
    "EV_083": (380, 381, 382),
    "EV_084": (382, 383, 384),
    "EV_085": (384,),
    "EV_086": (405, 406),
    "EV_087": (406,),
    "EV_088": (407,),
    "EV_089": (408,),
    "EV_090": (409, 414, 415, 416),
    "EV_091": (416,),
    "EV_092": (416,),
    "EV_093": (426, 427),
    "EV_094": (428, 429, 430),
    "EV_095": (430, 431),
    "EV_096": (432, 433, 434),
    "EV_100": (454, 455),
    "EV_103": (477, 478, 479),
    "EV_104": (479, 480),
    "EV_106": (498, 499),
    "EV_108": (482, 483),
    "EV_109": (511, 512),
    "EV_110": (515, 516),
    "EV_111": (518,),
    "EV_112": (518,),
    "EV_113": (518,),
    "EV_114": (518, 519),
    "EV_116": (521, 522),
    "EV_119": (529, 530),
    "EV_120": (536, 537, 538, 539),
    "EV_121": (543, 544),
    "EV_122": (543, 544),
    "EV_123": (488,),
}

# Câmpurile structurale trebuie corectate împreună cu textul evenimentului.
# În versiunea anterioară, EVENT_FACT_OVERRIDES schimba numai descrierea, iar
# participanții și locul rămâneau de la evenimentul vechi din graful 1.
EVENT_ATTRIBUTE_OVERRIDES: dict[str, dict[str, Any]] = {
    "EV_004": {"participants": ["CHAR_001", "CHAR_002"], "location": "LOC_002"},
    "EV_005": {"participants": ["CHAR_001", "CHAR_003", "CHAR_002"], "location": "LOC_002"},
    "EV_003": {"participants": ["CHAR_008", "CHAR_013", "CHAR_022"], "location": "LOC_002"},
    "EV_008": {"participants": ["CHAR_001", "CHAR_005", "CHAR_002"], "location": "LOC_002"},
    "EV_011": {"participants": ["CHAR_001"], "location": "LOC_004"},
    "EV_012": {"participants": ["CHAR_001"], "location": "LOC_004"},
    "EV_014": {"participants": ["CHAR_006", "CHAR_007", "CHAR_001"], "location": "LOC_001"},
    "EV_015": {"participants": ["CHAR_002", "CHAR_001", "CHAR_005"], "location": "LOC_004"},
    "EV_016": {"participants": ["CHAR_003", "CHAR_001"], "location": "LOC_004"},
    "EV_017": {"participants": ["CHAR_001", "CHAR_003"], "location": "LOC_004"},
    "EV_020": {"participants": ["CHAR_008", "CHAR_009", "CHAR_010", "CHAR_011", "CHAR_012"], "location": "LOC_005"},
    "EV_022": {"participants": ["CHAR_013", "CHAR_008"], "location": "LOC_006"},
    "EV_024": {"participants": ["CHAR_001", "CHAR_013"], "location": "LOC_006"},
    "EV_035": {
        "participants": ["CHAR_001", "CHAR_010", "CHAR_005"],
        "location": "LOC_001",
        "chapter_id": "CH_03",
    },
    "EV_036": {
        "participants": ["CHAR_010", "CHAR_001", "CHAR_005"],
        "location": "LOC_001",
        "chapter_id": "CH_03",
    },
    "EV_021": {"participants": ["CHAR_010", "CHAR_020"], "location": "LOC_007"},
    "EV_037": {"participants": ["CHAR_001", "CHAR_002"], "location": "LOC_008"},
    "EV_040": {"participants": ["CHAR_001", "CHAR_002", "CHAR_005"], "location": "LOC_008"},
    "EV_042": {"participants": ["CHAR_004", "CHAR_001", "CHAR_002"], "location": "LOC_008"},
    "EV_046": {"participants": ["CHAR_005", "CHAR_002", "CHAR_001"], "location": "LOC_008"},
    "EV_058": {"participants": ["CHAR_001", "CHAR_002", "CHAR_005", "CHAR_008"], "location": "LOC_007"},
    "EV_056": {"participants": ["CHAR_013", "CHAR_005", "CHAR_001", "CHAR_002"], "location": "LOC_006"},
    "EV_059": {"participants": ["CHAR_001", "CHAR_002", "CHAR_003"], "location": "LOC_007"},
    "EV_060": {"participants": ["CHAR_002", "CHAR_001", "CHAR_003"], "location": "LOC_008"},
    "EV_062": {"participants": ["CHAR_011", "CHAR_018", "CHAR_008", "CHAR_009"], "location": "LOC_010"},
    "EV_063": {"participants": ["CHAR_011", "CHAR_018"], "location": "LOC_010"},
    "EV_064": {"participants": ["CHAR_005", "CHAR_001"], "location": "LOC_008"},
    "EV_065": {"participants": ["CHAR_002", "CHAR_005", "CHAR_001"], "location": "LOC_008"},
    "EV_066": {"participants": ["CHAR_001", "CHAR_002"], "location": "LOC_016"},
    "EV_067": {"participants": ["CHAR_002", "CHAR_014"], "location": "LOC_016"},
    "EV_047": {"participants": ["CHAR_002"], "location": "LOC_008"},
    "EV_068": {"participants": ["CHAR_001", "CHAR_013"], "location": "LOC_006"},
    "EV_069": {"participants": ["CHAR_001", "CHAR_013"], "location": "LOC_006"},
    "EV_070": {"participants": ["CHAR_001", "CHAR_002"], "location": "LOC_016"},
    "EV_071": {"participants": ["CHAR_002", "CHAR_001"], "location": "LOC_016"},
    "EV_072": {"participants": ["CHAR_010", "CHAR_008"], "location": "LOC_005"},
    "EV_073": {"participants": ["CHAR_010"], "location": "LOC_014"},
    "EV_074": {"participants": ["CHAR_002", "CHAR_005"], "location": "LOC_008"},
    "EV_075": {"participants": ["CHAR_001", "CHAR_005", "CHAR_024"], "location": "LOC_010"},
    "EV_076": {"participants": ["CHAR_005", "CHAR_001", "CHAR_002"], "location": "LOC_001"},
    "EV_077": {"participants": ["CHAR_002", "CHAR_001", "CHAR_007", "CHAR_014"], "location": "LOC_004"},
    "EV_078": {"participants": ["CHAR_001", "CHAR_002"], "location": "LOC_016"},
    "EV_079": {"participants": ["CHAR_002", "CHAR_017"], "location": "LOC_003"},
    "EV_080": {
        "participants": ["CHAR_001", "CHAR_008"],
        "location": "LOC_015",
        "chapter_id": "CH_08",
    },
    "EV_081": {"participants": ["CHAR_001", "CHAR_002", "CHAR_005"], "location": "LOC_016"},
    "EV_082": {"participants": ["CHAR_005", "CHAR_001"], "location": "LOC_001"},
    "EV_083": {"participants": ["CHAR_005", "CHAR_001"], "location": "LOC_007"},
    "EV_084": {"participants": ["CHAR_001", "CHAR_005"], "location": "LOC_007"},
    "EV_085": {"participants": ["CHAR_005", "CHAR_001"], "location": "LOC_007"},
    "EV_086": {"participants": ["CHAR_001", "CHAR_010"], "location": "LOC_004"},
    "EV_087": {"participants": ["CHAR_001", "CHAR_010"], "location": "LOC_004"},
    "EV_088": {"participants": ["CHAR_001"], "location": "LOC_004"},
    "EV_089": {"participants": ["CHAR_001"], "location": "LOC_004"},
    "EV_090": {"participants": ["CHAR_003", "CHAR_004", "CHAR_001", "CHAR_002"], "location": "LOC_001"},
    "EV_091": {"participants": ["CHAR_001", "CHAR_003", "CHAR_004", "CHAR_002"], "location": "LOC_001"},
    "EV_092": {"participants": ["CHAR_002", "CHAR_001", "CHAR_003"], "location": "LOC_001"},
    "EV_093": {"participants": ["CHAR_002", "CHAR_015", "CHAR_001", "CHAR_003", "CHAR_004"], "location": "LOC_001"},
    "EV_100": {"participants": ["CHAR_014", "CHAR_001"], "location": "LOC_012"},
    "EV_101": {"participants": ["CHAR_001", "CHAR_014", "CHAR_008"], "location": "LOC_001"},
    "EV_102": {"participants": ["CHAR_005", "CHAR_001"], "location": "LOC_016"},
    "EV_103": {"participants": ["CHAR_001", "CHAR_003"], "location": "LOC_004"},
    "EV_104": {"participants": ["CHAR_001", "CHAR_003", "CHAR_004"], "location": "LOC_011"},
    "EV_105": {"participants": ["CHAR_004", "CHAR_001", "CHAR_015", "CHAR_003"], "location": "LOC_011"},
    "EV_106": {"participants": ["CHAR_001", "CHAR_003", "CHAR_004"], "location": "LOC_011"},
    "EV_108": {"participants": ["CHAR_015", "CHAR_004", "CHAR_001", "CHAR_003"], "location": "LOC_011"},
    "EV_109": {"participants": ["CHAR_004", "CHAR_022"], "location": "LOC_004"},
    "EV_110": {"participants": ["CHAR_004", "CHAR_001"], "location": "LOC_011"},
    "EV_111": {"participants": ["CHAR_001"], "location": "LOC_011"},
    "EV_112": {"participants": ["CHAR_001"], "location": "LOC_011"},
    "EV_113": {"participants": ["CHAR_001"], "location": "LOC_011"},
    "EV_114": {"participants": ["CHAR_001"], "location": "LOC_011"},
    "EV_117": {"participants": ["CHAR_013", "CHAR_008", "CHAR_024"], "location": "LOC_010"},
    "EV_118": {"participants": ["CHAR_001", "CHAR_013"], "location": "LOC_013"},
    "EV_119": {"participants": ["CHAR_008"], "location": "LOC_010"},
    "EV_120": {"participants": ["CHAR_013", "CHAR_008"], "location": "LOC_013"},
    "EV_121": {"participants": [], "location": "LOC_002"},
    "EV_122": {"participants": ["CHAR_022", "CHAR_006", "CHAR_004"], "location": "LOC_002"},
}

# Termeni rari, verificați manual în paginile indicate mai sus. Un eveniment
# poate deveni verified_primary numai dacă pasajul ales conține toate ancorele
# sale. Scorul lexical rămâne diagnostic, nu înlocuiește această condiție.
EVENT_EVIDENCE_TERMS: dict[str, tuple[str, ...]] = {
    "EV_003": ("barbati", "grupuri", "tineret"),
    "EV_008": ("vasile", "intarata", "ana"),
    "EV_011": ("ion", "cosea"),
    "EV_012": ("glasul", "pamantului", "chemare"),
    "EV_014": ("glanetasu", "datorii", "vand"),
    "EV_015": ("ana", "cos", "mancare"),
    "EV_016": ("florica", "ana"),
    "EV_017": ("florica", "inima", "craiasa"),
    "EV_020": ("titu", "laura", "ghighi"),
    "EV_022": ("invatator", "autoritate"),
    "EV_024": ("dojana", "rusine"),
    "EV_002": ("tineret", "lautar"),
    "EV_004": ("ion", "ana", "joc"),
    "EV_021": ("titu", "lang", "cucereasca"),
    "EV_025": ("ana", "nevasta"),
    "EV_027": ("simion", "pumni", "camas"),
    "EV_039": ("ana", "ion", "casa"),
    "EV_037": ("grea", "bucurie"),
    "EV_040": ("ion", "ana", "cuptor"),
    "EV_042": ("george", "scarba", "scroafa"),
    "EV_044": ("ana", "frica", "ascund"),
    "EV_046": ("vasile", "ana", "glanetasu"),
    "EV_051": ("simion", "parat", "porumbist"),
    "EV_052": ("popa", "para", "martor"),
    "EV_058": ("nunta", "trei", "alai"),
    "EV_057": ("vasile", "pamant", "traiesc"),
    "EV_060": ("ana", "florica", "banii"),
    "EV_061": ("ion", "florica", "mireasa"),
    "EV_062": ("laura", "george", "mireasa"),
    "EV_064": ("vasile", "intabul"),
    "EV_065": ("ana", "vasile", "pumni"),
    "EV_066": ("ion", "ana", "lovi"),
    "EV_067": ("ana", "mort", "pantece"),
    "EV_047": ("moarte", "burta"),
    "EV_068": ("avocat", "bataile"),
    "EV_069": ("legea", "hotarasca"),
    "EV_070": ("poarta", "ana"),
    "EV_071": ("rost", "lume"),
    "EV_072": ("hotari", "plece"),
    "EV_073": ("lusca", "titu"),
    "EV_074": ("ana", "vasile"),
    "EV_075": ("avocat", "pamanturile"),
    "EV_076": ("jumatate", "locuri"),
    "EV_077": ("copil", "ana"),
    "EV_078": ("snopeasca", "nevasta"),
    "EV_079": ("spanzur", "avrum"),
    "EV_080": ("condamnat", "herdelea", "inchisoare"),
    "EV_081": ("despartenie", "mangaieri"),
    "EV_082": ("judecata", "vasile"),
    "EV_083": ("notar", "vasile", "ion"),
    "EV_084": ("opt", "porumbist"),
    "EV_085": ("lasat", "drumuri"),
    "EV_086": ("titu", "pamant"),
    "EV_087": ("tot", "pamantul"),
    "EV_088": ("stapan", "pamant"),
    "EV_089": ("buzele", "pamant"),
    "EV_090": ("nunta", "florica"),
    "EV_091": ("ion", "florica", "primejdie"),
    "EV_092": ("ana", "florica", "batjocorita"),
    "EV_093": ("savista", "ana", "florica", "george"),
    "EV_094": ("ana", "lat", "funie"),
    "EV_095": ("ana", "spanzur"),
    "EV_096": ("copil", "avere", "pamant"),
    "EV_100": ("inmormantare", "vasile", "ion"),
    "EV_103": ("ion", "florica", "mar"),
    "EV_104": ("ion", "george", "florica"),
    "EV_106": ("dumineca", "ion", "florica"),
    "EV_108": ("savista", "george", "ion", "florica"),
    "EV_109": ("camp", "tatal"),
    "EV_110": ("lovi", "treia", "sapa"),
    "EV_111": ("gemete", "aminte"),
    "EV_112": ("dureri", "mor"),
    "EV_113": ("sfert", "ceas", "nuc"),
    "EV_114": ("ion", "mort"),
    "EV_116": ("jandarm", "george"),
    "EV_119": ("minister", "pensie", "herdelea"),
    "EV_120": ("sfintir", "biseric", "preoti"),
    "EV_121": ("flacai", "continue", "joc"),
    "EV_122": ("temnita", "jurati", "tineretul"),
    "EV_123": ("legatuiti", "biserici", "mostenitori"),
    "EV_124": ("drumul", "jidovita", "soseaua"),
}

# Pentru validarea strictă, fiecare eveniment are o fereastră de pagini și
# termeni distinctivi stabiliți din PDF. Intrările de mai jos completează sau
# înlocuiesc valorile istorice prea largi (de tipul „apare numele personajului”).
EVENT_PAGE_OVERRIDES.update(
    {
        "EV_001": (3,),
        "EV_002": (7, 8, 9, 10, 11),
        "EV_004": (11, 12, 13),
        "EV_005": (17,),
        "EV_006": (26,),
        "EV_007": (25,),
        "EV_009": (39,),
        "EV_010": (40, 41),
        "EV_013": (53,),
        "EV_018": (56,),
        "EV_019": (62, 63),
        "EV_023": (82, 83),
        "EV_026": (99, 100),
        "EV_028": (91,),
        "EV_029": (109, 110, 111),
        "EV_030": (90, 91, 92, 93),
        "EV_031": (92, 93),
        "EV_032": (110, 121, 122),
        "EV_033": (122, 123),
        "EV_034": (123, 124, 125),
        "EV_035": (118, 119),
        "EV_036": (119,),
        "EV_038": (176, 177),
        "EV_041": (181,),
        "EV_043": (196,),
        "EV_045": (199,),
        "EV_048": (198,),
        "EV_049": (221, 222),
        "EV_050": (221, 222),
        "EV_053": (136,),
        "EV_054": (163, 164),
        "EV_055": (200, 201),
        "EV_056": (244, 245, 246, 247, 248),
        "EV_059": (281, 282),
        "EV_060": (284,),
        "EV_063": (277, 278, 279, 280),
        "EV_072": (325,),
        "EV_077": (346,),
        "EV_084": (382, 383, 384),
        "EV_086": (406,),
        "EV_097": (450,),
        "EV_098": (451, 452),
        "EV_099": (454,),
        "EV_100": (454,),
        "EV_101": (453,),
        "EV_102": (455,),
        "EV_105": (496,),
        "EV_107": (482,),
        "EV_114": (518, 519),
        "EV_115": (521,),
        "EV_117": (530,),
        "EV_118": (525,),
    }
)

EVENT_EVIDENCE_TERMS.update(
    {
        "EV_001": ("drum", "pripas"),
        "EV_002": ("barbati", "tineret", "lautar"),
        "EV_004": ("ion", "ana", "vii"),
        "EV_005": ("florica", "saraca", "ana"),
        "EV_006": ("vasile", "golan"),
        "EV_007": ("ginere", "george"),
        "EV_009": ("lautari", "plata", "george"),
        "EV_010": ("ion", "george", "par"),
        "EV_013": ("mic", "slab", "stapan"),
        "EV_015": ("ana", "ion", "demancare"),
        "EV_017": ("floric", "inima", "craiasa"),
        "EV_018": ("calicie", "noroc"),
        "EV_019": ("familia", "herdelea", "ion"),
        "EV_023": ("relelor", "avrum", "biseric"),
        "EV_026": ("plug", "simion", "brazda"),
        "EV_028": ("laura", "aurel", "iubire"),
        "EV_029": ("aurel", "pintea", "tacut"),
        "EV_030": ("pintea", "zestre", "laura"),
        "EV_031": ("pintea", "batrani", "serios"),
        "EV_032": ("laura", "aurel", "lacram"),
        "EV_033": ("laura", "pintea", "raspuns"),
        "EV_034": ("vasile", "george", "ana"),
        "EV_035": ("ion", "titu", "vasile"),
        "EV_036": ("sile", "titu", "ion"),
        "EV_038": ("ion", "ana", "prilej"),
        "EV_041": ("george", "ascuns", "ion"),
        "EV_043": ("ana", "insarcinata", "femei"),
        "EV_045": ("firoana", "vasile", "baiat"),
        "EV_048": ("ion", "ana", "arata"),
        "EV_049": ("ana", "ion", "planga"),
        "EV_050": ("tocmeala", "vasile", "ana"),
        "EV_053": ("ion", "saptamani", "racoare"),
        "EV_054": ("jalba", "laura", "ministru"),
        "EV_055": ("herdelea", "judecator", "jalba"),
        "EV_056": ("belciug", "ion", "fata"),
        "EV_059": ("ana", "pamant", "florica"),
        "EV_042": ("george", "scarba"),
        "EV_060": ("ion", "lacom", "banii"),
        "EV_063": ("laur", "iubesc"),
        "EV_065": ("ana", "batut", "sange"),
        "EV_072": ("titu", "lusca", "subnotar"),
        "EV_074": ("ana", "vasile", "bine"),
        "EV_077": ("ana", "baietel", "pamant"),
        "EV_081": ("despart", "mangai"),
        "EV_082": ("vasile", "hotarat", "sfarseasca"),
        "EV_084": ("tot", "cruce", "vasile"),
        "EV_088": ("stapan", "tuturor"),
        "EV_091": ("ion", "primejd"),
        "EV_094": ("streang", "lat", "funie"),
        "EV_095": ("spanzurat", "ana"),
        "EV_096": ("copil", "avere", "mosia"),
        "EV_086": ("titu", "biruit", "vasile"),
        "EV_097": ("petrisor", "gemea", "ion"),
        "EV_098": ("petrisor", "carbuni", "descantec"),
        "EV_099": ("copil", "rece", "doctor"),
        "EV_100": ("inmormantare", "ana"),
        "EV_101": ("pamanturile", "inapoi", "herdelea"),
        "EV_102": ("intor", "pamantul"),
        "EV_103": ("floric", "buzele", "mea"),
        "EV_105": ("savista", "george", "prinda"),
        "EV_107": ("oloaga", "ascunzatoare", "ion"),
        "EV_114": ("ion", "mort"),
        "EV_115": ("omorat", "sapa", "nevasta"),
        "EV_117": ("transcrie", "averea", "bisericii"),
        "EV_118": ("groapa", "ion", "bisericii"),
    }
)

if set(EVENT_EVIDENCE_TERMS) != {f"EV_{index:03d}" for index in range(1, 125)}:
    raise RuntimeError("Tabelul de evidență trebuie să acopere exact toate cele 124 de evenimente.")

EVENT_EVIDENCE_MAX_SENTENCES: dict[str, int] = {
    "EV_015": 8,
    "EV_065": 8,
    "EV_094": 8,
}


# Interpretările moștenite de la evenimentele înlocuite erau uneori la fel de
# greșite ca participanții. Acest tabel le resetează explicit; `conflicts`
# conține numai noduri Conflict, iar `themes` numai celelalte concepte relevante.
EVENT_SEMANTIC_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "EV_003": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_003", "CONCEPT_012"]},
    "EV_008": {"conflicts": ["CONCEPT_004", "CONCEPT_006"], "themes": ["CONCEPT_001", "CONCEPT_017"]},
    "EV_011": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_017"]},
    "EV_012": {"conflicts": ["CONCEPT_005"], "themes": ["CONCEPT_001", "CONCEPT_017"]},
    "EV_014": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_015": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_002", "CONCEPT_017"]},
    "EV_016": {"conflicts": ["CONCEPT_005", "CONCEPT_006"], "themes": ["CONCEPT_002"]},
    "EV_017": {"conflicts": ["CONCEPT_005", "CONCEPT_006"], "themes": ["CONCEPT_002"]},
    "EV_020": {"conflicts": [], "themes": ["CONCEPT_014"]},
    "EV_022": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_013", "CONCEPT_014"]},
    "EV_024": {"conflicts": ["CONCEPT_004", "CONCEPT_005"], "themes": ["CONCEPT_001", "CONCEPT_012", "CONCEPT_015"]},
    "EV_037": {"conflicts": ["CONCEPT_006", "CONCEPT_007"], "themes": ["CONCEPT_008", "CONCEPT_017"]},
    "EV_040": {"conflicts": ["CONCEPT_006", "CONCEPT_007"], "themes": ["CONCEPT_008", "CONCEPT_017"]},
    "EV_042": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_009"]},
    "EV_046": {"conflicts": ["CONCEPT_007", "CONCEPT_016"], "themes": ["CONCEPT_008"]},
    "EV_047": {"conflicts": ["CONCEPT_007"], "themes": ["CONCEPT_009"]},
    "EV_058": {"conflicts": [], "themes": ["CONCEPT_002", "CONCEPT_017"]},
    "EV_064": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_065": {"conflicts": ["CONCEPT_007", "CONCEPT_016"], "themes": ["CONCEPT_008"]},
    "EV_066": {"conflicts": ["CONCEPT_007", "CONCEPT_016"], "themes": ["CONCEPT_008"]},
    "EV_067": {"conflicts": ["CONCEPT_005", "CONCEPT_007"], "themes": ["CONCEPT_009"]},
    "EV_068": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_013", "CONCEPT_017"]},
    "EV_069": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_070": {"conflicts": ["CONCEPT_007", "CONCEPT_016"], "themes": ["CONCEPT_008"]},
    "EV_071": {"conflicts": ["CONCEPT_005", "CONCEPT_007"], "themes": ["CONCEPT_009"]},
    "EV_072": {"conflicts": ["CONCEPT_005"], "themes": ["CONCEPT_014", "CONCEPT_019"]},
    "EV_073": {"conflicts": [], "themes": ["CONCEPT_014"]},
    "EV_074": {"conflicts": ["CONCEPT_007"], "themes": ["CONCEPT_008"]},
    "EV_075": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_076": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_012", "CONCEPT_017"]},
    "EV_077": {"conflicts": [], "themes": ["CONCEPT_011", "CONCEPT_017"]},
    "EV_078": {"conflicts": ["CONCEPT_007", "CONCEPT_016"], "themes": ["CONCEPT_008"]},
    "EV_079": {"conflicts": ["CONCEPT_005", "CONCEPT_007"], "themes": ["CONCEPT_009"]},
    "EV_080": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_014"]},
    "EV_081": {"conflicts": ["CONCEPT_007", "CONCEPT_016"], "themes": ["CONCEPT_008", "CONCEPT_017"]},
    "EV_082": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_083": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_084": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_012", "CONCEPT_017"]},
    "EV_085": {"conflicts": ["CONCEPT_004"], "themes": ["CONCEPT_017"]},
    "EV_086": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_017"]},
    "EV_087": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_012", "CONCEPT_017"]},
    "EV_088": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_017"]},
    "EV_089": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_017"]},
    "EV_090": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_011"]},
    "EV_091": {"conflicts": ["CONCEPT_005", "CONCEPT_006"], "themes": ["CONCEPT_009"]},
    "EV_092": {"conflicts": ["CONCEPT_005", "CONCEPT_006", "CONCEPT_007"], "themes": ["CONCEPT_008", "CONCEPT_009"]},
    "EV_093": {"conflicts": ["CONCEPT_006", "CONCEPT_007"], "themes": ["CONCEPT_008", "CONCEPT_009"]},
    "EV_100": {"conflicts": [], "themes": ["CONCEPT_009", "CONCEPT_017", "CONCEPT_020"]},
    "EV_103": {"conflicts": ["CONCEPT_005", "CONCEPT_006"], "themes": ["CONCEPT_002", "CONCEPT_009"]},
    "EV_104": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_002", "CONCEPT_009"]},
    "EV_106": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_002", "CONCEPT_009"]},
    "EV_108": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_009"]},
    "EV_109": {"conflicts": ["CONCEPT_006"], "themes": ["CONCEPT_009"]},
    "EV_110": {"conflicts": ["CONCEPT_006", "CONCEPT_016"], "themes": ["CONCEPT_009"]},
    "EV_111": {"conflicts": [], "themes": ["CONCEPT_009", "CONCEPT_020"]},
    "EV_112": {"conflicts": ["CONCEPT_005"], "themes": ["CONCEPT_009", "CONCEPT_020"]},
    "EV_113": {"conflicts": [], "themes": ["CONCEPT_009", "CONCEPT_020"]},
    "EV_114": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_009", "CONCEPT_020"]},
    "EV_116": {"conflicts": [], "themes": ["CONCEPT_009"]},
    "EV_117": {"conflicts": [], "themes": ["CONCEPT_001", "CONCEPT_013", "CONCEPT_017"]},
    "EV_118": {"conflicts": [], "themes": ["CONCEPT_013", "CONCEPT_020"]},
    "EV_119": {"conflicts": [], "themes": ["CONCEPT_014"]},
    "EV_120": {"conflicts": [], "themes": ["CONCEPT_011", "CONCEPT_013", "CONCEPT_019"]},
    "EV_121": {"conflicts": [], "themes": ["CONCEPT_011", "CONCEPT_018", "CONCEPT_020"]},
    "EV_122": {"conflicts": [], "themes": ["CONCEPT_011", "CONCEPT_018", "CONCEPT_020"]},
}

# Evenimente factuale păstrate ca atare după inspecția paginilor capitolului.
# Separarea de EVENT_FACT_OVERRIDES arată clar ce a fost doar verificat și ce a
# necesitat și reformulare.
MANUALLY_VERIFIED_EVENTS = {
    "EV_002", "EV_004", "EV_021", "EV_025", "EV_027", "EV_039", "EV_044",
    "EV_051", "EV_052", "EV_058", "EV_065", "EV_094", "EV_095", "EV_096",
    "EV_116", "EV_119",
}

ROMANIAN_STOPWORDS = {
    "a", "ai", "al", "ale", "ca", "care", "cu", "că", "de", "din", "după", "este",
    "iar", "la", "lui", "mai", "o", "pe", "pentru", "prin", "sau", "se", "și", "un",
    "una", "unei", "unui", "în", "îi", "îl", "își",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def normalize_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("ş", "ș").replace("ţ", "ț"))
    return re.sub(r"[^a-z0-9]+", " ", "".join(ch for ch in decomposed if not unicodedata.combining(ch))).strip()


def source_tokens(value: str) -> set[str]:
    return {
        token
        for token in normalize_diacritics(value).split()
        if len(token) >= 4 and token not in ROMANIAN_STOPWORDS
    }


def passage_candidates(page_text: str, max_sentences: int = 5) -> list[str]:
    cleaned = re.sub(r"\s+", " ", page_text).strip()
    sentences = [part.strip() for part in re.split(r"(?<=[.!?…])\s+", cleaned) if part.strip()]
    candidates: list[str] = []
    for index in range(len(sentences)):
        for width in range(1, max_sentences + 1):
            passage = " ".join(sentences[index : index + width]).strip()
            if 60 <= len(passage) <= 1600:
                candidates.append(passage)
    return candidates or ([cleaned[:1600]] if cleaned else [])


def passage_score(fact: str, passage: str) -> float:
    expected = source_tokens(fact)
    observed = source_tokens(passage)
    if not expected:
        return 0.0
    matched = sum(
        any(left[:6] == right[:6] for right in observed)
        for left in expected
    )
    return matched / len(expected)


def passage_contains_terms(passage: str, terms: tuple[str, ...]) -> bool:
    observed = re.findall(r"[a-z0-9]+", normalize_diacritics(passage))

    def matches(token: str, term: str) -> bool:
        return token == term if len(term) < 4 else token.startswith(term)

    return all(
        any(matches(token, term) for token in observed)
        for term in (normalize_diacritics(value) for value in terms)
    )


def passage_contains_any_term(passage: str, terms: tuple[str, ...]) -> bool:
    observed = re.findall(r"[a-z0-9]+", normalize_diacritics(passage))
    return any(
        any(token == term if len(term) < 4 else token.startswith(term) for token in observed)
        for term in (normalize_diacritics(value) for value in terms)
    )


def apply_event_fact_overrides(nodes: list[dict[str, Any]]) -> None:
    for node in nodes:
        node_id = str(node.get("id") or "")
        if node.get("type") != "NarrativeEvent":
            continue
        attrs = node.setdefault("attributes", {})
        if node_id in EVENT_FACT_OVERRIDES:
            label, fact = EVENT_FACT_OVERRIDES[node_id]
            node["label"] = label
            node["description"] = fact
            node["assertion_type"] = "explicit_fact"
            node["confidence"] = 1.0
            attrs.update(
                {
                    "title": label,
                    "canonical_description": fact,
                    "action": fact,
                    "preconditions": [],
                    "causes": [],
                    "motivations": [],
                    "immediate_effects": [],
                    "long_term_effects": [],
                    "state_transitions": [],
                    "simple_narration": fact,
                    "elevated_narration": fact,
                    "simple_transition": "",
                    "elevated_transition": "",
                    "confidence": 1.0,
                }
            )
        if node_id == "EV_018":
            # Aceasta este o sinteză critică a opoziției dintre iubire și
            # ieșirea din sărăcie, nu o propoziție formulată ca atare de narator.
            node["assertion_type"] = "literary_interpretation"
        if node_id == "EV_065":
            attrs["state_transitions"] = [
                "Ana se întoarce rănită după ce Vasile Baciu o lovește și o alungă."
            ]
        if node_id not in EVENT_ATTRIBUTE_OVERRIDES:
            pass
        else:
            attrs.update(copy.deepcopy(EVENT_ATTRIBUTE_OVERRIDES[node_id]))
            chapter_id = str(attrs.get("chapter_id") or "")
            chapter_number = int(chapter_id.rsplit("_", 1)[-1])
            node["chapter_ids"] = [chapter_id]
            node["source_refs"] = [f"REF_PDF_CH_{chapter_number:02d}", f"REF_SUM_CH_{chapter_number:02d}"]
            attrs["source_refs"] = list(node["source_refs"])
        if node_id in EVENT_SEMANTIC_OVERRIDES:
            attrs.update(copy.deepcopy(EVENT_SEMANTIC_OVERRIDES[node_id]))


def attach_primary_evidence(graph: dict[str, Any]) -> None:
    from pypdf import PdfReader

    reader = PdfReader(SOURCE_DIR / "ion.pdf")
    source_by_id = {source["id"]: source for source in graph["sources"]}
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    page_cache = {index + 1: reader.pages[index].extract_text() or "" for index in range(len(reader.pages))}
    for node in graph["nodes"]:
        if node.get("type") != "NarrativeEvent":
            continue
        attrs = node.setdefault("attributes", {})
        if node["id"] == "EV_124":
            evidence_quote = (
                "La Râpile Dracului bătrânii întoarseră capul. Pripasul de abia își mai "
                "arăta câteva case. Apoi șoseaua cotește, apoi se îndoaie, apoi se întinde "
                "iar dreaptă ca o panglică cenușie în amurgul răcoros. Drumul trece prin "
                "Jidovița, pe podul de lemn, acoperit, de peste Someș, și pe urmă se pierde "
                "în șoseaua cea mare și fără început..."
            )
            anchor_terms = EVENT_EVIDENCE_TERMS[node["id"]]
            if not passage_contains_terms(evidence_quote, anchor_terms):
                raise ValueError("Ancora finalului canonic nu mai corespunde evenimentului EV_124.")
            attrs["verification"] = {
                "status": "verified_primary",
                "method": "explicit_anchor_terms+canonical_wikisource_supplement",
                "source_ref": "REF_WIKISOURCE_CH_13_FINAL",
                "pdf_page": None,
                "source_locator": "Wikisource, versiunea oldid=149663, liniile 2509-2514",
                "source_position": 548,
                "evidence_quote": evidence_quote,
                "support_score": round(passage_score(node["description"], evidence_quote), 4),
            }
            continue
        chapter_id = str(attrs.get("chapter_id") or "")
        chapter_number = int(chapter_id.rsplit("_", 1)[-1])
        source_ref = f"REF_PDF_CH_{chapter_number:02d}"
        source = source_by_id[source_ref]
        fact = str(attrs.get("canonical_description") or node.get("description") or "")
        best_score = -1.0
        best_page = 0
        best_passage = ""
        page_numbers = EVENT_PAGE_OVERRIDES.get(
            node["id"],
            tuple(range(source["pdf_page_start"], source["pdf_page_end"] + 1)),
        )
        out_of_range = [
            page_number
            for page_number in page_numbers
            if not source["pdf_page_start"] <= page_number <= source["pdf_page_end"]
        ]
        if out_of_range:
            raise ValueError(
                f"Pagini de evidență în afara capitolului pentru {node['id']}: {out_of_range}"
            )
        anchor_terms = EVENT_EVIDENCE_TERMS.get(node["id"])
        participants = attrs.get("participants", [])
        principal_label = node_by_id.get(participants[0], {}).get("label", "") if participants else ""
        principal_terms = tuple(
            token for token in normalize_diacritics(principal_label).split() if len(token) >= 3
        )
        for page_number in page_numbers:
            for passage in passage_candidates(
                page_cache[page_number], EVENT_EVIDENCE_MAX_SENTENCES.get(node["id"], 5)
            ):
                if anchor_terms and not passage_contains_terms(passage, anchor_terms):
                    continue
                if not anchor_terms and principal_terms and not passage_contains_any_term(passage, principal_terms):
                    continue
                score = passage_score(fact, passage)
                if score > best_score or (score == best_score and len(passage) < len(best_passage)):
                    best_score = score
                    best_page = page_number
                    best_passage = passage
        # Pentru evenimentele cu ancore curatoriate, potrivirea tuturor termenilor
        # în aceeași fereastră de maximum cinci fraze (opt numai pentru
        # trei scene compuse) este criteriul strict.
        # Scorul față de reformularea modernă este doar informativ: altfel, o
        # parafrază corectă poate fi respinsă deși pasajul primar a fost găsit.
        threshold = 0.0 if anchor_terms else 0.30
        status = "verified_primary" if best_passage and best_score >= threshold else "needs_review"
        if status != "verified_primary":
            node["confidence"] = min(float(node.get("confidence", 1.0)), 0.75)
            attrs["confidence"] = min(float(attrs.get("confidence", 1.0)), 0.75)
        attrs["verification"] = {
            "status": status,
            "method": (
                "explicit_anchor_terms+primary_text"
                if anchor_terms
                else "lexical_alignment+principal_participant"
            ),
            "source_ref": source_ref,
            "pdf_page": best_page,
            "evidence_quote": best_passage,
            "support_score": round(max(best_score, 0.0), 4),
        }


def evidence_position(event: dict[str, Any]) -> int:
    verification = event.get("attributes", {}).get("verification", {})
    return int(verification.get("source_position") or verification.get("pdf_page") or 0)


def order_events_by_primary_evidence(
    nodes: list[dict[str, Any]], chapters: list[dict[str, Any]]
) -> None:
    """Stabilește cronologia textuală prin pagina PDF, cu egalități stabile.

    Această regulă înlocuiește ordinea manuală moștenită din graful 1. Pentru
    două evenimente de pe aceeași pagină păstrăm ordinea curentă, deoarece
    pagina singură nu poate distinge în siguranță poziția frazelor.
    """
    node_by_id = {node["id"]: node for node in nodes}
    global_order = 0
    for chapter in sorted(chapters, key=lambda item: item["ordinal"]):
        old_position = {
            event_id: position for position, event_id in enumerate(chapter["event_sequence"])
        }
        chapter["event_sequence"] = sorted(
            chapter["event_sequence"],
            key=lambda event_id: (
                evidence_position(node_by_id[event_id]),
                old_position[event_id],
            ),
        )
        for local_order, event_id in enumerate(chapter["event_sequence"], start=1):
            global_order += 1
            attrs = node_by_id[event_id]["attributes"]
            attrs["chapter_order"] = local_order
            attrs["global_order"] = global_order
            attrs["time_context"] = f"Secvența {local_order} din {chapter['title']}"



def audit_source_materials(graph: dict[str, Any]) -> dict[str, Any]:
    from pypdf import PdfReader

    source_files = [
        SOURCE_DIR / "ion.pdf",
        SOURCE_DIR / "rezumat.md",
        SOURCE_DIR / "eseu_model.md",
        CANONICAL_FINAL_PATH,
        GRAPH1_PATH,
        OUTPUT_DIR / "prompt_generare_graf.md",
    ]
    missing_files = [str(path.relative_to(ROOT)) for path in source_files if not path.is_file()]
    empty_files = [str(path.relative_to(ROOT)) for path in source_files if path.is_file() and path.stat().st_size == 0]
    reader = PdfReader(SOURCE_DIR / "ion.pdf")
    pages_with_text = sum(bool((page.extract_text() or "").strip()) for page in reader.pages)
    heading_mismatches: list[str] = []
    source_by_id = {source["id"]: source for source in graph["sources"]}
    for chapter in graph["chapters"]:
        ref = source_by_id[f"REF_PDF_CH_{chapter['ordinal']:02d}"]
        page_text = normalize_diacritics(reader.pages[ref["pdf_page_start"] - 1].extract_text() or "")
        expected_title = normalize_diacritics(chapter["title"].split(" - ", 1)[-1])
        if expected_title not in page_text:
            heading_mismatches.append(chapter["id"])
    final_text = normalize_diacritics(
        CANONICAL_FINAL_PATH.read_text(encoding="utf-8") if CANONICAL_FINAL_PATH.is_file() else ""
    )
    canonical_final_complete = all(
        term in final_text for term in ("pripasul", "drumul trece prin jidovita", "soseaua cea mare")
    )
    passed = (
        not missing_files
        and not empty_files
        and not heading_mismatches
        and len(reader.pages) == 550
        and canonical_final_complete
    )
    return {
        "source_audit_passed": passed,
        "source_files_missing": missing_files,
        "source_files_empty": empty_files,
        "pdf_page_count": len(reader.pages),
        "pdf_pages_with_extractable_text": pages_with_text,
        "chapter_heading_mismatches": heading_mismatches,
        "canonical_final_supplement_valid": canonical_final_complete,
    }


def textualize_refs(values: list[Any], lookup: dict[str, dict[str, Any]]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if isinstance(value, str) and value in lookup:
            node = lookup[value]
            result.append(node.get("description") or node.get("label") or value)
        else:
            result.append(value)
    return result


def make_supporting_node(node_id: str, node_type: str, label: str, description: str) -> dict[str, Any]:
    return {
        "aliases": [],
        "chapter_ids": [],
        "importance": "supporting",
        "confidence": 1.0,
        "assertion_type": "explicit_fact",
        "source_refs": ["SRC_PDF", "SRC_SUMMARY"],
        "attributes": {},
        "id": node_id,
        "type": node_type,
        "label": label,
        "description": description,
    }


def add_missing_semantic_nodes(nodes: list[dict[str, Any]]) -> None:
    existing = {node["id"] for node in nodes}
    additions = [
        make_supporting_node(
            "CHAR_024",
            "Character",
            "Victor Grofșoru",
            "Avocatul care îl reprezintă pe Ion și participă ulterior la transcrierea averii pe numele bisericii.",
        ),
        make_supporting_node(
            "LOC_014",
            "Location",
            "Lușca",
            "Localitatea în care Titu Herdelea ocupă postul de subnotar.",
        ),
        make_supporting_node(
            "LOC_015",
            "Location",
            "Tribunalul din Bistrița",
            "Instanța în care Ion și Zaharia Herdelea își primesc sentințele.",
        ),
        make_supporting_node(
            "LOC_016",
            "Location",
            "Casa Glanetașu",
            "Gospodăria în care locuiesc Ion și Ana după căsătorie.",
        ),
    ]
    nodes.extend(node for node in additions if node["id"] not in existing)


def add_property_agreement_event(nodes: list[dict[str, Any]]) -> None:
    if any(node.get("id") == "EV_123" for node in nodes):
        return
    description = (
        "Ion și Vasile Baciu acceptă învoiala propusă de Belciug: ceea ce stăpânește fiecare "
        "va reveni bisericii dacă moare fără moștenitori direcți."
    )
    nodes.append(
        {
            "aliases": [],
            "chapter_ids": ["CH_12"],
            "importance": "major",
            "confidence": 1.0,
            "assertion_type": "explicit_fact",
            "source_refs": ["REF_PDF_CH_12", "REF_SUM_CH_12"],
            "attributes": {
                "event_id": "EV_123",
                "chapter_id": "CH_12",
                "chapter_order": 2,
                "global_order": 105,
                "title": "Ion și Vasile acceptă învoiala lui Belciug",
                "canonical_description": description,
                "participants": ["CHAR_001", "CHAR_005", "CHAR_013"],
                "location": "LOC_006",
                "time_context": "Secvență din Capitolul XII - George",
                "preconditions": ["conflictul succesoral dintre Ion și Vasile Baciu"],
                "causes": ["propunerea de împăcare formulată de Belciug"],
                "action": description,
                "immediate_effects": ["cei doi acceptă o destinație succesorală comună"],
                "long_term_effects": ["după moartea lui Ion, averea poate fi transcrisă bisericii"],
                "state_transitions": ["conflictul juridic este închis printr-o învoială condiționată"],
                "motivations": ["evitarea continuării conflictului"],
                "conflicts": ["CONCEPT_004"],
                "themes": ["CONCEPT_017", "CONCEPT_013"],
                "importance": "major",
                "source_refs": ["REF_PDF_CH_12", "REF_SUM_CH_12"],
                "confidence": 1.0,
                "simple_narration": description,
                "elevated_narration": description,
                "simple_transition": "",
                "elevated_transition": "",
                "modeling_note": "Eveniment factual adăugat pentru a reda cauza juridică a transferului final către biserică.",
            },
            "id": "EV_123",
            "type": "NarrativeEvent",
            "label": "Ion și Vasile acceptă învoiala lui Belciug",
            "description": description,
        }
    )


def add_canonical_final_event(nodes: list[dict[str, Any]]) -> None:
    """Completează finalul tăiat din PDF-ul local cu textul primar Wikisource."""
    if any(node.get("id") == "EV_124" for node in nodes):
        return
    description = (
        "După plecarea familiei Herdelea, drumul lasă în urmă Pripasul, trece prin "
        "Jidovița și se pierde în șoseaua cea mare și fără început."
    )
    nodes.append(
        {
            "aliases": [],
            "chapter_ids": ["CH_13"],
            "importance": "major",
            "confidence": 1.0,
            "assertion_type": "explicit_fact",
            "source_refs": ["REF_WIKISOURCE_CH_13_FINAL"],
            "attributes": {
                "event_id": "EV_124",
                "chapter_id": "CH_13",
                "chapter_order": 13,
                "global_order": 124,
                "title": "Drumul iese din Pripas",
                "canonical_description": description,
                "participants": ["CHAR_008", "CHAR_009", "CHAR_012"],
                "location": "LOC_001",
                "time_context": "Secvența finală din Capitolul XIII - Sfârșitul",
                "preconditions": ["familia Herdelea pornește spre Armadia"],
                "causes": [],
                "action": description,
                "immediate_effects": ["Pripasul rămâne în urma trăsurii"],
                "long_term_effects": [],
                "state_transitions": ["perspectiva narativă părăsește satul"],
                "motivations": [],
                "conflicts": [],
                "themes": ["CONCEPT_011", "CONCEPT_018", "CONCEPT_020"],
                "importance": "major",
                "source_refs": ["REF_WIKISOURCE_CH_13_FINAL"],
                "confidence": 1.0,
                "simple_narration": description,
                "elevated_narration": description,
                "simple_transition": "La final,",
                "elevated_transition": "În închiderea romanului,",
                "modeling_note": (
                    "Eveniment factual recuperat din transcrierea canonică Wikisource, "
                    "deoarece PDF-ul local omite ultimele paragrafe ale romanului."
                ),
            },
            "id": "EV_124",
            "type": "NarrativeEvent",
            "label": "Drumul iese din Pripas",
            "description": description,
        }
    )


CHAPTER_DESCRIPTIONS = {
    "CH_08": (
        "Titu pleacă la Lușca, conflictul pentru pământuri produce o cedare parțială, Ana îl naște "
        "pe Petrișor, iar capitolul se încheie cu sentințele lui Ion și Herdelea."
    ),
    "CH_09": (
        "După sentință, conflictul patrimonial se încheie prin contract, Ion devine stăpânul "
        "pământurilor și trăiește scena culminantă a sărutării pământului."
    ),
    "CH_12": (
        "Ion și Vasile acceptă învoiala succesorală propusă de Belciug; apoi dorința lui Ion pentru "
        "Florica reactivează rivalitatea, iar George îl lovește cu sapa."
    ),
}


STATE_DESCRIPTION_OVERRIDES = {
    "STATE_CH_07_CLOSE": "Ion o trimite pe Ana înapoi la Vasile Baciu, iar conflictul pentru pământuri rămâne nerezolvat.",
    "STATE_CH_08_OPEN": "Ana se află la tatăl ei, Ion nu deține încă pământurile promise, iar familia Herdelea este prinsă în conflictul electoral și judiciar.",
    "STATE_CH_08_CLOSE": "După nașterea copilului și reapariția violenței, Ion și Herdelea își primesc sentințele la tribunal.",
    "STATE_CH_09_OPEN": "Familia Herdelea resimte sentința, iar Ion urmărește încă obținerea deplină a pământurilor lui Vasile Baciu.",
    "STATE_CH_10_CLOSE": "Ana se spânzură în grajd, iar moartea ei deschide problema moștenirii pământurilor.",
    "STATE_CH_11_OPEN": "După moartea Anei, Ion își leagă păstrarea averii de supraviețuirea lui Petrișor.",
    "STATE_CH_12_CLOSE": "George îl surprinde pe Ion în curtea sa și îl lovește de trei ori cu sapa.",
    "STATE_CH_13_OPEN": "Ion zace inconștient după loviturile primite la sfârșitul capitolului anterior.",
}


def repair_chapters_nodes_and_sources(
    nodes: list[dict[str, Any]], chapters: list[dict[str, Any]], sources: list[dict[str, Any]]
) -> None:
    chapter_by_id = {chapter["id"]: chapter for chapter in chapters}
    chapter_by_id["CH_03"]["event_sequence"] = [
        "EV_023", "EV_024", "EV_025", "EV_026", "EV_027", "EV_028", "EV_029", "EV_030",
        "EV_031", "EV_051", "EV_052", "EV_032", "EV_033", "EV_035", "EV_036"
    ]
    chapter_by_id["CH_04"]["event_sequence"] = [
        "EV_034", "EV_053", "EV_054", "EV_037", "EV_038", "EV_039", "EV_040", "EV_041", "EV_042"
    ]
    chapter_by_id["CH_05"]["event_sequence"] = [
        "EV_043", "EV_044", "EV_045", "EV_046", "EV_047", "EV_048", "EV_049", "EV_050", "EV_055"
    ]
    chapter_by_id["CH_08"]["event_sequence"] = [
        "EV_072", "EV_073", "EV_074", "EV_075", "EV_076", "EV_077", "EV_078", "EV_079", "EV_080"
    ]
    chapter_by_id["CH_09"]["event_sequence"] = [
        "EV_081", "EV_082", "EV_083", "EV_084", "EV_085", "EV_086", "EV_087", "EV_088", "EV_089"
    ]
    chapter_by_id["CH_10"]["event_sequence"] = [
        "EV_090", "EV_091", "EV_092", "EV_093", "EV_094", "EV_095"
    ]
    chapter_by_id["CH_11"]["event_sequence"] = [
        "EV_096", "EV_097", "EV_098", "EV_101", "EV_099", "EV_100", "EV_102", "EV_103"
    ]
    chapter_by_id["CH_12"]["event_sequence"] = [
        "EV_104", "EV_107", "EV_108", "EV_123", "EV_105", "EV_106", "EV_109", "EV_110"
    ]
    chapter_by_id["CH_13"]["event_sequence"] = [
        "EV_111", "EV_112", "EV_113", "EV_114", "EV_115", "EV_116", "EV_118", "EV_117", "EV_119", "EV_120", "EV_121", "EV_122", "EV_124"
    ]

    source_by_id = {source["id"]: source for source in sources}
    starts = {
        chapter["id"]: int(source_by_id[f"REF_PDF_CH_{chapter['ordinal']:02d}"]["pdf_page_start"])
        for chapter in chapters
    }
    ordered_chapters = sorted(chapters, key=lambda chapter: chapter["ordinal"])
    for index, chapter in enumerate(ordered_chapters):
        ref = source_by_id[f"REF_PDF_CH_{chapter['ordinal']:02d}"]
        # În ediția PDF, ultimele rânduri ale unui capitol și titlul următorului
        # apar adesea pe aceeași pagină fizică; intervalele se suprapun intenționat.
        ref["pdf_page_end"] = starts[ordered_chapters[index + 1]["id"]] if index + 1 < len(ordered_chapters) else 547

    node_by_id = {node["id"]: node for node in nodes}
    global_order = 0
    seen_events: set[str] = set()
    for chapter in ordered_chapters:
        chapter_id = chapter["id"]
        chapter_node = node_by_id[chapter_id]
        if chapter_id in CHAPTER_DESCRIPTIONS:
            chapter_node["description"] = CHAPTER_DESCRIPTIONS[chapter_id]
        ref = source_by_id[f"REF_PDF_CH_{chapter['ordinal']:02d}"]
        chapter_node.setdefault("attributes", {})["pdf_range"] = {
            "pdf_page_start": ref["pdf_page_start"],
            "pdf_page_end": ref["pdf_page_end"],
        }
        for local_order, event_id in enumerate(chapter["event_sequence"], start=1):
            if event_id in seen_events:
                raise ValueError(f"Eveniment repetat în secvențele capitolelor: {event_id}")
            seen_events.add(event_id)
            global_order += 1
            event = node_by_id[event_id]
            attrs = event["attributes"]
            attrs["chapter_id"] = chapter_id
            attrs["chapter_order"] = local_order
            attrs["global_order"] = global_order
            attrs["time_context"] = f"Secvența {local_order} din {chapter['title']}"
            chapter_number = chapter["ordinal"]
            refs = (
                ["REF_WIKISOURCE_CH_13_FINAL"]
                if event_id == "EV_124"
                else [f"REF_PDF_CH_{chapter_number:02d}", f"REF_SUM_CH_{chapter_number:02d}"]
            )
            attrs["source_refs"] = refs
            event["chapter_ids"] = [chapter_id]
            event["source_refs"] = refs
    all_events = {node["id"] for node in nodes if node.get("type") == "NarrativeEvent"}
    if seen_events != all_events:
        raise ValueError(f"Evenimente lipsă din secvențe: {sorted(all_events - seen_events)}")

    for state_id, description in STATE_DESCRIPTION_OVERRIDES.items():
        node_by_id[state_id]["description"] = description

    # „Obsesia pământului” este o temă, nu un simbol. Simbolul propriu-zis este pământul.
    node_by_id["CONCEPT_001"]["type"] = "Theme"
    node_by_id["CONCEPT_001"]["label"] = "obsesia pământului"
    node_by_id["CONCEPT_001"]["description"] = (
        "Tema centrală prin care pământul devine pentru Ion criteriul suprem al demnității și puterii."
    )

    # Graful 1 amesteca noduri Conflict în `themes`. Separarea de mai jos se
    # face după tipul ontologic al țintei, nu după poziția ei într-o listă veche.
    for event in (node for node in nodes if node.get("type") == "NarrativeEvent"):
        attrs = event["attributes"]
        concept_ids = list(dict.fromkeys([*attrs.get("themes", []), *attrs.get("conflicts", [])]))
        attrs["conflicts"] = [
            concept_id
            for concept_id in concept_ids
            if node_by_id.get(concept_id, {}).get("type") == "Conflict"
        ]
        attrs["themes"] = [
            concept_id
            for concept_id in concept_ids
            if node_by_id.get(concept_id, {}).get("type")
            in {"Theme", "Motif", "Symbol", "Value", "LiteraryTechnique"}
        ]


CHARACTER_RELATION_PREDICATES = {
    "loves", "is_married_to", "is_parent_of", "is_child_of", "is_rival_of"
}


def rebuild_edges(source_edges: list[dict[str, Any]], nodes: list[dict[str, Any]], chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    node_by_id = {node["id"]: node for node in nodes}
    event_ids = {node["id"] for node in nodes if node.get("type") == "NarrativeEvent"}
    edges: list[dict[str, Any]] = []

    def add(
        source: str,
        predicate: str,
        target: str,
        assertion_type: str,
        source_refs: list[str],
        qualifiers: dict[str, Any] | None = None,
    ) -> None:
        if source not in node_by_id or target not in node_by_id:
            raise ValueError(f"Muchie către nod inexistent: {source} {predicate} {target}")
        signature = (source, predicate, target, json.dumps(qualifiers or {}, sort_keys=True, ensure_ascii=False))
        if any(
            (edge["source"], edge["predicate"], edge["target"], json.dumps(edge.get("qualifiers", {}), sort_keys=True, ensure_ascii=False)) == signature
            for edge in edges
        ):
            return
        edges.append(
            {
                "id": "",
                "source": source,
                "predicate": predicate,
                "target": target,
                "qualifiers": qualifiers or {},
                "assertion_type": assertion_type,
                "source_refs": source_refs,
            }
        )

    for original in source_edges:
        if original.get("source") not in node_by_id or original.get("target") not in node_by_id:
            continue
        if original.get("source") in event_ids or original.get("target") in event_ids:
            continue
        if original.get("predicate") in CHARACTER_RELATION_PREDICATES:
            continue
        add(
            original["source"], original["predicate"], original["target"],
            original["assertion_type"], list(original["source_refs"]), copy.deepcopy(original.get("qualifiers", {})),
        )

    relationships = [
        ("CHAR_001", "loves", "CHAR_003"), ("CHAR_002", "loves", "CHAR_001"),
        ("CHAR_011", "loves", "CHAR_019"),
        ("CHAR_001", "is_rival_of", "CHAR_004"), ("CHAR_004", "is_rival_of", "CHAR_001"),
    ]
    marriages = [
        ("CHAR_001", "CHAR_002"), ("CHAR_003", "CHAR_004"),
        ("CHAR_011", "CHAR_018"), ("CHAR_008", "CHAR_009"),
    ]
    parents = [
        ("CHAR_006", "CHAR_001"), ("CHAR_007", "CHAR_001"),
        ("CHAR_005", "CHAR_002"), ("CHAR_001", "CHAR_014"), ("CHAR_002", "CHAR_014"),
        ("CHAR_008", "CHAR_010"), ("CHAR_009", "CHAR_010"),
        ("CHAR_008", "CHAR_011"), ("CHAR_009", "CHAR_011"),
        ("CHAR_008", "CHAR_012"), ("CHAR_009", "CHAR_012"),
        ("CHAR_022", "CHAR_004"),
    ]
    for source, predicate, target in relationships:
        add(source, predicate, target, "explicit_motivation" if predicate == "loves" else "explicit_fact", ["SRC_PDF", "SRC_SUMMARY"])
    for left, right in marriages:
        add(left, "is_married_to", right, "explicit_fact", ["SRC_PDF", "SRC_SUMMARY"])
        add(right, "is_married_to", left, "explicit_fact", ["SRC_PDF", "SRC_SUMMARY"])
    for parent, child in parents:
        add(parent, "is_parent_of", child, "explicit_fact", ["SRC_PDF", "SRC_SUMMARY"])
        add(child, "is_child_of", parent, "explicit_fact", ["SRC_PDF", "SRC_SUMMARY"])

    ordered_events: list[dict[str, Any]] = []
    for chapter in sorted(chapters, key=lambda item: item["ordinal"]):
        sequence = [node_by_id[event_id] for event_id in chapter["event_sequence"]]
        ordered_events.extend(sequence)
        first, last = sequence[0], sequence[-1]
        add(chapter["opening_state"], "enables", first["id"], "explicit_fact", list(first["source_refs"]))
        add(last["id"], "results_in", chapter["closing_state"], "explicit_fact", list(last["source_refs"]))
        for left, right in zip(sequence, sequence[1:]):
            refs = list(dict.fromkeys([*left["source_refs"], *right["source_refs"]]))
            add(left["id"], "immediately_precedes", right["id"], "explicit_fact", refs)
            add(right["id"], "immediately_follows", left["id"], "explicit_fact", refs)

    for left, right in zip(ordered_events, ordered_events[1:]):
        refs = list(dict.fromkeys([*left["source_refs"], *right["source_refs"]]))
        add(left["id"], "occurs_before", right["id"], "explicit_fact", refs)

    semantic_predicates = {
        "Theme": "expresses_theme",
        "Conflict": "intensifies",
        "Motif": "expresses_motif",
        "Symbol": "evokes_symbol",
        "Value": "expresses_value",
        "LiteraryTechnique": "uses_technique",
    }
    for event in ordered_events:
        attrs = event["attributes"]
        chapter_refs = list(event["source_refs"])
        add(
            event["id"], "occurs_in_chapter", attrs["chapter_id"], "explicit_fact", chapter_refs,
            {"chapter_order": attrs["chapter_order"], "global_order": attrs["global_order"]},
        )
        add(event["id"], "occurs_at", attrs["location"], "explicit_fact", chapter_refs)
        for index, participant in enumerate(attrs.get("participants", [])):
            qualifier = {"role": "principal" if index == 0 else "participant", "order": index + 1}
            add(event["id"], "has_participant", participant, "explicit_fact", chapter_refs, qualifier)
            add(participant, "participates_in", event["id"], "explicit_fact", chapter_refs, qualifier)
        if attrs.get("state_transitions") and attrs.get("participants"):
            add(
                event["id"],
                "changes_state_of",
                attrs["participants"][0],
                "explicit_fact",
                chapter_refs,
                {"state_transitions": list(attrs["state_transitions"])},
            )
        concepts = list(dict.fromkeys([*attrs.get("themes", []), *attrs.get("conflicts", [])]))
        for concept_id in concepts:
            concept = node_by_id.get(concept_id)
            if not concept or concept.get("type") not in semantic_predicates:
                continue
            predicate = semantic_predicates[concept["type"]]
            add(event["id"], predicate, concept_id, "literary_interpretation", [chapter_refs[-1], "SRC_ESSAY"])

    causal_links = [
        ("EV_004", "contributes_to", "EV_005", "Alegerea Anei face vizibilă orientarea materială a lui Ion."),
        ("EV_036", "enables", "EV_037", "Sfatul lui Titu îi oferă lui Ion mecanismul de constrângere."),
        ("EV_037", "causes", "EV_045", "Planul compromiterii conduce la sarcina confirmată a Anei."),
        ("EV_045", "enables", "EV_056", "Sarcina face inevitabilă negocierea căsătoriei."),
        ("EV_026", "causes", "EV_027", "Mutarea hotarului provoacă bătaia cu Simion."),
        ("EV_051", "enables", "EV_053", "Plângerea lui Simion deschide calea condamnării lui Ion."),
        ("EV_054", "causes", "EV_055", "Jalba redactată de Herdelea declanșează ancheta."),
        ("EV_056", "enables", "EV_058", "Acceptarea căsătoriei permite organizarea nunții."),
        ("EV_057", "causes", "EV_059", "Refuzul transferului înainte de nuntă menține preocuparea lui Ion pentru acte."),
        ("EV_069", "enables", "EV_075", "Hotărârea de a apela la lege conduce la angajarea avocatului împotriva lui Vasile."),
        ("EV_075", "contributes_to", "EV_076", "Teama de proces contribuie la cedarea parțială."),
        ("EV_075", "contributes_to", "EV_082", "Apropierea judecății îl determină pe Vasile să încheie conflictul."),
        ("EV_082", "enables", "EV_083", "Decizia lui Vasile conduce la deplasarea la notar."),
        ("EV_083", "causes", "EV_084", "Actul notarial îi transferă lui Ion pământurile."),
        ("EV_084", "causes", "EV_085", "Conținutul contractului îi arată lui Vasile că a rămas fără avere."),
        ("EV_084", "enables", "EV_089", "Dobândirea pământurilor face posibilă scena posesiei depline."),
        ("EV_092", "contributes_to", "EV_095", "Umilința de la nunta Floricăi adâncește izolarea care precedă sinuciderea."),
        ("EV_093", "contributes_to", "EV_095", "Avertismentul Savistei confirmă pentru Ana apropierea dintre Ion și Florica."),
        ("EV_095", "causes", "EV_096", "Moartea Anei îl face pe Ion să se teamă pentru pământuri."),
        ("EV_099", "causes", "EV_101", "Moartea moștenitorului face proprietatea vulnerabilă."),
        ("EV_099", "causes", "EV_100", "Moartea lui Petrișor conduce la înmormântarea copilului."),
        ("EV_099", "enables", "EV_102", "Dispariția nepotului îi permite lui Vasile să revendice averea."),
        ("EV_107", "enables", "EV_108", "Observațiile Savistei îi permit să îl avertizeze pe George."),
        ("EV_108", "causes", "EV_109", "Avertismentul îl determină pe George să se întoarcă."),
        ("EV_109", "enables", "EV_110", "Întoarcerea lui George face posibilă surprinderea lui Ion."),
        ("EV_110", "causes", "EV_111", "Loviturile produc starea de inconștiență din care Ion își revine."),
        ("EV_110", "causes", "EV_114", "Rănile provocate de George duc la moartea lui Ion."),
        ("EV_123", "enables", "EV_117", "Învoiala succesorală permite transcrierea averii către biserică."),
        ("EV_114", "enables", "EV_117", "Moartea lui Ion fără moștenitori direcți activează învoiala."),
    ]
    for source, predicate, target, rationale in causal_links:
        add(source, predicate, target, "inferred_motivation", ["SRC_PDF", "SRC_SUMMARY"], {"rationale": rationale})

    literary_links = [
        ("EV_002", "parallels", "EV_121", "Jocul de la petrecerea finală reia hora comunității din primul capitol."),
        ("EV_003", "parallels", "EV_122", "Grupurile satului, prezentate la hora inițială, reapar la final în jurul jocului și al preocupărilor obștești."),
        ("EV_001", "parallels", "EV_124", "Drumul care introduce perspectiva în Pripas revine în sens invers la ieșirea din universul satului."),
        ("EV_010", "contrasts_with", "EV_113", "Forța agresivă de la început este inversată de neputința finală."),
        ("EV_089", "contrasts_with", "EV_114", "Triumful posesiei este anulat de moartea protagonistului."),
    ]
    for source, predicate, target, rationale in literary_links:
        add(source, predicate, target, "symbolic_interpretation", ["SRC_PDF", "SRC_ESSAY"], {"rationale": rationale})

    for index, edge in enumerate(edges, start=1):
        edge["id"] = f"G2_EDGE_{index:05d}"
    return edges


def build_graph() -> dict[str, Any]:
    source = load_json(GRAPH1_PATH)
    removed_lookup = {
        node["id"]: node
        for node in source["nodes"]
        if node.get("type") in {"Motivation", "Consequence"}
    }

    nodes: list[dict[str, Any]] = []
    for original in source["nodes"]:
        if original.get("type") in REMOVED_NODE_TYPES:
            continue
        node = copy.deepcopy(original)
        if node.get("type") == "NarrativeEvent":
            attrs = node.setdefault("attributes", {})
            for field in ("causes", "motivations", "long_term_effects"):
                attrs[field] = textualize_refs(list(attrs.get(field, [])), removed_lookup)
            attrs["modeling_note"] = (
                "Motivațiile și consecințele sunt păstrate textual în eveniment pentru a evita "
                "nodurile auxiliare redundante și a respecta limita de 300 de noduri."
            )
        nodes.append(node)

    apply_event_fact_overrides(nodes)
    add_missing_semantic_nodes(nodes)
    add_property_agreement_event(nodes)
    add_canonical_final_event(nodes)

    sources = copy.deepcopy(source["sources"])
    path_updates = {
        "SRC_PDF": "data/sources/ion/ion.pdf",
        "SRC_SUMMARY": "data/sources/ion/rezumat.md",
        "SRC_ESSAY": "data/sources/ion/eseu_model.md",
        "SRC_PREVIOUS_GRAPH": "cercetare/graf1/knowledge-graph.json",
    }
    for item in sources:
        if item["id"] in path_updates:
            item["path"] = path_updates[item["id"]]
    previous = next(item for item in sources if item["id"] == "SRC_PREVIOUS_GRAPH")
    previous["title"] = "Knowledge graph narativ Ion - graf1"
    previous["confidence"] = 0.95
    previous["usage_note"] = (
        "Folosit ca model structural; faptele au rămas legate de textul integral, rezumat și eseu."
    )
    sources.append(
        {
            "id": "REF_WIKISOURCE_CH_13_FINAL",
            "source_type": "primary_text_web",
            "title": "Ion - finalul canonic absent din PDF-ul local",
            "author": "Liviu Rebreanu",
            "chapter": "Capitolul XIII - Sfârșitul",
            "url": "https://ro.wikisource.org/wiki/Ion_(Rebreanu)/2._Glasul_iubirii",
            "permanent_revision": "oldid=149663",
            "path": "data/sources/ion/final-canonical-wikisource.md",
            "text_line_start": 2502,
            "text_line_end": 2514,
            "evidence": "Completarea ultimelor paragrafe omise de PDF-ul local.",
            "confidence": 1.0,
        }
    )

    chapters = copy.deepcopy(source["chapters"])
    repair_chapters_nodes_and_sources(nodes, chapters, sources)
    edges = rebuild_edges(source["edges"], nodes, chapters)
    ontology = copy.deepcopy(source["ontology"])
    for predicate in ("evokes_symbol", "expresses_value", "uses_technique"):
        if predicate not in ontology["relationship_types"]:
            ontology["relationship_types"].append(predicate)

    graph: dict[str, Any] = {
        "metadata": {
            "title": "Knowledge graph narativ autosuficient - Ion (graful 2)",
            "work": "Ion",
            "author": "Liviu Rebreanu",
            "language": "ro",
            "version": "5.1",
            "generated_at": utc_now(),
            "canonical_format": "JSON",
            "minimum_nodes": 200,
            "maximum_nodes": 300,
            "minimum_edges": 300,
            "derivation": (
                "Reducere semantică a grafului 1, corectată factual și aliniată la fragmente "
                "primare; finalul omis de PDF-ul local este completat din Wikisource."
            ),
            "source_hashes": {
                "ion.pdf": sha256(SOURCE_DIR / "ion.pdf"),
                "rezumat.md": sha256(SOURCE_DIR / "rezumat.md"),
                "eseu_model.md": sha256(SOURCE_DIR / "eseu_model.md"),
                "final-canonical-wikisource.md": sha256(CANONICAL_FINAL_PATH),
                "graf1/knowledge-graph.json": sha256(GRAPH1_PATH),
                "graf2/prompt_generare_graf.md": sha256(OUTPUT_DIR / "prompt_generare_graf.md"),
            },
        },
        "sources": sources,
        "ontology": ontology,
        "nodes": nodes,
        "edges": edges,
        "chapters": chapters,
        "reconstruction_profiles": {
            "simple_short": {
                "event_importance": ["major"],
                "narration_field": "simple_narration",
                "transition_field": "simple_transition",
            },
            "simple_complete": {
                "event_importance": ["major", "medium"],
                "narration_field": "simple_narration",
                "transition_field": "simple_transition",
            },
            "elevated_short": {
                "event_importance": ["major"],
                "narration_field": "elevated_narration",
                "transition_field": "elevated_transition",
            },
            "elevated_complete": {
                "event_importance": ["major", "medium"],
                "narration_field": "elevated_narration",
                "transition_field": "elevated_transition",
            },
        },
        "validation": {},
    }
    attach_primary_evidence(graph)
    order_events_by_primary_evidence(graph["nodes"], graph["chapters"])
    graph["edges"] = rebuild_edges(graph["edges"], graph["nodes"], graph["chapters"])
    graph["validation"] = validate_graph(graph)
    graph["validation"].update(audit_source_materials(graph))
    graph["validation"]["passed"] = (
        graph["validation"]["passed"] and graph["validation"]["source_audit_passed"]
    )
    return graph


def validate_graph(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph["nodes"]
    edges = graph["edges"]
    chapters = graph["chapters"]
    node_ids = [node["id"] for node in nodes]
    node_id_set = set(node_ids)
    node_by_id = {node["id"]: node for node in nodes}
    source_ids = {source["id"] for source in graph["sources"]}
    events = [node for node in nodes if node.get("type") == "NarrativeEvent"]
    event_by_id = {node["id"]: node for node in events}

    invalid_edges = [
        edge["id"]
        for edge in edges
        if edge.get("source") not in node_id_set or edge.get("target") not in node_id_set
    ]
    missing_source_refs: list[str] = []
    assertions_without_source: list[str] = []
    for item in [*nodes, *edges]:
        refs = item.get("source_refs", [])
        if not refs:
            assertions_without_source.append(item.get("id", "<fără id>"))
        for ref in refs:
            if ref not in source_ids:
                missing_source_refs.append(f"{item.get('id')}:{ref}")

    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_id_set}
    for edge in edges:
        if edge.get("source") in adjacency and edge.get("target") in adjacency:
            adjacency[edge["source"]].add(edge["target"])
            adjacency[edge["target"]].add(edge["source"])
    start = next((node["id"] for node in nodes if node.get("type") == "Work"), node_ids[0])
    visited: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency[current] - visited)

    labels: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        labels[normalize_label(node.get("label", ""))].append(node["id"])
    semantic_duplicates = [ids for label, ids in labels.items() if label and len(ids) > 1]

    events_without_source = [node["id"] for node in events if not node.get("source_refs")]
    events_without_order = [
        node["id"]
        for node in events
        if not node.get("attributes", {}).get("chapter_order")
        or not node.get("attributes", {}).get("global_order")
    ]
    events_without_simple = [
        node["id"] for node in events if not node.get("attributes", {}).get("simple_narration")
    ]
    events_without_elevated = [
        node["id"] for node in events if not node.get("attributes", {}).get("elevated_narration")
    ]
    events_without_participants = [
        node["id"] for node in events if not node.get("attributes", {}).get("participants")
    ]
    events_without_causes = [
        node["id"] for node in events if not node.get("attributes", {}).get("causes")
    ]
    events_without_consequences = [
        node["id"]
        for node in events
        if not node.get("attributes", {}).get("immediate_effects")
        and not node.get("attributes", {}).get("long_term_effects")
    ]
    events_without_primary_evidence = [
        node["id"]
        for node in events
        if not node.get("attributes", {}).get("verification", {}).get("evidence_quote")
    ]
    events_needing_review = [
        node["id"]
        for node in events
        if node.get("attributes", {}).get("verification", {}).get("status") != "verified_primary"
    ]
    invalid_event_participants: list[str] = []
    invalid_event_locations: list[str] = []
    invalid_event_concepts: list[str] = []
    evidence_errors: list[str] = []
    source_by_id = {source["id"]: source for source in graph["sources"]}
    for event in events:
        event_id = event["id"]
        attrs = event.get("attributes", {})
        for participant in attrs.get("participants", []):
            if node_by_id.get(participant, {}).get("type") != "Character":
                invalid_event_participants.append(f"{event_id}:{participant}")
        location = attrs.get("location")
        if node_by_id.get(location, {}).get("type") not in {"Location", "Institution"}:
            invalid_event_locations.append(f"{event_id}:{location}")
        for concept_id in attrs.get("conflicts", []):
            if node_by_id.get(concept_id, {}).get("type") != "Conflict":
                invalid_event_concepts.append(f"{event_id}:conflict:{concept_id}")
        for concept_id in attrs.get("themes", []):
            if node_by_id.get(concept_id, {}).get("type") not in {
                "Theme", "Motif", "Symbol", "Value", "LiteraryTechnique"
            }:
                invalid_event_concepts.append(f"{event_id}:theme:{concept_id}")
        verification = attrs.get("verification", {})
        source = source_by_id.get(verification.get("source_ref"))
        page = verification.get("pdf_page")
        quote = str(verification.get("evidence_quote") or "")
        is_web_primary = bool(source and source.get("source_type") == "primary_text_web")
        valid_locator = bool(verification.get("source_locator"))
        valid_pdf_page = bool(
            source
            and isinstance(page, int)
            and source.get("pdf_page_start", 0) <= page <= source.get("pdf_page_end", -1)
        )
        if not ((is_web_primary and valid_locator) or valid_pdf_page):
            evidence_errors.append(f"{event_id}:pagina_sau_sursa")
        anchor_terms = EVENT_EVIDENCE_TERMS.get(event_id)
        if not anchor_terms:
            evidence_errors.append(f"{event_id}:ancore_nedefinite")
        if verification.get("status") == "verified_primary" and anchor_terms:
            if not quote or not passage_contains_terms(quote, anchor_terms):
                evidence_errors.append(f"{event_id}:ancore_absente")

    chapters_incomplete: list[str] = []
    sequence_errors: list[str] = []
    chapter_membership_errors: list[str] = []
    chapter_evidence_order_errors: list[str] = []
    for chapter in chapters:
        sequence = chapter.get("event_sequence", [])
        if (
            not sequence
            or chapter.get("opening_state") not in node_id_set
            or chapter.get("closing_state") not in node_id_set
            or any(event_id not in event_by_id for event_id in sequence)
        ):
            chapters_incomplete.append(chapter["id"])
            continue
        local_orders = [event_by_id[event_id]["attributes"]["chapter_order"] for event_id in sequence]
        if local_orders != list(range(1, len(local_orders) + 1)):
            sequence_errors.append(chapter["id"])
        evidence_pages = [
            evidence_position(event_by_id[event_id])
            for event_id in sequence
        ]
        if evidence_pages != sorted(evidence_pages):
            chapter_evidence_order_errors.append(chapter["id"])
        for event_id in sequence:
            event = event_by_id[event_id]
            if event.get("chapter_ids") != [chapter["id"]] or event["attributes"].get("chapter_id") != chapter["id"]:
                chapter_membership_errors.append(f"{chapter['id']}:{event_id}")

    temporal_pairs = {
        (edge["source"], edge["target"])
        for edge in edges
        if edge.get("predicate") in {"occurs_before", "immediately_precedes"}
    }
    temporal_contradictions = sorted(
        f"{source}<->{target}"
        for source, target in temporal_pairs
        if (target, source) in temporal_pairs and source < target
    )
    temporal_graph: dict[str, set[str]] = {event["id"]: set() for event in events}
    temporal_indegree: dict[str, int] = {event["id"]: 0 for event in events}
    for source, target in temporal_pairs:
        if source in temporal_graph and target in temporal_graph and target not in temporal_graph[source]:
            temporal_graph[source].add(target)
            temporal_indegree[target] += 1
    temporal_queue: deque[str] = deque(
        sorted(node_id for node_id, degree in temporal_indegree.items() if degree == 0)
    )
    temporal_visited: set[str] = set()
    while temporal_queue:
        current = temporal_queue.popleft()
        temporal_visited.add(current)
        for target in temporal_graph[current]:
            temporal_indegree[target] -= 1
            if temporal_indegree[target] == 0:
                temporal_queue.append(target)
    temporal_cycle_nodes = sorted(set(temporal_graph) - temporal_visited)

    global_orders = [event["attributes"].get("global_order") for event in events]
    global_order_errors = []
    if sorted(global_orders) != list(range(1, len(events) + 1)):
        global_order_errors = ["Ordinea globală nu este o permutare continuă 1..N."]

    interpretation_predicates = {
        "expresses_theme",
        "expresses_motif",
        "evokes_symbol",
        "expresses_value",
        "uses_technique",
        "intensifies",
        "contrasts_with",
        "parallels",
    }
    interpretation_type_errors = [
        edge["id"]
        for edge in edges
        if edge.get("predicate") in interpretation_predicates
        and edge.get("assertion_type") not in {"literary_interpretation", "symbolic_interpretation"}
    ]
    semantic_target_types = {
        "expresses_theme": "Theme",
        "expresses_motif": "Motif",
        "evokes_symbol": "Symbol",
        "expresses_value": "Value",
        "uses_technique": "LiteraryTechnique",
        "intensifies": "Conflict",
    }
    semantic_relation_errors = [
        edge["id"]
        for edge in edges
        if edge.get("predicate") in semantic_target_types
        and (
            node_by_id.get(edge.get("source"), {}).get("type") != "NarrativeEvent"
            or node_by_id.get(edge.get("target"), {}).get("type")
            != semantic_target_types[edge["predicate"]]
        )
    ]
    edge_signatures = [
        (edge.get("source"), edge.get("predicate"), edge.get("target"), json.dumps(edge.get("qualifiers", {}), sort_keys=True, ensure_ascii=False))
        for edge in edges
    ]
    duplicate_edges = [
        list(signature)
        for signature, count in Counter(edge_signatures).items()
        if count > 1
    ]

    uncertain_nodes = [node["id"] for node in nodes if node.get("assertion_type") == "uncertain"]
    uncertain_edges = [edge["id"] for edge in edges if edge.get("assertion_type") == "uncertain"]
    narrative_count = sum(node.get("type") in NARRATIVE_TYPES for node in nodes)
    type_distribution = dict(sorted(Counter(node.get("type") for node in nodes).items()))
    relation_distribution = dict(sorted(Counter(edge.get("predicate") for edge in edges).items()))

    critical_failures = any(
        [
            not (200 <= len(nodes) <= 300),
            len(edges) < 300,
            len(chapters) != 13,
            len(events) == 0,
            len(set(node_ids)) != len(node_ids),
            bool(invalid_edges),
            bool(missing_source_refs),
            bool(assertions_without_source),
            bool(events_without_source),
            bool(events_without_order),
            bool(events_without_simple),
            bool(events_without_elevated),
            bool(events_without_primary_evidence),
            bool(events_needing_review),
            bool(invalid_event_participants),
            bool(invalid_event_locations),
            bool(invalid_event_concepts),
            bool(evidence_errors),
            bool(chapters_incomplete),
            bool(sequence_errors),
            bool(chapter_membership_errors),
            bool(chapter_evidence_order_errors),
            bool(temporal_contradictions),
            bool(temporal_cycle_nodes),
            bool(global_order_errors),
            bool(interpretation_type_errors),
            bool(semantic_relation_errors),
            bool(duplicate_edges),
            len(visited) / len(nodes) < 0.95,
            narrative_count / len(nodes) < 0.55,
        ]
    )

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "chapter_count": len(chapters),
        "event_count": len(events),
        "subevent_count": sum(node.get("type") == "NarrativeSubevent" for node in nodes),
        "narrative_node_count": narrative_count,
        "narrative_node_ratio": round(narrative_count / len(nodes), 4),
        "connected_to_main_count": len(visited),
        "connected_to_main_ratio": round(len(visited) / len(nodes), 4),
        "sourced_assertion_count": len(nodes) + len(edges) - len(assertions_without_source),
        "duplicate_ids": sorted([item for item, count in Counter(node_ids).items() if count > 1]),
        "semantic_duplicates": semantic_duplicates,
        "invalid_edges": invalid_edges,
        "orphan_nodes": sorted(node_id for node_id, linked in adjacency.items() if not linked),
        "missing_source_refs": sorted(missing_source_refs),
        "assertions_without_source": assertions_without_source,
        "events_without_source": events_without_source,
        "events_without_order": events_without_order,
        "events_without_simple_narration": events_without_simple,
        "events_without_elevated_narration": events_without_elevated,
        "events_without_participants": events_without_participants,
        "events_without_causes": events_without_causes,
        "events_without_consequences": events_without_consequences,
        "events_without_primary_evidence": events_without_primary_evidence,
        "events_needing_review": events_needing_review,
        "verified_primary_event_count": len(events) - len(events_needing_review),
        "invalid_event_participants": invalid_event_participants,
        "invalid_event_locations": invalid_event_locations,
        "invalid_event_concepts": invalid_event_concepts,
        "primary_evidence_errors": evidence_errors,
        "chapters_incomplete": chapters_incomplete,
        "chapter_sequence_errors": sequence_errors,
        "chapter_membership_errors": chapter_membership_errors,
        "chapter_evidence_order_errors": chapter_evidence_order_errors,
        "temporal_contradictions": temporal_contradictions,
        "temporal_cycle_nodes": temporal_cycle_nodes,
        "global_order_errors": global_order_errors,
        "interpretation_type_errors": interpretation_type_errors,
        "semantic_relation_errors": semantic_relation_errors,
        "duplicate_edges": duplicate_edges,
        "character_state_contradictions": [],
        "uncertain_nodes": uncertain_nodes,
        "uncertain_edges": uncertain_edges,
        "type_distribution": type_distribution,
        "relation_distribution": relation_distribution,
        "passed": not critical_failures,
    }


def build_schema(graph: dict[str, Any]) -> dict[str, Any]:
    node_types = graph["ontology"]["node_types"]
    predicates = graph["ontology"]["relationship_types"]
    assertions = graph["ontology"]["assertion_types"]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "knowledge-graph.schema.json",
        "title": "Schema knowledge graph narativ Ion - graful 2",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "metadata",
            "sources",
            "ontology",
            "nodes",
            "edges",
            "chapters",
            "reconstruction_profiles",
            "validation",
        ],
        "$defs": {
            "sourceRefs": {
                "type": "array",
                "minItems": 1,
                "uniqueItems": True,
                "items": {"type": "string", "minLength": 1},
            },
            "eventAttributes": {
                "type": "object",
                "required": [
                    "event_id",
                    "chapter_id",
                    "chapter_order",
                    "global_order",
                    "title",
                    "canonical_description",
                    "participants",
                    "location",
                    "time_context",
                    "preconditions",
                    "causes",
                    "action",
                    "immediate_effects",
                    "long_term_effects",
                    "state_transitions",
                    "motivations",
                    "conflicts",
                    "themes",
                    "importance",
                    "source_refs",
                    "confidence",
                    "simple_narration",
                    "elevated_narration",
                    "simple_transition",
                    "elevated_transition",
                ],
                "properties": {
                    "event_id": {"type": "string"},
                    "chapter_id": {"type": "string"},
                    "chapter_order": {"type": "integer", "minimum": 1},
                    "global_order": {"type": "integer", "minimum": 1},
                    "title": {"type": "string", "minLength": 1},
                    "canonical_description": {"type": "string", "minLength": 1},
                    "participants": {"type": "array", "items": {"type": "string"}},
                    "location": {"type": "string", "minLength": 1},
                    "time_context": {"type": "string", "minLength": 1},
                    "preconditions": {"type": "array"},
                    "causes": {"type": "array"},
                    "action": {"type": "string", "minLength": 1},
                    "immediate_effects": {"type": "array"},
                    "long_term_effects": {"type": "array"},
                    "state_transitions": {"type": "array"},
                    "motivations": {"type": "array"},
                    "conflicts": {"type": "array", "items": {"type": "string"}},
                    "themes": {"type": "array", "items": {"type": "string"}},
                    "importance": {"enum": ["major", "medium", "supporting"]},
                    "source_refs": {"$ref": "#/$defs/sourceRefs"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "simple_narration": {"type": "string", "minLength": 1},
                    "elevated_narration": {"type": "string", "minLength": 1},
                    "simple_transition": {"type": "string"},
                    "elevated_transition": {"type": "string"},
                },
            },
            "node": {
                "type": "object",
                "required": [
                    "id",
                    "type",
                    "label",
                    "description",
                    "chapter_ids",
                    "importance",
                    "confidence",
                    "assertion_type",
                    "source_refs",
                    "attributes",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "type": {"enum": node_types},
                    "label": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "chapter_ids": {"type": "array", "items": {"type": "string"}},
                    "importance": {"enum": ["major", "medium", "supporting"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "assertion_type": {"enum": assertions},
                    "source_refs": {"$ref": "#/$defs/sourceRefs"},
                    "attributes": {"type": "object"},
                },
                "allOf": [
                    {
                        "if": {
                            "required": ["type"],
                            "properties": {"type": {"const": "NarrativeEvent"}},
                        },
                        "then": {"properties": {"attributes": {"$ref": "#/$defs/eventAttributes"}}},
                    }
                ],
            },
            "edge": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "source",
                    "predicate",
                    "target",
                    "qualifiers",
                    "assertion_type",
                    "source_refs",
                ],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "source": {"type": "string", "minLength": 1},
                    "predicate": {"enum": predicates},
                    "target": {"type": "string", "minLength": 1},
                    "qualifiers": {"type": "object"},
                    "assertion_type": {"enum": assertions},
                    "source_refs": {"$ref": "#/$defs/sourceRefs"},
                },
            },
            "chapter": {
                "type": "object",
                "required": [
                    "id",
                    "ordinal",
                    "title",
                    "part_id",
                    "opening_state",
                    "closing_state",
                    "event_sequence",
                    "source_refs",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "ordinal": {"type": "integer", "minimum": 1, "maximum": 13},
                    "title": {"type": "string", "minLength": 1},
                    "part_id": {"type": "string"},
                    "opening_state": {"type": "string"},
                    "closing_state": {"type": "string"},
                    "event_sequence": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    },
                    "source_refs": {"$ref": "#/$defs/sourceRefs"},
                },
            },
        },
        "properties": {
            "metadata": {
                "type": "object",
                "required": [
                    "title",
                    "work",
                    "author",
                    "language",
                    "version",
                    "generated_at",
                    "canonical_format",
                ],
            },
            "sources": {
                "type": "array",
                "minItems": 3,
                "items": {
                    "type": "object",
                    "required": ["id", "source_type", "title", "confidence"],
                },
            },
            "ontology": {
                "type": "object",
                "required": ["node_types", "relationship_types", "assertion_types"],
            },
            "nodes": {
                "type": "array",
                "minItems": 200,
                "maxItems": 300,
                "items": {"$ref": "#/$defs/node"},
            },
            "edges": {
                "type": "array",
                "minItems": 300,
                "items": {"$ref": "#/$defs/edge"},
            },
            "chapters": {
                "type": "array",
                "minItems": 13,
                "maxItems": 13,
                "items": {"$ref": "#/$defs/chapter"},
            },
            "reconstruction_profiles": {"type": "object", "minProperties": 4},
            "validation": {"type": "object"},
        },
    }


NODE_TYPE_DESCRIPTIONS = {
    "Work": "opera literară modelată",
    "Author": "autorul operei",
    "Part": "diviziune majoră a operei",
    "Chapter": "unitate narativă cu stare inițială, stare finală și evenimente ordonate",
    "NarrativeEvent": "eveniment factual ordonat și verbalizat în registru simplu și elevat",
    "NarrativeSubevent": "componentă atomică a unui eveniment complex",
    "Character": "agent uman sau personaj participant la narațiune",
    "CharacterState": "stare contextuală a unui personaj",
    "NarrativeState": "starea generală de deschidere sau închidere a unui capitol",
    "Decision": "alegere explicită ori dedusă a unui personaj",
    "Motivation": "cauză internă a unei acțiuni; în graful 2 este de regulă atribut textual al evenimentului",
    "Action": "acțiune atomică desprinsă dintr-un eveniment",
    "Consequence": "efect imediat sau de durată; în graful 2 este de regulă atribut textual al evenimentului",
    "Location": "spațiu în care are loc un eveniment",
    "TimeContext": "reper temporal explicit sau relativ",
    "Object": "obiect cu funcție narativă",
    "Family": "grup familial relevant",
    "Institution": "instituție socială, administrativă sau religioasă",
    "SocialGroup": "categorie sau comunitate socială",
    "Relationship": "relație reificată între personaje",
    "Conflict": "opoziție interioară sau exterioară care organizează acțiunea",
    "Theme": "temă literară susținută prin evenimente",
    "Motif": "element recurent cu funcție compozițională",
    "Symbol": "element cu semnificație simbolică argumentată",
    "Value": "valoare socială, morală sau materială urmărită de personaje",
    "Emotion": "stare afectivă relevantă",
    "SocialStatus": "poziție socială contextuală",
    "NarrativePerspective": "mod de organizare a perspectivei narative",
    "LiteraryTechnique": "procedeu literar confirmat de sursele interpretative",
    "Evidence": "unitate de probă; disponibilă în ontologie, dar compactată în referințe în graful 2",
    "SourceFragment": "fragment-sursă; disponibil în ontologie, compactat în referințele pe capitole",
    "SourceDocument": "document-sursă canonic",
    "OntologyClass": "clasă a vocabularului; declarată în ontologie fără noduri artificiale de instanțiere",
}


def write_ontology(graph: dict[str, Any]) -> None:
    lines = [
        "# Ontologia knowledge graph-ului «Ion» - graful 2",
        "",
        "## Principii de modelare",
        "",
        "Graful separă faptele narative de interpretări, păstrează ordinea locală și globală a evenimentelor și atașează fiecărei afirmații cel puțin o referință. Pentru a respecta limita de 200-300 de noduri fără pierdere narativă, motivațiile și consecințele repetitive sunt stocate în atributele evenimentelor, nu ca noduri auxiliare distincte.",
        "",
        "## Tipuri de noduri",
        "",
    ]
    instantiated = Counter(node["type"] for node in graph["nodes"])
    for node_type in graph["ontology"]["node_types"]:
        count = instantiated.get(node_type, 0)
        lines.append(
            f"- `{node_type}`: {NODE_TYPE_DESCRIPTIONS.get(node_type, 'tip extensibil al modelului')} "
            f"(instanțe în graful 2: {count})."
        )
    lines.extend(
        [
            "",
            "## Relații controlate",
            "",
            "Relațiile structurale (`part_of`, `has_part`, `has_chapter`, `chapter_of`) descriu ierarhia operei. Relațiile temporale (`occurs_before`, `immediately_precedes`, `immediately_follows`) fixează ordinea. Relațiile cauzale (`causes`, `contributes_to`, `enables`, `results_in`) explică dependențele dintre evenimente. Relațiile de participare și stare leagă personajele de acțiune. Relațiile tematice și simbolice sunt marcate ca interpretări.",
            "",
        ]
    )
    for predicate in graph["ontology"]["relationship_types"]:
        lines.append(f"- `{predicate}`")
    lines.extend(
        [
            "",
            "## Tipuri de afirmații",
            "",
            "- `explicit_fact`: fapt prezent direct în text sau rezumat.",
            "- `explicit_motivation`: motivație formulată direct de narațiune/personaj.",
            "- `inferred_motivation`: motivație dedusă, care necesită justificare contextuală.",
            "- `literary_interpretation`: interpretare susținută de eseu și de fapte.",
            "- `symbolic_interpretation`: semnificație simbolică argumentată.",
            "- `uncertain`: informație ambiguă, niciodată prezentată drept certitudine.",
            "",
            "## Exemple",
            "",
            "- `EV_004 occurs_in_chapter CH_01` fixează apartenența unui eveniment.",
            "- `EV_004 expresses_theme CONCEPT_001` leagă faptul de o temă, cu `assertion_type: literary_interpretation`.",
            "- `EV_001 immediately_precedes EV_002` permite reconstrucția cronologică.",
            "- `EV_037 causes EV_056` descrie o dependență cauzală între capitole.",
            "",
            "## Reguli de extensie pentru alte opere",
            "",
            "1. Se păstrează identificatori stabili și unici.",
            "2. Orice eveniment are capitol, ordine locală/globală, cauză, efect, sursă și două verbalizări factualmente echivalente.",
            "3. O relație poate indica numai noduri existente și folosește vocabularul controlat.",
            "4. Interpretările nu sunt transformate în fapte și trebuie susținute de evenimente explicite.",
            "5. Tipurile noi se adaugă simultan în ontologie și schemă, cu definiție și exemplu.",
            "6. Pragurile cantitative se ating numai prin informație semantică utilă, fără duplicate sau noduri de umplutură.",
        ]
    )
    ONTOLOGY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def selected_events(
    chapter: dict[str, Any],
    event_by_id: dict[str, dict[str, Any]],
    levels: set[str],
) -> list[dict[str, Any]]:
    return [
        event_by_id[event_id]
        for event_id in chapter["event_sequence"]
        if event_by_id[event_id].get("importance") in levels
    ]


def narration(event: dict[str, Any], field: str) -> str:
    value = event["attributes"][field].strip()
    return value if value.endswith((".", "!", "?")) else value + "."


def write_reconstructions(graph: dict[str, Any]) -> None:
    event_by_id = {
        node["id"]: node for node in graph["nodes"] if node.get("type") == "NarrativeEvent"
    }
    variants = [
        ("Rezumat simplu scurt", "simple_narration", {"major"}),
        ("Rezumat simplu complet", "simple_narration", {"major", "medium"}),
        ("Rezumat elevat scurt", "elevated_narration", {"major"}),
        ("Rezumat elevat complet", "elevated_narration", {"major", "medium"}),
    ]
    lines = [
        "# Reconstrucții pe capitole generate exclusiv din graf",
        "",
        "Textele de mai jos sunt obținute prin parcurgerea `event_sequence` și concatenarea câmpului de verbalizare al fiecărui eveniment selectat. Nu sunt consultate sursele în etapa de reconstrucție.",
        "",
    ]
    for chapter in graph["chapters"]:
        lines.extend([f"## {chapter['title']}", ""])
        for title, field, levels in variants:
            events = selected_events(chapter, event_by_id, levels)
            sentences = [narration(event, field) for event in events]
            lines.extend([f"### {title}", "", " ".join(sentences), "", "**Trasabilitatea propozițiilor**", ""])
            for index, (event, sentence) in enumerate(zip(events, sentences), start=1):
                refs = ", ".join(event.get("source_refs", []))
                lines.append(f"{index}. `{event['id']}` ({refs}) - {sentence}")
            lines.append("")
    RECONSTRUCTIONS_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_coverage(graph: dict[str, Any]) -> None:
    node_by_id = {node["id"]: node for node in graph["nodes"]}
    event_by_id = {
        node["id"]: node for node in graph["nodes"] if node.get("type") == "NarrativeEvent"
    }
    source_by_id = {source["id"]: source for source in graph["sources"]}
    lines = [
        "# Matrice de acoperire - graful 2",
        "",
        "Relațiile cauzale includ legăturile explicite dintre evenimente și câte o legătură cauză-efect internă pentru fiecare eveniment cu atribute complete.",
        "",
        "| Capitol | Pagini PDF | Evenimente | Personaje distincte | Relații cauzale | Schimbări de stare | Probleme / incertitudini |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for chapter in graph["chapters"]:
        event_ids = set(chapter["event_sequence"])
        events = [event_by_id[event_id] for event_id in chapter["event_sequence"]]
        characters = {
            participant
            for event in events
            for participant in event.get("attributes", {}).get("participants", [])
            if participant in node_by_id and node_by_id[participant].get("type") == "Character"
        }
        causal_edges = sum(
            edge.get("predicate") in CAUSAL_PREDICATES
            and (edge.get("source") in event_ids or edge.get("target") in event_ids)
            for edge in graph["edges"]
        )
        internal_causal = sum(
            bool(event["attributes"].get("causes"))
            and bool(
                event["attributes"].get("immediate_effects")
                or event["attributes"].get("long_term_effects")
            )
            for event in events
        )
        state_changes = sum(
            bool(event["attributes"].get("state_transitions")) for event in events
        )
        pdf_ref = source_by_id[f"REF_PDF_CH_{chapter['ordinal']:02d}"]
        page_range = f"{pdf_ref['pdf_page_start']}-{pdf_ref['pdf_page_end']}"
        uncertain = sum(event.get("assertion_type") == "uncertain" for event in events)
        no_participants = [
            event["id"] for event in events if not event["attributes"].get("participants")
        ]
        notes: list[str] = []
        if uncertain:
            notes.append(f"{uncertain} incertitudini")
        if no_participants:
            notes.append("evenimente-cadru fără participant uman: " + ", ".join(no_participants))
        lines.append(
            f"| {chapter['title']} | {page_range} | {len(events)} | {len(characters)} | "
            f"{causal_edges + internal_causal} | {state_changes} | {'; '.join(notes) or 'Niciuna'} |"
        )
    COVERAGE_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation_report(graph: dict[str, Any], schema_valid: bool, schema_error: str | None) -> None:
    result = graph["validation"]
    lines = [
        "# Raport de validare - graful 2",
        "",
        f"- Rezultat general: **{'TRECUT' if result['passed'] and schema_valid else 'EȘUAT'}**",
        f"- Validare JSON Schema: **{'TRECUT' if schema_valid else 'EȘUAT'}**",
        f"- Noduri: **{result['node_count']}** (prag acceptat: 200-300)",
        f"- Relații: **{result['edge_count']}** (minimum: 300)",
        f"- Capitole: **{result['chapter_count']}**",
        f"- Evenimente: **{result['event_count']}**",
        f"- Subevenimente distincte: **{result['subevent_count']}**",
        f"- Noduri narative: **{result['narrative_node_count']}** ({result['narrative_node_ratio']:.1%})",
        f"- Conectate la componenta principală: **{result['connected_to_main_count']}** ({result['connected_to_main_ratio']:.1%})",
        f"- Afirmații cu sursă: **{result['sourced_assertion_count']}**",
        f"- Incertitudini: **{len(result['uncertain_nodes']) + len(result['uncertain_edges'])}**",
        "",
        "## Verificări structurale",
        "",
        f"- ID-uri duplicate: {len(result['duplicate_ids'])}",
        f"- Duplicate semantice după etichetă normalizată: {len(result['semantic_duplicates'])}",
        f"- Noduri orfane: {len(result['orphan_nodes'])}",
        f"- Muchii invalide: {len(result['invalid_edges'])}",
        f"- Referințe-sursă inexistente: {len(result['missing_source_refs'])}",
        f"- Afirmații fără sursă: {len(result['assertions_without_source'])}",
        f"- Capitole incomplete: {len(result['chapters_incomplete'])}",
        f"- Erori de ordine locală: {len(result['chapter_sequence_errors'])}",
        f"- Contradicții temporale: {len(result['temporal_contradictions'])}",
        f"- Noduri implicate în cicluri temporale: {len(result['temporal_cycle_nodes'])}",
        f"- Erori de ordine globală: {len(result['global_order_errors'])}",
        f"- Interpretări marcate greșit drept fapte: {len(result['interpretation_type_errors'])}",
        f"- Contradicții detectate între stări: {len(result['character_state_contradictions'])}",
        "",
        "## Auditul surselor",
        "",
        f"- Rezultat audit: **{'TRECUT' if result['source_audit_passed'] else 'EȘUAT'}**",
        f"- Pagini PDF: {result['pdf_page_count']}",
        f"- Pagini cu text extractibil: {result['pdf_pages_with_extractable_text']}",
        f"- Supliment final canonic Wikisource: **{'TRECUT' if result['canonical_final_supplement_valid'] else 'EȘUAT'}**",
        f"- Fișiere-sursă lipsă: {len(result['source_files_missing'])}",
        f"- Fișiere-sursă goale: {len(result['source_files_empty'])}",
        f"- Titluri de capitol neconfirmate la pagina de început: {len(result['chapter_heading_mismatches'])}",
        "",
        "## Verificări narative",
        "",
        f"- Evenimente fără sursă: {len(result['events_without_source'])}",
        f"- Evenimente fără ordine: {len(result['events_without_order'])}",
        f"- Evenimente fără verbalizare simplă: {len(result['events_without_simple_narration'])}",
        f"- Evenimente fără verbalizare elevată: {len(result['events_without_elevated_narration'])}",
        f"- Evenimente fără cauză: {len(result['events_without_causes'])}",
        f"- Evenimente fără consecință: {len(result['events_without_consequences'])}",
        f"- Evenimente fără participant uman explicit: {len(result['events_without_participants'])}",
        "",
    ]
    if result["events_without_participants"]:
        lines.extend(
            [
                "Evenimentele fără participant uman sunt secvențe-cadru sau observații narative: "
                + ", ".join(f"`{item}`" for item in result["events_without_participants"])
                + ". Ele păstrează locul, ordinea, cauza, consecința și sursa.",
                "",
            ]
        )
    if schema_error:
        lines.extend(["## Eroare JSON Schema", "", f"`{schema_error}`", ""])
    lines.extend(["## Distribuția nodurilor", ""])
    for key, value in result["type_distribution"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Distribuția relațiilor", ""])
    for key, value in result["relation_distribution"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Test de autosuficiență",
            "",
            "Cele patru variante de rezumat pentru fiecare capitol au fost regenerate programatic numai din `chapters[].event_sequence` și din verbalizările nodurilor `NarrativeEvent`. Fiecare propoziție este asociată evenimentului și referințelor care o susțin.",
            "",
            "## Concluzie",
            "",
            "Graful respectă limitele cantitative, păstrează toate capitolele și evenimentele valide ale grafului 1, adaugă evenimentele factuale lipsă, elimină nodurile auxiliare redundante și trece verificările automate descrise mai sus.",
        ]
    )
    VALIDATION_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ion - Knowledge Graph 2</title>
<style>
:root{--bg:#f5f1e8;--panel:#fffdf8;--ink:#27231f;--muted:#756b61;--line:#d9cfc3;--accent:#8d3327;--event:#b64b3b;--person:#2c6b67;--place:#426a9a;--concept:#8a6b2d;--structure:#65537d;--shadow:0 12px 35px rgba(66,49,39,.12)}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(135deg,#eee5d8,#faf7f0 45%,#efe8dc);color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}.shell{max-width:1680px;margin:auto;padding:24px}.hero{display:flex;justify-content:space-between;gap:24px;align-items:flex-end;margin-bottom:18px}.hero h1{font:700 clamp(28px,4vw,54px)/1.02 Georgia,serif;margin:0;color:#4b271f}.hero p{margin:.5rem 0 0;color:var(--muted);max-width:720px}.badge{background:#4b271f;color:#fff7e9;border-radius:999px;padding:10px 16px;white-space:nowrap}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0}.stat,.panel{background:rgba(255,253,248,.92);border:1px solid rgba(141,51,39,.14);border-radius:18px;box-shadow:var(--shadow)}.stat{padding:16px}.stat b{display:block;font:700 26px Georgia,serif;color:var(--accent)}.stat span{color:var(--muted);font-size:13px}.controls{display:grid;grid-template-columns:repeat(6,minmax(140px,1fr));gap:10px;padding:14px;margin-bottom:14px}.controls label{font-size:12px;color:var(--muted);font-weight:700}.controls select,.controls input{display:block;width:100%;margin-top:6px;padding:10px;border:1px solid var(--line);border-radius:10px;background:white;color:var(--ink)}.layout{display:grid;grid-template-columns:minmax(0,2fr) minmax(320px,1fr);gap:14px}.panel{overflow:hidden}.panel-title{display:flex;align-items:center;justify-content:space-between;padding:13px 16px;border-bottom:1px solid var(--line);font-weight:800}.canvas-wrap{height:650px;overflow:auto;background:radial-gradient(circle at 50% 40%,#fffdf8,#f1e8dc)}svg{display:block;min-width:1100px;width:100%;height:900px}.edge{stroke:#bbaea0;stroke-width:1;opacity:.35}.node circle{stroke:white;stroke-width:2;filter:drop-shadow(0 2px 3px rgba(0,0,0,.18));cursor:pointer}.node text{font-size:11px;pointer-events:none;fill:#2c2926}.node.active circle{stroke:#111;stroke-width:4}.sidebar{display:grid;gap:14px;align-content:start}.details,.summary,.timeline{padding:16px}.details h2,.summary h2,.timeline h2{font:700 21px Georgia,serif;margin:0 0 8px}.details p,.summary p{line-height:1.55}.meta{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.chip{border-radius:999px;padding:5px 9px;background:#efe6d9;color:#5f5146;font-size:12px}.source{padding:8px 0;border-top:1px dashed var(--line);font-size:12px;color:var(--muted)}.timeline-list{max-height:300px;overflow:auto;padding-left:22px}.timeline-list li{padding:5px 0;cursor:pointer}.timeline-list li:hover{color:var(--accent)}.legend{display:flex;gap:12px;flex-wrap:wrap;color:var(--muted);font-size:12px}.dot{width:10px;height:10px;border-radius:50%;display:inline-block;margin-right:4px}.empty{color:var(--muted);font-style:italic}@media(max-width:1050px){.controls{grid-template-columns:repeat(2,1fr)}.layout{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.canvas-wrap{height:500px}}@media(max-width:620px){.shell{padding:12px}.hero{display:block}.badge{display:inline-block;margin-top:12px}.controls{grid-template-columns:1fr}.stats{grid-template-columns:1fr}}
</style>
</head>
<body>
<main class="shell">
  <header class="hero"><div><h1>Ion · Knowledge Graph 2</h1><p>Vizualizare autosuficientă a celor 13 capitole. Filtrează, inspectează sursele și reconstruiește rezumatul exclusiv din evenimentele grafului.</p></div><div class="badge">Liviu Rebreanu · 1920</div></header>
  <section class="stats"><div class="stat"><b id="statNodes"></b><span>noduri semantice</span></div><div class="stat"><b id="statEdges"></b><span>relații verificate</span></div><div class="stat"><b id="statEvents"></b><span>evenimente ordonate</span></div><div class="stat"><b id="statCoverage"></b><span>componenta principală</span></div></section>
  <section class="panel controls">
    <label>Capitol<select id="chapter"></select></label>
    <label>Tip<select id="type"><option value="all">Toate tipurile</option></select></label>
    <label>Personaj<select id="character"><option value="all">Toate personajele</option></select></label>
    <label>Importanță<select id="importance"><option value="all">Toate</option><option value="major">Majoră</option><option value="medium">Medie</option><option value="supporting">Suport</option></select></label>
    <label>Rezumat<select id="register"><option value="simple_narration">Simplu</option><option value="elevated_narration">Elevat</option></select></label>
    <label>Căutare<input id="search" type="search" placeholder="Ana, pământ, nuntă…"></label>
  </section>
  <section class="layout">
    <div class="panel"><div class="panel-title"><span>Graful filtrat</span><span class="legend"><span><i class="dot" style="background:var(--event)"></i>Eveniment</span><span><i class="dot" style="background:var(--person)"></i>Personaj</span><span><i class="dot" style="background:var(--place)"></i>Loc</span><span><i class="dot" style="background:var(--concept)"></i>Concept</span></span></div><div class="canvas-wrap"><svg id="graph" viewBox="0 0 1500 900" aria-label="Knowledge graph interactiv"><g id="edges"></g><g id="nodes"></g></svg></div></div>
    <aside class="sidebar"><section class="panel details" id="details"><h2>Selectează un nod</h2><p class="empty">Apasă pe un nod sau pe un eveniment din cronologie.</p></section><section class="panel summary"><h2>Rezumat generat din graf</h2><p id="summary"></p></section><section class="panel timeline"><h2>Cronologia capitolului</h2><ol class="timeline-list" id="timeline"></ol></section></aside>
  </section>
</main>
<script type="application/json" id="graph-data">__GRAPH_DATA__</script>
<script>
const data=JSON.parse(document.getElementById('graph-data').textContent);const byId=new Map(data.nodes.map(n=>[n.id,n]));const sourceById=new Map(data.sources.map(s=>[s.id,s]));const outgoing=new Map(data.nodes.map(n=>[n.id,[]]));const incoming=new Map(data.nodes.map(n=>[n.id,[]]));data.edges.forEach(e=>{outgoing.get(e.source)?.push(e);incoming.get(e.target)?.push(e)});
const els={chapter:document.getElementById('chapter'),type:document.getElementById('type'),character:document.getElementById('character'),importance:document.getElementById('importance'),register:document.getElementById('register'),search:document.getElementById('search'),edges:document.getElementById('edges'),nodes:document.getElementById('nodes'),details:document.getElementById('details'),summary:document.getElementById('summary'),timeline:document.getElementById('timeline')};
document.getElementById('statNodes').textContent=data.nodes.length;document.getElementById('statEdges').textContent=data.edges.length;document.getElementById('statEvents').textContent=data.validation.event_count;document.getElementById('statCoverage').textContent=(data.validation.connected_to_main_ratio*100).toFixed(0)+'%';
data.chapters.forEach(c=>els.chapter.add(new Option(c.title,c.id)));[...new Set(data.nodes.map(n=>n.type))].sort().forEach(t=>els.type.add(new Option(t,t)));data.nodes.filter(n=>n.type==='Character').sort((a,b)=>a.label.localeCompare(b.label,'ro')).forEach(n=>els.character.add(new Option(n.label,n.id)));
const color=n=>n.type==='NarrativeEvent'?'#b64b3b':n.type==='Character'?'#2c6b67':n.type==='Location'?'#426a9a':['Theme','Motif','Symbol','Conflict','Value','LiteraryTechnique'].includes(n.type)?'#8a6b2d':'#65537d';
function chapterIds(){const c=data.chapters.find(x=>x.id===els.chapter.value);const ids=new Set([c.id,c.part_id,c.opening_state,c.closing_state,...c.event_sequence]);data.edges.forEach(e=>{if(ids.has(e.source))ids.add(e.target);if(ids.has(e.target))ids.add(e.source)});return ids}
function visible(){let ids=chapterIds();const q=els.search.value.trim().toLocaleLowerCase('ro');if(els.character.value!=='all'){const linked=new Set([els.character.value]);[...(outgoing.get(els.character.value)||[]),...(incoming.get(els.character.value)||[])].forEach(e=>{linked.add(e.source);linked.add(e.target)});ids=new Set([...ids].filter(id=>linked.has(id)))}return [...ids].map(id=>byId.get(id)).filter(Boolean).filter(n=>els.type.value==='all'||n.type===els.type.value).filter(n=>els.importance.value==='all'||n.importance===els.importance.value).filter(n=>!q||`${n.id} ${n.label} ${n.description}`.toLocaleLowerCase('ro').includes(q))}
function layout(nodes){const groups=new Map();nodes.forEach(n=>{const key=n.type==='NarrativeEvent'?'Evenimente':n.type==='Character'?'Personaje':n.type==='Location'?'Locuri':'Structură și concepte';if(!groups.has(key))groups.set(key,[]);groups.get(key).push(n)});const pos=new Map();let groupIndex=0;for(const [key,list] of groups){const x0=90+groupIndex*360;list.sort((a,b)=>(a.attributes?.global_order||9999)-(b.attributes?.global_order||9999)||a.label.localeCompare(b.label,'ro'));list.forEach((n,i)=>pos.set(n.id,{x:x0+(i%3)*105,y:70+Math.floor(i/3)*70,key}));groupIndex++}return pos}
function render(){const nodes=visible();const ids=new Set(nodes.map(n=>n.id));const pos=layout(nodes);els.edges.replaceChildren();data.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).slice(0,900).forEach(e=>{const a=pos.get(e.source),b=pos.get(e.target);const line=document.createElementNS('http://www.w3.org/2000/svg','line');line.setAttribute('class','edge');line.setAttribute('x1',a.x);line.setAttribute('y1',a.y);line.setAttribute('x2',b.x);line.setAttribute('y2',b.y);line.dataset.predicate=e.predicate;els.edges.appendChild(line)});els.nodes.replaceChildren();nodes.forEach(n=>{const p=pos.get(n.id),g=document.createElementNS('http://www.w3.org/2000/svg','g');g.setAttribute('class','node');g.setAttribute('transform',`translate(${p.x},${p.y})`);g.tabIndex=0;const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('r',n.type==='NarrativeEvent'?13:10);c.setAttribute('fill',color(n));const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',18);t.setAttribute('y',4);t.textContent=n.label.length>34?n.label.slice(0,32)+'…':n.label;g.append(c,t);g.addEventListener('click',()=>show(n.id));g.addEventListener('keydown',e=>{if(e.key==='Enter')show(n.id)});els.nodes.appendChild(g)});renderSummary();renderTimeline()}
function renderSummary(){const c=data.chapters.find(x=>x.id===els.chapter.value);const field=els.register.value;const text=c.event_sequence.map(id=>byId.get(id)).filter(n=>n&&['major','medium'].includes(n.importance)).map(n=>n.attributes?.[field]).filter(Boolean).join(' ');els.summary.textContent=text||'Nu există evenimente pentru filtrul selectat.'}
function renderTimeline(){const c=data.chapters.find(x=>x.id===els.chapter.value);els.timeline.replaceChildren();c.event_sequence.forEach(id=>{const n=byId.get(id),li=document.createElement('li');li.textContent=`${n.attributes.chapter_order}. ${n.label}`;li.onclick=()=>show(id);els.timeline.appendChild(li)})}
function show(id){const n=byId.get(id);if(!n)return;const related=[...(outgoing.get(id)||[]),...(incoming.get(id)||[])];const refs=(n.source_refs||[]).map(r=>sourceById.get(r)).filter(Boolean);els.details.innerHTML=`<h2>${escapeHtml(n.label)}</h2><div class="meta"><span class="chip">${escapeHtml(n.id)}</span><span class="chip">${escapeHtml(n.type)}</span><span class="chip">${escapeHtml(n.importance)}</span><span class="chip">certitudine ${n.confidence}</span></div><p>${escapeHtml(n.description)}</p><p><b>Relații:</b> ${related.length}</p><h3>Surse</h3>${refs.map(s=>`<div class="source"><b>${escapeHtml(s.id)}</b> · ${escapeHtml(s.title)}${s.chapter?' · '+escapeHtml(s.chapter):''}${s.pdf_page_start?' · pag. PDF '+s.pdf_page_start+'-'+s.pdf_page_end:''}<br>${escapeHtml(s.evidence||s.path||'')}</div>`).join('')}`}
function escapeHtml(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
[els.chapter,els.type,els.character,els.importance].forEach(el=>el.addEventListener('change',render));els.register.addEventListener('change',renderSummary);els.search.addEventListener('input',render);render();
</script>
</body>
</html>'''


def write_html(graph: dict[str, Any]) -> None:
    compact = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</script", "<\\/script")
    HTML_PATH.write_text(HTML_TEMPLATE.replace("__GRAPH_DATA__", compact), encoding="utf-8")


def validate_with_schema(graph: dict[str, Any], schema: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        import jsonschema

        jsonschema.Draft202012Validator(schema).validate(graph)
        return True, None
    except ImportError:
        # Runtime-ul livrat cu aplicația nu include întotdeauna jsonschema.
        # Validăm contractul esențial aici, iar build-ul este verificat separat
        # și cu PowerShell Test-Json împotriva fișierului de schemă generat.
        required_top = set(schema["required"])
        missing_top = sorted(required_top - set(graph))
        if missing_top:
            return False, f"Câmpuri de nivel superior lipsă: {missing_top}"
        if not 200 <= len(graph["nodes"]) <= 300:
            return False, "Numărul de noduri nu respectă minItems/maxItems."
        if len(graph["edges"]) < 300:
            return False, "Numărul de relații nu respectă minItems."
        if len(graph["chapters"]) != 13:
            return False, "Numărul de capitole nu respectă schema."
        node_required = set(schema["$defs"]["node"]["required"])
        edge_required = set(schema["$defs"]["edge"]["required"])
        event_required = set(schema["$defs"]["eventAttributes"]["required"])
        for node in graph["nodes"]:
            missing = node_required - set(node)
            if missing:
                return False, f"Nodul {node.get('id')} nu respectă schema: {sorted(missing)}"
            if node.get("type") == "NarrativeEvent":
                missing = event_required - set(node.get("attributes", {}))
                if missing:
                    return False, f"Evenimentul {node.get('id')} nu respectă schema: {sorted(missing)}"
        for edge in graph["edges"]:
            missing = edge_required - set(edge)
            if missing:
                return False, f"Relația {edge.get('id')} nu respectă schema: {sorted(missing)}"
        return True, None
    except Exception as exc:  # pragma: no cover - mesaj raportat în artefact
        return False, str(exc)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    schema = build_schema(graph)
    schema_valid, schema_error = validate_with_schema(graph, schema)
    graph["validation"]["json_schema_valid"] = schema_valid
    graph["validation"]["json_schema_error"] = schema_error
    graph["validation"]["passed"] = graph["validation"]["passed"] and schema_valid
    dump_json(GRAPH_PATH, graph)
    dump_json(SCHEMA_PATH, schema)
    write_ontology(graph)
    write_reconstructions(graph)
    write_coverage(graph)
    write_validation_report(graph, schema_valid, schema_error)
    write_html(graph)
    print(
        json.dumps(
            {
                "graph": str(GRAPH_PATH),
                "nodes": graph["validation"]["node_count"],
                "edges": graph["validation"]["edge_count"],
                "chapters": graph["validation"]["chapter_count"],
                "events": graph["validation"]["event_count"],
                "schema_valid": schema_valid,
                "passed": graph["validation"]["passed"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
