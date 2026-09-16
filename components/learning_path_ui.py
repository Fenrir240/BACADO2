from pathlib import Path
import json
import hashlib
import math
import random
import re
import textwrap

import streamlit as st
import streamlit.components.v1 as components

from components.ai_status_ui import ai_thinking

from services.annotation_service import (
    get_scene_annotations,
    save_scene_annotations,
)
from services.notes_service import (
    create_note,
    delete_note,
    get_notes,
    update_note,
)
from services.composition_service import load_composition_schemas
from services.literary_current_service import (
    literary_current_reader_text,
    load_literary_current,
)
from services.understanding_service import load_relevant_sequences
from services.flashcard_learning_service import (
    choose_next_flashcard,
    create_flashcard_session,
    get_flashcard_stats,
    get_mastered_card_ids,
    load_flashcard_deck,
    record_flashcard_outcome,
    register_session_outcome,
)
from services.exercise_bank_service import (
    choose_prebuilt_exercise,
    multiple_choice_test_items,
    quick_testing_available,
)
from services.progress_service import (
    award_quick_flashcard_point,
    award_quick_exercise_points,
    award_quick_test_points,
    get_characters_ai_progress,
    get_work_progress,
    mark_summary_done,
    update_composition_selection,
    update_characters_ai_progress,
    update_summary_quiz_score,
)

try:
    from services.ai_service import (
        answer_characters_teacher_turn,
        answer_learning_context_question,
        explain_learning_context_term,
    )
except ImportError:
    answer_characters_teacher_turn = None
    answer_learning_context_question = None
    explain_learning_context_term = None


SUMMARY_BY_WORK = {
    "ion": Path("data/sources/ion/rezumat-qwen-pe-capitole.md"),
}


SCENE_ANNOTATOR_COMPONENT = components.declare_component(
    "scene_annotator_v2",
    path=str(Path(__file__).parent / "scene_annotator_component"),
)

MATCHING_EXERCISE_COMPONENT = components.declare_component(
    "matching_exercise",
    path=str(Path(__file__).parent / "matching_exercise_component"),
)

CHRONOLOGY_EXERCISE_COMPONENT = components.declare_component(
    "chronology_exercise",
    path=str(Path(__file__).parent / "chronology_exercise_component"),
)

COMPLETION_EXERCISE_COMPONENT = components.declare_component(
    "completion_exercise",
    path=str(Path(__file__).parent / "completion_exercise_component"),
)

FLASHCARD_COMPONENT = components.declare_component(
    "learning_flashcard",
    path=str(Path(__file__).parent / "flashcard_component"),
)


SUMMARY_EXERCISES_BY_WORK = {
    "ion": [
        {
            "question": "Care este dorinta care il domina pe Ion pe parcursul romanului?",
            "options": [
                "Dorinta de a obtine pamant si statut in sat.",
                "Dorinta de a pleca definitiv din Pripas.",
                "Dorinta de a deveni invatator.",
                "Dorinta de a se impaca rapid cu George.",
            ],
            "answer": "Dorinta de a obtine pamant si statut in sat.",
        },
        {
            "question": "De ce se apropie Ion de Ana?",
            "options": [
                "Pentru ca Ana este fiica lui Vasile Baciu si poate aduce pamant.",
                "Pentru ca Ana il invata sa citeasca.",
                "Pentru ca Ana este sustinuta de familia Herdelea.",
                "Pentru ca George ii cere sa se apropie de ea.",
            ],
            "answer": "Pentru ca Ana este fiica lui Vasile Baciu si poate aduce pamant.",
        },
        {
            "question": "Ce se schimba dupa casatoria lui Ion cu Ana?",
            "options": [
                "Ion nu devine mai bun, ci o trateaza pe Ana cu raceala si violenta.",
                "Ion renunta la pamant si traieste linistit cu Ana.",
                "Vasile Baciu il accepta imediat ca pe un fiu.",
                "George paraseste satul si conflictul se incheie.",
            ],
            "answer": "Ion nu devine mai bun, ci o trateaza pe Ana cu raceala si violenta.",
        },
        {
            "question": "Ce arata scena sarutarii pamantului?",
            "options": [
                "Cat de puternica si dezumanizanta este obsesia lui Ion pentru pamant.",
                "Impacarea lui Ion cu Ana.",
                "Respectul lui Ion fata de familia Herdelea.",
                "Finalul conflictului erotic.",
            ],
            "answer": "Cat de puternica si dezumanizanta este obsesia lui Ion pentru pamant.",
        },
        {
            "question": "Ce rol are Florica in firul narativ?",
            "options": [
                "Este iubirea fata de care Ion ramane atras, desi o sacrifica pentru pamant.",
                "Este sora Anei si mostenitoarea lui Vasile Baciu.",
                "Este cea care il convinge pe Ion sa renunte la avere.",
                "Este personajul care conduce satul.",
            ],
            "answer": "Este iubirea fata de care Ion ramane atras, desi o sacrifica pentru pamant.",
        },
        {
            "question": "Ce sugereaza finalul romanului?",
            "options": [
                "Alegerile lui Ion au consecinte tragice si nu ii aduc implinirea dorita.",
                "Ion obtine fericirea deplina prin pamant.",
                "Ana si Ion se impaca definitiv.",
                "Conflictul social dispare din sat.",
            ],
            "answer": "Alegerile lui Ion au consecinte tragice si nu ii aduc implinirea dorita.",
        },
    ]
}


ION_SIGNIFICANT_SEQUENCES = [
    {
        "id": "cositul",
        "button_label": "Secvența 1",
        "title": "Cositul",
        "chapter": "Capitolul al II-lea, „Zvârcolirea”",
        "source": "Liviu Rebreanu, „Ion”, Glasul pământului",
        "text": """
Flăcăul sosi încălzit de drum. Se opri în marginea delniței, pe răzorul ce-o despărțea de altă fâneață, tot așa de lungă și de lată, pe care Toma Bulbuc o cumpărase acum vreo zece ani de la Glanetașu. Cu o privire setoasă, Ion cuprinse tot locul, cântărindu-l. Simțea o plăcere atât de mare văzându-și pământul, încât îi venea să cadă în genunchi și să-l îmbrățișeze. I se părea mai frumos, pentru că era al lui. Iarba deasă, grasă, presărată cu trifoi, unduia ostenită de răcoarea dimineții. Nu se putu stăpâni. Rupse un smoc de fire și le mototoli pătimaș în palme.

Se așeză pe răzor, înțepeni nicovala în pământ, potrivi tăișul coasei și apoi începu a-l bate cu ciocanul, rar, apăsat, cu ochii țintă la oțelul argintiu. Când isprăvi, se sculă, scoase de la brâu gresia, o înmuia bine în apa din toc și apoi mângâia ascuțișul coasei cu gresia, schimbând mereu degetele mânei stângi. Pe urmă, cu un pumn de iarbă, șterse toată coasa. În clipa aceea privirea i se odihnea pe delnița lui Toma Bulbuc, cosită, cu fânul adunat în căpițe, care stăteau încremenite ici-colo, ca niște mormoloci speriați. Pământul negru-gălbui părea un obraz mare ras de curând. Privindu-l, Ion oftă, murmură!... - Locul nostru, săracul!...

Sub sărutarea zorilor tot pământul, crestat în mii de frânturi, după toanele sau nevoile atâtor suflete moarte și vii, părea că respiră și trăiește. Porumbiștile, holdele de grâu și de ovăz, cânepiștile, grădinile, casele, pădurile, toate zumzeau, șușoteau, fâșâiau, vorbind un grai aspru, înțelegându-se și bucurându-se de lumina ce se aprindea din ce în ce mai biruitoare și roditoare. Glasul pământului pătrundea năvalnic în sufletul flăcăului, ca o chemare, copleșindu-l. Se simți mic și slab, cât un vierme pe care-l calci în picioare sau ca o frunză pe care vântul o vâltorește cum îi place. Suspină prelung, umilit și înfricoșat în fața uriașului: - Cât pământ, Doamne!...

În același timp însă iarba tăiată și udă parcă începea să i se zvârcolească sub picioare. Un fir îl înțepa în gleznă, din sus de opincă. Brazda culcată îl privea, neputincioasă, biruită, umplându-i inima deodată cu o mândrie de stăpân. Și atunci se văzu crescând din ce în ce mai mare. Vâjâiturile stranii păreau niște cântece de închinare. Sprijinit în coasă, pieptul i se umflă, spinarea i se îndreptă, iar ochii i se aprinseră într-o lucire de izbândă. Se simțea atât de puternic încât să domnească peste tot cuprinsul...

Totuși în fundul inimii lui rodea ca un cariu părerea de rău că din atâta hotar el nu stăpânește decât două-trei crâmpeie, pe când toată ființa lui arde de dorul de-a avea pământ, mult, cât mai mult...

Iubirea pământului l-a stăpânit de mic copil. Veșnic a pizmuit pe cei bogați și veșnic s-a înarmat într-o hotărâre pătimașă: «trebuie să aibă pământ mult, trebuie»! De pe atunci pământul i-a fost mai drag ca o mamă.
""".strip(),
    },
    {
        "id": "sarutarea",
        "button_label": "Secvența 2",
        "title": "Sărutarea pământului",
        "chapter": "Capitolul al IX-lea, „Sărutarea”",
        "source": "Liviu Rebreanu, „Ion”, Glasul iubirii",
        "text": """
Vremea se dezmorțea. Iarna, istovită ca o babă răutăcioasă, se zgârcea mereu, simțind apropierea primăverii din ce în ce mai dezmierdătoare. Haina de zăpadă se zdrențuia dezvelind trupul negru al câmpurilor...

Ion de-abia așteptase zilele acestea. Acuma, stăpân al tuturor pământurilor, râvnea să le vază, să le mângâie ca pe niște ibovnice credincioase. Ascunse sub troenele de omăt, degeaba le cercetase. Dragostea lui avea nevoie de inima moșiei. Dorea să simtă lutul sub picioare, să i se agațe de opinci, să-i soarbă mirosul, să-și umple ochii de culoarea lui îmbătătoare...

Ieși singur, cu mâna goală, în straie de sărbătoare, într-o Luni. Sui drept în Lunci, unde era porumbiștea cea mai mare și mai bună, pe spinarea dealului... Cu cât se apropia, cu atât vedea mai bine cum s-a dezbrăcat de zăpadă locul ca o fată frumoasă care și-ar fi lepădat cămașa arătându-și corpul gol, ispititor...

Sufletul îi era pătruns de fericire. Parcă nu mai râvnea nimic și nici nu mai era nimic în lume afară de fericirea lui. Pământul se închina în fața lui, tot pământul... Și tot era al lui, numai al lui acuma...

Se opri în mijlocul delniței. Lutul negru, lipicios îi țintuia picioarele, îngreunându-le, atrăgându-l ca brațele unei iubite pătimașe. Îi râdeau ochii, iar fața toată îi era scăldată într-o sudoare caldă de patimă. Îl cuprinse o poftă sălbatecă să îmbrățișeze huma, să o crâmpoțească în sărutări. Întinse mâinile spre brazdele drepte, zgrunțuroase și umede. Mirosul acru, proaspăt și roditor îi aprindea sângele.

Se aplecă, luă în mâini un bulgăre și-l sfărâmă între degete cu o plăcere înfricoșată. Mâinile îi rămaseră unse cu lutul cleios ca niște mănuși de doliu. Sorbi mirosul, frecându-și palmele.

Apoi încet, cucernic, fără să-și dea seama, se lăsă în genunchi, își coborî fruntea și-și lipi buzele cu voluptate pe pământul ud. Și-n sărutarea aceasta grăbită simți un fior rece, amețitor...

Se ridică deodată rușinat și se uită împrejur să nu-l fi văzut cineva. Fața însă îi zâmbea de o plăcere nesfârșită.

Își încrucișa brațele pe piept și-și linse buzele simțind neîncetat atingerea rece și dulceața amară a pământului. Satul, în vale, departe, părea un cuib de păsări ascuns în văgăună de frica uliului.

Se vedea acum mare și puternic ca un uriaș din basme care a biruit, în lupte grele, o ceată de balauri îngrozitori.

Își înfipse mai bine picioarele în pământ, ca și când ar fi vrut să potolească cele din urmă zvârcoliri ale unui dușman doborât. Și pământul parcă se clătina, se închina în fața lui...
""".strip(),
    },
]


ION_CHARACTER_GROUPS = [
    {
        "title": "Autoritati si intelectualitatea satului",
        "caption": "Au prestigiu cultural, religios sau administrativ, dar depind de tensiunile comunitatii.",
        "characters": [
            {
                "id": "preotul_belciug",
                "name": "Preotul Belciug",
                "short_role": "autoritate religioasa",
                "physical": "Romanul il individualizeaza mai ales prin energie si autoritate, nu printr-un portret fizic amplu.",
                "traits": "Este hotarat, orgolios, perseverent si influent; poate fi rigid si conflictual.",
                "village_role": "Preotul satului, voce morala si institutie de putere in Pripas.",
                "human_type": "Reprezinta autoritatea bisericeasca implicata direct in viata sociala a satului.",
            },
            {
                "id": "zaharia_herdelea",
                "name": "Zaharia Herdelea",
                "short_role": "invatatorul satului",
                "physical": "Portretul fizic este secundar; personajul este definit mai ales social si moral.",
                "traits": "Este educat si bine intentionat, dar slab, temator si usor de compromis.",
                "village_role": "Invatatorul satului, prins intre datoria profesionala, familie si presiunile autoritatilor.",
                "human_type": "Intelectualul rural vulnerabil, cu prestigiu limitat si dependente sociale.",
            },
            {
                "id": "maria_herdelea",
                "name": "Maria Herdelea",
                "short_role": "sotia invatatorului",
                "physical": "Nu este construita prin detalii fizice memorabile, ci prin rolul familial.",
                "traits": "Este grijulie, practica si preocupata de stabilitatea casei.",
                "village_role": "Sustine familia Herdelea si participa la grijile materiale ale acesteia.",
                "human_type": "Mama si sotia din familia intelectualitatii rurale, atenta la reputatie si siguranta.",
            },
            {
                "id": "titu_herdelea",
                "name": "Titu Herdelea",
                "short_role": "tanar intelectual",
                "physical": "Aspectul fizic nu este esential; conteaza mai mult postura de tanar in formare.",
                "traits": "Este sensibil, ambitios, visator si atras de idei literare si nationale.",
                "village_role": "Fiul invatatorului, apropiat de lumea cartii si de observarea vietii satului.",
                "human_type": "Intelectualul tanar, in cautarea unei directii si a unei identitati.",
            },
            {
                "id": "laura_herdelea",
                "name": "Laura Herdelea",
                "short_role": "fiica invatatorului",
                "physical": "Este prezentata ca tanara de maritat; portretul fizic ramane discret.",
                "traits": "Este sensibila, influentata de familie si de conventiile sociale.",
                "village_role": "Fiica din familia Herdelea, legata de tema casatoriei si a statutului social.",
                "human_type": "Tanara din mediul intelectual rural, pentru care casatoria are miza sociala.",
            },
            {
                "id": "ghighi_herdelea",
                "name": "Ghighi Herdelea",
                "short_role": "fiica mai mica a invatatorului",
                "physical": "Portret fizic sumar; are rol mai mic decat Laura.",
                "traits": "Este tanara, familista si legata de atmosfera casei Herdelea.",
                "village_role": "Completeaza imaginea familiei invatatorului.",
                "human_type": "Personaj secundar care arata viata domestica a intelectualitatii rurale.",
            },
        ],
    },
    {
        "title": "Tarani instariti",
        "caption": "Pamantul le da statut, autoritate si putere de negociere in sat.",
        "characters": [
            {
                "id": "vasile_baciu",
                "name": "Vasile Baciu",
                "short_role": "taran bogat, tatal Anei",
                "physical": "Este conturat mai ales prin prezenta dura si prin autoritatea de om instarit.",
                "traits": "Este aspru, violent, orgolios si suspicios; isi apara averea cu agresivitate.",
                "village_role": "Taran bogat, tatal Anei, detinator al pamantului dorit de Ion.",
                "human_type": "Tatal autoritar si proprietarul care masoara valoarea oamenilor prin avere.",
            },
            {
                "id": "george_bulbuc",
                "name": "George Bulbuc",
                "short_role": "flacau instarit, rivalul lui Ion",
                "physical": "Este construit ca flacau puternic si potrivit pentru statutul sau social.",
                "traits": "Este mandru, posesiv si impulsiv, dar are si siguranta celui cu avere.",
                "village_role": "Rivalul social si erotic al lui Ion; este initial pretendent pentru Ana, apoi sotul Floricai.",
                "human_type": "Rivalul legitim social, sustinut de avere si de regulile satului.",
            },
        ],
    },
    {
        "title": "Tarani saraci",
        "caption": "Sunt oamenii pentru care lipsa pamantului inseamna umilinta si dependenta.",
        "characters": [
            {
                "id": "ion",
                "name": "Ion al Glanetasului",
                "short_role": "protagonist, taran sarac",
                "physical": "Este tanar, viguros, puternic si plin de energie; forta lui fizica sustine imaginea de taran harnic.",
                "traits": "Este harnic, inteligent si ambitios, dar si lacom, egoist, brutal si dominat de obsesia pamantului.",
                "village_role": "Fiu de tarani saraci, vrea pamant pentru respect si statut social.",
                "human_type": "Arivistul rural si taranul dominat de patima pamantului.",
            },
            {
                "id": "alexandru_glanetasu",
                "name": "Alexandru Glanetasu",
                "short_role": "tatal lui Ion",
                "physical": "Portretul fizic conteaza mai putin decat degradarea sociala a familiei.",
                "traits": "Este slab, neputincios si asociat cu risipirea averii familiei.",
                "village_role": "Taran sarac, tatal lui Ion, simbol al decaderii sociale.",
                "human_type": "Parintele care lasa copilului sentimentul umilintei si al lipsei de pamant.",
            },
            {
                "id": "zenobia",
                "name": "Zenobia",
                "short_role": "mama lui Ion",
                "physical": "Nu are un portret fizic amplu; este definita prin pozitia de mama saraca.",
                "traits": "Este simpla, supusa si legata de grijile casei.",
                "village_role": "Mama lui Ion, parte a familiei sarace Glanetasu.",
                "human_type": "Femeia saraca din sat, prinsa in lipsuri si neputinta.",
            },
            {
                "id": "florica",
                "name": "Florica",
                "short_role": "fata saraca iubita de Ion",
                "physical": "Este prezentata ca frumoasa si atragatoare, in contrast cu Ana.",
                "traits": "Are farmec, vitalitate si naturalete; ramane totusi prinsa in jocul dorintelor masculine.",
                "village_role": "Fata saraca pe care Ion o iubeste, dar pe care o sacrifica pentru pamant.",
                "human_type": "Iubirea autentica pierduta din cauza interesului social.",
            },
        ],
    },
    {
        "title": "Victime si personaje prinse intre familii",
        "caption": "Arata consecintele presiunii sociale, ale casatoriei si ale luptei pentru avere.",
        "characters": [
            {
                "id": "ana",
                "name": "Ana",
                "short_role": "fiica lui Vasile Baciu",
                "physical": "Nu este idealizata ca frumusete; este prezentata mai ales ca fragila, timida si vulnerabila.",
                "traits": "Este sensibila, supusa si insetata de afectiune; slabiciunea ei este dependenta de iubirea lui Ion.",
                "village_role": "Fiica unui taran bogat, devine mijlocul prin care Ion incearca sa obtina pamant.",
                "human_type": "Victima inocenta a interesului pentru avere si a violentei patriarhale.",
            },
            {
                "id": "savista",
                "name": "Savista",
                "short_role": "personaj marginal",
                "physical": "Este marcata de vulnerabilitate fizica si de pozitia marginala in comunitate.",
                "traits": "Este observatoare, curioasa si legata de circulatia vestilor din sat.",
                "village_role": "Personaj secundar care contribuie la tensiunea sociala si la dezvaluirea unor relatii ascunse.",
                "human_type": "Martor marginal al satului, important prin ce vede si transmite.",
            },
        ],
    },
]


CHARACTER_BY_ID = {
    character["id"]: character
    for group in ION_CHARACTER_GROUPS
    for character in group["characters"]
}


ION_TREE_LAYOUT = {
    "root": {"label": "Satul Pripas", "x": 500, "y": 46},
    "groups": [
        {
            "label": "Autoritati / intelectuali",
            "x": 170,
            "y": 145,
            "character_ids": [
                "preotul_belciug",
                "zaharia_herdelea",
                "maria_herdelea",
                "titu_herdelea",
                "laura_herdelea",
                "ghighi_herdelea",
            ],
        },
        {
            "label": "Tarani instariti",
            "x": 405,
            "y": 145,
            "character_ids": ["vasile_baciu", "george_bulbuc"],
        },
        {
            "label": "Tarani saraci",
            "x": 635,
            "y": 145,
            "character_ids": ["ion", "alexandru_glanetasu", "zenobia", "florica"],
        },
        {
            "label": "Victime / marginali",
            "x": 845,
            "y": 145,
            "character_ids": ["ana", "savista"],
        },
    ],
    "characters": {
        "preotul_belciug": {"x": 55, "y": 255},
        "zaharia_herdelea": {"x": 140, "y": 255},
        "maria_herdelea": {"x": 225, "y": 255},
        "titu_herdelea": {"x": 95, "y": 370},
        "laura_herdelea": {"x": 180, "y": 370},
        "ghighi_herdelea": {"x": 265, "y": 370},
        "vasile_baciu": {"x": 360, "y": 270},
        "george_bulbuc": {"x": 455, "y": 270},
        "ion": {"x": 610, "y": 260},
        "alexandru_glanetasu": {"x": 525, "y": 375},
        "zenobia": {"x": 620, "y": 375},
        "florica": {"x": 715, "y": 375},
        "ana": {"x": 805, "y": 270},
        "savista": {"x": 900, "y": 270},
    },
}


