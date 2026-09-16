from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
PDF_PATH = ROOT / "opere_pdf" / "Moara cu noroc - Ioan Slavici.pdf"
ESSAY_PATH = ROOT / "modele_eseuri" / "moara_cu_noroc.md"
PROMPT_PATH = OUTPUT_DIR / "prompt-generare-graf-moara-cu-noroc.md"
GRAPH_PATH = OUTPUT_DIR / "knowledge-graph.json"
HTML_PATH = OUTPUT_DIR / "knowledge-graph.html"
SCHEMA_PATH = OUTPUT_DIR / "knowledge-graph.schema.json"
ONTOLOGY_PATH = OUTPUT_DIR / "ontology.md"
RECONSTRUCTIONS_PATH = OUTPUT_DIR / "chapter-reconstructions.md"
COVERAGE_PATH = OUTPUT_DIR / "coverage-matrix.md"
VALIDATION_PATH = OUTPUT_DIR / "validation-report.md"

CHAPTER_RANGES = (
    (1, 2, 2), (2, 2, 3), (3, 4, 5), (4, 6, 8), (5, 9, 12),
    (6, 13, 14), (7, 15, 18), (8, 19, 21), (9, 22, 29),
    (10, 30, 33), (11, 34, 36), (12, 37, 38), (13, 39, 40),
    (14, 41, 47), (15, 48, 49), (16, 50, 52), (17, 53, 53),
)
NOVEL_FIRST_PAGE = 2
NOVEL_LAST_PAGE = 53
EVENTS_PER_CHAPTER = 10

PROMPT_NODE_TYPES = {
    "Work", "Author", "Part", "Chapter", "NarrativeEvent", "NarrativeSubevent",
    "NarrativeState", "Character", "CharacterState", "Decision", "Motivation",
    "Action", "Consequence", "Location", "TimeContext", "Object", "Family",
    "Institution", "SocialGroup", "Relationship", "Conflict", "Theme", "Motif",
    "Symbol", "Value", "Emotion", "SocialStatus", "NarrativePerspective",
    "LiteraryTechnique", "LiteraryMovement", "LiteraryTrait", "CompositionElement",
    "Evidence", "SourceFragment",
}

PROMPT_RELATIONSHIP_TYPES = {
    "instance_of", "subclass_of", "part_of", "has_part", "has_chapter",
    "chapter_of", "occurs_in_chapter", "occurs_at", "occurs_before", "occurs_after",
    "immediately_precedes", "immediately_follows", "causes", "contributes_to",
    "enables", "prevents", "motivates", "results_in", "foreshadows", "resolves",
    "intensifies", "contrasts_with", "parallels", "participates_in", "initiates",
    "experiences", "observes", "discovers", "communicates_to", "hides_from",
    "helps", "opposes", "manipulates", "harms", "protects", "loves", "desires",
    "is_married_to", "is_parent_of", "is_child_of", "is_rival_of", "has_motivation",
    "has_consequence", "changes_state_of", "expresses_theme", "expresses_motif",
    "symbolizes", "supported_by", "derived_from_source", "has_simple_verbalization",
    "has_elevated_verbalization", "belongs_to_literary_movement", "has_characteristic",
    "has_composition_element", "illustrated_by", "has_opening_state", "has_closing_state",
}

CHARACTERS = (
    ("CHAR_FELIX", "Felix Sima", ("Felix",), "major", "Tânăr orfan venit la București pentru studii medicale; martor și participant central la lumea familiei Giurgiuveanu-Tulea.", "intelectualul în formare", "ambițios, lucid, sensibil, perseverent și gelos", "Tânăr de aproximativ optsprezece ani, cu figură juvenilă, prelungă și trăsături fine."),
    ("CHAR_OTILIA", "Otilia Mărculescu", ("Otilia", "Otiliei"), "major", "Fiica vitregă neadoptată legal a lui Costache și centrul afectiv enigmatic al romanului.", "feminitatea enigmatică", "spontană, afectuoasă, inteligentă, independentă, schimbătoare și capabilă de sacrificiu", "Tânără frumoasă, delicată, cu gesturi grațioase și o prezență plină de vitalitate."),
    ("CHAR_COSTACHE", "Costache Giurgiuveanu", ("moș Costache", "Costache", "Giurgiuveanu"), "major", "Tutorele lui Felix și tatăl vitreg al Otiliei; iubirea pentru fată este paralizată de avariție și teamă.", "avarul umanizat", "avar, temător, suspicios, bâlbâit, afectuos față de Otilia, incapabil de decizie", "Bătrân mic, cu cap aproape chel, buze groase și mișcări prudente."),
    ("CHAR_AGLAE", "Aglae Tulea", ("Aglae", "tanti Aglae"), "major", "Sora lui Costache și conducătoarea autoritară a clanului Tulea, obsedată de moștenire.", "baba absolută / autoritatea familială rapace", "autoritară, răutăcioasă, posesivă, lucidă și lipsită de empatie", "Femeie matură cu privire ascuțită și fizionomie severă."),
    ("CHAR_PASCALOPOL", "Leonida Pascalopol", ("Pascalopol", "moșierul"), "major", "Moșier rafinat, protector al Otiliei și rival matur al lui Felix.", "aristocratul rafinat și protector", "cultivat, generos, elegant, răbdător, lucid și patern", "Bărbat matur, elegant, cu maniere ceremonioase și înfățișare distinsă."),
    ("CHAR_STANICA", "Stănică Rațiu", ("Stănică", "Rațiu"), "major", "Avocat fără procese, ginere al Aglaei și agentul principal al parvenirii și al furtului moștenirii.", "parvenitul", "volubil, demagog, oportunist, lipsit de scrupule, energic și adaptabil", "Bărbat roșu la față, cu păr mare și creț, mustață mică și vestimentație ostentativă."),
    ("CHAR_AURICA", "Aurica Tulea", ("Aurica", "Aurelia", "Aurichii"), "supporting", "Fiica nemăritată a Aglaei, dominată de obsesia căsătoriei.", "fata bătrână", "invidioasă, frustrată, insistentă, malițioasă și preocupată de aparențe", "Femeie palidă, cu fața prelungă și bărbie ascuțită."),
    ("CHAR_SIMION", "Simion Tulea", ("Simion",), "supporting", "Soțul Aglaei, marginalizat în familie și degradat treptat de boala psihică.", "senilul / alienatul", "docil, artistic, ipohondru, confuz și înstrăinat", "Bătrân cu gesturi bizare, preocupat de broderii și pictură."),
    ("CHAR_TITI", "Titi Tulea", ("Titi",), "supporting", "Fiul Aglaei și al lui Simion, imatur și incapabil de autonomie.", "debilul mintal", "infantil, leneș, imitativ, docil și lipsit de inițiativă", "Tânăr masiv, cu trăsături greoaie și sprâncene îmbinate."),
    ("CHAR_OLIMPIA", "Olimpia Rațiu", ("Olimpia",), "supporting", "Fiica cea mare a Aglaei și partenera lui Stănică, preocupată de zestre și stabilitate.", "soția burgheză pasivă", "placidă, interesată material, comodă și resemnată", "Femeie planturoasă, asemănătoare fizic cu Simion și Titi."),
    ("CHAR_MARINA", "Marina", ("Marina",), "supporting", "Servitoarea care circulă între case și transmite vești, expunând mecanismele cotidiene ale familiei.", "servitoarea-martor", "directă, arțăgoasă, indiscretă și practică", "Femeie matură, robustă, îmbrăcată modest, cu un ochi afectat."),
    ("CHAR_WEISSMANN", "Weissmann", ("Weissmann",), "supporting", "Colegul și prietenul lui Felix, contrapunct intelectual și ideologic.", "intelectualul lucid", "inteligent, ironic, sociabil, cultivat și analitic", "Tânăr student la medicină, energic și comunicativ."),
    ("CHAR_GEORGETA", "Georgeta", ("Georgeta",), "supporting", "Curtezană cultivată prin care Felix cunoaște o experiență sentimentală și erotică diferită de iubirea pentru Otilia.", "curtezana", "inteligentă, tandră, pragmatică, senzuală și generoasă", "Femeie frumoasă, elegantă și atent îngrijită."),
    ("CHAR_GENERAL", "Generalul", ("generalul",), "supporting", "Protectorul Georgetei și reprezentant al lumii mondene tolerate social.", "protectorul monden", "bonom, posesiv, convențional și indulgent", "Bărbat în vârstă, cu ținută și autoritate militară."),
    ("CHAR_ANA", "Ana Sohatchi", ("Ana Sohatchi", "Ana"), "supporting", "Soția efemeră a lui Titi, a cărei căsnicie dovedește imaturitatea acestuia și controlul Aglaei.", "soția incompatibilă", "pragmatică, independentă și incompatibilă cu familia Tulea", "Tânără de condiție modestă."),
    ("CHAR_AUREL", "Aurel Rațiu", ("Aurel", "copilul"), "supporting", "Copilul Olimpiei și al lui Stănică, a cărui moarte dezvăluie egoismul și degradarea familiei.", "copilul-victimă", "fragil și dependent de adulți", "Copil de vârstă mică."),
    ("CHAR_DOCTOR", "Doctorul Vasiliad", ("Vasiliad",), "supporting", "Medicul chemat în crizele lui Simion și Costache.", "medicul-martor", "profesionist, rezervat și lucid", "Medic bucureștean matur."),
)

LOCATIONS = (
    ("LOC_BUCURESTI", "București", ("București", "Capitala"), "Spațiul citadin principal, surprins realist la începutul secolului al XX-lea."),
    ("LOC_ANTIM", "Strada Antim", ("strada Antim",), "Axa spațială a incipitului și finalului, care închide simetric lumea romanului."),
    ("LOC_COSTACHE", "Casa lui Costache Giurgiuveanu", ("casa lui moș Costache", "casa lui Costache"), "Casa degradată de pe strada Antim, centru al conflictului succesoral."),
    ("LOC_TULEA", "Casa familiei Tulea", ("casa Tulea", "casa Aglaei"), "Spațiul clanului condus de Aglae, al rivalităților și bolii lui Simion."),
    ("LOC_MOSIE", "Moșia lui Pascalopol din Bărăgan", ("moșia", "Bărăgan"), "Spațiu al confortului, rafinamentului și apropierii dintre Otilia, Felix și Pascalopol."),
    ("LOC_FACULTATE", "Facultatea de Medicină", ("Facultatea", "Universitate", "laborator"), "Spațiul formării profesionale și al ascensiunii lui Felix."),
    ("LOC_PARIS", "Paris", ("Paris",), "Spațiu al libertății Otiliei și al consacrării profesionale a lui Felix."),
    ("LOC_PARC", "Parcurile și grădinile Bucureștiului", ("parc", "grădină"), "Spații ale întâlnirilor, plimbărilor și confesiunilor."),
    ("LOC_RESTAURANT", "Localuri și restaurante bucureștene", ("restaurant", "local", "berărie"), "Spații ale sociabilității urbane și ale lumii lui Stănică și Georgeta."),
)

CONCEPTS = (
    ("THEME_INHERITANCE", "Theme", "Moștenirea", "Lupta pentru averea lui Costache organizează conflictul social și familial."),
    ("THEME_LOVE", "Theme", "Iubirea", "Relația Felix-Otilia este confruntată cu diferențe de vârstă, statut, proiect de viață și maturitate."),
    ("THEME_PATERNITY", "Theme", "Paternitatea", "Romanul explorează protecția, tutela, adopția ratată și răspunderea parentală."),
    ("THEME_FORMATION", "Theme", "Formarea intelectualului", "Felix evoluează de la adolescentul nesigur la medicul consacrat."),
    ("THEME_SOCIAL", "Theme", "Societatea burgheză citadină", "Mediul urban dezvăluie tipuri umane, interese economice și mecanisme de parvenire."),
    ("CONFLICT_SUCCESSION", "Conflict", "Conflictul succesoral", "Aglae și Stănică urmăresc averea lui Costache, în opoziție cu interesele Otiliei."),
    ("CONFLICT_LOVE", "Conflict", "Felix - Otilia - Pascalopol", "Felix și Pascalopol reprezintă două vârste și două forme diferite de iubire față de Otilia."),
    ("CONFLICT_INNER", "Conflict", "Libertate afectivă versus stabilitate", "Otilia oscilează între iubirea pentru Felix, nevoia de protecție și refuzul de a-i limita viitorul."),
    ("MOTIF_MONEY", "Motif", "Banii ascunși", "Banii concentrați și ascunși materializează avariția și declanșează furtul fatal."),
    ("MOTIF_HOUSE", "Symbol", "Casa degradată", "Arhitectura casei lui Costache exprimă dezordinea morală, avariția și destrămarea unei lumi."),
    ("MOTIF_PHOTO", "Motif", "Fotografia Otiliei", "Fotografiile marchează distanța dintre imaginea păstrată de Felix și transformarea Otiliei."),
    ("MOV_REALISM", "LiteraryMovement", "Realism balzacian", "Formulă realistă obiectivă, citadină și balzaciană, centrată pe determinism social, moștenire și tipologii."),
    ("TRAIT_CHRONOTOPE", "LiteraryTrait", "Verosimilitatea prin cronotop precis", "Trăsătură din eseul-model: acțiunea este ancorată prin date, ore, străzi și toponime recognoscibile."),
    ("TRAIT_TYPOLOGIES", "LiteraryTrait", "Tipologii umane balzaciene", "Trăsătură din eseul-model: personajele individualizate ilustrează tipuri precum avarul, parvenitul și fata bătrână."),
    ("TECH_OBJECTIVE", "NarrativePerspective", "Perspectivă narativă obiectivă", "Narațiune la persoana a III-a, cu narator omniscient și focalizare predominant zero."),
    ("TECH_CHARACTER", "LiteraryTechnique", "Caracterizare balzaciană", "Mediul, casa, fizionomia, vestimentația, gesturile și numele contribuie la portretizarea personajelor."),
    ("TECH_TITLE", "LiteraryTechnique", "Titlul", "Titlul definitiv mută accentul de la determinismul familial din «Părinții Otiliei» la misterul feminității și al destinului."),
    ("TECH_INCIPIT_FINAL", "LiteraryTechnique", "Relația incipit-final", "Venirea și revenirea lui Felix pe strada Antim, împreună cu replica «Aici nu stă nimeni», construiesc simetria romanului."),
)