ION_RELATION_GRAPH = {
    "nodes": {
        "ion": {"label": "Ion", "x": 500, "y": 285, "group": "central"},
        "ana": {"label": "Ana", "x": 365, "y": 235, "group": "victim"},
        "florica": {"label": "Florica", "x": 635, "y": 230, "group": "poor"},
        "george_bulbuc": {"label": "George", "x": 765, "y": 305, "group": "rich"},
        "vasile_baciu": {"label": "Vasile Baciu", "x": 245, "y": 195, "group": "rich"},
        "alexandru_glanetasu": {"label": "Al. Glanetasu", "x": 310, "y": 380, "group": "poor"},
        "zenobia": {"label": "Zenobia", "x": 445, "y": 410, "group": "poor"},
        "zaharia_herdelea": {"label": "Z. Herdelea", "x": 435, "y": 95, "group": "intellectual"},
        "titu_herdelea": {"label": "Titu", "x": 575, "y": 105, "group": "intellectual"},
        "preotul_belciug": {"label": "Belciug", "x": 270, "y": 85, "group": "authority"},
        "savista": {"label": "Savista", "x": 815, "y": 170, "group": "witness"},
    },
    "edges": [
        {
            "source": "ion",
            "target": "ana",
            "title": "Ion - Ana",
            "text": "Relație construită pe interes, nu pe iubire. Ana îl iubește și caută afecțiune, în timp ce Ion o vede mai ales ca drum spre pământul lui Vasile Baciu. După căsătorie, raportul devine rece și violent, iar Ana ajunge victima obsesiei lui Ion.",
        },
        {
            "source": "ion",
            "target": "florica",
            "title": "Ion - Florica",
            "text": "Între ei există atracție autentică, dar Ion o sacrifică pe Florica pentru statut și pământ. Florica rămâne asociată cu iubirea firească, însă relația reaprinsă după căsătoriile lor distruge echilibrul social și duce la conflictul final.",
        },
        {
            "source": "ion",
            "target": "george_bulbuc",
            "title": "Ion - George",
            "text": "Sunt rivali sociali și erotici. George are avere și poziție, Ion are ambiție și dorință de ascensiune. Rivalitatea trece de la Ana la Florica și se transformă în ură, culminând cu uciderea lui Ion.",
        },
        {
            "source": "ion",
            "target": "vasile_baciu",
            "title": "Ion - Vasile Baciu",
            "text": "Relația este dominată de conflictul pentru pământ. Vasile îl disprețuiește pe Ion ca flăcău sărac, iar Ion îl vede ca obstacol și sursă a averii dorite. Căsătoria cu Ana devine o luptă de negociere și forță.",
        },
        {
            "source": "ana",
            "target": "vasile_baciu",
            "title": "Ana - Vasile Baciu",
            "text": "Relație tată-fiică marcată de autoritate și violență. Vasile își apără averea și o tratează pe Ana ca pe o miză socială. Ana se simte lipsită de sprijin, ceea ce o face vulnerabilă în fața lui Ion.",
        },
        {
            "source": "ana",
            "target": "george_bulbuc",
            "title": "Ana - George",
            "text": "George este pretendentul potrivit social pentru Ana, fiind flăcău înstărit. Pentru Ana însă, relația nu are forța iubirii pentru Ion. Legătura arată presiunea satului de a uni familii după avere și statut.",
        },
        {
            "source": "george_bulbuc",
            "target": "florica",
            "title": "George - Florica",
            "text": "Căsătoria lor pare o așezare socială, dar este umbrită de atracția dintre Florica și Ion. George ajunge să o privească pe Florica prin suspiciune și posesivitate, iar gelozia lui declanșează pedeapsa finală.",
        },
        {
            "source": "savista",
            "target": "florica",
            "title": "Savista - Florica",
            "text": "Savista funcționează ca martor marginal al lumii satului. În raport cu Florica, ea observă și transmite tensiuni ascunse, contribuind la expunerea relațiilor care amenință ordinea comunității.",
        },
        {
            "source": "savista",
            "target": "george_bulbuc",
            "title": "Savista - George",
            "text": "Legătura lor este importantă prin circulația veștilor. Savista amplifică suspiciunile și îl împinge pe George spre confirmarea trădării, devenind o piesă discretă în mecanismul conflictului final.",
        },
        {
            "source": "ion",
            "target": "alexandru_glanetasu",
            "title": "Ion - Alexandru Glanetasu",
            "text": "Relație tată-fiu marcată de rușinea sărăciei. Ion vede în tatăl său imaginea decăderii și a neputinței, iar această moștenire îi alimentează dorința obsesivă de pământ și respect.",
        },
        {
            "source": "ion",
            "target": "zenobia",
            "title": "Ion - Zenobia",
            "text": "Zenobia aparține familiei sărace din care Ion vrea să se ridice. Relația arată presiunea casei sărace și lipsa de sprijin real; Ion își proiectează salvarea în pământ, nu în familie.",
        },
        {
            "source": "ion",
            "target": "zaharia_herdelea",
            "title": "Ion - Zaharia Herdelea",
            "text": "Herdelea reprezintă intelectualitatea satului, iar Ion caută uneori sprijin sau validare în această zonă. Relația arată contactul dintre țăranul ambițios și autoritatea culturală fragilă a satului.",
        },
        {
            "source": "zaharia_herdelea",
            "target": "preotul_belciug",
            "title": "Zaharia Herdelea - Belciug",
            "text": "Relația este tensionată de orgoliu, autoritate și poziție socială. Belciug are forță morală și instituțională, iar Herdelea este vulnerabil în fața presiunilor comunității și ale autorităților.",
        },
        {
            "source": "zaharia_herdelea",
            "target": "titu_herdelea",
            "title": "Zaharia Herdelea - Titu",
            "text": "Relație tată-fiu din familia intelectualității rurale. Titu privește satul cu sensibilitate și aspirații culturale, iar Herdelea reflectă grijile practice ale statutului social și ale supraviețuirii.",
        },
        {
            "source": "ion",
            "target": "titu_herdelea",
            "title": "Ion - Titu Herdelea",
            "text": "Titu observă lumea satului și îl privește pe Ion ca pe un caz reprezentativ al energiei țărănești. Relația lor pune față în față acțiunea brutală a lui Ion și perspectiva intelectualului tânăr.",
        },
    ],
}


def _legacy_ion_character_mindmaps() -> dict:
    return {
        "characters": CHARACTER_BY_ID,
        "groups": ION_CHARACTER_GROUPS,
        "tree_layout": ION_TREE_LAYOUT,
        "relation_graph": {"central_node_id": "ion", **ION_RELATION_GRAPH},
    }


def _load_character_mindmaps(work_id: str) -> dict:
    path = (
        Path("data")
        / "generated_works"
        / work_id
        / "intelegere-opera"
        / "personaje-mindmaps.json"
    )
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            required = {"characters", "groups", "tree_layout", "relation_graph"}
            if isinstance(payload, dict) and required.issubset(payload):
                return payload
        except (OSError, json.JSONDecodeError):
            pass
    if work_id == "ion":
        return _legacy_ion_character_mindmaps()
    raise FileNotFoundError(
        f"Mind-mapurile pentru {work_id} nu au fost generate încă."
    )


def _generated_character_mindmaps_path(work_id: str) -> Path:
    return (
        Path("data")
        / "generated_works"
        / work_id
        / "intelegere-opera"
        / "personaje-mindmaps.json"
    )


def _summary_path_for_work(work_id: str) -> Path | None:
    configured = SUMMARY_BY_WORK.get(work_id)
    if configured is not None:
        return configured
    source_dir = Path("data") / "sources" / work_id
    for filename in ("rezumat-pe-capitole.md", "rezumat-qwen-pe-capitole.md"):
        candidate = source_dir / filename
        if candidate.is_file():
            return candidate
    generated_dir = Path("data") / "generated_works" / work_id / "intelegere-opera"
    for filename in ("rezumat-pe-capitole.md", "rezumat-qwen-pe-capitole.md", "toata-opera.json"):
        candidate = generated_dir / filename
        if candidate.is_file():
            return candidate
    return None


def render_learning_path(work: dict, progress: dict) -> None:
    if (
        _summary_path_for_work(work["id"]) is None
        and not _generated_character_mindmaps_path(work["id"]).is_file()
    ):
        st.info(
            "Conținutul pentru Înțelegerea operei nu a fost încă generat. "
            "Rulează pipeline-ul pe knowledge graph-ul acestei opere."
        )
        return

    steps = _get_learning_steps(progress)
    selected_step = _get_selected_step(work["id"])

    if selected_step not in {step["id"] for step in steps}:
        selected_step = "summary"
        _set_selected_step(work["id"], selected_step)

    _render_step_menu(work, progress, selected_step)

    if selected_step == "summary":
        _render_summary_step(work, progress)
    elif selected_step == "literary_current":
        _render_literary_current_step(work, progress)
    elif selected_step == "characters":
        _render_characters_step(work, progress)
    elif selected_step == "scenes":
        _render_scenes_step(work, progress)
    elif selected_step == "structure":
        _render_composition_step(work, progress)
    else:
        _render_locked_or_placeholder(selected_step, progress)

def render_quick_test(work: dict, progress: dict) -> None:
    """Render the compact three-panel revision workspace."""
    st.markdown('<div class="quick-test-marker"></div>', unsafe_allow_html=True)

    if not quick_testing_available(work["id"]):
        st.info(
            "Testarea rapidă nu a fost încă generată pentru această operă. "
            "Rulează pipeline-ul testare-rapida pe knowledge graph-ul ei."
        )
        return

    flashcards_col, exercises_col, tests_col = st.columns([1, 1.28, 1], gap="medium")

    with flashcards_col:
        _render_quick_flashcards(work)
    with exercises_col:
        _render_quick_exercises(work)
    with tests_col:
        _render_quick_tests(work)


def _quick_exercise_award_id(
    work_id: str,
    exercise_type: str,
    exercise_data: object,
) -> str:
    """Create a stable ID so the same exercise cannot award progress twice."""
    payload = json.dumps(exercise_data, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{work_id}:{exercise_type}:{digest}"


def _render_quick_flashcards(work: dict) -> None:
    st.markdown('<div class="quick-test-section-title">① Flashcarduri</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="quick-test-section-caption">Întoarce cardul, verifică răspunsul și evaluează-te sincer</div>',
        unsafe_allow_html=True,
    )

    try:
        deck = load_flashcard_deck(work["id"])
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        st.error(f"Banca de flashcarduri nu poate fi încărcată: {error}")
        return

    session_key = f"adaptive_flashcard_session_{work['id']}"
    handled_event_key = f"adaptive_flashcard_event_{work['id']}"
    session = st.session_state.get(session_key)
    stats = get_flashcard_stats(work["id"])
    total_cards = len(deck["cards"])

    if session is None:
        with st.container(height=455, border=True):
            st.markdown("#### Sesiune de flashcarduri")
            st.write(
                "Apasă pe card ca să vezi răspunsul-model. Apoi marchează dacă ai știut "
                "sau nu răspunsul. Cardurile neștiute revin după alte 5 carduri."
            )
            st.caption(
                f"Învățate: {stats['mastered']} din {total_cards} · "
                f"Răspunsuri date: {stats['seen']}"
            )
            if st.button(
                "Începe",
                key=f"start_flashcards_{work['id']}",
                type="primary",
                use_container_width=True,
            ):
                st.session_state[session_key] = create_flashcard_session()
                st.session_state.pop(handled_event_key, None)
                st.rerun()
        return

    mastered_ids = get_mastered_card_ids(work["id"])
    current_id = session.get("current_id")
    if current_id in mastered_ids or current_id not in deck["cards_by_id"]:
        current_id = choose_next_flashcard(deck, session, mastered_ids)
        st.session_state[session_key] = session

    if current_id is None:
        with st.container(height=455, border=True):
            st.success("Ai parcurs corect toate flashcardurile din această operă!")
            st.caption(f"Învățate: {total_cards} din {total_cards}")
        return

    card = deck["cards_by_id"][current_id]
    remaining = total_cards - len(mastered_ids)
    component_event = FLASHCARD_COMPONENT(
        card_id=card["id"],
        front=card["front"],
        back=card["back"],
        category=card.get("category", "Recapitulare"),
        counter=f"Cardul {int(session.get('shown_count', 1))} · {remaining} rămase",
        key=f"adaptive_card_{work['id']}_{session.get('shown_count', 0)}_{card['id']}",
        default=None,
    )

    if not isinstance(component_event, dict) or component_event.get("type") != "flashcard_outcome":
        return
    event_id = str(component_event.get("event_id", ""))
    if (
        not event_id
        or event_id == st.session_state.get(handled_event_key)
        or component_event.get("card_id") != card["id"]
    ):
        return

    outcome = component_event.get("outcome")
    if outcome not in {"correct", "wrong"}:
        return
    correct = outcome == "correct"
    st.session_state[handled_event_key] = event_id
    record_flashcard_outcome(work["id"], card["id"], correct)
    register_session_outcome(session, card, correct)
    if correct:
        award_quick_flashcard_point(work["id"], card["id"])
    st.session_state[session_key] = session
    st.rerun()


def _render_quick_exercises(work: dict) -> None:
    st.markdown('<div class="quick-test-section-title">② Exerciții</div>', unsafe_allow_html=True)
    st.markdown('<div class="quick-test-section-caption">Exersează prin diferite tipuri de itemi</div>', unsafe_allow_html=True)
    exercise_key = f"quick_exercise_type_{work['id']}"
    selected_type = st.session_state.get(exercise_key, "Ordine cronologică")
    labels = ["Ordine cronologică", "Asociere", "Completare"]
    if selected_type not in labels:
        selected_type = labels[0]
        st.session_state[exercise_key] = selected_type
    button_cols = st.columns(3, gap="small")
    for label, col in zip(labels, button_cols):
        with col:
            if st.button(label, key=f"quick_exercise_{work['id']}_{label}", type="primary" if selected_type == label else "secondary", use_container_width=True):
                st.session_state[exercise_key] = label
                st.rerun()

    generated_key = f"quick_generated_exercise_{work['id']}_{selected_type}"
    version_key = f"quick_exercise_version_{work['id']}_{selected_type}"
    generated_exercise = st.session_state.get(generated_key)
    exercise_version = st.session_state.get(version_key, 0)
    seen_key = f"quick_seen_exercises_{work['id']}_{selected_type}"
    if generated_exercise is None:
        try:
            generated_exercise = choose_prebuilt_exercise(
                work["id"],
                selected_type,
                st.session_state.get(seen_key, []),
            )
            st.session_state[generated_key] = generated_exercise
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
            st.error(f"Banca de exerciții nu poate fi încărcată: {error}")
            return

    with st.container(border=True):
        if selected_type == "Ordine cronologică":
            st.markdown("**Trage evenimentele unul peste altul până obții ordinea cronologică.**")
            chronology_items = [
                {
                    "id": str(
                        item.get("event_id")
                        or f"{generated_exercise.get('id', 'chronology')}_item_{item.get('position', index)}"
                    ),
                    "label": item["event"],
                }
                for index, item in enumerate(generated_exercise["items"], start=1)
            ]
            chronology_ids_by_position = {
                item["position"]: chronology_items[index]["id"]
                for index, item in enumerate(generated_exercise["items"])
            }
            expected_order = [
                chronology_ids_by_position[item["position"]]
                for item in sorted(
                    generated_exercise["items"], key=lambda item: item["position"]
                )
            ]
            order_key = f"quick_chronology_order_{work['id']}_{exercise_version}"
            feedback_key = f"quick_chronology_feedback_{work['id']}_{exercise_version}"
            result_key = f"quick_chronology_result_{work['id']}_{exercise_version}"
            current_order = st.session_state.get(
                order_key, [item["id"] for item in chronology_items]
            )
            component_event = CHRONOLOGY_EXERCISE_COMPONENT(
                items=chronology_items,
                order=current_order,
                feedback=st.session_state.get(feedback_key, {}),
                key=f"quick_chronology_component_{work['id']}_{exercise_version}",
                default=None,
            )
            if component_event and component_event.get("type") == "order_changed":
                event_key = f"processed_chronology_event_{work['id']}_{exercise_version}"
                if st.session_state.get(event_key) != component_event.get("event_id"):
                    st.session_state[event_key] = component_event.get("event_id")
                    st.session_state[order_key] = component_event.get("order", current_order)
                    st.session_state.pop(feedback_key, None)
                    st.session_state.pop(result_key, None)
                    st.rerun()

            if st.session_state.get(result_key):
                st.success(st.session_state[result_key])

            if st.button(
                "Verifică ordinea",
                key=f"check_quick_order_{work['id']}_{exercise_version}",
                type="primary",
                use_container_width=True,
            ):
                current_order = st.session_state.get(order_key, current_order)
                feedback = {
                    event_id: index < len(expected_order)
                    and event_id == expected_order[index]
                    for index, event_id in enumerate(current_order)
                }
                st.session_state[feedback_key] = feedback
                if current_order == expected_order:
                    canonical_events = [
                        (item["event"], item["position"])
                        for item in sorted(
                            generated_exercise["items"],
                            key=lambda item: item["position"],
                        )
                    ]
                    exercise_id = _quick_exercise_award_id(
                        work["id"], selected_type, {"items": canonical_events}
                    )
                    earned_points = award_quick_exercise_points(
                        work["id"], exercise_id
                    )
                    message = "Bravo! Ai așezat toate evenimentele în ordinea corectă."
                    if earned_points:
                        message += " +2 puncte de progres."
                    st.session_state[result_key] = message
                else:
                    st.error("Ordinea nu este încă corectă. Elementele marcate cu roșu trebuie mutate.")
                st.rerun()
        elif selected_type == "Asociere":
            st.markdown("**Unește fiecare enunț cu răspunsul care i se potrivește.**")
            pairs = generated_exercise["pairs"]
            left_items = [
                {"id": f"left_{index}", "label": pair["left"]}
                for index, pair in enumerate(pairs)
            ]
            right_items = [
                {"id": f"right_{index}", "label": pair["right"]}
                for index, pair in enumerate(pairs)
            ]
            random.Random(f"{work['id']}:{selected_type}:{exercise_version}").shuffle(right_items)
            expected_connections = {
                f"left_{index}": f"right_{index}"
                for index in range(len(pairs))
            }
            connections_key = f"quick_matching_connections_{work['id']}_{exercise_version}"
            feedback_key = f"quick_matching_feedback_{work['id']}_{exercise_version}"
            result_key = f"quick_matching_result_{work['id']}_{exercise_version}"
            component_event = MATCHING_EXERCISE_COMPONENT(
                left_items=left_items,
                right_items=right_items,
                connections=st.session_state.get(connections_key, {}),
                feedback=st.session_state.get(feedback_key, {}),
                key=f"quick_matching_component_{work['id']}_{exercise_version}",
                default=None,
            )
            if component_event and component_event.get("type") == "connections_changed":
                event_key = f"processed_matching_event_{work['id']}_{exercise_version}"
                if st.session_state.get(event_key) != component_event.get("event_id"):
                    st.session_state[event_key] = component_event.get("event_id")
                    st.session_state[connections_key] = component_event.get("connections", {})
                    st.session_state.pop(feedback_key, None)
                    st.session_state.pop(result_key, None)
                    st.rerun()

            if st.session_state.get(result_key):
                st.success(st.session_state[result_key])

            if st.button("Verifică asocierile", key=f"check_matching_{work['id']}_{exercise_version}", type="primary", use_container_width=True):
                connections = st.session_state.get(connections_key, {})
                feedback = {
                    left_id: connections.get(left_id) == right_id
                    for left_id, right_id in expected_connections.items()
                    if left_id in connections
                }
                st.session_state[feedback_key] = feedback
                if len(connections) < len(expected_connections):
                    st.warning("Realizează toate asocierile înainte de verificare.")
                elif all(feedback.get(left_id) for left_id in expected_connections):
                    exercise_id = _quick_exercise_award_id(work["id"], selected_type, {"pairs": pairs})
                    earned_points = award_quick_exercise_points(work["id"], exercise_id)
                    message = "Excelent! Toate asocierile sunt corecte."
                    if earned_points:
                        message += " +2 puncte de progres."
                    st.session_state[result_key] = message
                else:
                    st.error("Unele asocieri nu sunt corecte. Liniile roșii trebuie refăcute.")
                st.rerun()
        elif selected_type == "Completare":
            st.markdown("**Trage răspunsurile în cele trei spații potrivite.**")
            completion_text = generated_exercise["text"]
            completion_answers = generated_exercise["answers"]
            answer_items = [
                {"id": f"answer_{index}", "label": answer}
                for index, answer in enumerate(completion_answers)
            ]
            random.Random(
                f"{work['id']}:{selected_type}:{exercise_version}"
            ).shuffle(answer_items)
            placements_key = f"quick_completion_placements_{work['id']}_{exercise_version}"
            feedback_key = f"quick_completion_feedback_{work['id']}_{exercise_version}"
            result_key = f"quick_completion_result_{work['id']}_{exercise_version}"
            placements = st.session_state.get(
                placements_key, [None] * len(completion_answers)
            )
            component_event = COMPLETION_EXERCISE_COMPONENT(
                text=completion_text,
                answers=answer_items,
                placements=placements,
                feedback=st.session_state.get(feedback_key, {}),
                key=f"quick_completion_component_{work['id']}_{exercise_version}",
                default=None,
            )
            if component_event and component_event.get("type") == "placements_changed":
                event_key = f"processed_completion_event_{work['id']}_{exercise_version}"
                if st.session_state.get(event_key) != component_event.get("event_id"):
                    st.session_state[event_key] = component_event.get("event_id")
                    st.session_state[placements_key] = component_event.get(
                        "placements", placements
                    )
                    st.session_state.pop(feedback_key, None)
                    st.session_state.pop(result_key, None)
                    st.rerun()

            result = st.session_state.get(result_key)
            if isinstance(result, dict):
                if result.get("status") == "success":
                    st.success(result.get("message", "Corect!"))
                elif result.get("status") == "warning":
                    st.warning(result.get("message", "Completează toate spațiile."))
                else:
                    st.error(result.get("message", "Răspunsurile nu sunt corecte."))

            if st.button(
                "Verifică",
                key=f"check_fill_{work['id']}_{exercise_version}",
                type="primary",
                use_container_width=True,
            ):
                placements = st.session_state.get(placements_key, placements)
                expected_placements = [
                    f"answer_{index}" for index in range(len(completion_answers))
                ]
                feedback = {
                    f"slot_{index}": index < len(placements)
                    and placements[index] == expected_placements[index]
                    for index in range(len(expected_placements))
                }
                st.session_state[feedback_key] = feedback
                if len(placements) < len(expected_placements) or any(
                    placement is None for placement in placements
                ):
                    st.session_state[result_key] = {
                        "status": "warning",
                        "message": "Trage câte un răspuns în fiecare spațiu înainte de verificare.",
                    }
                elif placements == expected_placements:
                    exercise_id = _quick_exercise_award_id(
                        work["id"], selected_type, {"text": completion_text, "answers": completion_answers}
                    )
                    earned_points = award_quick_exercise_points(work["id"], exercise_id)
                    message = "Corect! Ai completat setul fără greșeli."
                    if earned_points:
                        message += " +2 puncte de progres."
                    st.session_state[result_key] = {
                        "status": "success",
                        "message": message,
                    }
                else:
                    st.session_state[result_key] = {
                        "status": "error",
                        "message": "Există cel puțin un răspuns greșit. Mută elementele marcate cu roșu.",
                    }
                st.rerun()
    if st.button("▧ Vezi mai multe exerciții", key=f"more_exercises_{work['id']}", use_container_width=True):
        try:
            seen_ids = list(st.session_state.get(seen_key, []))
            current_id = str(generated_exercise.get("id", ""))
            if current_id and current_id not in seen_ids:
                seen_ids.append(current_id)
            fresh_exercise = choose_prebuilt_exercise(
                work["id"],
                selected_type,
                seen_ids,
            )
            if str(fresh_exercise.get("id", "")) in seen_ids:
                seen_ids = []
                fresh_exercise = choose_prebuilt_exercise(work["id"], selected_type)
            st.session_state[seen_key] = seen_ids
            st.session_state[generated_key] = fresh_exercise
            st.session_state[version_key] = exercise_version + 1
            st.rerun()
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
            st.error(f"Nu am putut încărca următorul exercițiu: {error}")


@st.dialog("Rezultatele testului", width="large")
def _render_quick_test_results_dialog(
    work_id: str,
    test_version: int,
    questions: list[tuple],
    saved_answers: dict,
) -> None:
    score = sum(
        saved_answers.get(str(index)) == correct
        for index, (_, _, correct) in enumerate(questions, 1)
    )
    st.markdown(f"### Scor: {score} din {len(questions)}")
    st.progress(score / len(questions))

    for index, (question, _, correct) in enumerate(questions, 1):
        selected = saved_answers.get(str(index))
        with st.container(border=True):
            if selected == correct:
                st.markdown(f"✅ **{index}. {question}**")
                st.caption(f"Răspunsul tău: {selected}")
            else:
                st.markdown(f"❌ **{index}. {question}**")
                st.write(f"Răspunsul tău: {selected or 'Nu ai răspuns'}")
                st.caption(f"Răspuns corect: {correct}")

    if st.button(
        "Închide",
        key=f"close_quick_test_results_{work_id}_{test_version}",
        type="primary",
        use_container_width=True,
    ):
        st.rerun()


def _render_quick_tests(work: dict) -> None:
    st.markdown('<div class="quick-test-section-title">③ Teste</div>', unsafe_allow_html=True)
    st.markdown('<div class="quick-test-section-caption">Generează teste și verifică-te</div>', unsafe_allow_html=True)
    test_key = f"quick_generated_test_{work['id']}"
    with st.container(height=525, border=False):
        with st.container(border=True):
            st.markdown("**Generează un test nou**")
            count_col, type_col = st.columns(2, gap="small")
            with count_col:
                question_count = st.selectbox("Număr de întrebări", [5, 10], index=1, key=f"quick_test_count_{work['id']}")
            with type_col:
                st.selectbox("Tip întrebări", ["Doar grilă"], key=f"quick_test_type_{work['id']}")
            if st.button("⚒ Generează test", key=f"generate_quick_test_{work['id']}", type="primary", use_container_width=True):
                try:
                    cursor_key = f"quick_test_bank_cursor_{work['id']}"
                    cursor = int(st.session_state.get(cursor_key, 0))
                    st.session_state[test_key] = multiple_choice_test_items(
                        work["id"], question_count, cursor
                    )
                    st.session_state[cursor_key] = cursor + question_count
                    st.session_state[f"quick_test_submitted_{work['id']}"] = False
                    st.session_state[f"quick_test_index_{work['id']}"] = 0
                    version_key = f"quick_test_version_{work['id']}"
                    next_version = int(st.session_state.get(version_key, 0)) + 1
                    st.session_state[version_key] = next_version
                    st.session_state[
                        f"quick_test_answers_{work['id']}_{next_version}"
                    ] = {}
                    st.session_state[
                        f"quick_test_earned_points_{work['id']}_{next_version}"
                    ] = 0
                    st.rerun()
                except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
                    st.error(f"Banca de grile nu poate fi încărcată: {error}")

        questions = st.session_state.get(test_key)
        if not questions:
            st.info("Alege numărul de întrebări și generează primul test.")
            return

        st.markdown(f"**Test generat — „{work['title']}” ({len(questions)} întrebări)**")
        index_key = f"quick_test_index_{work['id']}"
        submitted_key = f"quick_test_submitted_{work['id']}"
        is_submitted = bool(st.session_state.get(submitted_key))
        test_version = int(st.session_state.get(f"quick_test_version_{work['id']}", 0))
        answers_key = f"quick_test_answers_{work['id']}_{test_version}"
        earned_points_key = f"quick_test_earned_points_{work['id']}_{test_version}"
        saved_answers = st.session_state.get(answers_key, {})
        if not isinstance(saved_answers, dict):
            saved_answers = {}
            st.session_state[answers_key] = saved_answers
        current_index = st.session_state.get(index_key, 0)
        question, options, _ = questions[current_index]
        answer_number = str(current_index + 1)
        answer_widget_key = (
            f"quick_test_answer_{work['id']}_{test_version}_{current_index + 1}"
        )
        saved_answer = saved_answers.get(answer_number)
        if answer_widget_key not in st.session_state and saved_answer in options:
            st.session_state[answer_widget_key] = saved_answer
        selected_answer = st.radio(
            f"{current_index + 1}. {question}",
            options,
            index=None,
            disabled=is_submitted,
            key=answer_widget_key,
        )
        if selected_answer is not None:
            saved_answers[answer_number] = selected_answer
            st.session_state[answers_key] = saved_answers

        answered_count = sum(
            str(index) in saved_answers for index in range(1, len(questions) + 1)
        )
        all_questions_answered = answered_count == len(questions)

        previous_col, counter_col, next_col = st.columns([1.15, 0.8, 1.15], gap="small")
        with previous_col:
            if st.button("‹ Întrebarea anterioară", key=f"previous_quick_test_{work['id']}", use_container_width=True, disabled=current_index == 0):
                st.session_state[index_key] -= 1
                st.rerun()
        with counter_col:
            st.markdown(f"<p style='text-align:center; padding-top:.55rem;'><b>{current_index + 1} / {len(questions)}</b></p>", unsafe_allow_html=True)
        with next_col:
            if st.button("Următoarea întrebare ›", key=f"next_quick_test_{work['id']}", type="primary", use_container_width=True, disabled=current_index == len(questions) - 1):
                st.session_state[index_key] += 1
                st.rerun()

        if st.button(
            "Finalizează testul",
            key=f"submit_quick_test_{work['id']}",
            type="primary",
            use_container_width=True,
            disabled=is_submitted or not all_questions_answered,
        ):
            correct_question_ids = [
                _quick_exercise_award_id(
                    work["id"],
                    "Test grilă",
                    {"question": question, "answer": correct},
                )
                for index, (question, _, correct) in enumerate(questions, 1)
                if saved_answers.get(str(index)) == correct
            ]
            st.session_state[earned_points_key] = award_quick_test_points(
                work["id"], correct_question_ids
            )
            st.session_state[submitted_key] = True
            st.rerun()

        if not is_submitted and not all_questions_answered:
            st.caption(
                f"Răspunsuri completate: {answered_count} din {len(questions)}. "
                "Răspunde la toate întrebările pentru a finaliza testul."
            )

        if st.session_state.get(submitted_key):
            score = sum(
                saved_answers.get(str(index)) == correct
                for index, (_, _, correct) in enumerate(questions, 1)
            )
            earned_points = float(st.session_state.get(earned_points_key, 0) or 0)
            earned_points_text = f"{earned_points:g}".replace(".", ",")
            progress_message = (
                f" +{earned_points_text} puncte de progres." if earned_points else ""
            )
            st.success(
                f"Ai răspuns corect la {score} din {len(questions)} întrebări."
                + progress_message
            )
            st.progress(score / len(questions))
            st.caption("Progres test")

    if st.button(
        "▥ Vezi rezultate după finalizare",
        key=f"quick_results_{work['id']}",
        use_container_width=True,
        disabled=not bool(st.session_state.get(submitted_key)),
    ):
        _render_quick_test_results_dialog(
            work["id"], test_version, questions, saved_answers
        )


def _get_selected_step(work_id: str) -> str:
    key = f"learning_step_{work_id}"

    if key not in st.session_state:
        st.session_state[key] = "summary"

    return st.session_state[key]


def _set_selected_step(work_id: str, step_id: str) -> None:
    st.session_state[f"learning_step_{work_id}"] = step_id


def _render_step_menu(work: dict, progress: dict, selected_step: str) -> None:
    steps = _get_learning_steps(progress, work)
    cols = st.columns(len(steps), gap="small")

    for step, col in zip(steps, cols):
        button_type = "primary" if selected_step == step["id"] else "secondary"
        help_text = step["caption"]
        if step["locked"]:
            help_text = f"Blocat - {step['caption']}"

        with col:
            if st.button(
                step["title"],
                key=f"open_learning_{work['id']}_{step['id']}",
                type=button_type,
                use_container_width=True,
                disabled=step["locked"],
                help=help_text,
            ):
                _set_selected_step(work["id"], step["id"])
                st.rerun()


def _get_learning_steps(progress: dict, work: dict | None = None) -> list[dict]:
    is_poezie = bool(work and work.get("type") == "poezie")
    return [
        {
            "id": "summary",
            "title": "Toată opera" if is_poezie else "Rezumat",
            "caption": "Text integral și comentariu pe strofe" if is_poezie else "Citire ghidata",
            "done": progress["summary_done"],
            "locked": False,
        },
        {
            "id": "literary_current",
            "title": "Curent literar",
            "caption": "Încadrare și trăsături ilustrate în operă",
            "done": progress.get("literary_current_done", False),
            "locked": False,
        },
        {
            "id": "characters",
            "title": "Voci lirice & Imagini" if is_poezie else "Personaje",
            "caption": "Lirismul măștilor și mindmap senzorial" if is_poezie else "Mind-mapuri si fise de personaj",
            "done": progress["characters_done"],
            "locked": False,
        },
        {
            "id": "scenes",
            "title": "Secvențe relevante",
            "caption": "Idei poetice pentru temă și eseu" if is_poezie else "Scene-cheie pentru tema si eseu",
            "done": progress["scenes_done"],
            "locked": False,
        },
        {
            "id": "structure",
            "title": "Elemente compoziționale",
            "caption": (
                "Titlu, opoziții și limbaj poetic"
                if is_poezie
                else "Incipit, final, conflict, perspectiva"
            ),
            "done": progress["structure_done"],
            "locked": False,
        },
    ]


def _render_summary_step(work: dict, progress: dict) -> None:
    summary_text = _read_summary(work["id"])

    content_col, tools_col = st.columns([1.65, 1], gap="large")
    with content_col:
        _render_summary_workspace(work, summary_text)
    with tools_col:
        _render_summary_tools(work, summary_text)


def _render_literary_current_step(work: dict, progress: dict) -> None:
    try:
        payload = load_literary_current(work["id"])
    except FileNotFoundError:
        st.info(
            "Materialul despre curentul literar nu a fost generat încă. Rulează "
            "scripts/intelegere_opera.py pe knowledge graph-ul operei."
        )
        return
    except (ValueError, json.JSONDecodeError) as error:
        st.error(f"Materialul despre curentul literar nu poate fi încărcat: {error}")
        return

    material = payload["literary_current"]
    movement = material.get("movement", {})
    movement_id = str(movement.get("id") or "literary_current")
    annotation_id = f"literary_current_{movement_id}"
    context_text = literary_current_reader_text(payload)
    generation = payload.get("generation", {})
    content_col, tools_col = st.columns([1.65, 1], gap="large")
    with content_col:
        annotations = get_scene_annotations(work["id"], annotation_id)
        component_event = SCENE_ANNOTATOR_COMPONENT(
            work_id=work["id"],
            sequence_id=annotation_id,
            title=str(movement.get("name") or "Curent literar"),
            chapter="Încadrarea operei și trăsături",
            source=(
                "Conținut generat de Qwen 3.7 Flash din knowledge graph"
                if generation.get("model") == "qwen/qwen3.7-flash"
                else f"Conținut AI din knowledge graph · {generation.get('model', '')}"
            ),
            text=context_text,
            annotations=annotations,
            key=f"literary_current_annotator_{work['id']}_{movement_id}",
            default=None,
        )
        _handle_literary_current_annotation_event(
            work, annotation_id, movement, component_event
        )
    with tools_col:
        _render_literary_current_tools(
            work, annotation_id, movement, context_text
        )


def _handle_literary_current_annotation_event(
    work: dict,
    annotation_id: str,
    movement: dict,
    component_event: dict | None,
) -> None:
    if not isinstance(component_event, dict) or not component_event.get("event_id"):
        return
    processed_key = f"processed_literary_current_event_{work['id']}_{annotation_id}"
    if st.session_state.get(processed_key) == component_event["event_id"]:
        return
    st.session_state[processed_key] = component_event["event_id"]
    if component_event.get("type") == "annotations_changed":
        save_scene_annotations(
            work["id"], annotation_id, component_event.get("annotations", [])
        )
    elif component_event.get("type") == "ask_ai":
        selected_text = str(component_event.get("selected_text") or "").strip()
        if selected_text:
            pending_key = f"literary_current_pending_ai_{work['id']}_{annotation_id}"
            st.session_state[pending_key] = (
                f"Explică în contextul curentului {movement.get('name', '')} și al operei "
                f"fragmentul pe care l-am marcat: „{selected_text}”."
            )


def _render_literary_current_tools(
    work: dict,
    annotation_id: str,
    movement: dict,
    context_text: str,
) -> None:
    notes_key = f"notes_popover_{work['id']}_literary_current"
    dictionary_key = f"dictionary_popover_{work['id']}_literary_current"
    st.markdown("### Instrumente")
    _render_literary_current_ai_professor(
        work, annotation_id, movement, context_text
    )
    notes_col, dictionary_col = st.columns(2, gap="small")
    with notes_col:
        with st.popover(
            "Carnetelul meu",
            key=notes_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_context_notebook(work, "literary_current")
            _render_popover_close_button(notes_key)
    with dictionary_col:
        with st.popover(
            "Dictionar AI",
            key=dictionary_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_literary_current_dictionary(work, movement, context_text)
            _render_popover_close_button(dictionary_key)


def _render_literary_current_ai_professor(
    work: dict,
    annotation_id: str,
    movement: dict,
    context_text: str,
) -> None:
    history_key = f"literary_current_ai_{work['id']}_{annotation_id}"
    input_key = f"literary_current_ai_input_{work['id']}_{annotation_id}"
    clear_key = f"literary_current_ai_clear_{work['id']}_{annotation_id}"
    pending_key = f"literary_current_pending_ai_{work['id']}_{annotation_id}"
    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""
    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    f"Bună! Întreabă-mă despre {movement.get('name', 'curentul literar')} "
                    f"și încadrarea operei {work.get('title', '')}."
                ),
            }
        ]

    pending_question = str(st.session_state.pop(pending_key, "")).strip()
    if pending_question:
        st.session_state[history_key].append(
            {"role": "user", "content": pending_question}
        )
        st.session_state[history_key].append(
            {
                "role": "assistant",
                "content": _answer_literary_current_question(
                    work, movement, context_text, pending_question
                ),
            }
        )

    with st.container(border=True):
        st.markdown("#### ✨ AI Profesor")
        with st.container(height=235, border=True):
            for message in st.session_state[history_key]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        question = st.text_area(
            "Întreabă despre curentul literar",
            key=input_key,
            placeholder="Cum demonstrez această trăsătură în operă?",
            height=58,
            label_visibility="collapsed",
        )
        if st.button(
            "Trimite",
            key=f"send_literary_current_ai_{work['id']}_{annotation_id}",
            type="primary",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning("Scrie mai întâi o întrebare pentru AI Profesor.")
            else:
                clean_question = question.strip()
                st.session_state[history_key].append(
                    {"role": "user", "content": clean_question}
                )
                with ai_thinking():
                    answer = _answer_literary_current_question(
                        work, movement, context_text, clean_question
                    )
                st.session_state[history_key].append(
                    {"role": "assistant", "content": answer}
                )
                st.session_state[clear_key] = True
                st.rerun()


def _answer_literary_current_question(
    work: dict,
    movement: dict,
    context_text: str,
    question: str,
) -> str:
    if answer_learning_context_question is None:
        return "AI-ul nu este legat încă pentru curentul literar."
    try:
        return answer_learning_context_question(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            user_question=question,
            context_title=f"Curent literar – {movement.get('name', '')}",
            context_text=context_text,
        ).strip()
    except Exception as error:
        return f"A apărut o eroare la apelul Qwen: {error}"


def _render_literary_current_dictionary(
    work: dict,
    movement: dict,
    context_text: str,
) -> None:
    result_key = f"literary_current_dictionary_result_{work['id']}"
    with st.container(border=True):
        st.markdown("#### Dictionar AI")
        term = st.text_input(
            "Caută un termen",
            key=f"literary_current_dictionary_input_{work['id']}",
            placeholder="ex: narator omniscient, tipicitate",
            label_visibility="collapsed",
        )
        if st.button(
            "Caută",
            key=f"search_literary_current_dictionary_{work['id']}",
            type="primary",
            use_container_width=True,
        ):
            if not term.strip():
                st.warning("Scrie mai întâi un termen.")
            elif explain_learning_context_term is None:
                st.session_state[result_key] = "Dicționarul AI nu este legat încă."
            else:
                try:
                    st.session_state[result_key] = explain_learning_context_term(
                        work_title=str(work.get("title") or "Opera"),
                        work_author=str(work.get("author") or "autorul operei"),
                        term=term.strip(),
                        context_title=f"Curent literar – {movement.get('name', '')}",
                        context_text=context_text,
                    ).strip()
                except Exception as error:
                    st.session_state[result_key] = f"A apărut o eroare: {error}"
            st.rerun()
        if st.session_state.get(result_key):
            st.write(st.session_state[result_key])


def _render_summary_exercises(work: dict) -> None:
    exercises = SUMMARY_EXERCISES_BY_WORK.get(work["id"], [])

    if not exercises:
        return

    index_key = f"summary_exercises_index_{work['id']}"
    score_key = f"summary_exercises_score_{work['id']}"
    done_key = f"summary_exercises_done_{work['id']}"
    feedback_key = f"summary_exercises_step_feedback_{work['id']}"

    if index_key not in st.session_state:
        st.session_state[index_key] = 0

    if score_key not in st.session_state:
        st.session_state[score_key] = 0

    if done_key not in st.session_state:
        st.session_state[done_key] = False

    with st.expander(
        "Exercitii pentru firul narativ",
        expanded=st.session_state[done_key] or st.session_state[index_key] > 0,
    ):
        if st.session_state[done_key]:
            st.success(
                f"Ai raspuns corect la {st.session_state[score_key]} din {len(exercises)} intrebari."
            )

            if not get_current_summary_progress(work["id"]):
                mark_summary_done(work["id"])
                st.rerun()

            if st.button(
                "Reia exercitiile",
                key=f"restart_summary_exercises_{work['id']}",
                use_container_width=True,
            ):
                _reset_summary_exercises_state(
                    index_key,
                    score_key,
                    done_key,
                    feedback_key,
                )
                st.rerun()
            return

        current_index = st.session_state[index_key]
        exercise = exercises[current_index]
        answer_key = f"summary_exercises_answer_{work['id']}_{current_index}"

        st.markdown(f"**Intrebarea {current_index + 1} din {len(exercises)}**")
        answer = st.selectbox(
            exercise["question"],
            ["Alege un raspuns"] + exercise["options"],
            key=answer_key,
            index=0,
        )

        if st.button(
            "Raspunde",
            key=f"submit_summary_exercise_{work['id']}",
            type="primary",
            use_container_width=True,
        ):
            if answer == "Alege un raspuns":
                st.warning("Alege un raspuns inainte sa continui.")
                return

            is_correct = answer == exercise["answer"]

            if is_correct:
                st.session_state[score_key] += 1
                st.session_state[feedback_key] = "Corect."
            else:
                st.session_state[feedback_key] = (
                    f"Nu chiar. Raspunsul corect era: {exercise['answer']}"
                )

            st.session_state[index_key] += 1

            if st.session_state[index_key] >= len(exercises):
                st.session_state[done_key] = True
                earned_points = round((st.session_state[score_key] / len(exercises)) * 10)
                update_summary_quiz_score(work["id"], earned_points)
                mark_summary_done(work["id"])

            st.rerun()

        if feedback_key in st.session_state:
            st.info(st.session_state[feedback_key])


def _reset_summary_exercises_state(
    index_key: str,
    score_key: str,
    done_key: str,
    feedback_key: str,
) -> None:
    st.session_state[index_key] = 0
    st.session_state[score_key] = 0
    st.session_state[done_key] = False
    st.session_state.pop(feedback_key, None)


def get_current_summary_progress(work_id: str) -> bool:
    return get_work_progress(work_id)["summary_done"]


def _render_summary_tools(work: dict, summary_text: str) -> None:
    st.markdown("### Instrumente")
    _render_summary_ai_professor(work, summary_text)
    _render_summary_tool_popovers(work, summary_text)


def _render_summary_tool_popovers(work: dict, summary_text: str) -> None:
    notes_key = f"notes_popover_{work['id']}_summary"
    dictionary_key = f"dictionary_popover_{work['id']}_summary"
    notes_col, dictionary_col = st.columns(2, gap="small")

    with notes_col:
        with st.popover(
            "Carnetelul meu",
            key=notes_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_summary_notebook(work)
            _render_popover_close_button(notes_key)

    with dictionary_col:
        with st.popover(
            "Dictionar AI",
            key=dictionary_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_summary_dictionary(work, summary_text)
            _render_popover_close_button(dictionary_key)


def _close_popover(popover_key: str) -> None:
    st.session_state[popover_key] = False


def _render_popover_close_button(popover_key: str) -> None:
    st.button(
        "Închide fereastra",
        key=f"close_{popover_key}",
        use_container_width=True,
        on_click=_close_popover,
        args=(popover_key,),
    )


def _render_summary_workspace(work: dict, summary_text: str) -> None:
    st.container(height=600, border=True).markdown(summary_text)




def _render_summary_ai_professor(work: dict, summary_text: str) -> None:
    history_key = f"summary_ai_professor_{work['id']}"
    status_key = f"summary_ai_professor_status_{work['id']}"
    input_key = f"summary_ai_professor_input_{work['id']}"
    clear_key = f"summary_ai_professor_clear_input_{work['id']}"
    is_poetry = work.get("type") == "poezie"

    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""

    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    "Bună! Întreabă-mă despre text, tablourile lirice sau evoluția discursului poetic."
                    if is_poetry
                    else "Buna! Intreaba-ma orice despre rezumatul operei."
                ),
            }
        ]

    with st.container(border=True):
        st.markdown("#### ✨ AI Profesor")

        chat_box = st.container(height=235, border=True)
        with chat_box:
            for message in st.session_state[history_key]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        question = st.text_area(
            "Întreabă despre textul poetic" if is_poetry else "Intreaba despre rezumat",
            key=input_key,
            placeholder=(
                "Cum evoluează vocile lirice de la primul tablou la final?"
                if is_poetry
                else "Care este cauza principală a conflictului?"
            ),
            height=58,
            label_visibility="collapsed",
        )
        submitted = st.button(
            "Trimite",
            key=f"send_summary_ai_question_{work['id']}",
            type="primary",
            use_container_width=True,
        )

        if submitted and not question.strip():
            st.warning("Scrie mai intai o intrebare pentru AI Profesor.")

        if submitted and question.strip():
            st.session_state[history_key].append(
                {"role": "user", "content": question.strip()}
            )
            st.session_state[status_key] = "Se genereaza raspunsul..."
            with ai_thinking():
                answer = _answer_summary_question(work, question.strip(), summary_text)

            st.session_state[history_key].append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
            st.session_state[status_key] = "Raspuns primit."
            st.session_state[clear_key] = True
            st.rerun()

        if status_key in st.session_state:
            st.caption(st.session_state[status_key])