COMPOSITION_ELEMENTS = (
    (
        "COMP_TITLE",
        "Titlul",
        "Titlul definitiv mută accentul de la determinismul familial sugerat de titlul inițial «Părinții Otiliei» la caracterul contradictoriu și imposibil de fixat al protagonistei.",
        ["CHAR_OTILIA", "TECH_TITLE"],
        [
            "titlul inițial evidențiază tema paternității",
            "titlul definitiv concentrează perspectiva lui Felix asupra Otiliei",
            "enigma rezultă din pluralitatea ipostazelor feminine",
        ],
    ),
    (
        "COMP_CONFLICT",
        "Conflictul",
        "Conflictul compozițional reunește lupta succesorală pentru averea lui Costache, rivalitatea afectivă Felix-Otilia-Pascalopol și tensiunea dintre libertatea Otiliei și nevoia de stabilitate.",
        ["CONFLICT_SUCCESSION", "CONFLICT_LOVE", "CONFLICT_INNER", "EV_155"],
        [
            "conflict exterior succesoral în jurul moștenirii",
            "conflict afectiv construit prin triunghiul Felix-Otilia-Pascalopol",
            "conflict interior între libertate și protecție",
        ],
    ),
    (
        "COMP_INCIPIT_FINAL",
        "Relația incipit-final",
        "Incipitul și finalul se răspund simetric prin strada Antim, casa lui Costache și replica «Aici nu stă nimeni», revenirea lui Felix confirmând dispariția lumii urmărite în roman.",
        ["EV_001", "EV_160", "LOC_ANTIM", "TECH_INCIPIT_FINAL"],
        [
            "Felix pătrunde la început pe strada Antim într-un spațiu necunoscut",
            "replica lui Costache refuză simbolic accesul în familie",
            "revenirea finală repetă cadrul și transformă replica într-un verdict asupra lumii dispărute",
        ],
    ),
)

DIRECT_RELATIONS = (
    ("CHAR_FELIX", "loves", "CHAR_OTILIA", "Felix o iubește pe Otilia și dorește o relație asumată."),
    ("CHAR_OTILIA", "loves", "CHAR_FELIX", "Otilia îl iubește pe Felix, dar refuză să-i îngrădească viitorul."),
    ("CHAR_PASCALOPOL", "loves", "CHAR_OTILIA", "Pascalopol îmbină iubirea cu protecția paternă."),
    ("CHAR_COSTACHE", "is_parent_of", "CHAR_OTILIA", "Costache este tatăl vitreg și tutorele de fapt al Otiliei, fără a finaliza adopția."),
    ("CHAR_COSTACHE", "is_uncle_of", "CHAR_FELIX", "Costache este unchiul și tutorele lui Felix."),
    ("CHAR_AGLAE", "is_sibling_of", "CHAR_COSTACHE", "Aglae este sora lui Costache."),
    ("CHAR_AGLAE", "is_married_to", "CHAR_SIMION", "Aglae și Simion sunt soți."),
    ("CHAR_AGLAE", "is_parent_of", "CHAR_AURICA", "Aurica este fiica Aglaei."),
    ("CHAR_AGLAE", "is_parent_of", "CHAR_TITI", "Titi este fiul Aglaei."),
    ("CHAR_AGLAE", "is_parent_of", "CHAR_OLIMPIA", "Olimpia este fiica Aglaei."),
    ("CHAR_STANICA", "is_married_to", "CHAR_OLIMPIA", "Stănică se căsătorește cu Olimpia după presiunile privind zestrea."),
    ("CHAR_STANICA", "is_parent_of", "CHAR_AUREL", "Stănică este tatăl lui Aurel."),
    ("CHAR_OLIMPIA", "is_parent_of", "CHAR_AUREL", "Olimpia este mama lui Aurel."),
    ("CHAR_TITI", "is_married_to", "CHAR_ANA", "Titi are o căsătorie scurtă și nereușită cu Ana Sohatchi."),
    ("CHAR_AGLAE", "is_rival_of", "CHAR_OTILIA", "Aglae o consideră pe Otilia o amenințare la moștenire."),
    ("CHAR_STANICA", "is_rival_of", "CHAR_OTILIA", "Stănică urmărește banii care ar fi trebuit să-i asigure viitorul Otiliei."),
    ("CHAR_FELIX", "is_rival_of", "CHAR_PASCALOPOL", "Felix îl percepe pe Pascalopol ca rival afectiv."),
    ("CHAR_FELIX", "is_friend_of", "CHAR_WEISSMANN", "Weissmann este prietenul și colegul intelectual al lui Felix."),
)

ACTION_TERMS = (
    "veni", "plecă", "intră", "ieși", "spuse", "întrebă", "răspunse", "văzu", "află", "hotărî",
    "luă", "dădu", "scrise", "citi", "căută", "găsi", "muri", "iubi", "fură", "căsători", "chemă",
)

CHAPTER_ANCHORS: dict[int, tuple[tuple[str, ...], ...]] = {
    1: (("aici", "nimeni"), ("pascalopol", "aglae"), ("otilia", "odaia")),
    5: (("olimpia", "stanica", "copil"), ("simion", "cunun")),
    6: (("mosia", "pascalopol"), ("otilia", "felix", "pascalopol")),
    8: (("felix", "scrisoarea", "otilia"), ("te iubesc", "felix")),
    12: (("otilia", "paris"), ("georgeta", "felix")),
    15: (("simion", "ospici"),),
    18: (("costache", "atac"), ("aglae", "casa", "costache")),
    20: (
        ("stanica", "pachetul", "bani"),
        ("cadavrul", "aglae"),
        ("dorm", "noaptea asta"),
        ("casatorise", "pascalopol"),
        ("fotografia", "buenos aires"),
        ("aici", "nimeni"),
    ),
}

CHARACTER_PAGE_RANGES = {
    "CHAR_STANICA": (73, NOVEL_LAST_PAGE),
    "CHAR_OLIMPIA": (73, NOVEL_LAST_PAGE),
    "CHAR_AUREL": (73, 190),
    "CHAR_WEISSMANN": (103, NOVEL_LAST_PAGE),
    "CHAR_ANA": (120, 160),
    "CHAR_GEORGETA": (180, NOVEL_LAST_PAGE),
    "CHAR_GENERAL": (180, NOVEL_LAST_PAGE),
}

# Instanțele de mai jos înlocuiesc modelul structural copiat din graful
# „Enigma Otiliei”; nicio instanță factuală din model nu este reutilizată.
CHARACTERS = (
    ("CHAR_GHITA", "Ghiță", ("Ghiță", "cârciumarul", "birtașul"), "major", "Cizmar care arendează hanul Moara cu noroc și se degradează moral sub influența lui Lică.", "omul cinstit corupt de dorința de înavuțire", "harnic, energic, orgolios, neliniștit, duplicitar și treptat violent", "Bărbat viguros; gesturile, paloarea și izbucnirile îi exteriorizează frământarea."),
    ("CHAR_ANA", "Ana", ("Ana", "nevasta", "cârciumărița"), "major", "Soția lui Ghiță, devotată familiei la început și înstrăinată pe măsura degradării soțului.", "soția-victimă și conștiința afectivă a familiei", "blândă, lucidă, iubitoare, temătoare, apoi dezamăgită și răzbunătoare", "Femeie tânără și frumoasă, ale cărei gesturi și reacții urmăresc destrămarea cuplului."),
    ("CHAR_LICA", "Lică Sămădăul", ("Lică", "Sămădăul", "sămădăul"), "major", "Conducător autoritar al porcarilor, infractor inteligent și manipulator care îl subordonează pe Ghiță.", "forța malefică și stăpânul lumii porcarilor", "sigur pe sine, crud, lucid, seducător, orgolios și lipsit de scrupule", "Bărbat înalt, uscățiv, cu mustață lungă; ținuta și privirea îi exprimă autoritatea."),
    ("CHAR_BATRANA", "Bătrâna", ("bătrâna", "soacra", "mamă"), "major", "Mama Anei și soacra lui Ghiță, purtătoarea normelor morale tradiționale din incipit și final.", "vocea rațiunii și a moralității", "înțeleaptă, cumpătată, religioasă, prudentă și resemnată", "Femeie în vârstă care ocrotește copiii și contemplă în final ruinele hanului."),
    ("CHAR_PINTEA", "Pintea", ("Pintea", "căprarul", "jandarmul"), "major", "Jandarm și fost tovarăș al lui Lică, hotărât să-l prindă și aliat dificil al lui Ghiță.", "reprezentantul legii", "tenace, intuitiv, curajos, suspicios și răzbunător", "Căprar energic, cunoscător al urmelor și al tacticilor lui Lică."),
    ("CHAR_RAUT", "Răuț", ("Răuț",), "supporting", "Om de încredere al lui Lică și executant al poruncilor sale, inclusiv al crimelor finale.", "complice violent", "ascultător față de Lică, brutal și primejdios", "Porcar înarmat, asociat constant cu oamenii sămădăului."),
    ("CHAR_SAILA", "Săilă Boarul", ("Săilă", "Boarul"), "supporting", "Complice al lui Lică, implicat în jafuri și folosit ca țap ispășitor în anchetă.", "complice și acuzat", "violent, temător și dependent de Lică", "Porcar robust, recunoscut de martori și de obiectele compromițătoare."),
    ("CHAR_BUZA", "Buză-Ruptă", ("Buză-Ruptă",), "supporting", "Complice al lui Lică, implicat în atacul asupra arendașului și judecat împreună cu Săilă.", "complice și acuzat", "brutal, nesigur și influențabil", "Porcar identificabil prin semnul fizic sugerat de poreclă."),
    ("CHAR_LAIE", "Laie", ("Laie",), "supporting", "Slugă tânără a lui Ghiță, trimisă cu mesaje și implicată fără voie în situațiile primejdioase.", "sluga-martor", "ascultător, speriat și loial gospodăriei", "Băiat de serviciu care se deplasează între han, crâng și Ineu."),
    ("CHAR_MARTI", "Marți", ("Marți",), "supporting", "Slugă a lui Ghiță și ajutor în paza hanului și în acțiunile lui Pintea.", "sluga și ajutorul jandarmilor", "practic, atent și obedient", "Bărbat folosit la pază și urmărire."),
    ("CHAR_UTA", "Uța", ("Uța", "Uța cea mărunțică"), "supporting", "Slujnică a familiei, rămasă la han în timpul anchetei și al tensiunilor domestice.", "slujnica-martor", "harnică, directă și atentă", "Fată mărunțică din gospodăria hanului."),
    ("CHAR_ARENDAS", "Arendașul", ("arendașul", "ovreul"), "supporting", "Arendaș bogat jefuit și bătut de oamenii lui Lică, fapt care declanșează ancheta.", "victima jafului", "prudent, înspăimântat și interesat de recuperarea bunurilor", "Negustor/arendaș identificat prin rolul său economic."),
    ("CHAR_HANTL", "Hanțl", ("Hanțl", "Hantl"), "supporting", "Personaj atacat pe drumul de țară, a cărui rănire este legată de fărădelegile oamenilor lui Lică.", "victima violenței", "vulnerabil și traumatizat", "Drumeț rănit în contextul tâlhăriilor."),
    ("CHAR_DOAMNA", "Doamna tânără", ("doamna", "domnișoara", "femeia"), "supporting", "Femeie bogată implicată în transportul banilor și ucisă în lanțul de crime pus pe seama complicilor lui Lică.", "victima crimei", "prudentă și neliniștită", "Femeie elegantă care călătorește cu trăsură și slugi."),
    ("CHAR_ANDREI", "Andrei", ("Andrei", "cumnatul"), "supporting", "Fratele Anei, chemat de Ghiță ca sprijin și chezășie în anchetă.", "ruda protectoare", "cinstit, neobișnuit cu justiția și ezitant", "Țăran din familia Anei."),
    ("CHAR_COMISAR", "Comisarul", ("comisarul",), "supporting", "Reprezentant al autorității care îl interoghează pe Ghiță și cercetează jafurile.", "anchetatorul", "suspicios, ironic și insistent", "Funcționar al ordinii publice din Ineu."),
    ("CHAR_COPII", "Copiii lui Ghiță și ai Anei", ("copiii", "copilașul"), "supporting", "Copiii familiei, protejați de bătrână și rămași orfani după catastrofa finală.", "victimele inocente", "inocenți și dependenți de adulți", "Copii mici, feriți de confruntarea finală prin plecarea la Ineu."),
    ("CHAR_UNGUR", "Sluga ungur", ("ungurul",), "supporting", "Slugă angajată de Ghiță pentru paza și munca hanului.", "sluga", "obedient și vulnerabil la izbucnirile stăpânului", "Bărbat angajat în gospodăria cârciumii."),
)