def _answer_summary_question(work: dict, question: str, summary_text: str) -> str:
    if answer_learning_context_question is None:
        return "AI-ul nu este legat inca pentru rezumat."

    try:
        answer = answer_learning_context_question(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            user_question=question,
            context_title=(
                "Textul și tablourile lirice"
                if work.get("type") == "poezie"
                else "Rezumatul operei"
            ),
            context_text=summary_text,
        ).strip()
        return answer or "AI-ul nu a returnat niciun raspuns. Incearca din nou."
    except Exception as error:
        return f"A aparut o eroare la apelul AI: {error}"


def _render_summary_notebook(work: dict) -> None:
    notes_key = f"summary_notes_list_{work['id']}"
    selected_key = f"summary_selected_note_{work['id']}"
    editing_key = f"summary_editing_note_{work['id']}"

    _ensure_summary_notes_state(work, notes_key, selected_key)

    with st.container(border=True):
        note_col, action_col = st.columns([1, 0.85])

        with note_col:
            st.markdown("#### Carnetelul meu")

        with action_col:
            if st.button(
                "Adauga notita",
                key=f"add_summary_note_{work['id']}",
                type="primary",
                use_container_width=True,
            ):
                note = create_note(
                    work["id"],
                    "summary",
                    f"Notita {len(st.session_state[notes_key]) + 1}",
                )
                st.session_state[notes_key].append(note)
                st.session_state[selected_key] = note["id"]
                st.session_state[editing_key] = note["id"]
                st.rerun()

        with st.expander("Deschide carnetelul", expanded=bool(st.session_state[notes_key])):
            _render_summary_notes_list(work, notes_key, selected_key, editing_key)


def _ensure_summary_notes_state(
    work: dict,
    notes_key: str,
    selected_key: str,
) -> None:
    old_notes_key = f"summary_notes_{work['id']}"
    old_note = st.session_state.get(old_notes_key, "").strip()
    transient_notes = list(st.session_state.get(notes_key, []))

    if old_note and not transient_notes:
        transient_notes = [{"title": "Notita 1", "content": old_note}]

    _ensure_notes_state(
        work=work,
        scope="summary",
        notes_key=notes_key,
        selected_key=selected_key,
        transient_notes=transient_notes,
    )


def _ensure_notes_state(
    work: dict,
    scope: str,
    notes_key: str,
    selected_key: str,
    transient_notes: list[dict] | None = None,
) -> None:
    loaded_user_key = f"{notes_key}_loaded_user_id"
    current_user_id = int(st.session_state["auth_user"]["id"])
    previously_loaded_user_id = st.session_state.get(loaded_user_key)

    if previously_loaded_user_id != current_user_id:
        if previously_loaded_user_id is not None:
            transient_notes = []

        persisted_notes = get_notes(work["id"], scope)

        if not persisted_notes:
            for transient_note in transient_notes or []:
                persisted_notes.append(
                    create_note(
                        work["id"],
                        scope,
                        transient_note.get("title", "Notita fara titlu"),
                        transient_note.get("content", ""),
                    )
                )

        st.session_state[notes_key] = persisted_notes
        st.session_state[loaded_user_key] = current_user_id

    existing_ids = {note["id"] for note in st.session_state[notes_key]}
    if st.session_state.get(selected_key) not in existing_ids:
        first_note = st.session_state[notes_key][0] if st.session_state[notes_key] else None
        st.session_state[selected_key] = first_note["id"] if first_note else None


def _render_summary_notes_list(
    work: dict,
    notes_key: str,
    selected_key: str,
    editing_key: str,
) -> None:
    notes = st.session_state[notes_key]

    if not notes:
        st.caption("Nu ai notite inca. Apasa pe Adauga notita ca sa incepi.")
        return

    for note in notes:
        note_id = note["id"]
        title = note["title"].strip() or "Notita fara titlu"
        preview = note["content"].strip().replace("\n", " ")

        item_col, edit_col, delete_col = st.columns([1.05, 1.05, 0.9])

        with item_col:
            button_label = title if not preview else f"{title}\n{preview[:42]}"
            if st.button(
                button_label,
                key=f"select_summary_note_{work['id']}_{note_id}",
                type="primary" if st.session_state[selected_key] == note_id else "secondary",
                use_container_width=True,
            ):
                st.session_state[selected_key] = note_id
                st.session_state[editing_key] = None
                st.rerun()

        with edit_col:
            if st.button(
                "Modifica",
                key=f"edit_summary_note_{work['id']}_{note_id}",
                use_container_width=True,
            ):
                st.session_state[selected_key] = note_id
                st.session_state[editing_key] = note_id
                st.rerun()

        with delete_col:
            if st.button(
                "Sterge",
                key=f"delete_summary_note_{work['id']}_{note_id}",
                use_container_width=True,
            ):
                _delete_summary_note(notes_key, selected_key, editing_key, note_id)
                st.rerun()

    selected_note = _get_selected_summary_note(notes_key, selected_key)

    if selected_note is None:
        return

    st.divider()

    if st.session_state.get(editing_key) == selected_note["id"]:
        _render_summary_note_editor(work, notes_key, editing_key, selected_note)
    else:
        st.markdown(f"**{selected_note['title'].strip() or 'Notita fara titlu'}**")
        st.write(selected_note["content"] or "Notita este goala. Apasa pe Modifica pentru a scrie in ea.")


def _delete_summary_note(
    notes_key: str,
    selected_key: str,
    editing_key: str,
    note_id: int,
) -> None:
    delete_note(note_id)
    st.session_state[notes_key] = [
        note for note in st.session_state[notes_key] if note["id"] != note_id
    ]

    if st.session_state.get(selected_key) == note_id:
        first_note = st.session_state[notes_key][0] if st.session_state[notes_key] else None
        st.session_state[selected_key] = first_note["id"] if first_note else None

    if st.session_state.get(editing_key) == note_id:
        st.session_state[editing_key] = None


def _get_selected_summary_note(notes_key: str, selected_key: str) -> dict | None:
    selected_id = st.session_state.get(selected_key)

    for note in st.session_state[notes_key]:
        if note["id"] == selected_id:
            return note

    return None


def _render_summary_note_editor(
    work: dict,
    notes_key: str,
    editing_key: str,
    note: dict,
) -> None:
    with st.form(key=f"summary_note_editor_{work['id']}_{note['id']}"):
        title = st.text_input("Titlu notita", value=note["title"])
        content = st.text_area(
            "Continut notita",
            value=note["content"],
            height=170,
            placeholder="Scrie aici ideea, intrebarea sau formularea pe care vrei sa o retii.",
        )

        save_col, cancel_col = st.columns(2)

        with save_col:
            save = st.form_submit_button("Salveaza", type="primary", use_container_width=True)

        with cancel_col:
            cancel = st.form_submit_button("Renunta", use_container_width=True)

    if save:
        saved_note = update_note(note["id"], title, content)
        note.update(saved_note)
        st.session_state[editing_key] = None
        st.rerun()

    if cancel:
        st.session_state[editing_key] = None
        st.rerun()


def _render_summary_dictionary(work: dict, summary_text: str) -> None:
    result_key = f"summary_dictionary_result_{work['id']}"
    status_key = f"summary_dictionary_status_{work['id']}"
    input_key = f"summary_dictionary_input_{work['id']}"
    clear_key = f"summary_dictionary_clear_input_{work['id']}"

    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""

    with st.container(border=True):
        st.markdown("#### Dictionar AI")

        term = st.text_input(
            "Cauta un cuvant sau o expresie",
            key=input_key,
            placeholder="ex: motiv literar, conflict interior",
            label_visibility="collapsed",
        )
        submitted = st.button(
            "Cauta",
            key=f"search_summary_dictionary_{work['id']}",
            type="primary",
            use_container_width=True,
        )

        if submitted and not term.strip():
            st.warning("Scrie mai intai un cuvant sau o expresie.")

        if submitted and term.strip():
            st.session_state[status_key] = "Se cauta explicatia..."
            with st.spinner("Dictionarul AI cauta explicatia..."):
                st.session_state[result_key] = _explain_dictionary_term(
                    work,
                    term.strip(),
                    summary_text,
                )
            st.session_state[status_key] = "Explicatie primita."
            st.session_state[clear_key] = True
            st.rerun()

        if status_key in st.session_state:
            st.caption(st.session_state[status_key])

        if result_key in st.session_state and st.session_state[result_key]:
            st.write(st.session_state[result_key])


def _explain_dictionary_term(work: dict, term: str, summary_text: str) -> str:
    if explain_learning_context_term is None:
        return "Dictionarul AI nu este legat inca."

    try:
        answer = explain_learning_context_term(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            term=term,
            context_title=(
                "Textul și tablourile lirice"
                if work.get("type") == "poezie"
                else "Rezumatul operei"
            ),
            context_text=summary_text,
        ).strip()
        return answer or "Dictionarul AI nu a returnat niciun raspuns. Incearca din nou."
    except Exception as error:
        return f"A aparut o eroare la apelul AI: {error}"


def _render_characters_tools(work: dict) -> None:
    context_text = _build_characters_context_text(work["id"])
    st.markdown("### Instrumente")
    _render_characters_ai_professor(work, context_text)
    notes_key = f"notes_popover_{work['id']}_characters"
    dictionary_key = f"dictionary_popover_{work['id']}_characters"
    notes_col, dictionary_col = st.columns(2, gap="small")
    with notes_col:
        with st.popover(
            "Carnetelul meu",
            key=notes_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_characters_notebook(work)
            _render_popover_close_button(notes_key)
    with dictionary_col:
        with st.popover(
            "Dictionar AI",
            key=dictionary_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_characters_dictionary(work, context_text)
            _render_popover_close_button(dictionary_key)


def _build_characters_context_text(work_id: str) -> str:
    parts = []

    voci_path = Path("data") / "generated_works" / work_id / "intelegere-opera" / "voci-si-imagini.json"
    if voci_path.is_file():
        try:
            voci_data = json.loads(voci_path.read_text(encoding="utf-8"))
            parts.append("VOCILE ȘI INSTANȚELE LIRICE:")
            for voice in voci_data.get("voices", []):
                parts.append(
                    f"- {voice.get('name', '')} ({voice.get('role', '')})\n"
                    f"  Atitudine/Personalitate: {voice.get('attitude', '')} | {voice.get('personality', '')}\n"
                    f"  Fizic/Prezență: {voice.get('physical_description', '')}\n"
                    f"  Mărci lingvistice: {voice.get('linguistic_markers', '')}\n"
                    f"  Strofe: {voice.get('associated_stanzas', [])}"
                )
            mindmap = voci_data.get("sensory_mindmap", {})
            parts.append(f"\nHARTA IMAGINILOR ARTISTICE ({mindmap.get('title', 'Senzorial')}):")
            for cat in mindmap.get("categories", []):
                parts.append(f"Categorie: {cat.get('type', '')}")
                for itm in cat.get("items", []):
                    parts.append(f"  * {itm.get('label', '')}: «{itm.get('quote', '')}» (Strofa {itm.get('stanza', '')})")
            return "\n\n".join(parts)
        except Exception:
            pass

    try:
        mindmaps = _load_character_mindmaps(work_id)
        for group in mindmaps.get("groups", []):
            group_title = group.get("title") or group.get("name") or "Grup"
            parts.append(f"GRUP: {group_title}")
            if "caption" in group:
                parts.append(group["caption"])

            chars = group.get("characters", [])
            if isinstance(chars, list):
                for character in chars:
                    if isinstance(character, dict):
                        parts.append(
                            "\n".join(
                                [
                                    f"- {character.get('name', '')} ({character.get('short_role', character.get('role', ''))})",
                                    f"  Fizic: {character.get('physical', character.get('physical_description', ''))}",
                                    f"  Trasaturi: {character.get('traits', character.get('personality', ''))}",
                                    f"  Rol: {character.get('village_role', character.get('role', ''))}",
                                    f"  Tip uman: {character.get('human_type', character.get('category', ''))}",
                                ]
                            )
                        )
                    elif isinstance(character, str):
                        parts.append(f"- {character}")

        raw_chars = mindmaps.get("characters", {})
        if isinstance(raw_chars, dict):
            for cid, char in raw_chars.items():
                if isinstance(char, dict):
                    parts.append(
                        f"- {char.get('name', cid)}: {char.get('short_role', char.get('role', ''))} | {char.get('traits', '')}"
                    )
        elif isinstance(raw_chars, list):
            for char in raw_chars:
                if isinstance(char, dict):
                    parts.append(
                        f"- {char.get('name', '')}: {char.get('role', '')} | {char.get('personality', '')}"
                    )
    except Exception:
        pass

    return "\n\n".join(parts)


def _render_characters_ai_professor(work: dict, context_text: str) -> None:
    history_key = f"characters_ai_professor_{work['id']}"
    status_key = f"characters_ai_professor_status_{work['id']}"
    input_key = f"characters_ai_professor_input_{work['id']}"
    clear_key = f"characters_ai_professor_clear_input_{work['id']}"
    pending_question_key = f"characters_ai_pending_question_{work['id']}"
    xp_key = f"characters_ai_xp_{work['id']}"
    deferred_key = f"characters_ai_deferred_questions_{work['id']}"
    ai_progress = get_characters_ai_progress(work["id"])
    enhanced_xp_chat = work["id"] == "enigma_otiliei"
    is_poetry = work.get("type") == "poezie" or (
        Path("data")
        / "generated_works"
        / work["id"]
        / "intelegere-opera"
        / "voci-si-imagini.json"
    ).is_file()

    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""

    st.session_state[pending_question_key] = ai_progress["pending_question"]
    st.session_state[xp_key] = ai_progress["xp"]
    st.session_state[deferred_key] = ai_progress["deferred_questions"]

    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    (
                        "Bună! Întreabă-mă despre vocile lirice, imaginile artistice și planurile din "
                        if is_poetry
                        else "Bună! Întreabă-mă orice despre personajele din "
                    )
                    + f"„{work.get('title', 'operă')}”."
                ),
            }
        ]

    if (
        enhanced_xp_chat
        and st.session_state[pending_question_key]
        and _replace_malformed_characters_response(
            st.session_state[history_key],
            st.session_state[pending_question_key],
        )
    ):
        st.session_state[pending_question_key] = ""
        update_characters_ai_progress(
            work["id"],
            st.session_state[xp_key],
            "",
            st.session_state[deferred_key],
        )

    with st.container(border=True):
        title_col, queue_col = st.columns([8, 1])
        with title_col:
            st.markdown("#### ✨ AI Profesor")
        if enhanced_xp_chat:
            with queue_col:
                queue_opened = st.button(
                    f"🕒 {len(st.session_state[deferred_key])}",
                    key=f"open_characters_ai_queue_{work['id']}",
                    help="Întrebări păstrate pentru mai târziu",
                    use_container_width=True,
                )
            if queue_opened:
                _render_characters_ai_question_queue_dialog(work, context_text)
        st.caption(f"XP conversatie: {st.session_state[xp_key]}")

        chat_box = st.container(height=235, border=True)
        with chat_box:
            for message in st.session_state[history_key]:
                with st.chat_message(message["role"]):
                    if message["role"] == "assistant":
                        answer_text, xp_question = _split_assistant_xp_message(message)
                        if answer_text:
                            st.write(answer_text)
                        if xp_question:
                            with st.container(border=True):
                                st.caption("Întrebare pentru XP")
                                st.markdown(f"**{xp_question}**")
                    else:
                        st.write(message["content"])

        active_xp_question = st.session_state[pending_question_key]
        if enhanced_xp_chat and active_xp_question:
            st.caption("Întrebarea activă poate primi maximum 3 XP.")
            ignore_col, defer_col = st.columns(2)
            with ignore_col:
                ignored = st.button(
                    "Ignoră întrebarea",
                    key=f"ignore_characters_ai_question_{work['id']}",
                    use_container_width=True,
                )
            with defer_col:
                deferred = st.button(
                    "Pune în listă pentru mai târziu",
                    key=f"defer_characters_ai_question_{work['id']}",
                    use_container_width=True,
                )

            if ignored:
                _remove_xp_question_from_history(
                    st.session_state[history_key],
                    active_xp_question,
                )
                st.session_state[pending_question_key] = ""
                update_characters_ai_progress(
                    work["id"],
                    st.session_state[xp_key],
                    "",
                    st.session_state[deferred_key],
                )
                st.session_state[status_key] = "Întrebarea XP a fost ignorată."
                st.rerun()

            if deferred:
                deferred_questions = list(st.session_state[deferred_key])
                if active_xp_question not in deferred_questions:
                    deferred_questions.append(active_xp_question)
                st.session_state[deferred_key] = deferred_questions
                st.session_state[pending_question_key] = ""
                update_characters_ai_progress(
                    work["id"],
                    st.session_state[xp_key],
                    "",
                    deferred_questions,
                )
                st.session_state[status_key] = "Întrebarea a fost păstrată pentru mai târziu."
                st.rerun()

        question = st.text_area(
            "Întreabă despre vocile lirice" if is_poetry else "Intreaba despre personaje",
            key=input_key,
            placeholder=(
                "Cum se diferențiază cele două voci lirice?"
                if is_poetry
                else "Ce rol are Ana in roman?"
            ),
            height=58,
            label_visibility="collapsed",
        )
        submitted = st.button(
            "Trimite",
            key=f"send_characters_ai_question_{work['id']}",
            type="primary",
            use_container_width=True,
        )

        if submitted and not question.strip():
            st.warning("Scrie mai intai o intrebare pentru AI Profesor.")

        if submitted and question.strip():
            _submit_characters_ai_turn(
                work,
                context_text,
                question.strip(),
                st.session_state[pending_question_key],
                st.session_state[deferred_key],
            )
            st.session_state[clear_key] = True
            st.rerun()

        if status_key in st.session_state:
            st.caption(st.session_state[status_key])