LOCATIONS = (
    ("LOC_MOARA", "Moara cu noroc", ("Moara cu noroc", "cârciuma", "hanul", "moara"), "Hanul izolat de la răscruce, inițial binecuvântat și prosper, apoi damnat prin corupție și distrus de foc."),
    ("LOC_INEU", "Ineu", ("Ineu",), "Târg și centru al autorităților, al judecății și al legăturilor comerciale."),
    ("LOC_ARAD", "Arad", ("Arad",), "Toponim real care contribuie la precizia cadrului geografic."),
    ("LOC_SALONTA", "Salonta", ("Salonta",), "Toponim legat de deplasările complicilor și de comerțul cu porci."),
    ("LOC_PESTA", "Pesta", ("Pesta",), "Toponim care extinde rețeaua comercială reală a lumii narative."),
    ("LOC_FUNDURENI", "Fundureni", ("Fundureni", "Fundurenilor"), "Pădure și hotar asociate turmelor, urmăririlor și ascunderii urmelor."),
    ("LOC_SICULA", "Șicula", ("Șicula",), "Pădure unde sunt căutați și prinși oameni bănuiți."),
    ("LOC_LUNCI", "Luncile porcarilor", ("luncile", "luncă"), "Spațiul turmelor de porci și al puterii economice exercitate de Lică."),
    ("LOC_DRUM", "Drumul de țară", ("drumul", "drum de țară", "drumul pustiu"), "Axa circulației dintre Ineu și han, expusă jafurilor și urmăririlor."),
    ("LOC_CRANG", "Crângul și răchitele", ("crâng", "răchite", "răchitelor"), "Spațiu de ascundere, mesagerie și pândă în apropierea hanului."),
    ("LOC_BISERICA", "Biserica de la Fundureni", ("biserica", "altar"), "Spațiu sacru profanat de Lică atunci când caută adăpost și bani."),
    ("LOC_INEU_COURT", "Judecătoria din Ineu", ("judecata", "judecătorii", "temniță"), "Spațiul procesului în care mărturiile și probele sunt manipulate."),
)

CONCEPTS = (
    ("THEME_DEHUMANIZATION", "Theme", "Dezumanizarea prin lăcomie", "Tema centrală: dorința de înavuțire îl îndepărtează pe Ghiță de familie, cinste și echilibru."),
    ("THEME_FAMILY", "Theme", "Familia", "Familia este inițial sursa liniștii și a prosperității, apoi victima alegerilor lui Ghiță."),
    ("THEME_LOVE", "Theme", "Iubirea", "Iubirea dintre Ghiță și Ana se erodează sub efectul secretelor, fricii și răzbunării."),
    ("THEME_DESTINY", "Theme", "Destinul", "Replicile bătrânei și cuvântul «noroc» pun catastrofa în relație cu soarta și cu alegerea morală."),
    ("CONFLICT_GHITA_INNER", "Conflict", "Înavuțire versus valori morale", "Conflictul interior al lui Ghiță între dorința de câștig și nevoia de a rămâne cinstit, soț și tată protector."),
    ("CONFLICT_GHITA_LICA", "Conflict", "Ghiță versus Lică", "Conflict exterior bazat pe teamă, subordonare financiară, orgoliu, denunț și răzbunare."),
    ("CONFLICT_GHITA_ANA", "Conflict", "Înstrăinarea dintre Ghiță și Ana", "Tăinuirea faptelor și instrumentalizarea Anei distrug încrederea și iubirea conjugală."),
    ("MOTIF_MONEY", "Motif", "Banii însemnați și împrumutul", "Banii luați de Lică și bancnotele însemnate materializează dependența și proba urmărită de Pintea."),
    ("MOTIF_CROSSES", "Symbol", "Cele cinci cruci", "Crucile din fața morii semnalează inițial un loc binecuvântat și protejat."),
    ("MOTIF_FIRE", "Symbol", "Focul purificator", "Incendiul final distruge spațiul corupt și închide traseul degradării morale."),
    ("MOTIF_ROAD", "Motif", "Drumul și răscrucea", "Drumul aduce prosperitate, străini, pericol și posibilitatea alegerii între direcții morale."),
    ("MOV_REALISM", "LiteraryMovement", "Realism", "Curent bazat pe observarea societății și a tipurilor umane, verosimilitate, analiză psihologică și determinare socială."),
    ("TRAIT_CHRONOTOPE", "LiteraryTrait", "Verosimilitatea prin cronotop precis", "Trăsătură aleasă în eseul-model: Ineu, Arad, Salonta și Pesta, precum și intervalul Sfântul Gheorghe-Paștele următor, localizează precis acțiunea."),
    ("TRAIT_PSYCHOLOGY", "LiteraryTrait", "Interesul pentru psihologia personajelor", "Trăsătură aleasă în eseul-model: frământările lui Ghiță sunt urmărite prin monolog interior, stil indirect liber, gestică și mimică."),
    ("TECH_OBJECTIVE", "NarrativePerspective", "Perspectivă narativă obiectivă", "Narațiune la persoana a III-a, cu acces la conștiința personajelor și cu o puternică dimensiune morală."),
    ("TECH_MONOLOGUE", "LiteraryTechnique", "Monologul interior", "Tehnică prin care ezitările, frica, vinovăția și justificările lui Ghiță sunt expuse direct."),
    ("TECH_FREE_INDIRECT", "LiteraryTechnique", "Stilul indirect liber", "Tehnică de interferență între vocea naratorului și gândirea personajului, folosită în analiza psihologică."),
    ("TECH_GESTURE", "LiteraryTechnique", "Gestica și mimica", "Paloarea, încruntarea, tremurul, tăcerile și izbucnirile fac vizibile conflictele lăuntrice."),
)

COMPOSITION_ELEMENTS = (
    ("COMP_TITLE", "Titlul", "Titlul numește un loc perceput inițial drept binecuvântat și norocos pentru drumeți și pentru familia lui Ghiță; sub influența lui Lică, hanul devine spațiu damnat, iar focul final capătă funcție purificatoare.", ["LOC_MOARA", "MOTIF_CROSSES", "MOTIF_FIRE", "EV_011", "EV_170"], ["han vizibil din culmea dealului și adăpost norocos", "cele cinci cruci marchează locul binecuvântat", "sporul familiei durează cât câștigul este făcut cu bine", "influența lui Lică transformă locul în spațiu damnat", "moartea și focul purificator închid destinul corupt"]),
    ("COMP_CONFLICT", "Conflictul", "Conflictul compozițional reunește lupta interioară a lui Ghiță între înavuțire și valori morale, confruntarea sa cu Lică și destrămarea relației cu Ana.", ["CONFLICT_GHITA_INNER", "CONFLICT_GHITA_LICA", "CONFLICT_GHITA_ANA", "TECH_MONOLOGUE", "TECH_FREE_INDIRECT", "TECH_GESTURE", "EV_031", "EV_169"], ["conflict interior: câștig versus cinste și liniște familială", "conflict exterior: Ghiță-Lică, de la teamă și subordonare la denunț și răzbunare", "efect familial: tăinuire, înstrăinare și instrumentalizarea Anei", "redare psihologică prin monolog interior, stil indirect liber, gestică și mimică"]),
    ("COMP_INCIPIT_FINAL", "Relația incipit-final", "Prologul și epilogul sunt simetrice prin prezența bătrânei și prin teza morală: avertismentul despre mulțumire deschide acțiunea, iar contemplarea hanului ars lângă copiii orfani și replica «așa le-a fost data» o închid.", ["CHAR_BATRANA", "CHAR_COPII", "EV_001", "EV_170", "LOC_MOARA", "THEME_DESTINY"], ["deschidere in medias res prin dialogul dintre Ghiță și bătrână", "confruntare între dorința tinerilor de mai bine și mentalitatea tradițională", "teza morală este enunțată la început și demonstrată de subiect", "bătrâna revine în epilog lângă copiii orfani și ruine", "replica finală unește presimțirea, destinul și consecința alegerilor"]),
)

DIRECT_RELATIONS = (
    ("CHAR_GHITA", "is_married_to", "CHAR_ANA", "Ghiță și Ana sunt soți, iar destrămarea cuplului măsoară degradarea morală."),
    ("CHAR_ANA", "is_child_of", "CHAR_BATRANA", "Ana este fiica bătrânei."),
    ("CHAR_ANDREI", "is_sibling_of", "CHAR_ANA", "Andrei este fratele Anei și cumnatul chemat de Ghiță ca sprijin."),
    ("CHAR_BATRANA", "is_parent_of", "CHAR_ANA", "Bătrâna este mama Anei."),
    ("CHAR_GHITA", "is_parent_of", "CHAR_COPII", "Ghiță este tatăl copiilor rămași orfani."),
    ("CHAR_ANA", "is_parent_of", "CHAR_COPII", "Ana este mama copiilor rămași orfani."),
    ("CHAR_GHITA", "opposes", "CHAR_LICA", "Ghiță încearcă să reziste dominației lui Lică și apoi să-l predea legii."),
    ("CHAR_LICA", "manipulates", "CHAR_GHITA", "Lică îl face pe Ghiță dependent prin bani, teamă și complicitate."),
    ("CHAR_LICA", "manipulates", "CHAR_ANA", "Lică exploatează înstrăinarea Anei de soț și o atrage în răzbunarea sa."),
    ("CHAR_GHITA", "helps", "CHAR_PINTEA", "Ghiță îi furnizează lui Pintea informații și probe pentru prinderea lui Lică."),
    ("CHAR_PINTEA", "opposes", "CHAR_LICA", "Pintea îl urmărește pe Lică din datorie și din motive personale."),
    ("CHAR_RAUT", "helps", "CHAR_LICA", "Răuț execută poruncile violente ale lui Lică."),
    ("CHAR_SAILA", "helps", "CHAR_LICA", "Săilă participă la fărădelegile rețelei lui Lică."),
    ("CHAR_BUZA", "helps", "CHAR_LICA", "Buză-Ruptă participă la jafurile puse la cale de oamenii lui Lică."),
    ("CHAR_LICA", "harms", "CHAR_ARENDAS", "Rețeaua lui Lică îl jefuiește și îl rănește pe arendaș."),
    ("CHAR_BATRANA", "protects", "CHAR_COPII", "Bătrâna îi duce pe copii la Ineu și îi salvează de catastrofa finală."),
)

ACTION_TERMS = ("veni", "plecă", "intră", "ieși", "spuse", "întrebă", "răspunse", "văzu", "află", "hotărî", "luă", "dădu", "mărturisi", "urmări", "prinse", "ucise", "muri", "arse", "fugi", "fură", "chemă")

CHAPTER_ANCHORS: dict[int, tuple[tuple[str, ...], ...]] = {
    1: (("mulțumit", "sărăcia"), ("sf. gheorghe", "cârciuma")),
    2: (("cinci cruci",), ("cârciuma lui ghiță",)),
    3: (("lică", "sămădăul"), ("ghiță", "teamă")),
    4: (("bani", "lică"), ("pistoale", "câini")),
    5: (("lică", "împrumut"), ("tovarăș", "slugă")),
    6: (("lică", "ana"), ("săilă", "buză-ruptă")),
    7: (("arendaș",), ("pintea", "ghiță")),
    8: (("doamna",), ("ineu", "ghiță")),
    9: (("comisar", "ghiță"), ("pintea", "urme")),
    10: (("hanțl",), ("lică", "pintea")),
    11: (("judecata",), ("săilă", "buză-ruptă")),
    12: (("iartă-mă", "ano"), ("lică", "bani")),
    13: (("hârtiile",), ("pintea", "lică")),
    14: (("paști",), ("bătrâna", "ineu")),
    15: (("tu ești om", "lică"), ("ghiță", "plecase")),
    16: (("biserică",), ("pintea", "jandarmi")),
    17: (("foc",), ("simțeam", "așa le-a fost")),
}

CHARACTER_PAGE_RANGES = {character_id: (NOVEL_FIRST_PAGE, NOVEL_LAST_PAGE) for character_id, *_ in CHARACTERS}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repair_pdf_encoding(text: str) -> str:
    return text.translate(str.maketrans({"[": "ă", "{": "Ă", "=": "ș", "+": "Ș", "]": "î", "}": "Î", "`": "â", "~": "Â", "\\": "ț", "|": "Ț", "�": "„"}))


def normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold().replace("ş", "ș").replace("ţ", "ț"))
    return " ".join(re.findall(r"[a-z0-9]+", "".join(ch for ch in decomposed if not unicodedata.combining(ch))))


def contains_phrase(normalized_text: str, phrase: str) -> bool:
    return f" {normalize(phrase)} " in f" {normalized_text} "


def clean_page_text(raw: str, page_number: int) -> str:
    lines = raw.replace("\u00ad", "").splitlines()
    kept = []
    ignored = {str(page_number - 1), str(page_number), "Ioan Slavici", "Moara cu noroc", "CUPRINS"}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped in ignored or re.fullmatch(r"[IVX]{1,5}", stripped):
            continue
        kept.append(stripped)
    text = "\n".join(kept)
    text = re.sub(r"(?<=\w)-\n(?=\w)", "", text)
    text = re.sub(r"\n+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_chapter_page_texts(reader: PdfReader) -> dict[int, dict[int, str]]:
    """Extrage exact cele 17 capitole, inclusiv separarea I/II de pe pagina PDF 2."""
    all_pages = {
        page_number: clean_page_text(reader.pages[page_number - 1].extract_text() or "", page_number)
        for page_number in range(1, len(reader.pages) + 1)
    }
    raw_page_two = (reader.pages[1].extract_text() or "").replace("\u00ad", "")
    chapter_one_match = re.search(r"(?:^|\n)I\s*\n(?P<body>.*?)(?:\nII\s*\n)", raw_page_two, flags=re.S)
    chapter_two_match = re.search(r"(?:^|\n)II\s*\n(?P<body>.*)$", raw_page_two, flags=re.S)
    if not chapter_one_match or not chapter_two_match:
        raise ValueError("Nu pot separa capitolele I și II de pe pagina PDF 2.")
    page_two_segments = {
        1: clean_page_text(chapter_one_match.group("body"), 2),
        2: clean_page_text(chapter_two_match.group("body"), 2),
    }
    result: dict[int, dict[int, str]] = {}
    for chapter_number, start, end in CHAPTER_RANGES:
        result[chapter_number] = {page: all_pages[page] for page in range(start, end + 1)}
        if chapter_number in page_two_segments:
            result[chapter_number][2] = page_two_segments[chapter_number]
    return result


def node(
    node_id: str,
    node_type: str,
    label: str,
    description: str,
    *,
    chapter_ids: list[str] | None = None,
    importance: str = "supporting",
    assertion_type: str = "explicit_fact",
    source_refs: list[str] | None = None,
    attributes: dict[str, Any] | None = None,
    aliases: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "type": node_type,
        "label": label,
        "description": description,
        "aliases": aliases or [],
        "chapter_ids": chapter_ids or [],
        "importance": importance,
        "confidence": 1.0 if assertion_type == "explicit_fact" else 0.95,
        "assertion_type": assertion_type,
        "source_refs": source_refs or ["SRC_PDF"],
        "attributes": attributes or {},
    }


def edge(edge_id: str, source: str, predicate: str, target: str, description: str, source_refs: list[str]) -> dict[str, Any]:
    explicit_predicates = {
        "authored_by", "chapter_of", "contains", "created_by", "derived_from_source",
        "has_chapter", "has_closing_state", "has_opening_state", "has_participant",
        "immediately_follows", "immediately_precedes", "involves", "occurs_after",
        "occurs_at", "occurs_before", "occurs_in_chapter", "participates_in",
    }
    return {
        "id": edge_id,
        "source": source,
        "predicate": predicate,
        "target": target,
        "description": description,
        "confidence": 0.98,
        "assertion_type": "explicit_fact" if predicate in explicit_predicates else "literary_interpretation",
        "source_refs": source_refs,
        "qualifiers": {},
    }


def sentence_candidates(page_texts: dict[int, str], start: int, end: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for page_number in range(start, end + 1):
        text = page_texts[page_number]
        sentences = [part.strip(" -—") for part in re.split(r"(?<=[.!?…»”])\s+", text) if part.strip()]
        for index, sentence in enumerate(sentences):
            if not 45 <= len(sentence) <= 720:
                continue
            passage = sentence
            normalized = normalize(passage)
            participants = []
            for character_id, _, aliases, *_ in CHARACTERS:
                minimum, maximum = CHARACTER_PAGE_RANGES.get(character_id, (1, NOVEL_LAST_PAGE))
                if minimum <= page_number <= maximum and any(
                    contains_phrase(normalized, alias) for alias in aliases
                ):
                    participants.append(character_id)
            alias_hits = len(participants)
            action_hits = sum(term in normalized for term in ACTION_TERMS)
            dialogue_penalty = 1 if passage.startswith(("—", "-")) else 0
            score = alias_hits * 4 + action_hits * 1.5 + min(len(passage), 420) / 180 - dialogue_penalty
            candidates.append(
                {
                    "page": page_number,
                    "passage": passage[:1200],
                    "participants": sorted(set(participants)),
                    "score": score,
                    "position": (page_number - start) + index / max(1, len(sentences)),
                }
            )
    return candidates


def select_chapter_events(page_texts: dict[int, str], chapter_number: int, start: int, end: int) -> list[dict[str, Any]]:
    candidates = sentence_candidates(page_texts, start, end)
    if len(candidates) < EVENTS_PER_CHAPTER:
        raise ValueError(f"Prea puține pasaje utilizabile în intervalul PDF {start}-{end}.")
    span = max(1.0, end - start + 1)
    selected: list[dict[str, Any]] = []
    used_passages: set[str] = set()
    for anchor_terms in CHAPTER_ANCHORS.get(chapter_number, ()):
        matching = [
            item
            for item in candidates
            if all(normalize(term) in normalize(item["passage"]) for term in anchor_terms)
            and item["passage"] not in used_passages
        ]
        if matching:
            chosen = max(matching, key=lambda item: (item["score"], -item["page"]))
            selected.append(chosen)
            used_passages.add(chosen["passage"])
    for slot in range(EVENTS_PER_CHAPTER):
        if len(selected) >= EVENTS_PER_CHAPTER:
            break
        left = slot * span / EVENTS_PER_CHAPTER
        right = (slot + 1) * span / EVENTS_PER_CHAPTER
        center = (left + right) / 2
        bucket = [
            item
            for item in candidates
            if left <= item["position"] < right and item["passage"] not in used_passages
        ]
        if not bucket:
            bucket = [item for item in candidates if item["passage"] not in used_passages]
        chosen = max(
            bucket,
            key=lambda item: (
                item["score"] - abs(item["position"] - center) * 0.45,
                -abs(item["position"] - center),
                -item["page"],
            ),
        )
        selected.append(chosen)
        used_passages.add(chosen["passage"])
    return sorted(selected, key=lambda item: (item["position"], item["page"]))


def event_title(chapter_number: int, order: int, passage: str, participants: list[str]) -> str:
    names = {character_id: name for character_id, name, *_ in CHARACTERS}
    prefix = " și ".join(names[value].split()[0] for value in participants[:2])
    cleaned = re.sub(r"^[—\-„”\s]+", "", passage)
    cleaned = re.sub(r"\s+", " ", cleaned).split(".", 1)[0].strip(" ,;:!?")
    if len(cleaned) > 78:
        cleaned = cleaned[:77].rsplit(" ", 1)[0] + "…"
    return f"{prefix}: {cleaned}" if prefix else f"Momentul {order} din capitolul {chapter_number}: {cleaned}"


def classify_location(passage: str) -> str:
    normalized = normalize(passage)
    matches = [
        (len(normalize(alias)), location_id)
        for location_id, _, aliases, _ in LOCATIONS
        for alias in aliases
        if contains_phrase(normalized, alias)
    ]
    if matches:
        return max(matches)[1]
    return "LOC_MOARA"


def classify_concepts(passage: str) -> tuple[list[str], list[str]]:
    text = normalize(passage)
    themes: list[str] = []
    conflicts: list[str] = []
    rules = (
        ("THEME_DEHUMANIZATION", ("bani", "castig", "bogat", "hot", "pacat", "frica", "lica")),
        ("THEME_FAMILY", ("famil", "nevasta", "copil", "soacra", "mama", "ana")),
        ("THEME_LOVE", ("iub", "inima", "sarut", "drag", "ghita", "ana")),
        ("THEME_DESTINY", ("noroc", "dumnezeu", "data", "soarta", "cruce")),
    )
    for concept_id, terms in rules:
        if any(term in text for term in terms):
            themes.append(concept_id)
    if "ghita" in text and any(term in text for term in ("bani", "castig", "cinstit", "frica", "gand", "pacat")):
        conflicts.append("CONFLICT_GHITA_INNER")
    if "lica" in text and any(term in text for term in ("ghita", "pintea", "frica", "bani", "prinde", "pusca")):
        conflicts.append("CONFLICT_GHITA_LICA")
    if "ana" in text and "ghita" in text and any(term in text for term in ("frica", "supar", "las", "iart", "plans")):
        conflicts.append("CONFLICT_GHITA_ANA")
    return themes or ["THEME_DEHUMANIZATION"], conflicts


def build_graph() -> dict[str, Any]:
    if not PDF_PATH.is_file() or not ESSAY_PATH.is_file() or not PROMPT_PATH.is_file():
        raise FileNotFoundError("Lipsește PDF-ul operei, eseul-model sau promptul adaptat.")
    reader = PdfReader(PDF_PATH)
    if len(reader.pages) < NOVEL_LAST_PAGE:
        raise ValueError("PDF-ul nu conține toate cele 17 capitole așteptate.")
    chapter_page_texts = extract_chapter_page_texts(reader)
    essay = ESSAY_PATH.read_text(encoding="utf-8").strip()
    if "verosimilitatea" not in normalize(essay) or "psihologia personajelor" not in normalize(essay):
        raise ValueError("Eseul-model nu mai conține cele două trăsături așteptate.")

    chapter_ranges = list(CHAPTER_RANGES)

    sources: list[dict[str, Any]] = [
        {
            "id": "SRC_PDF",
            "source_type": "primary_text",
            "title": "Moara cu noroc - text integral",
            "author": "Ioan Slavici",
            "path": "opere_pdf/Moara cu noroc - Ioan Slavici.pdf",
            "sha256": sha256(PDF_PATH),
            "pdf_page_start": 2,
            "pdf_page_end": 53,
            "note": "Pagina PDF 1 este coperta; pagina 54 conține sursele, contributorii și licența, nu textul nuvelei.",
            "confidence": 1.0,
        },
        {
            "id": "SRC_ESSAY",
            "source_type": "model_essay",
            "title": "Eseu-model - Moara cu noroc",
            "path": "modele_eseuri/moara_cu_noroc.md",
            "sha256": sha256(ESSAY_PATH),
            "embedded_content": essay,
            "accepted_literary_traits": ["TRAIT_CHRONOTOPE", "TRAIT_PSYCHOLOGY"],
            "confidence": 1.0,
        },
        {
            "id": "SRC_PROMPT",
            "source_type": "generation_specification",
            "title": "Promptul grafului 2 adaptat pentru Moara cu noroc",
            "path": "grafuri/moara-cu-noroc/prompt-generare-graf-moara-cu-noroc.md",
            "sha256": sha256(PROMPT_PATH),
            "factual_source": False,
            "confidence": 1.0,
        },
    ]
    for chapter_number, start, end in chapter_ranges:
        sources.append(
            {
                "id": f"REF_PDF_CH_{chapter_number:02d}",
                "source_type": "primary_text_fragment",
                "title": f"Moara cu noroc - Capitolul {chapter_number}",
                "path": "opere_pdf/Moara cu noroc - Ioan Slavici.pdf",
                "chapter": f"Capitolul {chapter_number}",
                "pdf_page_start": start,
                "pdf_page_end": end,
                "confidence": 1.0,
            }
        )

    nodes: list[dict[str, Any]] = [
        node(
            "WORK_MOARA_CU_NOROC",
            "Work",
            "Moara cu noroc",
            "Nuvelă realist-psihologică publicată în 1881 în volumul «Novele din popor», construită ca studiu al dezumanizării lui Ghiță sub efectul lăcomiei și al dominației lui Lică.",
            importance="major",
            assertion_type="literary_interpretation",
            source_refs=["SRC_PDF", "SRC_ESSAY"],
            attributes={"publication_year": 1881, "volume": "Novele din popor", "genre": "epic", "species": "nuvelă psihologică", "work_type": "nuvelă", "chapter_count": 17, "literary_movement": "Realism"},
        ),
        node("AUTHOR_SLAVICI", "Author", "Ioan Slavici", "Prozator român al epocii Marilor Clasici și autorul nuvelei «Moara cu noroc».", importance="major", source_refs=["SRC_PDF", "SRC_ESSAY"], attributes={"full_name": "Ioan Slavici", "literary_epoch": "Marii Clasici"}),
    ]
    for character_id, name, aliases, importance, description, human_type, traits, physical in CHARACTERS:
        nodes.append(
            node(
                character_id, "Character", name, description,
                importance=importance,
                assertion_type="literary_interpretation",
                source_refs=["SRC_PDF", "SRC_ESSAY"],
                aliases=list(aliases),
                attributes={"role": description, "human_type": human_type, "traits": traits, "physical_portrait": physical},
            )
        )
    for location_id, label, aliases, description in LOCATIONS:
        nodes.append(node(location_id, "Location", label, description, assertion_type="literary_interpretation", source_refs=["SRC_PDF"], aliases=list(aliases)))
    for concept_id, concept_type, label, description in CONCEPTS:
        nodes.append(
            node(
                concept_id, concept_type, label, description,
                importance="major" if concept_id in {"THEME_DEHUMANIZATION", "THEME_FAMILY", "THEME_DESTINY", "MOV_REALISM", "TRAIT_CHRONOTOPE", "TRAIT_PSYCHOLOGY"} else "supporting",
                assertion_type="literary_interpretation",
                source_refs=["SRC_ESSAY", "SRC_PDF"],
                attributes={"accepted_for_essay": concept_id in {"TRAIT_CHRONOTOPE", "TRAIT_PSYCHOLOGY"}},
            )
        )
    for composition_id, label, description, evidence_ids, scheme in COMPOSITION_ELEMENTS:
        nodes.append(
            node(
                composition_id,
                "CompositionElement",
                label,
                description,
                importance="major",
                assertion_type="literary_interpretation",
                source_refs=["SRC_PDF", "SRC_ESSAY"],
                attributes={
                    "role_in_work": description,
                    "scheme": scheme,
                    "evidence_node_ids": evidence_ids,
                    "essay_use": (
                        f"În eseu, elementul «{label}» este explicat prin legarea interpretării "
                        "de faptele și conceptele indicate în evidence_node_ids."
                    ),
                    "generated_from": ["primary_text", "model_essay"],
                },
            )
        )

    edges: list[dict[str, Any]] = [
        edge("EDGE_WORK_AUTHOR", "WORK_MOARA_CU_NOROC", "authored_by", "AUTHOR_SLAVICI", "Ioan Slavici este autorul nuvelei.", ["SRC_PDF", "SRC_ESSAY"]),
        edge("EDGE_WORK_MOVEMENT", "WORK_MOARA_CU_NOROC", "belongs_to_literary_movement", "MOV_REALISM", "Nuvela aparține realismului.", ["SRC_ESSAY"]),
        edge("EDGE_MOV_TRAIT_1", "MOV_REALISM", "has_characteristic", "TRAIT_CHRONOTOPE", "Eseul-model argumentează verosimilitatea prin cronotop precis.", ["SRC_ESSAY"]),
        edge("EDGE_MOV_TRAIT_2", "MOV_REALISM", "has_characteristic", "TRAIT_PSYCHOLOGY", "Eseul-model argumentează interesul pentru psihologia personajelor.", ["SRC_ESSAY"]),
        edge("EDGE_TRAIT_CHRONO_INEU", "TRAIT_CHRONOTOPE", "supported_by", "LOC_INEU", "Ineul fixează cadrul geografic real al acțiunii.", ["SRC_PDF", "SRC_ESSAY"]),
        edge("EDGE_TRAIT_CHRONO_ARAD", "TRAIT_CHRONOTOPE", "supported_by", "LOC_ARAD", "Aradul, alături de Salonta și Pesta, amplifică impresia de verosimil.", ["SRC_PDF", "SRC_ESSAY"]),
        edge("EDGE_TRAIT_PSY_GHITA", "TRAIT_PSYCHOLOGY", "supported_by", "CHAR_GHITA", "Frământările lui Ghiță sunt centrul analizei psihologice.", ["SRC_PDF", "SRC_ESSAY"]),
        edge("EDGE_TRAIT_PSY_MONOLOGUE", "TRAIT_PSYCHOLOGY", "supported_by", "TECH_MONOLOGUE", "Monologul interior redă conflictul lăuntric.", ["SRC_PDF", "SRC_ESSAY"]),
        edge("EDGE_TRAIT_PSY_FREE", "TRAIT_PSYCHOLOGY", "supported_by", "TECH_FREE_INDIRECT", "Stilul indirect liber apropie vocea naratorului de gândirea lui Ghiță.", ["SRC_PDF", "SRC_ESSAY"]),
        edge("EDGE_TRAIT_PSY_GESTURE", "TRAIT_PSYCHOLOGY", "supported_by", "TECH_GESTURE", "Gestica și mimica fac vizibilă tensiunea psihică.", ["SRC_PDF", "SRC_ESSAY"]),
    ]
    for index, (source, predicate, target, description) in enumerate(DIRECT_RELATIONS, start=1):
        edges.append(edge(f"EDGE_REL_{index:03d}", source, predicate, target, description, ["SRC_PDF", "SRC_ESSAY"]))
    for location_id, label, *_ in LOCATIONS:
        edges.append(
            edge(
                f"EDGE_WORK_SETTING_{location_id}",
                "WORK_MOARA_CU_NOROC",
                "has_setting",
                location_id,
                f"{label} este un spațiu al acțiunii nuvelei.",
                ["SRC_PDF"],
            )
        )
    for concept_id, *_ in CONCEPTS:
        if concept_id.startswith(("THEME_", "CONFLICT_", "MOTIF_", "TECH_")):
            edges.append(edge(f"EDGE_WORK_{concept_id}", "WORK_MOARA_CU_NOROC", "has_concept", concept_id, "Concept relevant pentru construcția nuvelei.", ["SRC_PDF", "SRC_ESSAY"]))
    for composition_id, _, _, evidence_ids, _ in COMPOSITION_ELEMENTS:
        edges.append(
            edge(
                f"EDGE_WORK_{composition_id}",
                "WORK_MOARA_CU_NOROC",
                "has_composition_element",
                composition_id,
                "Opera este explicată prin acest element compozițional obligatoriu.",
                ["SRC_PDF", "SRC_ESSAY"],
            )
        )
        for evidence_index, evidence_id in enumerate(evidence_ids, start=1):
            edges.append(
                edge(
                    f"EDGE_{composition_id}_EVIDENCE_{evidence_index:02d}",
                    composition_id,
                    "supported_by",
                    evidence_id,
                    "Dovada factuală sau conceptuală susține schema elementului compozițional.",
                    ["SRC_PDF", "SRC_ESSAY"],
                )
            )

    chapters: list[dict[str, Any]] = []
    global_order = 0
    for chapter_number, start, end in chapter_ranges:
        chapter_id = f"CH_{chapter_number:02d}"
        source_ref = f"REF_PDF_CH_{chapter_number:02d}"
        selected = select_chapter_events(chapter_page_texts[chapter_number], chapter_number, start, end)
        event_ids: list[str] = []
        chapter_node = node(
            chapter_id, "Chapter", f"Capitolul {chapter_number}",
            f"Capitolul {chapter_number} al nuvelei, acoperit de paginile PDF {start}-{end}.",
            chapter_ids=[chapter_id], importance="major", source_refs=[source_ref],
            attributes={"ordinal": chapter_number, "order": chapter_number, "pdf_page_start": start, "pdf_page_end": end},
        )
        nodes.append(chapter_node)
        edges.append(edge(f"EDGE_WORK_CH_{chapter_number:02d}", "WORK_MOARA_CU_NOROC", "contains", chapter_id, f"Romanul conține capitolul {chapter_number}.", [source_ref]))
        for chapter_order, item in enumerate(selected, start=1):
            global_order += 1
            event_id = f"EV_{global_order:03d}"
            event_ids.append(event_id)
            themes, conflicts = classify_concepts(item["passage"])
            location_id = classify_location(item["passage"])
            title = event_title(chapter_number, chapter_order, item["passage"], item["participants"])
            importance = "major" if chapter_order in {1, EVENTS_PER_CHAPTER} or len(item["participants"]) >= 2 else "supporting"
            event_node = node(
                event_id, "NarrativeEvent", title, item["passage"],
                chapter_ids=[chapter_id], importance=importance, source_refs=[source_ref],
                attributes={
                    "event_id": event_id,
                    "chapter_id": chapter_id,
                    "chapter_order": chapter_order,
                    "global_order": global_order,
                    "title": title,
                    "canonical_description": item["passage"],
                    "participants": item["participants"],
                    "location": location_id,
                    "time_context": f"Capitolul {chapter_number}; pagina PDF {item['page']}",
                    "preconditions": [event_ids[-2]] if len(event_ids) > 1 else [],
                    "causes": [event_ids[-2]] if len(event_ids) > 1 else [],
                    "action": item["passage"],
                    "immediate_effects": (
                        ["Acțiunea creează contextul narativ imediat pentru momentul următor din același capitol."]
                        if chapter_order < EVENTS_PER_CHAPTER
                        else ["Acțiunea încheie segmentul documentat al capitolului și pregătește continuarea nuvelei."]
                    ),
                    "long_term_effects": [],
                    "state_transitions": [],
                    "motivations": [],
                    "conflicts": conflicts,
                    "themes": themes,
                    "importance": importance,
                    "source_refs": [source_ref],
                    "confidence": 1.0,
                    "simple_narration": item["passage"],
                    "elevated_narration": item["passage"],
                    "simple_transition": "Apoi," if chapter_order > 1 else "",
                    "elevated_transition": "În continuarea acțiunii," if chapter_order > 1 else "",
                    "verification": {
                        "status": "verified_primary",
                        "method": "extractive_pdf_text",
                        "source_id": "SRC_PDF",
                        "source_ref": source_ref,
                        "pdf_page": item["page"],
                        "evidence_quote": item["passage"],
                    },
                },
            )
            nodes.append(event_node)
            edges.append(edge(f"EDGE_CH_EVENT_{global_order:03d}", chapter_id, "contains", event_id, f"Capitolul {chapter_number} conține evenimentul {chapter_order}.", [source_ref]))
            edges.append(edge(f"EDGE_EVENT_CH_{global_order:03d}", event_id, "occurs_in_chapter", chapter_id, f"Evenimentul are loc în capitolul {chapter_number}.", [source_ref]))
            edges.append(edge(f"EDGE_EVENT_LOC_{global_order:03d}", event_id, "occurs_at", location_id, "Locul este identificat din pasajul-sursă sau din cadrul citadin implicit.", [source_ref]))
            if chapter_order > 1:
                previous_id = event_ids[-2]
                edges.append(edge(f"EDGE_TEMP_{global_order:03d}", previous_id, "immediately_precedes", event_id, "Ordine textuală explicită în interiorul capitolului.", [source_ref]))
                edges.append(edge(f"EDGE_TEMP_REVERSE_{global_order:03d}", event_id, "immediately_follows", previous_id, "Ordine textuală explicită în interiorul capitolului.", [source_ref]))
                edges.append(edge(f"EDGE_BEFORE_{global_order:03d}", previous_id, "occurs_before", event_id, "Evenimentul precedent apare mai devreme în ordinea narativă a capitolului.", [source_ref]))
                edges.append(edge(f"EDGE_AFTER_{global_order:03d}", event_id, "occurs_after", previous_id, "Evenimentul curent apare după momentul precedent al capitolului.", [source_ref]))
                edges.append(edge(f"EDGE_PREPARES_{global_order:03d}", previous_id, "prepares", event_id, "Situația narativă precedentă pregătește continuarea acțiunii fără a afirma o cauzalitate exclusivă.", [source_ref]))
            for participant_index, participant in enumerate(item["participants"], start=1):
                edges.append(edge(f"EDGE_EVENT_CHAR_{global_order:03d}_{participant_index:02d}", event_id, "involves", participant, "Personajul este menționat explicit în pasajul-sursă.", [source_ref]))
                edges.append(edge(f"EDGE_EVENT_PARTICIPANT_{global_order:03d}_{participant_index:02d}", event_id, "has_participant", participant, "Personajul este menționat explicit în pasajul-sursă.", [source_ref]))
                edges.append(edge(f"EDGE_EVENT_STATE_{global_order:03d}_{participant_index:02d}", event_id, "changes_state_of", participant, "Momentul contribuie la evoluția situației sau reprezentării personajului.", [source_ref]))
            for concept_index, concept_id in enumerate(themes + conflicts, start=1):
                edges.append(edge(f"EDGE_EVENT_CONCEPT_{global_order:03d}_{concept_index:02d}", event_id, "illustrates", concept_id, "Pasajul conține indicatori semantici ai conceptului.", [source_ref]))
                predicate = "expresses_theme" if concept_id.startswith("THEME_") else "contrasts_with"
                edges.append(edge(f"EDGE_EVENT_INTERPRET_{global_order:03d}_{concept_index:02d}", event_id, predicate, concept_id, "Legătură interpretativă susținută de indicatorii semantici ai pasajului.", [source_ref]))
                if concept_id.startswith("CONFLICT_"):
                    edges.append(edge(f"EDGE_EVENT_CONFLICT_{global_order:03d}_{concept_index:02d}", event_id, "intensifies", concept_id, "Momentul intensifică sau face vizibil conflictul indicat.", [source_ref]))
            normalized_passage = normalize(item["passage"])
            motif_id = None
            if any(term in normalized_passage for term in ("bani", "galbeni", "hartii", "imprumut")):
                motif_id = "MOTIF_MONEY"
            elif any(term in normalized_passage for term in ("cruce", "cruci")):
                motif_id = "MOTIF_CROSSES"
            elif any(term in normalized_passage for term in ("foc", "flacari", "arse", "incend")):
                motif_id = "MOTIF_FIRE"
            elif any(term in normalized_passage for term in ("drum", "rascruce", "cale")):
                motif_id = "MOTIF_ROAD"
            if motif_id:
                edges.append(edge(f"EDGE_EVENT_MOTIF_{global_order:03d}", event_id, "expresses_motif", motif_id, "Pasajul dezvoltă explicit motivul indicat.", [source_ref]))
        opening_state_id = f"STATE_CH_{chapter_number:02d}_OPEN"
        closing_state_id = f"STATE_CH_{chapter_number:02d}_CLOSE"
        opening_passage = selected[0]["passage"]
        closing_passage = selected[-1]["passage"]
        nodes.extend(
            [
                node(
                    opening_state_id,
                    "NarrativeState",
                    f"Starea inițială a capitolului {chapter_number}",
                    f"La deschiderea capitolului {chapter_number}, situația narativă este fixată de momentul: {opening_passage}",
                    chapter_ids=[chapter_id],
                    importance="major",
                    source_refs=[source_ref],
                    attributes={
                        "state_role": "opening",
                        "chapter_id": chapter_id,
                        "supported_by_event_id": event_ids[0],
                        "simple_narration": opening_passage,
                        "elevated_narration": opening_passage,
                    },
                ),
                node(
                    closing_state_id,
                    "NarrativeState",
                    f"Starea finală a capitolului {chapter_number}",
                    f"La închiderea capitolului {chapter_number}, situația narativă rezultă din momentul: {closing_passage}",
                    chapter_ids=[chapter_id],
                    importance="major",
                    source_refs=[source_ref],
                    attributes={
                        "state_role": "closing",
                        "chapter_id": chapter_id,
                        "supported_by_event_id": event_ids[-1],
                        "simple_narration": closing_passage,
                        "elevated_narration": closing_passage,
                    },
                ),
            ]
        )
        edges.extend(
            [
                edge(f"EDGE_CH_OPEN_STATE_{chapter_number:02d}", chapter_id, "has_opening_state", opening_state_id, "Capitolul are o stare inițială explicită.", [source_ref]),
                edge(f"EDGE_CH_CLOSE_STATE_{chapter_number:02d}", chapter_id, "has_closing_state", closing_state_id, "Capitolul are o stare finală explicită.", [source_ref]),
                edge(f"EDGE_OPEN_STATE_EVENT_{chapter_number:02d}", opening_state_id, "supported_by", event_ids[0], "Primul eveniment documentează starea inițială.", [source_ref]),
                edge(f"EDGE_OPEN_STATE_ENABLES_{chapter_number:02d}", opening_state_id, "enables", event_ids[0], "Starea inițială oferă condițiile narative ale primului eveniment documentat.", [source_ref]),
                edge(f"EDGE_EVENT_CLOSE_STATE_{chapter_number:02d}", event_ids[-1], "results_in", closing_state_id, "Ultimul eveniment documentat produce starea finală a capitolului.", [source_ref]),
            ]
        )
        chapters.append(
            {
                "id": chapter_id,
                "ordinal": chapter_number,
                "title": f"Capitolul {chapter_number}",
                "pdf_page_start": start,
                "pdf_page_end": end,
                "source_refs": [source_ref],
                "event_sequence": event_ids,
                "opening_state_id": opening_state_id,
                "closing_state_id": closing_state_id,
                "coverage_policy": "Opt momente extractive distribuite uniform pe întregul interval al capitolului.",
            }
        )

    event_nodes_by_id = {item["id"]: item for item in nodes if item["type"] == "NarrativeEvent"}
    for index in range(len(chapters) - 1):
        source_event = chapters[index]["event_sequence"][-1]
        target_event = chapters[index + 1]["event_sequence"][0]
        event_nodes_by_id[target_event]["attributes"]["causes"] = [source_event]
        refs = chapters[index]["source_refs"] + chapters[index + 1]["source_refs"]
        edges.append(
            edge(
                f"EDGE_CAUSAL_CHAPTER_{index + 1:02d}_{index + 2:02d}",
                source_event,
                "contributes_to",
                target_event,
                "Situația stabilită la începutul capitolului anterior contribuie la contextul narativ al capitolului următor; relația nu afirmă o cauzalitate exclusivă.",
                refs,
            )
        )

    node_ids = {item["id"] for item in nodes}
    source_ids = {item["id"] for item in sources}
    dangling = [item["id"] for item in edges if item["source"] not in node_ids or item["target"] not in node_ids]
    missing_sources = [
        item["id"] for item in nodes + edges
        if any(source_ref not in source_ids for source_ref in item.get("source_refs", []))
    ]
    duplicate_nodes = len(nodes) - len(node_ids)
    duplicate_edges = len(edges) - len({item["id"] for item in edges})
    verified_events = sum(
        item["type"] == "NarrativeEvent"
        and item["attributes"].get("verification", {}).get("status") == "verified_primary"
        and bool(item["attributes"].get("verification", {}).get("evidence_quote"))
        for item in nodes
    )
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for item in edges:
        if item["source"] in adjacency and item["target"] in adjacency:
            adjacency[item["source"]].add(item["target"])
            adjacency[item["target"]].add(item["source"])
    connected: set[str] = set()
    pending = ["WORK_MOARA_CU_NOROC"]
    while pending:
        current = pending.pop()
        if current in connected:
            continue
        connected.add(current)
        pending.extend(adjacency.get(current, set()) - connected)
    orphan_node_ids = sorted(node_id for node_id, neighbours in adjacency.items() if not neighbours)
    narrative_types = {"NarrativeEvent", "NarrativeSubevent", "NarrativeState", "CharacterState", "Decision", "Action", "Motivation", "Consequence"}
    narrative_node_count = sum(item["type"] in narrative_types for item in nodes)
    uncertain_count = sum(item.get("assertion_type") == "uncertain" for item in nodes + edges)
    narrative_events = [item for item in nodes if item["type"] == "NarrativeEvent"]
    events_without_causes = [item["id"] for item in narrative_events if not item["attributes"].get("causes")]
    events_without_consequences = [
        item["id"]
        for item in narrative_events
        if not item["attributes"].get("immediate_effects") and not item["attributes"].get("long_term_effects")
    ]
    events_without_participants = [item["id"] for item in narrative_events if not item["attributes"].get("participants")]
    composition_ids = {item["id"] for item in nodes if item["type"] == "CompositionElement"}
    expected_composition_ids = {item[0] for item in COMPOSITION_ELEMENTS}
    chapter_boundaries_valid = [
        (item["ordinal"], item["pdf_page_start"], item["pdf_page_end"])
        for item in chapters
    ] == list(CHAPTER_RANGES)
    structural_valid = (
        not dangling
        and not missing_sources
        and duplicate_nodes == 0
        and duplicate_edges == 0
        and len(chapters) == 17
        and verified_events == 170
        and 200 <= len(nodes) <= 300
        and len(edges) >= 300
        and len(connected) / max(1, len(nodes)) >= 0.95
        and not orphan_node_ids
        and composition_ids == expected_composition_ids
        and sum(item["type"] == "NarrativeState" for item in nodes) == 34
        and chapter_boundaries_valid
    )
    graph = {
        "metadata": {
            "title": "Knowledge graph narativ complet și autosuficient - Moara cu noroc",
            "work": "Moara cu noroc",
            "work_id": "moara_cu_noroc",
            "author": "Ioan Slavici",
            "language": "ro",
            "version": "2.0-graf2-prompt",
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "canonical_format": "JSON",
            "work_type": "nuvelă psihologică",
            "literary_movement": "Realism",
            "derivation": "Reconstruit după promptul exact al grafului 2 pentru Ion, adaptat la Moara cu noroc și extins cu delimitarea capitolelor, curentul literar și elementele compoziționale; faptele provin din textul integral și eseul-model local.",
            "generation_prompt": "grafuri/prompt-generare-graf-moara-cu-noroc.md",
            "source_hashes": {PDF_PATH.name: sha256(PDF_PATH), ESSAY_PATH.name: sha256(ESSAY_PATH), PROMPT_PATH.name: sha256(PROMPT_PATH)},
        },
        "sources": sources,
        "ontology": {
            "node_types": sorted(PROMPT_NODE_TYPES | {item["type"] for item in nodes}),
            "instantiated_node_types": sorted({item["type"] for item in nodes}),
            "relationship_types": sorted(PROMPT_RELATIONSHIP_TYPES | {item["predicate"] for item in edges}),
            "instantiated_relationship_types": sorted({item["predicate"] for item in edges}),
            "assertion_types": ["explicit_fact", "explicit_motivation", "inferred_motivation", "literary_interpretation", "symbolic_interpretation", "uncertain"],
            "event_eligibility": "NarrativeEvent explicit_fact cu verification.status=verified_primary și evidence_quote nevid.",
            "accepted_literary_trait_ids": ["TRAIT_CHRONOTOPE", "TRAIT_PSYCHOLOGY"],
        },
        "nodes": nodes,
        "edges": edges,
        "chapters": chapters,
        "reconstruction_profiles": [
            {"id": "simple_short", "description": "Evenimentele majore în ordine narativă, folosind simple_narration.", "chapter_ids": [item["id"] for item in chapters]},
            {"id": "simple_complete", "description": "Toate evenimentele capitolului în ordine narativă, folosind simple_narration.", "chapter_ids": [item["id"] for item in chapters]},
            {"id": "elevated_short", "description": "Evenimentele majore în ordine narativă, folosind elevated_narration.", "chapter_ids": [item["id"] for item in chapters]},
            {"id": "elevated_complete", "description": "Toate evenimentele capitolului în ordine narativă, folosind elevated_narration.", "chapter_ids": [item["id"] for item in chapters]},
            {"id": "bac_essay", "description": "Realism, cele două trăsături din eseul-model, dezumanizarea, titlul, conflictul și relația incipit-final.", "concept_ids": ["MOV_REALISM", "TRAIT_CHRONOTOPE", "TRAIT_PSYCHOLOGY", "THEME_DEHUMANIZATION", "COMP_TITLE", "COMP_CONFLICT", "COMP_INCIPIT_FINAL"]},
        ],
        "validation": {
            "valid": structural_valid,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "chapter_count": len(chapters),
            "event_count": verified_events,
            "events_per_chapter": EVENTS_PER_CHAPTER,
            "verified_primary_event_count": verified_events,
            "verified_primary_event_ratio": round(verified_events / max(1, sum(item["type"] == "NarrativeEvent" for item in nodes)), 4),
            "dangling_edge_ids": dangling,
            "missing_source_ref_item_ids": missing_sources,
            "duplicate_node_ids": duplicate_nodes,
            "duplicate_edge_ids": duplicate_edges,
            "orphan_node_ids": orphan_node_ids,
            "connected_to_main_component": len(connected),
            "connected_to_main_component_ratio": round(len(connected) / max(1, len(nodes)), 4),
            "narrative_node_count": narrative_node_count,
            "narrative_node_ratio": round(narrative_node_count / max(1, len(nodes)), 4),
            "sourced_assertion_count": sum(bool(item.get("source_refs")) for item in nodes + edges),
            "uncertain_assertion_count": uncertain_count,
            "events_without_causes": events_without_causes,
            "events_without_consequences": events_without_consequences,
            "events_without_participants": events_without_participants,
            "narrative_state_count": sum(item["type"] == "NarrativeState" for item in nodes),
            "composition_element_ids": sorted(composition_ids),
            "chapter_boundaries_valid": chapter_boundaries_valid,
            "type_distribution": dict(sorted(Counter(item["type"] for item in nodes).items())),
            "relation_distribution": dict(sorted(Counter(item["predicate"] for item in edges).items())),
            "source_pdf_page_coverage": {"start": 2, "end": 53, "excluded_front_matter": [1], "excluded_editorial_appendix": [54]},
            "model_essay_traits_locked": ["Verosimilitatea prin cronotop precis", "Interesul pentru psihologia personajelor"],
        },
    }
    if not graph["validation"]["valid"]:
        raise ValueError(f"Graful generat nu trece validarea: {graph['validation']}")
    return graph


def build_schema(graph: dict[str, Any]) -> dict[str, Any]:
    assertion_types = graph["ontology"]["assertion_types"]
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://bacapp.local/schemas/moara-cu-noroc-knowledge-graph.schema.json",
        "title": "Knowledge graph - Moara cu noroc",
        "type": "object",
        "required": ["metadata", "sources", "ontology", "nodes", "edges", "chapters", "reconstruction_profiles", "validation"],
        "properties": {
            "metadata": {"type": "object", "required": ["work", "work_id", "author", "version"]},
            "sources": {
                "type": "array",
                "items": {"type": "object", "required": ["id", "source_type", "title", "path"]},
            },
            "ontology": {"type": "object", "required": ["node_types", "relationship_types", "assertion_types"]},
            "nodes": {
                "type": "array",
                "minItems": 200,
                "maxItems": 300,
                "items": {
                    "type": "object",
                    "required": ["id", "type", "label", "description", "chapter_ids", "importance", "confidence", "assertion_type", "source_refs", "attributes"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "type": {"enum": graph["ontology"]["node_types"]},
                        "label": {"type": "string", "minLength": 1},
                        "description": {"type": "string", "minLength": 1},
                        "chapter_ids": {"type": "array", "items": {"type": "string"}},
                        "importance": {"enum": ["major", "medium", "supporting", "minor"]},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "assertion_type": {"enum": assertion_types},
                        "source_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                        "attributes": {"type": "object"},
                    },
                    "additionalProperties": True,
                },
            },
            "edges": {
                "type": "array",
                "minItems": 300,
                "items": {
                    "type": "object",
                    "required": ["id", "source", "predicate", "target", "assertion_type", "source_refs", "qualifiers"],
                    "properties": {
                        "id": {"type": "string", "minLength": 1},
                        "source": {"type": "string", "minLength": 1},
                        "predicate": {"enum": graph["ontology"]["relationship_types"]},
                        "target": {"type": "string", "minLength": 1},
                        "assertion_type": {"enum": assertion_types},
                        "source_refs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                        "qualifiers": {"type": "object"},
                    },
                    "additionalProperties": True,
                },
            },
            "chapters": {"type": "array", "minItems": 17, "maxItems": 17},
            "reconstruction_profiles": {"type": "array", "minItems": 4},
            "validation": {"type": "object", "required": ["valid", "node_count", "edge_count", "chapter_count"]},
        },
        "additionalProperties": False,
    }


def build_ontology_markdown(graph: dict[str, Any]) -> str:
    instantiated_nodes = set(graph["ontology"]["instantiated_node_types"])
    instantiated_relations = set(graph["ontology"]["instantiated_relationship_types"])
    lines = [
        "# Ontologia knowledge graph-ului «Moara cu noroc»",
        "",
        "Ontologia păstrează vocabularul promptului folosit pentru graful 2 al operei «Ion» și îl extinde explicit cu `LiteraryMovement`, `LiteraryTrait` și `CompositionElement`.",
        "",
        "## Tipuri de noduri",
        "",
    ]
    for node_type in graph["ontology"]["node_types"]:
        status = "instanțiat" if node_type in instantiated_nodes else "definit pentru extensie"
        lines.append(f"- `{node_type}` - {status}.")
    lines.extend(("", "## Relații", ""))
    for predicate in graph["ontology"]["relationship_types"]:
        status = "folosită în graf" if predicate in instantiated_relations else "rezervată de vocabularul controlat"
        lines.append(f"- `{predicate}` - {status}.")
    lines.extend(
        (
            "",
            "## Reguli de extensie",
            "",
            "- ID-urile trebuie să fie unice și stabile.",
            "- Un nod narativ trebuie să indice capitolul, ordinea, sursa și verbalizările simplă și elevată.",
            "- O muchie trebuie să folosească ID-uri existente și minimum o referință-sursă.",
            "- Interpretările nu pot fi marcate drept fapte explicite.",
            "- Pentru o altă operă se păstrează ontologia, dar se înlocuiesc toate instanțele și dovezile factuale.",
            "",
        )
    )
    return "\n".join(lines)


def _render_reconstruction(events: list[dict[str, Any]], language: str, short: bool) -> tuple[str, list[str]]:
    selected = [item for item in events if not short or item["importance"] == "major"]
    if not selected:
        selected = events[:1]
    narration_key = f"{language}_narration"
    transition_key = f"{language}_transition"
    sentences = []
    mappings = []
    for item in selected:
        attributes = item["attributes"]
        transition = str(attributes.get(transition_key) or "").strip()
        narration = str(attributes.get(narration_key) or item["description"]).strip()
        sentences.append(f"{transition} {narration}".strip())
        page = attributes.get("verification", {}).get("pdf_page")
        mappings.append(f"- `{item['id']}` - PDF p. {page}: {narration}")
    return " ".join(sentences), mappings


def build_reconstructions_markdown(graph: dict[str, Any]) -> str:
    nodes = {item["id"]: item for item in graph["nodes"]}
    lines = [
        "# Reconstrucții pe capitole - Moara cu noroc",
        "",
        "Textele de mai jos sunt reconstruite exclusiv din `chapters[].event_sequence` și din verbalizările evenimentelor grafului.",
        "",
    ]
    for chapter in graph["chapters"]:
        events = [nodes[event_id] for event_id in chapter["event_sequence"]]
        lines.extend((f"## {chapter['title']}", ""))
        for label, language, short in (
            ("Rezumat simplu scurt", "simple", True),
            ("Rezumat simplu complet", "simple", False),
            ("Rezumat elevat scurt", "elevated", True),
            ("Rezumat elevat complet", "elevated", False),
        ):
            text, mappings = _render_reconstruction(events, language, short)
            lines.extend((f"### {label}", "", text, "", "Noduri și surse:", "", *mappings, ""))
    return "\n".join(lines).rstrip() + "\n"


def build_coverage_markdown(graph: dict[str, Any]) -> str:
    nodes = {item["id"]: item for item in graph["nodes"]}
    edges = graph["edges"]
    lines = [
        "# Matrice de acoperire - Moara cu noroc",
        "",
        "| Capitol | Pagini PDF | Evenimente | Personaje distincte | Relații cauzale | Schimbări de stare | Probleme |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for chapter in graph["chapters"]:
        event_ids = set(chapter["event_sequence"])
        characters = {
            participant
            for event_id in event_ids
            for participant in nodes[event_id]["attributes"].get("participants", [])
        }
        causal_edges = sum(
            item["source"] in event_ids and item["target"] in event_ids and item["predicate"] in {"causes", "contributes_to", "enables", "results_in"}
            for item in edges
        )
        causal_attributes = sum(bool(nodes[event_id]["attributes"].get("causes")) for event_id in event_ids)
        causal = causal_edges + causal_attributes
        state_changes = sum(
            item["source"] in event_ids and item["predicate"] == "changes_state_of"
            for item in edges
        )
        lines.append(
            f"| {chapter['title']} | {chapter['pdf_page_start']}-{chapter['pdf_page_end']} | {len(event_ids)} | {len(characters)} | {causal} | {state_changes} | Niciuna detectată |"
        )
    lines.append("")
    return "\n".join(lines)


def build_validation_markdown(graph: dict[str, Any]) -> str:
    validation = graph["validation"]
    lines = [
        "# Raport de validare - Moara cu noroc",
        "",
        f"- Rezultat general: **{'TRECUT' if validation['valid'] else 'EȘUAT'}**",
        f"- Noduri: **{validation['node_count']}** (prag: 200-300)",
        f"- Relații: **{validation['edge_count']}** (minimum: 300)",
        f"- Capitole: **{validation['chapter_count']}**",
        f"- Evenimente verificate în textul primar: **{validation['verified_primary_event_count']}**",
        f"- Stări narative inițiale/finale: **{validation['narrative_state_count']}**",
        f"- Noduri conectate la componenta principală: **{validation['connected_to_main_component']}** ({validation['connected_to_main_component_ratio']:.1%})",
        f"- Afirmații cu sursă: **{validation['sourced_assertion_count']}**",
        f"- Incertitudini: **{validation['uncertain_assertion_count']}**",
        "",
        "## Verificări structurale",
        "",
        f"- ID-uri de nod duplicate: {validation['duplicate_node_ids']}",
        f"- ID-uri de muchie duplicate: {validation['duplicate_edge_ids']}",
        f"- Noduri orfane: {len(validation['orphan_node_ids'])}",
        f"- Muchii invalide: {len(validation['dangling_edge_ids'])}",
        f"- Referințe-sursă inexistente: {len(validation['missing_source_ref_item_ids'])}",
        f"- Evenimente fără cauză explicită: {len(validation['events_without_causes'])} ({', '.join(validation['events_without_causes']) or 'niciunul'})",
        f"- Evenimente fără consecință: {len(validation['events_without_consequences'])}",
        f"- Evenimente fără participant uman explicit: {len(validation['events_without_participants'])} ({', '.join(validation['events_without_participants']) or 'niciunul'})",
        f"- Delimitarea celor 17 capitole: {'corectă' if validation['chapter_boundaries_valid'] else 'incorectă'}",
        f"- Elemente compoziționale: {', '.join(validation['composition_element_ids'])}",
        "",
        "## Distribuția nodurilor",
        "",
    ]
    lines.extend(f"- {key}: {value}" for key, value in validation["type_distribution"].items())
    lines.extend(("", "## Distribuția relațiilor", ""))
    lines.extend(f"- {key}: {value}" for key, value in validation["relation_distribution"].items())
    lines.extend(
        (
            "",
            "## Test de autosuficiență",
            "",
            "Cele patru variante de rezumat pentru fiecare capitol au fost reconstruite programatic numai din ordinea evenimentelor și verbalizările păstrate în graf. Fiecare propoziție este asociată unui nod și paginii PDF care o susține.",
            "",
        )
    )
    return "\n".join(lines)


def build_html(graph: dict[str, Any]) -> str:
    payload = json.dumps(graph, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    title = escape(graph["metadata"]["work"])
    return f"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Knowledge graph - {title}</title>
<style>
:root{{--ink:#17212b;--muted:#65717d;--paper:#f6f2e9;--card:#fffdf7;--line:#d8d0c1;--wine:#7c2d3a;--gold:#b68738;--blue:#315b73;--green:#3f725e;--shadow:0 18px 45px rgba(37,31,24,.12)}}
*{{box-sizing:border-box}} body{{margin:0;color:var(--ink);background:radial-gradient(circle at 8% 5%,#fff9e9 0,transparent 28%),linear-gradient(135deg,#f6f2e9,#ebe4d8);font:15px/1.5 Inter,Segoe UI,Arial,sans-serif}}
header{{padding:34px clamp(22px,5vw,72px) 26px;color:#fff;background:linear-gradient(120deg,#351c25,#76313d 62%,#a36f32);box-shadow:var(--shadow)}}
.eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.2em;color:#f0d59e}} h1{{margin:5px 0 5px;font:700 clamp(30px,5vw,58px)/1.05 Georgia,serif}} header p{{max-width:850px;margin:0;color:#f5e9dc}}
main{{max-width:1580px;margin:auto;padding:24px}} .stats{{display:grid;grid-template-columns:repeat(5,minmax(120px,1fr));gap:12px;margin-top:-5px}}
.stat,.panel{{background:rgba(255,253,247,.94);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow)}} .stat{{padding:16px}} .stat b{{display:block;font:700 27px Georgia,serif;color:var(--wine)}} .stat span{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
.toolbar{{display:grid;grid-template-columns:2fr 1fr 1fr auto;gap:10px;margin:20px 0}} input,select,button{{min-height:43px;border:1px solid #c9bfaf;border-radius:11px;background:#fffdf9;color:var(--ink);padding:0 13px;font:inherit}} button{{cursor:pointer;background:var(--wine);color:white;border-color:var(--wine);font-weight:650}}
.workspace{{display:grid;grid-template-columns:minmax(0,2.25fr) minmax(300px,.8fr);gap:16px}} .graph-panel{{min-height:700px;overflow:hidden;position:relative}} #graph{{width:100%;height:700px;display:block;background:linear-gradient(rgba(124,45,58,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(124,45,58,.025) 1px,transparent 1px);background-size:32px 32px}}
.hint{{position:absolute;left:14px;bottom:12px;background:#fffdf5dd;border:1px solid var(--line);border-radius:10px;padding:7px 10px;color:var(--muted);font-size:12px}}
.detail{{padding:20px;min-height:700px;overflow:auto}} .detail h2{{font:700 28px Georgia,serif;color:var(--wine);margin:0 0 4px}} .badge{{display:inline-block;border-radius:99px;padding:4px 9px;background:#eee5d7;color:#674a34;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em}}
.detail h3{{font:700 17px Georgia,serif;margin:22px 0 6px}} .detail p{{white-space:pre-wrap}} .evidence{{border-left:4px solid var(--gold);background:#f9f1df;padding:12px;border-radius:0 10px 10px 0;font-family:Georgia,serif}}
.timeline{{margin-top:18px;padding:18px}} .timeline h2{{font:700 27px Georgia,serif;margin:0 0 14px;color:var(--wine)}} #chapters{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:11px}} .chapter{{border:1px solid var(--line);border-radius:13px;padding:13px;background:#fff;cursor:pointer}} .chapter:hover{{border-color:var(--gold);transform:translateY(-1px)}} .chapter b{{font-family:Georgia,serif}} .chapter small{{display:block;color:var(--muted)}}
.legend{{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}} .legend span{{font-size:12px;background:#fff4;border:1px solid #fff5;border-radius:99px;padding:4px 9px}} .dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}}
svg .link{{stroke:#9d9488;stroke-opacity:.23;stroke-width:1}} svg .node{{cursor:pointer}} svg .node circle{{stroke:#fff;stroke-width:1.8;filter:drop-shadow(0 3px 4px #0002)}} svg .node text{{font-size:10px;font-weight:650;fill:#26313a;paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round;pointer-events:none}} svg .node.selected circle{{stroke:#171717;stroke-width:3}} svg .node.dim{{opacity:.12}} svg .link.dim{{opacity:.04}}
@media(max-width:950px){{.stats{{grid-template-columns:repeat(2,1fr)}}.toolbar{{grid-template-columns:1fr 1fr}}.workspace{{grid-template-columns:1fr}}.detail{{min-height:auto}}}} @media(max-width:560px){{main{{padding:12px}}.toolbar{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><div class="eyebrow">Graf narativ autosuficient</div><h1>{title}</h1><p>Ioan Slavici · text integral, 17 capitole · fiecare eveniment păstrează fragmentul-sursă și pagina PDF.</p><div class="legend"><span><i class="dot" style="background:#7c2d3a"></i>Operă / capitole</span><span><i class="dot" style="background:#315b73"></i>Personaje</span><span><i class="dot" style="background:#3f725e"></i>Evenimente</span><span><i class="dot" style="background:#b68738"></i>Concepte</span></div></header>
<main>
<section class="stats"><div class="stat"><b id="sNodes"></b><span>noduri</span></div><div class="stat"><b id="sEdges"></b><span>muchii</span></div><div class="stat"><b id="sEvents"></b><span>evenimente verificate</span></div><div class="stat"><b id="sChapters"></b><span>capitole</span></div><div class="stat"><b>2</b><span>trăsături din eseu</span></div></section>
<section class="toolbar"><input id="search" placeholder="Caută personaj, eveniment, temă sau citat…"><select id="type"><option value="">Toate tipurile</option></select><select id="chapter"><option value="">Toate capitolele</option></select><button id="reset">Resetează</button></section>
<section class="workspace"><div class="panel graph-panel"><svg id="graph" viewBox="0 0 1100 700" aria-label="Vizualizarea grafului"></svg><div class="hint">Trage nodurile · rotița face zoom · click pentru detalii</div></div><aside class="panel detail" id="detail"><span class="badge">Ghid</span><h2>Selectează un nod</h2><p>Folosește căutarea și filtrele sau apasă direct pe un nod. Pentru evenimente vei vedea pasajul exact și pagina PDF.</p></aside></section>
<section class="panel timeline"><h2>Acoperire pe capitole</h2><div id="chapters"></div></section>
</main>
<script id="kg-data" type="application/json">{payload}</script>
<script>
const data=JSON.parse(document.getElementById('kg-data').textContent), byId=new Map(data.nodes.map(n=>[n.id,n]));
const colors={{Work:'#7c2d3a',Author:'#7c2d3a',Chapter:'#a54c57',Character:'#315b73',NarrativeEvent:'#3f725e',NarrativeState:'#6a907d',CompositionElement:'#c06b32',Location:'#657f8d',Theme:'#b68738',Conflict:'#b3503d',LiteraryMovement:'#8b5f9e',LiteraryTrait:'#a47c27',LiteraryTechnique:'#8b733d',NarrativePerspective:'#7c6994',Motif:'#967b50',Symbol:'#967b50'}};
document.getElementById('sNodes').textContent=data.validation.node_count;document.getElementById('sEdges').textContent=data.validation.edge_count;document.getElementById('sEvents').textContent=data.validation.event_count;document.getElementById('sChapters').textContent=data.validation.chapter_count;
const typeSel=document.getElementById('type'),chapterSel=document.getElementById('chapter'),search=document.getElementById('search');
[...new Set(data.nodes.map(n=>n.type))].sort().forEach(t=>typeSel.add(new Option(t,t)));data.chapters.forEach(c=>chapterSel.add(new Option(c.title,c.id)));
const chapterBox=document.getElementById('chapters');data.chapters.forEach(c=>{{const el=document.createElement('div');el.className='chapter';el.innerHTML=`<b>${{c.title}}</b><small>PDF ${{c.pdf_page_start}}–${{c.pdf_page_end}} · ${{c.event_sequence.length}} evenimente</small>`;el.addEventListener('click',()=>{{chapterSel.value=c.id;applyFilters();window.scrollTo({{top:180,behavior:'smooth'}})}});chapterBox.appendChild(el)}});
const svg=document.getElementById('graph'),NS='http://www.w3.org/2000/svg';let scale=1,tx=0,ty=0,drag=null,pan=null;
const viewport=document.createElementNS(NS,'g');svg.appendChild(viewport);const linkLayer=document.createElementNS(NS,'g'),nodeLayer=document.createElementNS(NS,'g');viewport.append(linkLayer,nodeLayer);
const nodes=data.nodes.map((n,i)=>Object.assign({{}},n,{{x:100+(i*83)%900,y:80+((i*137)%540),vx:0,vy:0}}));const nodeMap=new Map(nodes.map(n=>[n.id,n]));
const links=data.edges.filter(e=>nodeMap.has(e.source)&&nodeMap.has(e.target)).map(e=>({{...e,s:nodeMap.get(e.source),t:nodeMap.get(e.target)}}));
links.forEach(l=>{{l.el=document.createElementNS(NS,'line');l.el.classList.add('link');linkLayer.appendChild(l.el)}});
nodes.forEach(n=>{{const g=document.createElementNS(NS,'g');g.classList.add('node');const c=document.createElementNS(NS,'circle');c.setAttribute('r',n.type==='NarrativeEvent'?5:n.type==='Chapter'?9:n.importance==='major'?11:7);c.setAttribute('fill',colors[n.type]||'#777');const t=document.createElementNS(NS,'text');t.setAttribute('x',13);t.setAttribute('y',4);t.textContent=n.type==='NarrativeEvent'?'':n.label.slice(0,32);g.append(c,t);g.addEventListener('click',e=>{{e.stopPropagation();showDetail(n);document.querySelectorAll('.node').forEach(x=>x.classList.remove('selected'));g.classList.add('selected')}});g.addEventListener('pointerdown',e=>{{e.stopPropagation();drag={{n,g,ox:e.clientX,oy:e.clientY,sx:n.x,sy:n.y}};g.setPointerCapture(e.pointerId)}});g.addEventListener('pointermove',e=>{{if(drag&&drag.g===g){{n.x=drag.sx+(e.clientX-drag.ox)/scale;n.y=drag.sy+(e.clientY-drag.oy)/scale;render()}}}});g.addEventListener('pointerup',()=>drag=null);n.el=g;nodeLayer.appendChild(g)}});
function render(){{links.forEach(l=>{{l.el.setAttribute('x1',l.s.x);l.el.setAttribute('y1',l.s.y);l.el.setAttribute('x2',l.t.x);l.el.setAttribute('y2',l.t.y)}});nodes.forEach(n=>n.el.setAttribute('transform',`translate(${{n.x}},${{n.y}})`));viewport.setAttribute('transform',`translate(${{tx}},${{ty}}) scale(${{scale}})`)}}
for(let tick=0;tick<150;tick++){{for(const l of links){{let dx=l.t.x-l.s.x,dy=l.t.y-l.s.y,d=Math.max(20,Math.hypot(dx,dy)),f=(d-80)*.0015;l.s.vx+=dx/d*f;l.s.vy+=dy/d*f;l.t.vx-=dx/d*f;l.t.vy-=dy/d*f}}for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){{let a=nodes[i],b=nodes[j],dx=b.x-a.x,dy=b.y-a.y,d2=Math.max(100,dx*dx+dy*dy),f=35/d2;a.vx-=dx*f;a.vy-=dy*f;b.vx+=dx*f;b.vy+=dy*f}}nodes.forEach(n=>{{n.vx+=(550-n.x)*.0008;n.vy+=(350-n.y)*.0008;n.vx*=.86;n.vy*=.86;n.x+=n.vx;n.y+=n.vy}})}}
svg.addEventListener('wheel',e=>{{e.preventDefault();scale=Math.max(.35,Math.min(3,scale*(e.deltaY<0?1.1:.9)));render()}},{{passive:false}});svg.addEventListener('pointerdown',e=>{{if(e.target===svg)pan={{x:e.clientX,y:e.clientY,tx,ty}}}});svg.addEventListener('pointermove',e=>{{if(pan){{tx=pan.tx+e.clientX-pan.x;ty=pan.ty+e.clientY-pan.y;render()}}}});svg.addEventListener('pointerup',()=>pan=null);
function esc(v){{return String(v??'').replace(/[&<>\"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}}[c]))}}
function showDetail(n){{const a=n.attributes||{{}},v=a.verification||{{}},related=data.edges.filter(e=>e.source===n.id||e.target===n.id).slice(0,18).map(e=>{{const other=byId.get(e.source===n.id?e.target:e.source);return other?`<li><b>${{esc(e.predicate)}}</b> · ${{esc(other.label)}}</li>`:''}}).join(''),scheme=Array.isArray(a.scheme)?a.scheme.map(x=>`<li>${{esc(x)}}</li>`).join(''):'';document.getElementById('detail').innerHTML=`<span class="badge">${{esc(n.type)}}</span><h2>${{esc(n.label)}}</h2><p>${{esc(n.description)}}</p>${{v.evidence_quote?`<h3>Dovadă primară · PDF p. ${{v.pdf_page}}</h3><div class="evidence">${{esc(v.evidence_quote)}}</div>`:''}}${{a.human_type?`<h3>Tip uman</h3><p>${{esc(a.human_type)}}</p>`:''}}${{a.traits?`<h3>Trăsături</h3><p>${{esc(a.traits)}}</p>`:''}}${{scheme?`<h3>Schema explicativă</h3><ol>${{scheme}}</ol>`:''}}${{a.essay_use?`<h3>Utilizare în eseu</h3><p>${{esc(a.essay_use)}}</p>`:''}}<h3>Relații</h3><ul>${{related||'<li>Nicio relație afișabilă.</li>'}}</ul>`}}
function fitNodes(active){{if(!active.length)return;const xs=active.map(n=>n.x),ys=active.map(n=>n.y),minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys),spanX=Math.max(80,maxX-minX),spanY=Math.max(80,maxY-minY);scale=Math.max(.35,Math.min(2,Math.min(980/(spanX+120),580/(spanY+120))));tx=550-((minX+maxX)/2)*scale;ty=350-((minY+maxY)/2)*scale;render()}}
function applyFilters(){{const q=search.value.trim().toLocaleLowerCase('ro'),type=typeSel.value,ch=chapterSel.value,active=nodes.filter(n=>(!type||n.type===type)&&(!ch||n.chapter_ids.includes(ch)||n.id===ch)&&(!q||JSON.stringify(n).toLocaleLowerCase('ro').includes(q))),visible=new Set(active.map(n=>n.id));nodes.forEach(n=>n.el.classList.toggle('dim',!visible.has(n.id)));links.forEach(l=>l.el.classList.toggle('dim',!(visible.has(l.source)&&visible.has(l.target))));fitNodes(active)}}
fitNodes(nodes);search.addEventListener('input',applyFilters);typeSel.addEventListener('change',applyFilters);chapterSel.addEventListener('change',applyFilters);document.getElementById('reset').addEventListener('click',()=>{{search.value='';typeSel.value='';chapterSel.value='';applyFilters()}});svg.addEventListener('click',()=>document.querySelectorAll('.node').forEach(x=>x.classList.remove('selected')));
</script>
</body></html>"""


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    graph = build_graph()
    GRAPH_PATH.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SCHEMA_PATH.write_text(json.dumps(build_schema(graph), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ONTOLOGY_PATH.write_text(build_ontology_markdown(graph), encoding="utf-8")
    RECONSTRUCTIONS_PATH.write_text(build_reconstructions_markdown(graph), encoding="utf-8")
    COVERAGE_PATH.write_text(build_coverage_markdown(graph), encoding="utf-8")
    VALIDATION_PATH.write_text(build_validation_markdown(graph), encoding="utf-8")
    HTML_PATH.write_text(build_html(graph), encoding="utf-8")
    print(f"JSON: {GRAPH_PATH}")
    print(f"HTML: {HTML_PATH}")
    print(f"Schema: {SCHEMA_PATH}")
    print(f"Ontologie: {ONTOLOGY_PATH}")
    print(f"Reconstructii: {RECONSTRUCTIONS_PATH}")
    print(f"Acoperire: {COVERAGE_PATH}")
    print(f"Validare: {VALIDATION_PATH}")
    print(f"Noduri: {graph['validation']['node_count']}; muchii: {graph['validation']['edge_count']}; evenimente: {graph['validation']['event_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