def _submit_characters_ai_turn(
    work: dict,
    context_text: str,
    user_message: str,
    evaluation_question: str,
    deferred_questions: list[str],
) -> None:
    history_key = f"characters_ai_professor_{work['id']}"
    status_key = f"characters_ai_professor_status_{work['id']}"
    pending_question_key = f"characters_ai_pending_question_{work['id']}"
    xp_key = f"characters_ai_xp_{work['id']}"
    deferred_key = f"characters_ai_deferred_questions_{work['id']}"
    ai_progress = get_characters_ai_progress(work["id"])
    current_xp = int(ai_progress["xp"])

    st.session_state[history_key].append(
        {"role": "user", "content": user_message.strip()}
    )
    st.session_state[status_key] = "Se generează răspunsul..."
    with ai_thinking():
        answer, earned_xp, next_question = _answer_characters_question(
            work,
            user_message.strip(),
            context_text,
            evaluation_question,
            current_xp,
        )

    st.session_state[history_key].append(
        {
            "role": "assistant",
            "content": answer,
            "xp_question": next_question or "",
        }
    )
    new_xp = current_xp + earned_xp
    new_pending_question = next_question or ""
    st.session_state[xp_key] = new_xp
    st.session_state[pending_question_key] = new_pending_question
    st.session_state[deferred_key] = list(deferred_questions)
    update_characters_ai_progress(
        work["id"],
        new_xp,
        new_pending_question,
        deferred_questions,
    )
    st.session_state[status_key] = "Răspuns primit."


def _split_assistant_xp_message(message: dict) -> tuple[str, str | None]:
    content = str(message.get("content") or "").strip()
    xp_question = str(message.get("xp_question") or "").strip()
    if not xp_question:
        xp_question = _extract_xp_question_from_message(content) or ""

    if not xp_question:
        return content, None
    return _remove_xp_question_from_content(content, xp_question), xp_question


def _remove_xp_question_from_content(content: str, xp_question: str) -> str:
    content = str(content or "").strip()
    xp_question = str(xp_question or "").strip()
    if not xp_question:
        return content

    question_index = content.casefold().rfind(xp_question.casefold())
    if question_index < 0:
        return content

    before = content[:question_index].rstrip()
    after = content[question_index + len(xp_question) :].strip()
    return "\n\n".join(part for part in (before, after) if part)


def _remove_xp_question_from_history(history: list[dict], xp_question: str) -> None:
    for message in reversed(history):
        if message.get("role") != "assistant":
            continue

        stored_question = str(message.get("xp_question") or "").strip()
        content = str(message.get("content") or "")
        question_matches = stored_question.casefold() == xp_question.casefold()
        content_contains_question = xp_question.casefold() in content.casefold()
        if not question_matches and not content_contains_question:
            continue

        message["content"] = _remove_xp_question_from_content(
            content,
            xp_question,
        )
        message.pop("xp_question", None)
        return


def _replace_malformed_characters_response(
    history: list[dict],
    active_question: str,
) -> bool:
    for message in reversed(history):
        if message.get("role") != "assistant":
            continue

        answer_text, xp_question = _split_assistant_xp_message(message)
        if not xp_question or xp_question.casefold() != active_question.casefold():
            continue
        if _has_substantive_characters_answer(answer_text, None):
            return False

        message["content"] = (
            "Răspunsul AI nu a fost generat complet. Te rog trimite din nou întrebarea."
        )
        message.pop("xp_question", None)
        return True
    return False


@st.dialog("Întrebări pentru mai târziu", width="large")
def _render_characters_ai_question_queue_dialog(
    work: dict,
    context_text: str,
) -> None:
    deferred_key = f"characters_ai_deferred_questions_{work['id']}"
    selected_key = f"characters_ai_selected_deferred_question_{work['id']}"
    questions = list(get_characters_ai_progress(work["id"])["deferred_questions"])
    st.session_state[deferred_key] = questions

    if not questions:
        st.info("Nu ai întrebări păstrate pentru mai târziu.")
        return

    selected_question = st.session_state.get(selected_key, "")
    if selected_question not in questions:
        selected_question = ""
        st.session_state.pop(selected_key, None)

    st.caption("Alege o întrebare, formulează răspunsul și trimite-l profesorului AI.")
    for index, question in enumerate(questions, start=1):
        if st.button(
            question,
            key=f"select_deferred_character_question_{work['id']}_{index}_{_stable_text_id(question)}",
            type="primary" if question == selected_question else "secondary",
            use_container_width=True,
        ):
            st.session_state[selected_key] = question
            selected_question = question

    if not selected_question:
        return

    answer_key = (
        f"characters_ai_deferred_answer_{work['id']}_{_stable_text_id(selected_question)}"
    )
    answer = st.text_area(
        "Răspunsul tău",
        key=answer_key,
        placeholder="Scrie aici răspunsul tău...",
        height=120,
    )
    if st.button(
        "Trimite",
        key=f"send_deferred_character_answer_{work['id']}",
        type="primary",
        use_container_width=True,
    ):
        if not answer.strip():
            st.warning("Scrie un răspuns înainte de trimitere.")
            return

        remaining_questions = [
            question for question in questions if question != selected_question
        ]
        active_question = str(
            get_characters_ai_progress(work["id"])["pending_question"]
        ).strip()
        if active_question and active_question not in remaining_questions:
            remaining_questions.append(active_question)
        _submit_characters_ai_turn(
            work,
            context_text,
            answer.strip(),
            selected_question,
            remaining_questions,
        )
        st.session_state.pop(selected_key, None)
        st.rerun()


def _stable_text_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _answer_characters_question(
    work: dict,
    question: str,
    context_text: str,
    pending_question: str,
    current_xp: int,
) -> tuple[str, int, str | None]:
    if answer_characters_teacher_turn is None:
        return "AI-ul nu este legat inca pentru personaje.", 0, None

    try:
        enhanced_xp_chat = work.get("id") == "enigma_otiliei"
        max_xp = 3 if enhanced_xp_chat else 5
        for attempt in range(2):
            raw_answer = answer_characters_teacher_turn(
                work_title=str(work.get("title") or "Opera"),
                work_author=str(work.get("author") or "autorul operei"),
                user_message=question,
                context_text=context_text,
                pending_question=pending_question,
                current_xp=current_xp,
                require_xp_followup=enhanced_xp_chat,
                max_xp_per_answer=max_xp,
                format_retry=attempt > 0,
            ).strip()
            parsed_answer = _parse_characters_teacher_turn(
                raw_answer,
                max_xp=max_xp,
                require_xp_followup=enhanced_xp_chat,
            )
            if not enhanced_xp_chat or _has_substantive_characters_answer(
                parsed_answer[0],
                parsed_answer[2],
            ):
                return parsed_answer

        return (
            "AI-ul nu a reușit să formuleze un răspuns complet. Te rog încearcă din nou.",
            0,
            None,
        )
    except Exception as error:
        return f"A aparut o eroare la apelul AI: {error}", 0, None


def _parse_characters_teacher_turn(
    raw_answer: str,
    max_xp: int = 5,
    require_xp_followup: bool = False,
) -> tuple[str, int, str | None]:
    if not raw_answer:
        return "", 0, None

    tagged_message = _extract_tag_content(raw_answer, "message")
    message = (
        tagged_message
        if tagged_message is not None
        else _extract_incomplete_message_content(raw_answer)
    )
    xp_text = _extract_tag_content(raw_answer, "xp") or "0"
    next_question = _extract_tag_content(raw_answer, "next_question")

    try:
        earned_xp = max(0, min(int(xp_text.strip()), max_xp))
    except ValueError:
        earned_xp = 0

    if next_question:
        next_question = next_question.strip()
        if next_question.upper() == "NONE":
            next_question = None

    message = message.strip()
    if not next_question:
        next_question = _extract_xp_question_from_message(message)

    has_substantive_answer = _has_substantive_characters_answer(
        message,
        next_question,
    )
    if require_xp_followup and has_substantive_answer:
        next_question = _normalize_xp_question(
            next_question
            or (
                "Ce trăsătură a personajului discutat ți se pare cea mai importantă "
                "și cum o poți justifica? (+XP)"
            )
        )
        if next_question.casefold() not in message.casefold():
            message = f"{message}\n\n{next_question}"
    elif require_xp_followup:
        earned_xp = 0
        next_question = None

    return message, earned_xp, next_question


def _extract_incomplete_message_content(raw_answer: str) -> str:
    opening_tag = re.search(r"<message>", raw_answer, flags=re.IGNORECASE)
    if not opening_tag:
        return raw_answer.strip()

    remainder = raw_answer[opening_tag.end() :]
    boundary = re.search(
        r"</message>|<xp>|<next_question>|$",
        remainder,
        flags=re.IGNORECASE,
    )
    content = remainder[: boundary.start()] if boundary else remainder
    return re.sub(
        r"</?(?:message|xp|next_question)>",
        "",
        content,
        flags=re.IGNORECASE,
    ).strip()


def _has_substantive_characters_answer(
    message: str,
    xp_question: str | None,
) -> bool:
    visible_answer = _remove_xp_question_from_content(
        str(message or ""),
        str(xp_question or ""),
    )
    visible_answer = re.sub(r"<[^>]+>", " ", visible_answer)
    words = re.findall(r"[^\W\d_]{2,}", visible_answer, flags=re.UNICODE)
    has_complete_ending = bool(
        re.search(r"[.!?…][\"'”»’)\]]*$", visible_answer.strip())
    )
    return len(words) >= 3 and has_complete_ending


def _extract_xp_question_from_message(message: str) -> str | None:
    match = re.search(
        r"(?:^|[.!]\s+)([^.!?\n]*\?\s*\(\+xp\))\s*$",
        message,
        flags=re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def _normalize_xp_question(question: str) -> str:
    question = re.sub(r"\s*\(\+xp\)\s*$", "", question.strip(), flags=re.IGNORECASE)
    question = question.rstrip()
    if not question.endswith("?"):
        question = question.rstrip(".! ") + "?"
    return f"{question} (+XP)"


def _extract_tag_content(text: str, tag: str) -> str | None:
    match = re.search(fr"<{tag}>(.*?)</{tag}>", text, flags=re.DOTALL | re.IGNORECASE)

    if not match:
        return None

    return match.group(1).strip()


def _render_characters_notebook(work: dict) -> None:
    _render_context_notebook(work, "characters")


def _render_context_notebook(work: dict, scope: str) -> None:
    notes_key = f"{scope}_notes_list_{work['id']}"
    selected_key = f"{scope}_selected_note_{work['id']}"
    editing_key = f"{scope}_editing_note_{work['id']}"

    _ensure_context_notes_state(work, scope, notes_key, selected_key)

    with st.container(border=True):
        note_col, action_col = st.columns([1, 0.85])

        with note_col:
            st.markdown("#### Carnetelul meu")

        with action_col:
            if st.button(
                "Adauga notita",
                key=f"add_{scope}_note_{work['id']}",
                type="primary",
                use_container_width=True,
            ):
                note = create_note(
                    work["id"],
                    scope,
                    f"Notita {len(st.session_state[notes_key]) + 1}",
                )
                st.session_state[notes_key].append(note)
                st.session_state[selected_key] = note["id"]
                st.session_state[editing_key] = note["id"]
                st.rerun()

        with st.expander("Deschide carnetelul", expanded=bool(st.session_state[notes_key])):
            _render_context_notes_list(
                work,
                scope,
                notes_key,
                selected_key,
                editing_key,
            )


def _ensure_context_notes_state(
    work: dict,
    scope: str,
    notes_key: str,
    selected_key: str,
) -> None:
    _ensure_notes_state(
        work=work,
        scope=scope,
        notes_key=notes_key,
        selected_key=selected_key,
        transient_notes=list(st.session_state.get(notes_key, [])),
    )


def _render_context_notes_list(
    work: dict,
    scope: str,
    notes_key: str,
    selected_key: str,
    editing_key: str,
) -> None:
    notes = st.session_state[notes_key]

    if not notes:
        st.caption("Nu ai notite inca. Apasa pe Adauga notita ca sa incepi.")
        return

    for note in notes:
        note_id = note["id"]
        title = note["title"].strip() or "Notita fara titlu"
        preview = note["content"].strip().replace("\n", " ")

        item_col, edit_col, delete_col = st.columns([1.05, 1.05, 0.9])

        with item_col:
            button_label = title if not preview else f"{title}\n{preview[:42]}"
            if st.button(
                button_label,
                key=f"select_{scope}_note_{work['id']}_{note_id}",
                type="primary" if st.session_state[selected_key] == note_id else "secondary",
                use_container_width=True,
            ):
                st.session_state[selected_key] = note_id
                st.session_state[editing_key] = None
                st.rerun()

        with edit_col:
            if st.button(
                "Modifica",
                key=f"edit_{scope}_note_{work['id']}_{note_id}",
                use_container_width=True,
            ):
                st.session_state[selected_key] = note_id
                st.session_state[editing_key] = note_id
                st.rerun()

        with delete_col:
            if st.button(
                "Sterge",
                key=f"delete_{scope}_note_{work['id']}_{note_id}",
                use_container_width=True,
            ):
                _delete_summary_note(notes_key, selected_key, editing_key, note_id)
                st.rerun()

    selected_note = _get_selected_summary_note(notes_key, selected_key)

    if selected_note is None:
        return

    st.divider()

    if st.session_state.get(editing_key) == selected_note["id"]:
        _render_context_note_editor(work, scope, editing_key, selected_note)
    else:
        st.markdown(f"**{selected_note['title'].strip() or 'Notita fara titlu'}**")
        st.write(selected_note["content"] or "Notita este goala. Apasa pe Modifica pentru a scrie in ea.")


def _render_context_note_editor(
    work: dict,
    scope: str,
    editing_key: str,
    note: dict,
) -> None:
    with st.form(key=f"{scope}_note_editor_{work['id']}_{note['id']}"):
        title = st.text_input("Titlu notita", value=note["title"])
        content = st.text_area(
            "Continut notita",
            value=note["content"],
            height=170,
            placeholder="Scrie aici ideea, intrebarea sau formularea pe care vrei sa o retii.",
        )

        save_col, cancel_col = st.columns(2)

        with save_col:
            save = st.form_submit_button("Salveaza", type="primary", use_container_width=True)

        with cancel_col:
            cancel = st.form_submit_button("Renunta", use_container_width=True)

    if save:
        saved_note = update_note(note["id"], title, content)
        note.update(saved_note)
        st.session_state[editing_key] = None
        st.rerun()

    if cancel:
        st.session_state[editing_key] = None
        st.rerun()


def _render_characters_dictionary(work: dict, context_text: str) -> None:
    result_key = f"characters_dictionary_result_{work['id']}"
    status_key = f"characters_dictionary_status_{work['id']}"
    input_key = f"characters_dictionary_input_{work['id']}"
    clear_key = f"characters_dictionary_clear_input_{work['id']}"

    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""

    with st.container(border=True):
        st.markdown("#### Dictionar AI")

        term = st.text_input(
            "Cauta un cuvant sau o expresie",
            key=input_key,
            placeholder="ex: arivist, tip uman, intelectual rural",
            label_visibility="collapsed",
        )
        submitted = st.button(
            "Cauta",
            key=f"search_characters_dictionary_{work['id']}",
            type="primary",
            use_container_width=True,
        )

        if submitted and not term.strip():
            st.warning("Scrie mai intai un cuvant sau o expresie.")

        if submitted and term.strip():
            st.session_state[status_key] = "Se cauta explicatia..."
            with st.spinner("Dictionarul AI cauta explicatia..."):
                st.session_state[result_key] = _explain_characters_dictionary_term(
                    work,
                    term.strip(),
                    context_text,
                )
            st.session_state[status_key] = "Explicatie primita."
            st.session_state[clear_key] = True
            st.rerun()

        if status_key in st.session_state:
            st.caption(st.session_state[status_key])

        if result_key in st.session_state and st.session_state[result_key]:
            st.write(st.session_state[result_key])


def _explain_characters_dictionary_term(work: dict, term: str, context_text: str) -> str:
    if explain_learning_context_term is None:
        return "Dictionarul AI nu este legat inca pentru personaje."

    try:
        is_poetry = work.get("type") == "poezie" or (
            Path("data")
            / "generated_works"
            / work["id"]
            / "intelegere-opera"
            / "voci-si-imagini.json"
        ).is_file()
        answer = explain_learning_context_term(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            term=term,
            context_title="Voci lirice și imagini artistice" if is_poetry else "Personaje",
            context_text=context_text,
        ).strip()
        return answer or "Dictionarul AI nu a returnat niciun raspuns. Incearca din nou."
    except Exception as error:
        return f"A aparut o eroare la apelul AI: {error}"


def _render_characters_step(work: dict, progress: dict) -> None:
    content_col, tools_col = st.columns([1.65, 1], gap="large")
    with content_col:
        _render_characters_main_panel(work)

    with tools_col:
        _render_characters_tools(work)


def _render_characters_main_panel(work: dict) -> None:
    voci_path = Path("data") / "generated_works" / work["id"] / "intelegere-opera" / "voci-si-imagini.json"
    is_poetry = work.get("type") == "poezie" or voci_path.is_file()

    selected_view_key = f"characters_main_view_{work['id']}"

    if is_poetry and voci_path.is_file():
        try:
            voci_data = json.loads(voci_path.read_text(encoding="utf-8"))
        except Exception:
            voci_data = {}

        if selected_view_key not in st.session_state or st.session_state[selected_view_key] not in ("voices", "sensory_mindmap", "relation_graph"):
            st.session_state[selected_view_key] = "voices"

        selected_view = st.session_state[selected_view_key]

        with st.container(border=True):
            if selected_view == "voices":
                st.markdown("#### 🎭 Vocile Lirice & Lirismul Măștilor")
                voices = voci_data.get("voices", [])
                cols = st.columns(len(voices) if voices else 1)
                for idx, voice in enumerate(voices):
                    with cols[idx]:
                        with st.container(border=True):
                            st.markdown(f"### {voice.get('name', 'Voce Lirică')}")
                            st.caption(f"**Rol:** {voice.get('role', '')}")
                            st.markdown(f"**Atitudine:** {voice.get('attitude', '')}")
                            st.markdown(f"**Personalitate / Arhetip:** {voice.get('personality', '')}")
                            if voice.get("physical_description"):
                                st.markdown(f"**Descriere / Prezență:** {voice.get('physical_description')}")
                            if voice.get("linguistic_markers"):
                                st.info(f"**Mărci lingvistice:**\n{voice.get('linguistic_markers')}")
                            st.markdown(f"**Strofe asociate:** `{voice.get('associated_stanzas', [])}`")

            elif selected_view == "sensory_mindmap":
                mindmap = voci_data.get("sensory_mindmap", {})
                st.markdown(f"#### 🌸 {mindmap.get('title', 'Harta Imaginilor Artistice')}")
                categories = mindmap.get("categories", [])
                for cat in categories:
                    with st.expander(f"📌 {cat.get('type', 'Categorie Senzorială')}", expanded=True):
                        for item in cat.get("items", []):
                            st.markdown(f"- **{item.get('label', '')}** (Strofa {item.get('stanza', '')})")
                            st.markdown(f"  > *«{item.get('quote', '')}»*")

            elif selected_view == "relation_graph":
                st.markdown("#### 🌐 Diagrama Relațiilor și a Planurilor Lirice")
                try:
                    mindmaps = _load_character_mindmaps(work["id"])
                    if "relation_graph" in mindmaps and mindmaps["relation_graph"]:
                        components.html(
                            _build_interactive_relation_graph_html(mindmaps["relation_graph"]),
                            height=500,
                            scrolling=False,
                        )
                    else:
                        st.info("Graful de relații nu conține date.")
                except Exception as err:
                    st.info(f"Graful de relații: {err}")

        btn_col1, btn_col2, btn_col3 = st.columns(3)
        with btn_col1:
            if st.button(
                "🎭 Voci Lirice & Măști",
                key=f"show_voices_{work['id']}",
                type="primary" if selected_view == "voices" else "secondary",
                use_container_width=True,
            ):
                st.session_state[selected_view_key] = "voices"
                st.rerun()

        with btn_col2:
            if st.button(
                "🌸 Mindmap Senzorial",
                key=f"show_sensory_{work['id']}",
                type="primary" if selected_view == "sensory_mindmap" else "secondary",
                use_container_width=True,
            ):
                st.session_state[selected_view_key] = "sensory_mindmap"
                st.rerun()

        with btn_col3:
            if st.button(
                "🌐 Relații & Planuri",
                key=f"show_relations_poezie_{work['id']}",
                type="primary" if selected_view == "relation_graph" else "secondary",
                use_container_width=True,
            ):
                st.session_state[selected_view_key] = "relation_graph"
                st.rerun()
        return

    try:
        mindmaps = _load_character_mindmaps(work["id"])
    except FileNotFoundError:
        st.info(
            "Mind-mapurile personajelor nu au fost încă generate pentru această operă. "
            "Rulează generatorul Înțelegerea operei pe knowledge graph-ul ei."
        )
        return

    if selected_view_key not in st.session_state:
        st.session_state[selected_view_key] = "hierarchy_tree"

    selected_view = st.session_state[selected_view_key]

    with st.container(border=True):
        if selected_view == "hierarchy_tree":
            st.markdown("#### Arborele personajelor")
            components.html(
                _build_interactive_character_tree_html(
                    mindmaps["tree_layout"], mindmaps["characters"]
                ),
                height=500,
                scrolling=True,
            )
        elif selected_view == "village_relations":
            st.markdown("#### Diagrama relațiilor dintre personaje")
            components.html(
                _build_interactive_relation_graph_html(mindmaps["relation_graph"]),
                height=500,
                scrolling=False,
            )

    tree_col, relations_col = st.columns(2)

    with tree_col:
        if st.button(
            "Arborele personajelor",
            key=f"show_hierarchy_tree_{work['id']}",
            type="primary" if selected_view == "hierarchy_tree" else "secondary",
            use_container_width=True,
        ):
            st.session_state[selected_view_key] = "hierarchy_tree"
            st.rerun()

    with relations_col:
        if st.button(
            "Diagrama relațiilor",
            key=f"show_village_relations_{work['id']}",
            type="primary" if selected_view == "village_relations" else "secondary",
            use_container_width=True,
        ):
            st.session_state[selected_view_key] = "village_relations"
            st.rerun()


def _render_scenes_step(work: dict, progress: dict) -> None:
    try:
        sequences = _sequences_for_work(work["id"])
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        st.info(
            "Secvențele relevante nu au fost pregătite încă pentru această operă. "
            f"Detalii: {error}"
        )
        return
    selected_sequence = _get_selected_sequence(work["id"], sequences)
    context_text = _build_sequence_context_text(selected_sequence)

    content_col, tools_col = st.columns([1.65, 1], gap="large")
    with content_col:
        _render_sequence_screen(work, selected_sequence)
        _render_sequence_buttons(work, sequences, selected_sequence["id"])

    with tools_col:
        _render_scenes_tools(work, selected_sequence, context_text)


def _sequences_for_work(work_id: str) -> list[dict]:
    try:
        return load_relevant_sequences(work_id)
    except FileNotFoundError:
        if work_id == "ion":
            return ION_SIGNIFICANT_SEQUENCES
        raise


def _get_selected_sequence(work_id: str, sequences: list[dict]) -> dict:
    selected_key = f"selected_sequence_{work_id}"

    if selected_key not in st.session_state:
        st.session_state[selected_key] = sequences[0]["id"]

    selected_id = st.session_state[selected_key]
    sequence_by_id = {sequence["id"]: sequence for sequence in sequences}

    if selected_id not in sequence_by_id:
        selected_id = sequences[0]["id"]
        st.session_state[selected_key] = selected_id

    return sequence_by_id[selected_id]


def _render_sequence_screen(work: dict, selected_sequence: dict) -> None:
    annotations = get_scene_annotations(work["id"], selected_sequence["id"])
    component_event = SCENE_ANNOTATOR_COMPONENT(
        work_id=work["id"],
        sequence_id=selected_sequence["id"],
        title=selected_sequence["title"],
        chapter=selected_sequence["chapter"],
        source=selected_sequence["source"],
        text=selected_sequence["text"],
        annotations=annotations,
        key=f"scene_annotator_v2_{work['id']}_{selected_sequence['id']}",
        default=None,
    )
    _handle_scene_annotator_event(work, selected_sequence, component_event)


def _handle_scene_annotator_event(
    work: dict,
    selected_sequence: dict,
    component_event: dict | None,
) -> None:
    if not component_event:
        return

    event_id = component_event.get("event_id")
    if not event_id:
        return

    processed_key = f"processed_scene_annotator_event_{work['id']}_{selected_sequence['id']}"
    if st.session_state.get(processed_key) == event_id:
        return

    st.session_state[processed_key] = event_id

    if component_event.get("type") == "annotations_changed":
        save_scene_annotations(
            work["id"],
            selected_sequence["id"],
            component_event.get("annotations", []),
        )
        return

    if component_event.get("type") == "ask_ai":
        selected_text = str(component_event.get("selected_text", "")).strip()
        if not selected_text:
            return

        pending_key = _scene_ai_pending_query_key(work["id"], selected_sequence["id"])
        st.session_state[pending_key] = (
            "Explică mai bine, în contextul operei și al rolului secvenței, "
            f"fragmentul marcat: „{selected_text}”. "
            "Arată ce sugerează despre personaje, temă și funcția acestei "
            "secvențe într-un eseu de Bac."
        )


def _scene_ai_pending_query_key(work_id: str, sequence_id: str) -> str:
    return f"scenes_ai_pending_annotation_query_{work_id}_{sequence_id}"


def _render_sequence_buttons(
    work: dict,
    sequences: list[dict],
    selected_sequence_id: str,
) -> None:
    selected_key = f"selected_sequence_{work['id']}"
    columns = st.columns(len(sequences), gap="small")

    for sequence, column in zip(sequences, columns):
        with column:
            if st.button(
                sequence["button_label"],
                key=f"select_sequence_{work['id']}_{sequence['id']}",
                type="primary" if selected_sequence_id == sequence["id"] else "secondary",
                use_container_width=True,
            ):
                st.session_state[selected_key] = sequence["id"]
                st.rerun()


def _build_sequence_context_text(sequence: dict) -> str:
    parts = [
        f"SECVENTA SELECTATA: {sequence['title']}",
        f"LOCALIZARE: {sequence['chapter']}",
    ]
    if sequence.get("analysis_focus"):
        parts.extend(("ROL IN ESEUL-MODEL:", str(sequence["analysis_focus"])))
    parts.extend(("TEXT DIN OPERA:", sequence["text"]))
    return "\n\n".join(parts)


def _render_scenes_tools(work: dict, selected_sequence: dict, context_text: str) -> None:
    notes_key = f"notes_popover_{work['id']}_scenes"
    dictionary_key = f"dictionary_popover_{work['id']}_scenes"
    st.markdown("### Instrumente")
    _render_scenes_ai_professor(work, selected_sequence, context_text)
    notes_col, dictionary_col = st.columns(2, gap="small")
    with notes_col:
        with st.popover(
            "Carnetelul meu",
            key=notes_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_context_notebook(work, "scenes")
            _render_popover_close_button(notes_key)
    with dictionary_col:
        with st.popover(
            "Dictionar AI",
            key=dictionary_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_scenes_dictionary(work, selected_sequence, context_text)
            _render_popover_close_button(dictionary_key)


def _render_scenes_ai_professor(
    work: dict,
    selected_sequence: dict,
    context_text: str,
) -> None:
    sequence_id = selected_sequence["id"]
    history_key = f"scenes_ai_professor_{work['id']}_{sequence_id}"
    status_key = f"scenes_ai_professor_status_{work['id']}_{sequence_id}"
    input_key = f"scenes_ai_professor_input_{work['id']}_{sequence_id}"
    clear_key = f"scenes_ai_professor_clear_input_{work['id']}_{sequence_id}"

    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""

    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    "Buna! Intreaba-ma despre secventa selectata: "
                    f"{selected_sequence['title']}."
                ),
            }
        ]

    _process_pending_scene_ai_query(
        work,
        selected_sequence,
        context_text,
        history_key,
        status_key,
    )

    with st.container(border=True):
        st.markdown("#### ✨ AI Profesor")

        chat_box = st.container(height=235, border=True)
        with chat_box:
            for message in st.session_state[history_key]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        question = st.text_area(
            "Intreaba despre secventa selectata",
            key=input_key,
            placeholder="Ce arată această secvență despre personaj?",
            height=58,
            label_visibility="collapsed",
        )
        submitted = st.button(
            "Trimite",
            key=f"send_scenes_ai_question_{work['id']}_{sequence_id}",
            type="primary",
            use_container_width=True,
        )

        if submitted and not question.strip():
            st.warning("Scrie mai intai o intrebare pentru AI Profesor.")

        if submitted and question.strip():
            st.session_state[history_key].append(
                {"role": "user", "content": question.strip()}
            )
            st.session_state[status_key] = "Se genereaza raspunsul..."
            with ai_thinking():
                answer = _answer_scenes_question(
                    work,
                    question.strip(),
                    selected_sequence,
                    context_text,
                )

            st.session_state[history_key].append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
            st.session_state[status_key] = "Raspuns primit."
            st.session_state[clear_key] = True
            st.rerun()

        if status_key in st.session_state:
            st.caption(st.session_state[status_key])


def _process_pending_scene_ai_query(
    work: dict,
    selected_sequence: dict,
    context_text: str,
    history_key: str,
    status_key: str,
) -> None:
    pending_key = _scene_ai_pending_query_key(work["id"], selected_sequence["id"])
    pending_question = st.session_state.pop(pending_key, "").strip()

    if not pending_question:
        return

    st.session_state[history_key].append(
        {"role": "user", "content": pending_question}
    )
    st.session_state[status_key] = "Se genereaza raspunsul pentru fragmentul marcat..."

    with ai_thinking("AI Profesor analizează fragmentul"):
        answer = _answer_scenes_question(
            work,
            pending_question,
            selected_sequence,
            context_text,
        )

    st.session_state[history_key].append(
        {
            "role": "assistant",
            "content": answer,
        }
    )
    st.session_state[status_key] = "Raspuns primit pentru fragmentul marcat."


def _answer_scenes_question(
    work: dict,
    question: str,
    selected_sequence: dict,
    context_text: str,
) -> str:
    if answer_learning_context_question is None:
        return "AI-ul nu este legat inca pentru secvente."

    try:
        answer = answer_learning_context_question(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            user_question=question,
            context_title=f"Secvente semnificative - {selected_sequence['title']}",
            context_text=context_text,
        ).strip()
        return answer or "AI-ul nu a returnat niciun raspuns. Incearca din nou."
    except Exception as error:
        return f"A aparut o eroare la apelul AI: {error}"


def _render_scenes_dictionary(
    work: dict,
    selected_sequence: dict,
    context_text: str,
) -> None:
    sequence_id = selected_sequence["id"]
    result_key = f"scenes_dictionary_result_{work['id']}_{sequence_id}"
    status_key = f"scenes_dictionary_status_{work['id']}_{sequence_id}"
    input_key = f"scenes_dictionary_input_{work['id']}_{sequence_id}"
    clear_key = f"scenes_dictionary_clear_input_{work['id']}_{sequence_id}"

    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""

    with st.container(border=True):
        st.markdown("#### Dictionar AI")

        term = st.text_input(
            "Cauta un cuvant sau o expresie",
            key=input_key,
            placeholder="ex: simbol, comparație, termen necunoscut",
            label_visibility="collapsed",
        )
        submitted = st.button(
            "Cauta",
            key=f"search_scenes_dictionary_{work['id']}_{sequence_id}",
            type="primary",
            use_container_width=True,
        )

        if submitted and not term.strip():
            st.warning("Scrie mai intai un cuvant sau o expresie.")

        if submitted and term.strip():
            st.session_state[status_key] = "Se cauta explicatia..."
            with st.spinner("Dictionarul AI cauta explicatia..."):
                st.session_state[result_key] = _explain_scenes_dictionary_term(
                    work,
                    term.strip(),
                    selected_sequence,
                    context_text,
                )
            st.session_state[status_key] = "Explicatie primita."
            st.session_state[clear_key] = True
            st.rerun()

        if status_key in st.session_state:
            st.caption(st.session_state[status_key])

        if result_key in st.session_state and st.session_state[result_key]:
            st.write(st.session_state[result_key])


def _explain_scenes_dictionary_term(
    work: dict,
    term: str,
    selected_sequence: dict,
    context_text: str,
) -> str:
    if explain_learning_context_term is None:
        return "Dictionarul AI nu este legat inca pentru secvente."

    try:
        answer = explain_learning_context_term(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            term=term,
            context_title=f"Secvente semnificative - {selected_sequence['title']}",
            context_text=context_text,
        ).strip()
        return answer or "Dictionarul AI nu a returnat niciun raspuns. Incearca din nou."
    except Exception as error:
        return f"A aparut o eroare la apelul AI: {error}"


def _build_interactive_character_tree_html(tree_layout: dict, characters: dict) -> str:
    tree_payload = json.dumps(tree_layout, ensure_ascii=False)
    character_payload = json.dumps(characters, ensure_ascii=False)
    first_character_id = next(iter(characters), "")
    selected_payload = json.dumps(first_character_id, ensure_ascii=False)
    tree_width = int(tree_layout.get("width") or 980)
    tree_height = int(tree_layout.get("height") or 540)

    return textwrap.dedent(
        f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                :root {{
                    color-scheme: light;
                    font-family: Inter, Segoe UI, Arial, sans-serif;
                }}

                body {{
                    margin: 0;
                    background: transparent;
                    color: #153249;
                }}

                .tree-shell {{
                    border: 1px solid #dce8e5;
                    border-radius: 8px;
                    background: #ffffff;
                    padding: 12px;
                    box-sizing: border-box;
                    animation: diagramEnter 440ms cubic-bezier(0.18, 0.9, 0.3, 1.16) both;
                }}

                .tree-help {{
                    display: none;
                    margin: 0;
                    color: #607789;
                    font-size: 13px;
                }}

                .tree-toolbar {{
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    gap: 8px;
                    margin-bottom: 8px;
                }}

                .tree-toolbar button {{
                    border: 1px solid #cbdedb;
                    border-radius: 8px;
                    background: #ffffff;
                    color: #31566a;
                    font-weight: 800;
                    min-width: 34px;
                    height: 30px;
                    cursor: pointer;
                    transform: translateY(0);
                    box-shadow: 0 2px 0 #c3d8d4;
                    transition: transform 160ms cubic-bezier(0.2, 0.85, 0.35, 1.2), border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
                }}

                .tree-toolbar button:hover {{
                    transform: translateY(-2px);
                    border-color: #8bb4e7;
                    background: #eef4fc;
                    color: #2767c7;
                    box-shadow: 0 4px 0 #bfd0e6;
                }}

                .tree-toolbar button:active {{
                    transform: translateY(1px) scale(0.96);
                    box-shadow: 0 1px 0 #bfd0e6;
                }}

                .zoom-level {{
                    color: #607789;
                    font-size: 12px;
                    min-width: 42px;
                    text-align: center;
                }}

                .tree-canvas {{
                    overflow: auto;
                    max-height: 390px;
                    border-radius: 8px;
                    background: #f8fbfa;
                }}

                svg {{
                    display: block;
                    width: 100%;
                    height: auto;
                    min-height: 360px;
                }}

                .tree-line {{
                    stroke: #9fb8b6;
                    stroke-width: 2;
                }}

                .tree-group {{
                    fill: #edf5ff;
                    stroke: #73a1db;
                    stroke-width: 1.5;
                }}

                .tree-root {{
                    fill: #e8f7f0;
                    stroke: #16875f;
                    stroke-width: 2;
                }}

                .tree-node {{
                    fill: #ffffff;
                    stroke: #3d6073;
                    stroke-width: 2;
                    cursor: pointer;
                    transition: fill 120ms ease, stroke 120ms ease, transform 120ms ease;
                }}

                .tree-hitbox {{
                    fill: transparent;
                    cursor: pointer;
                }}

                .tree-node-group:hover .tree-node {{
                    fill: #eaf2ff;
                    stroke: #2767c7;
                }}

                .tree-node-group {{
                    transform-box: fill-box;
                    transform-origin: center;
                    transition: transform 190ms cubic-bezier(0.2, 0.85, 0.35, 1.22);
                }}

                .tree-node-group:hover {{
                    transform: scale(1.08);
                }}

                .tree-node-selected {{
                    fill: #dff3ec;
                    stroke: #16875f;
                    stroke-width: 4;
                    animation: selectedNodePulse 420ms cubic-bezier(0.2, 0.9, 0.35, 1.25);
                }}

                .tree-label-dark {{
                    fill: #153249;
                    font-weight: 700;
                    font-size: 12px;
                    text-anchor: middle;
                    pointer-events: none;
                }}

                .tree-label-light {{
                    fill: #153249;
                    font-size: 11px;
                    text-anchor: middle;
                    pointer-events: none;
                }}

                .tree-label-group {{
                    fill: #235a91;
                    font-size: 11px;
                    font-weight: 700;
                    text-anchor: middle;
                    pointer-events: none;
                }}

                .tree-callout {{
                    fill: #ffffff;
                    stroke: #57999b;
                    stroke-width: 2;
                    filter: drop-shadow(0 10px 18px rgba(27, 73, 72, 0.13));
                    animation: calloutPop 260ms cubic-bezier(0.2, 0.9, 0.35, 1.2);
                }}

                .callout-title {{
                    fill: #0e293d;
                    font-size: 15px;
                    font-weight: 800;
                }}

                .callout-text {{
                    fill: #31566a;
                    font-size: 12px;
                }}

                .details-grid {{
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 12px;
                    margin-top: 12px;
                }}

                .detail-card {{
                    border: 1px solid #dce8e5;
                    border-radius: 8px;
                    padding: 10px 12px;
                    background: #f8fbfa;
                    transform: translateY(0);
                    transition: transform 180ms cubic-bezier(0.2, 0.85, 0.35, 1.15), border-color 150ms ease, box-shadow 150ms ease;
                }}

                .detail-card:hover {{
                    transform: translateY(-3px);
                    border-color: #b8d7d0;
                    box-shadow: 0 8px 17px rgba(27, 73, 72, 0.1);
                }}

                .detail-card h4 {{
                    margin: 0 0 8px;
                    font-size: 14px;
                    color: #0e293d;
                }}

                .detail-card p {{
                    margin: 0;
                    color: #49687a;
                    font-size: 14px;
                    line-height: 1.45;
                }}

                @keyframes diagramEnter {{
                    0% {{ opacity: 0; transform: translateY(8px) scale(0.985); }}
                    72% {{ opacity: 1; transform: translateY(-2px) scale(1.003); }}
                    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
                }}

                @keyframes selectedNodePulse {{
                    0% {{ stroke-width: 2; }}
                    60% {{ stroke-width: 6; }}
                    100% {{ stroke-width: 4; }}
                }}

                @keyframes calloutPop {{
                    0% {{ opacity: 0; }}
                    100% {{ opacity: 1; }}
                }}

                @media (prefers-reduced-motion: reduce) {{
                    *, *::before, *::after {{
                        animation-duration: 0.01ms !important;
                        animation-delay: 0ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                    }}
                }}

                @media (max-width: 760px) {{
                    .details-grid {{
                        grid-template-columns: 1fr;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="tree-shell">
                <p class="tree-help">Apasa pe un nod ca sa schimbi personajul. Diagrama se actualizeaza local, fara reload de pagina.</p>
                <div class="tree-toolbar" aria-label="Controale zoom">
                    <button id="zoom-out" type="button" title="Micsoreaza">-</button>
                    <span id="zoom-level" class="zoom-level">100%</span>
                    <button id="zoom-in" type="button" title="Mareste">+</button>
                    <button id="zoom-reset" type="button" title="Reset zoom">Reset</button>
                </div>
                <div class="tree-canvas">
                    <svg id="character-tree" viewBox="0 0 {tree_width} {tree_height}" role="img" aria-label="Arborele personajelor"></svg>
                </div>
                <div class="details-grid">
                    <div class="detail-card">
                        <h4>Cum arata fizic</h4>
                        <p id="detail-physical"></p>
                    </div>
                    <div class="detail-card">
                        <h4>Calitati si defecte</h4>
                        <p id="detail-traits"></p>
                    </div>
                    <div class="detail-card">
                        <h4>Rol</h4>
                        <p id="detail-role"></p>
                    </div>
                    <div class="detail-card">
                        <h4>Ce fel de om este</h4>
                        <p id="detail-type"></p>
                    </div>
                </div>
            </div>

            <script>
                const treeLayout = {tree_payload};
                const characters = {character_payload};
                const svg = document.getElementById("character-tree");
                const zoomLevel = document.getElementById("zoom-level");
                const zoomInButton = document.getElementById("zoom-in");
                const zoomOutButton = document.getElementById("zoom-out");
                const zoomResetButton = document.getElementById("zoom-reset");
                const ns = "http://www.w3.org/2000/svg";
                let selectedId = {selected_payload};
                let zoom = 1;

                function updateZoom() {{
                    svg.style.width = `${{zoom * 100}}%`;
                    zoomLevel.textContent = `${{Math.round(zoom * 100)}}%`;
                }}

                zoomInButton.addEventListener("click", () => {{
                    zoom = Math.min(2, Number((zoom + 0.15).toFixed(2)));
                    updateZoom();
                }});

                zoomOutButton.addEventListener("click", () => {{
                    zoom = Math.max(0.75, Number((zoom - 0.15).toFixed(2)));
                    updateZoom();
                }});

                zoomResetButton.addEventListener("click", () => {{
                    zoom = 1;
                    updateZoom();
                }});

                function makeSvg(tag, attrs = {{}}, text = "") {{
                    const element = document.createElementNS(ns, tag);
                    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
                    if (text) element.textContent = text;
                    return element;
                }}

                function addLine(x1, y1, x2, y2) {{
                    svg.appendChild(makeSvg("line", {{
                        class: "tree-line",
                        x1,
                        y1,
                        x2,
                        y2,
                    }}));
                }}

                function initials(name) {{
                    const parts = name.split(/\\s+/).filter(Boolean);
                    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
                    return parts.slice(0, 2).map((part) => part[0].toUpperCase()).join("");
                }}

                function wrapText(text, maxChars = 48, maxLines = 2) {{
                    const words = text.split(/\\s+/);
                    const lines = [];
                    let current = "";

                    for (const word of words) {{
                        const candidate = `${{current}} ${{word}}`.trim();
                        if (candidate.length <= maxChars) {{
                            current = candidate;
                            continue;
                        }}

                        if (current) lines.push(current);
                        current = word;
                        if (lines.length === maxLines) break;
                    }}

                    if (current && lines.length < maxLines) lines.push(current);
                    if (lines.length === maxLines && words.join(" ").length > lines.join(" ").length) {{
                        lines[lines.length - 1] = `${{lines[lines.length - 1].replace(/\\.$/, "")}}...`;
                    }}
                    return lines;
                }}

                function calloutPosition(x, y) {{
                    if (x > 625) return {{ x: x - 345, y: Math.max(18, y - 88) }};
                    return {{ x: Math.min(x + 42, 645), y: Math.max(18, y - 88) }};
                }}

                function drawStaticTree() {{
                    svg.innerHTML = "";
                    const root = treeLayout.root;

                    for (const group of treeLayout.groups) {{
                        addLine(root.x, root.y + 24, group.x, group.y - 24);

                        for (const characterId of group.character_ids) {{
                            const position = treeLayout.characters[characterId];
                            addLine(group.x, group.y + 24, position.x, position.y - 22);
                        }}
                    }}

                    svg.appendChild(makeSvg("rect", {{
                        class: "tree-root",
                        x: root.x - 78,
                        y: root.y - 24,
                        width: 156,
                        height: 48,
                        rx: 18,
                    }}));
                    svg.appendChild(makeSvg("text", {{
                        class: "tree-label-light",
                        x: root.x,
                        y: root.y + 5,
                    }}, root.label));

                    for (const group of treeLayout.groups) {{
                        svg.appendChild(makeSvg("rect", {{
                            class: "tree-group",
                            x: group.x - 82,
                            y: group.y - 24,
                            width: 164,
                            height: 48,
                            rx: 16,
                        }}));
                        svg.appendChild(makeSvg("text", {{
                            class: "tree-label-group",
                            x: group.x,
                            y: group.y + 4,
                        }}, group.label));
                    }}

                    Object.entries(treeLayout.characters).forEach(([characterId, position]) => {{
                        const character = characters[characterId];
                        const nodeGroup = makeSvg("g", {{
                            class: "tree-node-group",
                            "data-character-id": characterId,
                            role: "button",
                            tabindex: 0,
                        }});

                        nodeGroup.appendChild(makeSvg("rect", {{
                            class: "tree-hitbox",
                            x: position.x - 58,
                            y: position.y - 30,
                            width: 116,
                            height: 88,
                            rx: 12,
                        }}));
                        nodeGroup.appendChild(makeSvg("circle", {{
                            class: characterId === selectedId ? "tree-node tree-node-selected" : "tree-node",
                            cx: position.x,
                            cy: position.y,
                            r: 22,
                        }}));
                        nodeGroup.appendChild(makeSvg("text", {{
                            class: characterId === selectedId ? "tree-label-light" : "tree-label-dark",
                            x: position.x,
                            y: position.y + 5,
                        }}, initials(character.name)));
                        nodeGroup.appendChild(makeSvg("text", {{
                            class: "tree-label-light",
                            x: position.x,
                            y: position.y + 42,
                        }}, character.tree_label || character.name));

                        nodeGroup.addEventListener("click", () => selectCharacter(characterId));
                        nodeGroup.addEventListener("keydown", (event) => {{
                            if (event.key === "Enter" || event.key === " ") {{
                                event.preventDefault();
                                selectCharacter(characterId);
                            }}
                        }});

                        svg.appendChild(nodeGroup);
                    }});

                    drawCallout();
                }}

                function drawCallout() {{
                    svg.querySelectorAll(".dynamic-callout").forEach((element) => element.remove());

                    const character = characters[selectedId];
                    const position = treeLayout.characters[selectedId];
                    const box = calloutPosition(position.x, position.y);
                    const connectorX = box.x > position.x ? box.x : box.x + 315;
                    const connectorY = box.y + 74;
                    const group = makeSvg("g", {{ class: "dynamic-callout" }});

                    group.appendChild(makeSvg("line", {{
                        class: "tree-line",
                        x1: position.x,
                        y1: position.y,
                        x2: connectorX,
                        y2: connectorY,
                    }}));
                    group.appendChild(makeSvg("rect", {{
                        class: "tree-callout",
                        x: box.x,
                        y: box.y,
                        width: 315,
                        height: 170,
                        rx: 12,
                    }}));
                    group.appendChild(makeSvg("text", {{
                        class: "callout-title",
                        x: box.x + 16,
                        y: box.y + 26,
                    }}, character.name));

                    const lines = [
                        character.short_role,
                        `Trasaturi: ${{character.traits}}`,
                        `Rol: ${{character.village_role}}`,
                        `Tip: ${{character.human_type}}`,
                    ].flatMap((line) => wrapText(line, 48, 2)).slice(0, 7);

                    lines.forEach((line, index) => {{
                        group.appendChild(makeSvg("text", {{
                            class: "callout-text",
                            x: box.x + 16,
                            y: box.y + 46 + index * 18,
                        }}, line));
                    }});

                    svg.appendChild(group);
                }}

                function updateDetails() {{
                    const character = characters[selectedId];
                    document.getElementById("detail-physical").textContent = character.physical;
                    document.getElementById("detail-traits").textContent = character.traits;
                    document.getElementById("detail-role").textContent = character.village_role;
                    document.getElementById("detail-type").textContent = character.human_type;
                }}

                function selectCharacter(characterId) {{
                    selectedId = characterId;
                    svg.querySelectorAll(".tree-node-group").forEach((nodeGroup) => {{
                        const circle = nodeGroup.querySelector("circle");
                        const label = nodeGroup.querySelector("text");
                        const isSelected = nodeGroup.dataset.characterId === selectedId;
                        circle.setAttribute("class", isSelected ? "tree-node tree-node-selected" : "tree-node");
                        label.setAttribute("class", isSelected ? "tree-label-light" : "tree-label-dark");
                    }});
                    drawCallout();
                    updateDetails();
                }}

                updateZoom();
                drawStaticTree();
                updateDetails();
            </script>
        </body>
        </html>
        """
    ).strip()


def _normalize_relation_graph(relation_graph: dict) -> dict:
    """Acceptă atât contractul vechi al personajelor, cât și graful liric."""
    raw_nodes = relation_graph.get("nodes") if isinstance(relation_graph, dict) else {}
    if isinstance(raw_nodes, dict):
        nodes = {str(node_id): dict(node) for node_id, node in raw_nodes.items()}
    elif isinstance(raw_nodes, list):
        nodes = {}
        count = max(len(raw_nodes), 1)
        for index, raw_node in enumerate(raw_nodes):
            if not isinstance(raw_node, dict) or not raw_node.get("id"):
                continue
            angle = (-math.pi / 2) + (2 * math.pi * index / count)
            node = dict(raw_node)
            node.setdefault("x", round(490 + math.cos(angle) * 310, 2))
            node.setdefault("y", round(280 + math.sin(angle) * 205, 2))
            node.setdefault("label", str(node.get("id")))
            node.setdefault("group", "concept")
            nodes[str(node["id"])] = node
    else:
        nodes = {}

    edges = []
    for raw_edge in relation_graph.get("edges", []) if isinstance(relation_graph, dict) else []:
        if not isinstance(raw_edge, dict):
            continue
        source = str(raw_edge.get("source") or raw_edge.get("from") or "")
        target = str(raw_edge.get("target") or raw_edge.get("to") or "")
        if source not in nodes or target not in nodes:
            continue
        label = str(raw_edge.get("label") or raw_edge.get("title") or "Relație")
        edges.append(
            {
                **raw_edge,
                "source": source,
                "target": target,
                "title": str(raw_edge.get("title") or label),
                "text": str(raw_edge.get("text") or raw_edge.get("description") or label),
            }
        )

    groups = []
    group_labels = {
        "voice": "voce lirică",
        "plane": "plan poetic",
        "symbol": "simbol",
        "concept": "concept",
        "theme": "temă",
    }
    for node in nodes.values():
        group = str(node.get("group") or "concept")
        if group not in {item["group"] for item in groups}:
            groups.append({"group": group, "label": group_labels.get(group, group)})

    return {
        **(relation_graph if isinstance(relation_graph, dict) else {}),
        "central_node_id": str(
            relation_graph.get("central_node_id")
            or next(iter(nodes), "")
        ),
        "nodes": nodes,
        "edges": edges,
        "legend": relation_graph.get("legend") or groups,
    }


def _build_interactive_relation_graph_html(relation_graph: dict) -> str:
    relation_graph = _normalize_relation_graph(relation_graph)
    graph_payload = json.dumps(relation_graph, ensure_ascii=False)
    legend_colors = {
        "central": "#ef4444",
        "victim": "#f97316",
        "poor": "#2563eb",
        "rich": "#16a34a",
        "intellectual": "#7c3aed",
        "authority": "#c2410c",
        "witness": "#0891b2",
        "voice": "#7c3aed",
        "plane": "#2563eb",
        "symbol": "#db2777",
        "concept": "#0f766e",
        "theme": "#c2410c",
    }
    legend = relation_graph.get("legend") or [
        {"group": "central", "label": "central"},
        {"group": "victim", "label": "victimă"},
        {"group": "poor", "label": "țărani săraci"},
        {"group": "rich", "label": "țărani înstăriți"},
        {"group": "intellectual", "label": "intelectuali"},
        {"group": "authority", "label": "autoritate"},
        {"group": "witness", "label": "martor"},
    ]
    legend_html = "".join(
        f'<span style="--legend-color:{legend_colors.get(item.get("group"), "#607789")}">'
        f'{item.get("label", item.get("group", ""))}</span>'
        for item in legend
    )

    return textwrap.dedent(
        f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                :root {{
                    color-scheme: light;
                    font-family: Inter, Segoe UI, Arial, sans-serif;
                }}

                body {{
                    margin: 0;
                    background: transparent;
                    color: #153249;
                }}

                .graph-shell {{
                    position: relative;
                    border: 1px solid #dce8e5;
                    border-radius: 8px;
                    background: #ffffff;
                    padding: 12px;
                    box-sizing: border-box;
                    overflow: hidden;
                    animation: graphEnter 440ms cubic-bezier(0.18, 0.9, 0.3, 1.16) both;
                }}

                .graph-toolbar {{
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    gap: 8px;
                    margin-bottom: 8px;
                }}

                .graph-toolbar button {{
                    border: 1px solid #cbdedb;
                    border-radius: 8px;
                    background: #ffffff;
                    color: #31566a;
                    font-weight: 800;
                    min-width: 34px;
                    height: 30px;
                    cursor: pointer;
                    transform: translateY(0);
                    box-shadow: 0 2px 0 #c3d8d4;
                    transition: transform 160ms cubic-bezier(0.2, 0.85, 0.35, 1.2), border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
                }}

                .graph-toolbar button:hover {{
                    transform: translateY(-2px);
                    border-color: #8bb4e7;
                    background: #eef4fc;
                    color: #2767c7;
                    box-shadow: 0 4px 0 #bfd0e6;
                }}

                .graph-toolbar button:active {{
                    transform: translateY(1px) scale(0.96);
                    box-shadow: 0 1px 0 #bfd0e6;
                }}

                .graph-zoom-level {{
                    color: #607789;
                    font-size: 12px;
                    min-width: 42px;
                    text-align: center;
                }}

                .graph-canvas {{
                    overflow: auto;
                    max-height: 520px;
                    border-radius: 8px;
                    background: #f8fbfa;
                }}

                svg {{
                    display: block;
                    width: 100%;
                    height: auto;
                }}

                .relation-line {{
                    stroke: #a8bdbb;
                    stroke-width: 2;
                    transition: stroke 140ms ease, stroke-width 140ms ease;
                }}

                .relation-hitbox {{
                    stroke: transparent;
                    stroke-width: 18;
                    cursor: help;
                }}

                .relation-edge:hover .relation-line {{
                    stroke: #2767c7;
                    stroke-width: 4;
                }}

                .node-circle {{
                    stroke: #ffffff;
                    stroke-width: 2;
                    filter: drop-shadow(0 6px 10px rgba(27, 73, 72, 0.16));
                }}

                .relation-node {{
                    cursor: pointer;
                    transform-box: fill-box;
                    transform-origin: center;
                    transition: transform 190ms cubic-bezier(0.2, 0.85, 0.35, 1.22);
                }}

                .relation-node:hover {{
                    transform: scale(1.09);
                }}

                .node-central {{ fill: #ef4444; }}
                .node-victim {{ fill: #f97316; }}
                .node-poor {{ fill: #2563eb; }}
                .node-rich {{ fill: #16a34a; }}
                .node-intellectual {{ fill: #7c3aed; }}
                .node-authority {{ fill: #c2410c; }}
                .node-witness {{ fill: #0891b2; }}
                .node-voice {{ fill: #7c3aed; }}
                .node-plane {{ fill: #2563eb; }}
                .node-symbol {{ fill: #db2777; }}
                .node-concept {{ fill: #0f766e; }}
                .node-theme {{ fill: #c2410c; }}

                .node-label {{
                    fill: #ffffff;
                    font-size: 13px;
                    font-weight: 800;
                    text-anchor: middle;
                    pointer-events: none;
                }}

                .node-role {{
                    fill: #dbeafe;
                    font-size: 10px;
                    text-anchor: middle;
                    pointer-events: none;
                }}

                .tooltip {{
                    position: absolute;
                    display: none;
                    max-width: 330px;
                    border: 1px solid #9dbce8;
                    border-radius: 8px;
                    background: #ffffff;
                    color: #153249;
                    padding: 12px;
                    box-shadow: 0 14px 28px rgba(27, 73, 72, 0.16);
                    pointer-events: none;
                    z-index: 10;
                    animation: graphTooltipPop 180ms cubic-bezier(0.2, 0.9, 0.35, 1.2);
                }}

                .tooltip-title {{
                    font-weight: 900;
                    margin-bottom: 6px;
                }}

                .tooltip-text {{
                    font-size: 13px;
                    line-height: 1.45;
                    color: #49687a;
                }}

                .legend {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 8px 14px;
                    margin-top: 8px;
                    color: #607789;
                    font-size: 12px;
                }}

                .legend span::before {{
                    content: "";
                    display: inline-block;
                    width: 9px;
                    height: 9px;
                    border-radius: 999px;
                    margin-right: 6px;
                    background: var(--legend-color);
                }}

                .legend span {{
                    transition: transform 170ms cubic-bezier(0.2, 0.85, 0.35, 1.18), color 150ms ease;
                }}

                .legend span:hover {{
                    transform: translateY(-2px);
                    color: #153249;
                }}

                @keyframes graphEnter {{
                    0% {{ opacity: 0; transform: translateY(8px) scale(0.985); }}
                    72% {{ opacity: 1; transform: translateY(-2px) scale(1.003); }}
                    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
                }}

                @keyframes graphTooltipPop {{
                    0% {{ opacity: 0; transform: translateY(5px) scale(0.96); }}
                    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
                }}

                @media (prefers-reduced-motion: reduce) {{
                    *, *::before, *::after {{
                        animation-duration: 0.01ms !important;
                        animation-delay: 0ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="graph-shell">
                <div class="graph-toolbar" aria-label="Controale zoom">
                    <button id="relation-zoom-out" type="button" title="Micsoreaza">-</button>
                    <span id="relation-zoom-level" class="graph-zoom-level">100%</span>
                    <button id="relation-zoom-in" type="button" title="Mareste">+</button>
                    <button id="relation-zoom-reset" type="button" title="Reset zoom">Reset</button>
                </div>
                <div class="graph-canvas">
                    <svg id="relation-graph" viewBox="0 0 980 560" role="img" aria-label="Diagrama relațiilor din operă"></svg>
                </div>
                <div class="legend">
                    {legend_html}
                </div>
                <div id="edge-tooltip" class="tooltip">
                    <div id="tooltip-title" class="tooltip-title"></div>
                    <div id="tooltip-text" class="tooltip-text"></div>
                </div>
            </div>

            <script>
                const graph = {graph_payload};
                const svg = document.getElementById("relation-graph");
                const tooltip = document.getElementById("edge-tooltip");
                const tooltipTitle = document.getElementById("tooltip-title");
                const tooltipText = document.getElementById("tooltip-text");
                const zoomLevel = document.getElementById("relation-zoom-level");
                const zoomInButton = document.getElementById("relation-zoom-in");
                const zoomOutButton = document.getElementById("relation-zoom-out");
                const zoomResetButton = document.getElementById("relation-zoom-reset");
                const ns = "http://www.w3.org/2000/svg";
                let zoom = 1;

                function updateZoom() {{
                    svg.style.width = `${{zoom * 100}}%`;
                    zoomLevel.textContent = `${{Math.round(zoom * 100)}}%`;
                }}

                zoomInButton.addEventListener("click", () => {{
                    zoom = Math.min(2, Number((zoom + 0.15).toFixed(2)));
                    updateZoom();
                }});

                zoomOutButton.addEventListener("click", () => {{
                    zoom = Math.max(0.75, Number((zoom - 0.15).toFixed(2)));
                    updateZoom();
                }});

                zoomResetButton.addEventListener("click", () => {{
                    zoom = 1;
                    updateZoom();
                }});

                function makeSvg(tag, attrs = {{}}, text = "") {{
                    const element = document.createElementNS(ns, tag);
                    Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
                    if (text) element.textContent = text;
                    return element;
                }}

                function midpoint(a, b) {{
                    return {{
                        x: (a.x + b.x) / 2,
                        y: (a.y + b.y) / 2,
                    }};
                }}

                function edgeCurve(source, target) {{
                    const mid = midpoint(source, target);
                    const dx = target.x - source.x;
                    const dy = target.y - source.y;
                    const length = Math.max(Math.sqrt(dx * dx + dy * dy), 1);
                    const offset = Math.min(42, length * 0.16);
                    const cx = mid.x - (dy / length) * offset;
                    const cy = mid.y + (dx / length) * offset;
                    return `M ${{source.x}} ${{source.y}} Q ${{cx}} ${{cy}} ${{target.x}} ${{target.y}}`;
                }}

                function showTooltip(event, edge) {{
                    tooltipTitle.textContent = edge.title;
                    tooltipText.textContent = edge.text;
                    tooltip.style.display = "block";
                    moveTooltip(event);
                }}

                function moveTooltip(event) {{
                    const shellRect = tooltip.parentElement.getBoundingClientRect();
                    const left = event.clientX - shellRect.left + 14;
                    const top = event.clientY - shellRect.top + 14;
                    const maxLeft = shellRect.width - tooltip.offsetWidth - 12;
                    const maxTop = shellRect.height - tooltip.offsetHeight - 12;
                    tooltip.style.left = `${{Math.max(8, Math.min(left, maxLeft))}}px`;
                    tooltip.style.top = `${{Math.max(8, Math.min(top, maxTop))}}px`;
                }}

                function hideTooltip() {{
                    tooltip.style.display = "none";
                }}

                function drawEdges() {{
                    for (const edge of graph.edges) {{
                        const source = graph.nodes[edge.source];
                        const target = graph.nodes[edge.target];
                        const path = edgeCurve(source, target);
                        const group = makeSvg("g", {{ class: "relation-edge" }});

                        group.appendChild(makeSvg("path", {{
                            class: "relation-line",
                            d: path,
                            fill: "none",
                        }}));
                        group.appendChild(makeSvg("path", {{
                            class: "relation-hitbox",
                            d: path,
                            fill: "none",
                        }}));

                        group.addEventListener("mouseenter", (event) => showTooltip(event, edge));
                        group.addEventListener("mousemove", moveTooltip);
                        group.addEventListener("mouseleave", hideTooltip);
                        svg.appendChild(group);
                    }}
                }}

                function drawNodes() {{
                    Object.entries(graph.nodes).forEach(([nodeId, node]) => {{
                        const group = makeSvg("g", {{ class: "relation-node", "data-node-id": nodeId }});
                        const nodeClass = `node-circle node-${{node.group}}`;

                        group.appendChild(makeSvg("circle", {{
                            class: nodeClass,
                            cx: node.x,
                            cy: node.y,
                            r: nodeId === graph.central_node_id ? 34 : 28,
                        }}));
                        group.appendChild(makeSvg("text", {{
                            class: "node-label",
                            x: node.x,
                            y: node.y + 4,
                        }}, node.label));

                        svg.appendChild(group);
                    }});
                }}

                updateZoom();
                drawEdges();
                drawNodes();
            </script>
        </body>
        </html>
        """
    ).strip()


def _render_streamlit_character_tree() -> None:
    _render_character_tree()


def _render_character_tree() -> None:
    selected_character_id = st.session_state.get("selected_character_ion", "ion")

    if selected_character_id not in CHARACTER_BY_ID:
        selected_character_id = "ion"
        st.session_state["selected_character_ion"] = selected_character_id

    tree_col, detail_col = st.columns([1.35, 1], gap="large")

    with tree_col:
        _render_native_character_tree(selected_character_id)

    with detail_col:
        _render_native_character_details(selected_character_id)


def _render_native_character_tree(selected_character_id: str) -> None:
    st.caption("Apasa pe un nod. Se actualizeaza doar selectia personajului, fara schimbare de URL.")
    st.markdown(
        """
        <style>
            .native-tree-root {
                border: 1px solid #a9d5c5;
                background: #e8f7f0;
                border-radius: 8px;
                padding: 0.7rem 1rem;
                text-align: center;
                font-weight: 800;
                margin-bottom: 0.5rem;
            }

            .native-tree-branches {
                text-align: center;
                color: #83a29f;
                font-family: Consolas, monospace;
                line-height: 1.1;
                margin-bottom: 0.5rem;
                white-space: pre;
            }

            .native-tree-group {
                border: 1px solid #c6d9f2;
                background: #f1f6fd;
                border-radius: 8px;
                padding: 0.65rem;
                min-height: 100%;
            }

            .native-tree-group-title {
                font-weight: 800;
                font-size: 0.86rem;
                margin-bottom: 0.25rem;
                color: #235a91;
            }

            .native-tree-group-caption {
                color: #607789;
                font-size: 0.76rem;
                line-height: 1.35;
                min-height: 3.1rem;
                margin-bottom: 0.55rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="native-tree-root">Satul Pripas</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="native-tree-branches">+--------------+--------------+--------------+</div>',
        unsafe_allow_html=True,
    )

    group_cols = st.columns(4, gap="small")

    for group, group_col in zip(ION_CHARACTER_GROUPS, group_cols):
        with group_col:
            st.markdown(
                f"""
                <div class="native-tree-group">
                    <div class="native-tree-group-title">{group["title"]}</div>
                    <div class="native-tree-group-caption">{group["caption"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            for character in group["characters"]:
                is_selected = character["id"] == selected_character_id
                label = f"{'[x]' if is_selected else '[ ]'} {character['name']}"
                st.button(
                    label,
                    key=f"native_character_node_{character['id']}",
                    type="primary" if is_selected else "secondary",
                    use_container_width=True,
                    on_click=_select_character_node,
                    args=(character["id"],),
                )


def _select_character_node(character_id: str) -> None:
    st.session_state["selected_character_ion"] = character_id


def _render_native_character_details(character_id: str) -> None:
    character = CHARACTER_BY_ID[character_id]

    st.markdown(f"#### {character['name']}")
    st.caption(character["short_role"])

    with st.container(border=True):
        st.markdown("**Cum arata fizic**")
        st.write(character["physical"])

    with st.container(border=True):
        st.markdown("**Calitati si defecte**")
        st.write(character["traits"])

    with st.container(border=True):
        st.markdown("**Rol**")
        st.write(character["village_role"])

    with st.container(border=True):
        st.markdown("**Ce fel de om este**")
        st.write(character["human_type"])


def _render_composition_step(work: dict, progress: dict) -> None:
    try:
        payload = load_composition_schemas(work["id"])
    except FileNotFoundError:
        st.info(
            "Schemele compoziționale nu au fost încă generate. Rulează generatorul "
            "cu Qwen 3.7 Flash pe knowledge graph-ul acestei opere."
        )
        return
    except (ValueError, json.JSONDecodeError) as error:
        st.error(f"Schemele compoziționale nu pot fi încărcate: {error}")
        return

    elements = [element for element in payload["elements"] if isinstance(element, dict)]
    if not elements:
        st.info("Fișierul generat nu conține nicio schemă compozițională.")
        return

    view_key = f"composition_main_view_{work['id']}"
    known_ids = [str(element.get("id") or "") for element in elements]
    if st.session_state.get(view_key) not in known_ids:
        st.session_state[view_key] = known_ids[0]
    selected_element = next(
        element
        for element in elements
        if str(element.get("id") or "") == st.session_state[view_key]
    )
    content_col, tools_col = st.columns([1.65, 1], gap="large")
    with content_col:
        _render_composition_main_panel(
            work, progress, elements, selected_element, view_key
        )
    with tools_col:
        _render_composition_tools(work, selected_element)


def _render_composition_main_panel(
    work: dict,
    progress: dict,
    elements: list[dict],
    selected_element: dict,
    view_key: str,
) -> None:
    selected_id = str(selected_element.get("id") or "")
    essay_elements = progress.get("composition_selected_elements", [])
    if not isinstance(essay_elements, list):
        essay_elements = []
    essay_elements = [str(value) for value in essay_elements if value][:2]

    with st.container(border=True):
        st.markdown(f"#### Schema: {selected_element.get('title', selected_id)}")
        components.html(
            _build_composition_mindmap_html(selected_element),
            height=610,
            scrolling=False,
        )

    view_columns = st.columns(len(elements), gap="small")
    for element, column in zip(elements, view_columns):
        element_id = str(element.get("id") or "")
        with column:
            if st.button(
                str(element.get("title") or element_id),
                key=f"show_composition_{work['id']}_{element_id}",
                type="primary" if element_id == selected_id else "secondary",
                use_container_width=True,
            ):
                st.session_state[view_key] = element_id
                st.rerun()

    is_selected = selected_id in essay_elements
    selection_is_full = len(essay_elements) >= 2 and not is_selected
    action_col, status_col = st.columns([0.72, 1.28], gap="small")
    with action_col:
        if st.button(
            "✓ Abordez în eseu" if is_selected else "Abordez în eseu",
            key=f"select_composition_{work['id']}_{selected_id}",
            type="primary" if is_selected else "secondary",
            use_container_width=True,
            disabled=selection_is_full,
            help=(
                "Ai ales deja două elemente. Elimină unul înainte să-l alegi pe acesta."
                if selection_is_full
                else None
            ),
        ):
            next_selected = list(essay_elements)
            if is_selected:
                next_selected.remove(selected_id)
            else:
                next_selected.append(selected_id)
            update_composition_selection(work["id"], next_selected)
            st.rerun()
    with status_col:
        selected_titles = [
            str(element.get("title") or element.get("id"))
            for element in elements
            if str(element.get("id")) in essay_elements
        ]
        if len(essay_elements) == 2:
            st.success("În eseu: " + " + ".join(selected_titles))
        else:
            remaining = 2 - len(essay_elements)
            st.info(f"Mai alege {remaining} {'element' if remaining == 1 else 'elemente'}.")


def _composition_context_text(element: dict) -> str:
    parts = [
        f"ELEMENT: {element.get('title', '')}",
        f"IDEE CENTRALĂ: {element.get('central_idea', '')}",
    ]
    for branch in element.get("branches", []):
        if not isinstance(branch, dict):
            continue
        parts.extend(
            [
                f"RAMURĂ: {branch.get('heading', '')}",
                f"IDEE-CHEIE: {branch.get('key_idea', '')}",
                f"EXPLICAȚIE: {branch.get('explanation', '')}",
            ]
        )
    formulas = [str(value) for value in element.get("memory_formula", []) if value]
    if formulas:
        parts.append("FORMULĂ DE MEMORARE: " + " → ".join(formulas))
    if element.get("essay_paragraph"):
        parts.append("PARAGRAF PENTRU ESEU: " + str(element["essay_paragraph"]))
    return "\n\n".join(parts)


def _render_composition_tools(work: dict, element: dict) -> None:
    context_text = _composition_context_text(element)
    element_id = str(element.get("id") or "")
    notes_key = f"notes_popover_{work['id']}_composition"
    dictionary_key = f"dictionary_popover_{work['id']}_composition_{element_id}"
    st.markdown("### Instrumente")
    _render_composition_ai_professor(work, element, context_text)
    notes_col, dictionary_col = st.columns(2, gap="small")
    with notes_col:
        with st.popover(
            "Carnetelul meu",
            key=notes_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_context_notebook(work, "composition")
            _render_popover_close_button(notes_key)
    with dictionary_col:
        with st.popover(
            "Dictionar AI",
            key=dictionary_key,
            use_container_width=True,
            width=420,
            on_change="rerun",
        ):
            _render_composition_dictionary(work, element, context_text)
            _render_popover_close_button(dictionary_key)


def _render_composition_ai_professor(work: dict, element: dict, context_text: str) -> None:
    element_id = str(element.get("id") or "")
    history_key = f"composition_ai_professor_{work['id']}_{element_id}"
    input_key = f"composition_ai_professor_input_{work['id']}_{element_id}"
    clear_key = f"composition_ai_professor_clear_{work['id']}_{element_id}"
    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""
    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": f"Bună! Întreabă-mă despre schema «{element.get('title', '')}».",
            }
        ]
    with st.container(border=True):
        st.markdown("#### ✨ AI Profesor")
        with st.container(height=235, border=True):
            for message in st.session_state[history_key]:
                with st.chat_message(message["role"]):
                    st.write(message["content"])
        question = st.text_area(
            "Întreabă despre schema selectată",
            key=input_key,
            placeholder="Cum explic această idee în eseu?",
            height=58,
            label_visibility="collapsed",
        )
        if st.button(
            "Trimite",
            key=f"send_composition_ai_{work['id']}_{element_id}",
            type="primary",
            use_container_width=True,
        ):
            if not question.strip():
                st.warning("Scrie mai întâi o întrebare pentru AI Profesor.")
            else:
                st.session_state[history_key].append(
                    {"role": "user", "content": question.strip()}
                )
                with ai_thinking():
                    answer = _answer_composition_question(
                        work, question.strip(), element, context_text
                    )
                st.session_state[history_key].append(
                    {"role": "assistant", "content": answer}
                )
                st.session_state[clear_key] = True
                st.rerun()


def _answer_composition_question(
    work: dict,
    question: str,
    element: dict,
    context_text: str,
) -> str:
    if answer_learning_context_question is None:
        return "AI-ul nu este legat încă pentru elementele compoziționale."
    try:
        answer = answer_learning_context_question(
            work_title=str(work.get("title") or "Opera"),
            work_author=str(work.get("author") or "autorul operei"),
            user_question=question,
            context_title=f"Element compozițional – {element.get('title', '')}",
            context_text=context_text,
        ).strip()
        return answer or "AI-ul nu a returnat niciun răspuns. Încearcă din nou."
    except Exception as error:
        return f"A apărut o eroare la apelul AI: {error}"


def _render_composition_dictionary(work: dict, element: dict, context_text: str) -> None:
    element_id = str(element.get("id") or "")
    result_key = f"composition_dictionary_result_{work['id']}_{element_id}"
    input_key = f"composition_dictionary_input_{work['id']}_{element_id}"
    clear_key = f"composition_dictionary_clear_{work['id']}_{element_id}"
    if st.session_state.pop(clear_key, False):
        st.session_state[input_key] = ""
    with st.container(border=True):
        st.markdown("#### Dictionar AI")
        term = st.text_input(
            "Caută un termen",
            key=input_key,
            placeholder="ex: incipit, conflict interior, eponim",
            label_visibility="collapsed",
        )
        if st.button(
            "Caută",
            key=f"search_composition_dictionary_{work['id']}_{element_id}",
            type="primary",
            use_container_width=True,
        ):
            if not term.strip():
                st.warning("Scrie mai întâi un cuvânt sau o expresie.")
            elif explain_learning_context_term is None:
                st.session_state[result_key] = "Dicționarul AI nu este legat încă."
            else:
                try:
                    st.session_state[result_key] = explain_learning_context_term(
                        work_title=str(work.get("title") or "Opera"),
                        work_author=str(work.get("author") or "autorul operei"),
                        term=term.strip(),
                        context_title=f"Element compozițional – {element.get('title', '')}",
                        context_text=context_text,
                    ).strip()
                except Exception as error:
                    st.session_state[result_key] = f"A apărut o eroare: {error}"
            st.session_state[clear_key] = True
            st.rerun()
        if st.session_state.get(result_key):
            st.write(st.session_state[result_key])


def _build_composition_mindmap_html(element: dict) -> str:
    payload = json.dumps(element, ensure_ascii=False).replace("</", "<\\/")
    return textwrap.dedent(
        f"""
        <!doctype html>
        <html lang="ro">
        <head>
          <meta charset="utf-8" />
          <style>
            :root {{ font-family: Inter, "Segoe UI", Arial, sans-serif; color:#173447; }}
            * {{ box-sizing:border-box; }}
            body {{ margin:0; background:transparent; }}
            .shell {{ border:1px solid #dce8e5; border-radius:12px; background:#fff; padding:10px; }}
            .toolbar {{ display:flex; justify-content:flex-end; align-items:center; gap:7px; margin-bottom:7px; }}
            .toolbar button {{ min-width:32px; height:29px; border:1px solid #cbdedb; border-radius:8px; background:#fff; color:#31566a; font-weight:800; cursor:pointer; }}
            .zoom {{ min-width:42px; color:#607789; font-size:12px; text-align:center; }}
            .viewport {{ height:388px; overflow:auto; border-radius:9px; background:radial-gradient(circle at 50% 47%,#e9f7f3 0,transparent 30%),#f8fbfa; }}
            .stage {{ position:relative; width:900px; height:388px; transform-origin:top left; transition:transform .18s ease; }}
            svg {{ position:absolute; inset:0; width:900px; height:388px; pointer-events:none; }}
            path {{ fill:none; stroke:#9fb8b6; stroke-width:2.4; stroke-linecap:round; }}
            .root {{ position:absolute; left:330px; top:137px; width:240px; min-height:112px; padding:15px; border:2px solid #16875f; border-radius:20px; background:linear-gradient(135deg,#e8f7f0,#d7f1e8); color:#155f4b; box-shadow:0 10px 24px rgba(22,135,95,.14); text-align:center; }}
            .root strong {{ display:block; margin-bottom:7px; font-size:17px; }}
            .root span {{ display:block; font-size:12px; line-height:1.35; color:#315d58; }}
            .branch {{ position:absolute; width:275px; min-height:105px; padding:12px 13px; border:1.5px solid #73a1db; border-radius:14px; background:#fff; color:#173447; box-shadow:0 8px 18px rgba(38,75,89,.09); cursor:pointer; text-align:left; transition:transform .16s ease,border-color .16s ease,background .16s ease; }}
            .branch:hover,.branch.selected {{ transform:translateY(-2px); border-color:#2767c7; background:#edf5ff; }}
            .branch strong {{ display:block; margin-bottom:7px; color:#245f9d; font-size:14px; }}
            .branch span {{ display:block; color:#49687a; font-size:12px; line-height:1.35; }}
            .b0 {{ left:18px; top:20px; }} .b1 {{ right:18px; top:20px; }}
            .b2 {{ left:18px; top:263px; }} .b3 {{ right:18px; top:263px; }}
            .detail {{ min-height:86px; margin-top:9px; padding:12px 14px; border:1px solid #dce8e5; border-radius:10px; background:#f8fbfa; }}
            .detail strong {{ color:#245f9d; }}
            .detail p {{ margin:5px 0 0; color:#49687a; font-size:13px; line-height:1.4; }}
            .memory {{ margin-top:8px; padding:9px 12px; border-radius:9px; background:#eef8f5; color:#276858; font-size:12px; font-weight:750; }}
          </style>
        </head>
        <body>
          <div class="shell">
            <div class="toolbar">
              <button id="out" type="button">−</button><span id="level" class="zoom">100%</span>
              <button id="in" type="button">+</button><button id="reset" type="button">Reset</button>
            </div>
            <div class="viewport"><div id="stage" class="stage">
              <svg viewBox="0 0 900 388" aria-hidden="true">
                <path d="M330 174 C285 174 305 73 293 73" />
                <path d="M570 174 C615 174 595 73 607 73" />
                <path d="M330 215 C285 215 305 316 293 316" />
                <path d="M570 215 C615 215 595 316 607 316" />
              </svg>
              <div class="root"><strong id="root-title"></strong><span id="root-text"></span></div>
              <button class="branch b0" data-index="0" type="button"><strong></strong><span></span></button>
              <button class="branch b1" data-index="1" type="button"><strong></strong><span></span></button>
              <button class="branch b2" data-index="2" type="button"><strong></strong><span></span></button>
              <button class="branch b3" data-index="3" type="button"><strong></strong><span></span></button>
            </div></div>
            <div class="detail"><strong id="detail-title"></strong><p id="detail-text"></p></div>
            <div class="memory" id="memory"></div>
          </div>
          <script>
            const element = {payload};
            const branches = Array.isArray(element.branches) ? element.branches.slice(0,4) : [];
            document.getElementById("root-title").textContent = element.title || "Element compozițional";
            document.getElementById("root-text").textContent = element.central_idea || "";
            const buttons = [...document.querySelectorAll(".branch")];
            function select(index) {{
              const branch = branches[index] || {{}};
              buttons.forEach((button,i) => button.classList.toggle("selected",i===index));
              document.getElementById("detail-title").textContent = branch.heading || "Idee";
              document.getElementById("detail-text").textContent = branch.explanation || "Explicație indisponibilă.";
            }}
            buttons.forEach((button,index) => {{
              const branch = branches[index] || {{}};
              button.querySelector("strong").textContent = branch.heading || `Ramura ${{index+1}}`;
              button.querySelector("span").textContent = branch.key_idea || "";
              button.addEventListener("click",() => select(index));
            }});
            document.getElementById("memory").textContent = "Formulă de memorare: " + (element.memory_formula || []).join(" → ");
            const stage=document.getElementById("stage"),level=document.getElementById("level"); let zoom=1;
            function applyZoom() {{
              stage.style.width=`${{900*zoom}}px`; stage.style.height=`${{388*zoom}}px`;
              stage.style.transform=`scale(${{zoom}})`; level.textContent=`${{Math.round(zoom*100)}}%`;
            }}
            document.getElementById("in").onclick=()=>{{zoom=Math.min(1.7,zoom+.15);applyZoom();}};
            document.getElementById("out").onclick=()=>{{zoom=Math.max(.7,zoom-.15);applyZoom();}};
            document.getElementById("reset").onclick=()=>{{zoom=1;applyZoom();}};
            select(0);
          </script>
        </body>
        </html>
        """
    ).strip()


def _render_locked_or_placeholder(selected_step: str, progress: dict) -> None:
    labels = {
        "scenes": "Secvente relevante",
        "structure": "Elemente de structura, compozitie si limbaj",
    }
    label = labels.get(selected_step, "Rubrica")

    st.markdown(f"### {label}")

    st.info("Rubrica este pregatita in meniu. Continutul detaliat poate fi construit in pasul urmator.")


def _read_summary(work_id: str) -> str:
    summary_path = _summary_path_for_work(work_id)

    if summary_path is None or not summary_path.exists():
        return "Rezumatul nu exista inca pentru aceasta opera."

    return summary_path.read_text(encoding="utf-8").strip()
