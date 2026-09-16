from pathlib import Path
from functools import lru_cache
import json
import random
import re

from services.ai_provider import get_ai_provider


SOURCE_DIR = Path("data/sources/ion")
ION_PDF_PATH = SOURCE_DIR / "ion.pdf"


def read_text_file(path: Path) -> str:
    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8").strip()


@lru_cache(maxsize=1)
def _get_ion_pdf_reader():
    """Keep the book reader in memory so subsequent card sets load quickly."""
    if not ION_PDF_PATH.exists():
        raise RuntimeError("PDF-ul operei Ion nu a fost găsit.")

    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("Lipsește pachetul necesar pentru citirea PDF-ului: pypdf.") from error

    return PdfReader(str(ION_PDF_PATH))


def _get_ion_pdf_excerpt() -> str:
    """Select varied readable pages so flashcards are grounded in the full book."""
    reader = _get_ion_pdf_reader()
    page_numbers = list(range(len(reader.pages)))
    random.shuffle(page_numbers)

    excerpts = []
    for page_number in page_numbers:
        text = (reader.pages[page_number].extract_text() or "").strip()
        if len(text) < 500:
            continue
        excerpts.append(f"[Pagina {page_number + 1}]\n{text[:1800]}")
        if len(excerpts) == 5:
            break

    if not excerpts:
        raise RuntimeError("Nu am putut extrage text utilizabil din PDF-ul operei.")

    return "\n\n".join(excerpts)


def generate_ion_flashcards(
    category: str,
    excluded_questions: list[str] | None = None,
) -> list[dict]:
    """Generate validated, non-repetitive flashcards from varied book excerpts."""
    book_excerpt = _get_ion_pdf_excerpt()
    category_label = "opera" if category == "opera" else "personaje"
    previous_questions = "\n".join(
        f"- {question}" for question in (excluded_questions or [])[-60:]
    ) or "- Nu există încă întrebări anterioare."
    prompt = f"""
Ești un profesor de limba română pentru Bacalaureat. Generează exact 6 flashcarduri
cu alegere multiplă despre romanul „Ion” de Liviu Rebreanu, pentru categoria: {category_label}.

Folosește numai informații corecte susținute explicit de fragmentele din opera propriu-zisă
de mai jos. Fiecare flashcard are o singură variantă corectă și patru opțiuni scurte.
Nu reformula și nu repeta semantic niciuna dintre întrebările deja generate. Alege detalii,
scene sau personaje diferite față de lista de întrebări anterioare.

Răspunde EXCLUSIV cu JSON valid, fără markdown și fără explicații, în forma:
{{"flashcards":[{{"question":"...","options":["...","...","...","..."],"answer":"..."}}]}}

ÎNTREBĂRI DE EVITAT:
{previous_questions}

FRAGMENTE DIN OPERA INTEGRALĂ:
{book_excerpt}
""".strip()

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "flashcards": {
                "type": "ARRAY",
                "minItems": 6,
                "maxItems": 6,
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "question": {"type": "STRING"},
                        "options": {
                            "type": "ARRAY",
                            "minItems": 4,
                            "maxItems": 4,
                            "items": {"type": "STRING"},
                        },
                        "answer": {"type": "STRING"},
                    },
                    "required": ["question", "options", "answer"],
                },
            }
        },
        "required": ["flashcards"],
    }

    provider = get_ai_provider()
    generate_json = getattr(provider, "generate_json", None) or provider.generate_text
    last_error: ValueError | json.JSONDecodeError | None = None

    # Schema JSON rezolvă majoritatea răspunsurilor incomplete; reîncercarea
    # acoperă situațiile rare în care modelul ignoră o regulă de validare.
    for _ in range(2):
        try:
            try:
                raw_response = generate_json(prompt, response_schema).strip()
            except TypeError:
                raw_response = generate_json(prompt).strip()

            if raw_response.startswith("```"):
                raw_response = raw_response.split("\n", 1)[-1]
                raw_response = raw_response.rsplit("```", 1)[0].strip()

            payload = json.loads(raw_response)
            cards = payload.get("flashcards", []) if isinstance(payload, dict) else []
            if not isinstance(cards, list) or len(cards) != 6:
                raise ValueError("AI-ul nu a returnat numărul corect de flashcarduri.")

            clean_cards = []
            for card in cards:
                if not isinstance(card, dict):
                    raise ValueError("AI-ul a returnat un flashcard incomplet.")
                question = str(card.get("question", "")).strip()
                raw_options = card.get("options", [])
                options = [str(option).strip() for option in raw_options] if isinstance(raw_options, list) else []
                answer = str(card.get("answer", "")).strip()
                if not question or len(options) != 4 or not answer or answer not in options:
                    raise ValueError("AI-ul a returnat un flashcard incomplet.")
                clean_cards.append({"question": question, "options": options, "answer": answer})

            return clean_cards
        except (ValueError, json.JSONDecodeError) as error:
            last_error = error

    raise last_error or ValueError("AI-ul nu a putut genera flashcarduri valide.")


def _fallback_ion_quick_exercise(exercise_type: str) -> dict:
    """Keep the quick-test flow usable when an AI response is malformed."""
    fallbacks = {
        "Ordine cronologică": {
            "items": [
                {"event": "Vasile Baciu îl disprețuiește pe Ion la hora satului.", "position": 1},
                {"event": "Ion o seduce pe Ana pentru a obține pământ.", "position": 2},
                {"event": "Ana rămâne tot mai singură și nefericită după căsătorie.", "position": 3},
                {"event": "George o ia de soție pe Florica.", "position": 4},
                {"event": "Ana moare.", "position": 5},
                {"event": "George îl surprinde și îl ucide pe Ion.", "position": 6},
            ]
        },
        "Asociere": {"pairs": [
            {"left": "Ion", "right": "ambiție, perseverență"},
            {"left": "Ana", "right": "fragilitate, suferință"},
            {"left": "Vasile Baciu", "right": "bogăție, autoritate"},
            {"left": "Florica", "right": "frumusețe, dorință"},
            {"left": "George Bulbuc", "right": "gelozie, violență"},
        ]},
        "Completare": {
            "text": "Ion este atras de ____ și sacrifică iubirea pentru ____. Romanul se încheie prin moartea lui ____. ",
            "answers": ["pământ", "avere", "Ion"],
        },
        "Alege răspunsul": {
            "question": "Ce determină drama Anei în roman?",
            "options": ["Indiferența și violența lui Ion", "Plecarea la oraș", "Boala", "Lipsa școlii"],
            "answer": "Indiferența și violența lui Ion",
        },
        "Întoarce cartea": {"cards": [
            {"prompt": "Ce reprezintă pământul pentru Ion?", "answer": "Putere, statut social și obsesia care îi conduce viața."},
            {"prompt": "Cine este Ana?", "answer": "Fiica lui Vasile Baciu și soția lui Ion."},
            {"prompt": "Cine este Florica?", "answer": "Fata pe care Ion o iubește, dar pe care o sacrifică pentru pământ."},
            {"prompt": "Cum moare Ion?", "answer": "Este ucis de George Bulbuc."},
        ]},
    }
    fallback = fallbacks[exercise_type]
    if exercise_type == "Ordine cronologică":
        random.shuffle(fallback["items"])
    return fallback


def generate_ion_chronology_from_summary() -> dict:
    """Ask the AI for six events explicitly grounded in the Ion summary."""
    summary = read_text_file(SOURCE_DIR / "rezumat.md")
    prompt = f"""
SARCINĂ UNICĂ: citește REZUMATUL de mai jos despre romanul „Ion”.

1. Alege EXACT șase evenimente care sunt afirmate explicit în rezumat.
2. Scrie evenimentele foarte scurt, în ordinea lor reală din acțiune.
3. Pentru fiecare, atribuie pozițiile 1, 2, 3, 4, 5 și 6, fără repetări.
4. Include acțiuni sau momente care îi au în centru pe minimum patru personaje
   diferite (de exemplu Ana, Vasile Baciu, Florica, George), nu doar pe Ion.
5. Nu inventa niciun eveniment și nu adăuga explicații, titluri sau markdown.

Răspunsul trebuie să fie EXCLUSIV acest JSON valid:
{{
  "items": [
    {{"event": "primul eveniment din rezumat", "position": 1}},
    {{"event": "al doilea eveniment din rezumat", "position": 2}},
    {{"event": "al treilea eveniment din rezumat", "position": 3}},
    {{"event": "al patrulea eveniment din rezumat", "position": 4}},
    {{"event": "al cincilea eveniment din rezumat", "position": 5}},
    {{"event": "ultimul eveniment din rezumat", "position": 6}}
  ]
}}

REZUMATUL DIN CARE AI VOIE SĂ ALEGI:
{summary}
""".strip()

    response_schema = {
        "type": "OBJECT",
        "properties": {
            "items": {
                "type": "ARRAY",
                "minItems": 6,
                "maxItems": 6,
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "event": {"type": "STRING"},
                        "position": {"type": "INTEGER"},
                    },
                    "required": ["event", "position"],
                },
            }
        },
        "required": ["items"],
    }

    try:
        provider = get_ai_provider()
        generate_json = getattr(provider, "generate_json", provider.generate_text)
        try:
            raw_response = generate_json(prompt, response_schema)
        except TypeError:
            # Providerii care nu suportă schema păstrează cererea JSON din prompt.
            raw_response = generate_json(prompt)
        payload = json.loads(raw_response.strip())
        items = payload.get("items", []) if isinstance(payload, dict) else []
        if len(items) != 6 or not all(isinstance(item, dict) for item in items):
            raise ValueError("AI-ul nu a extras exact șase evenimente.")

        normalized = []
        for item in items:
            event = str(item.get("event", "")).strip()
            position = int(str(item.get("position", "")).strip())
            if not event:
                raise ValueError("AI-ul a trimis un eveniment fără text.")
            normalized.append({"event": event, "position": position})

        if sorted(item["position"] for item in normalized) != [1, 2, 3, 4, 5, 6]:
            raise ValueError("AI-ul nu a atribuit pozițiile 1–6 o singură dată.")

        random.shuffle(normalized)
        return {"items": normalized}
    except Exception as error:
        error_text = str(error)
        if "RESOURCE_EXHAUSTED" in error_text or "quota" in error_text.lower():
            retry_match = re.search(r"retry in\s+(\d+)", error_text, flags=re.IGNORECASE)
            retry_hint = (
                f" Încearcă din nou peste aproximativ {retry_match.group(1)} secunde."
                if retry_match
                else " Încearcă din nou peste puțin timp."
            )
            raise RuntimeError(
                "Limita temporară de cereri pentru AI a fost atinsă."
                + retry_hint
            ) from error
        raise RuntimeError(
            "AI-ul nu a putut genera acum o cronologie validă din rezumat."
        ) from error


def generate_ion_quick_exercise(
    exercise_type: str,
    excluded_characters: list[str] | None = None,
) -> dict:
    """Generate one exercise matching the active quick-test exercise type."""
    if exercise_type == "Ordine cronologică":
        return generate_ion_chronology_from_summary()

    schemas = {
        "Ordine cronologică": '{"items":[{"event":"...","position":1}]}',
        "Asociere": '{"pairs":[{"left":"personaj","right":"trăsătură"}]}',
        "Completare": '{"text":"Text cu trei spații marcate prin ____.","answers":["...","...","..."]}',
        "Alege răspunsul": '{"question":"...","options":["...","...","...","..."],"answer":"..."}',
        "Întoarce cartea": '{"cards":[{"prompt":"...","answer":"..."}]}',
    }
    if exercise_type not in schemas:
        raise ValueError("Tip de exercițiu necunoscut.")

    summary = read_text_file(SOURCE_DIR / "rezumat.md")
    excluded_characters = excluded_characters or []
    exclusion_rule = (
        "\nPentru Asociere, NU folosi aceste personaje, fiindcă au apărut deja: "
        + ", ".join(excluded_characters)
        + ". Alege alte personaje relevante din rezumat, precum Savista, Zenobia, "
        "preotul Belciug, familia Herdelea sau Alexandru Glanetașu."
        if exercise_type == "Asociere" and excluded_characters
        else ""
    )
    prompt = f"""
Ești profesor de limba română pentru Bacalaureat. Generează un singur exercițiu
despre romanul „Ion” de Liviu Rebreanu, strict de tipul: {exercise_type}.
Folosește numai informații corecte din rezumat. Nu repeta formulările banale.

Cerințe:
- Ordine cronologică: exact 6 evenimente, fiecare cu poziție unică 1-6;
- Asociere: exact 5 perechi personaj-trăsătură. Scrie trăsăturile DOAR ca substantive
  fără gen gramatical, de exemplu „ambiție, perseverență”, nu „ambițios, perseverent”;
- Completare: exact 3 spații și 3 răspunsuri;
- Alege răspunsul: exact 4 opțiuni și una corectă;
- Întoarce cartea: exact 4 carduri întrebare-răspuns.

Răspunde EXCLUSIV cu JSON valid, fără markdown, folosind această schemă:
{schemas[exercise_type]}

REZUMAT:
{summary}
{exclusion_rule}
""".strip()

    try:
        provider = get_ai_provider()
        generate_json = getattr(provider, "generate_json", provider.generate_text)
        raw_response = generate_json(prompt).strip()
        if raw_response.startswith("```"):
            raw_response = raw_response.split("\n", 1)[-1]
            raw_response = raw_response.rsplit("```", 1)[0].strip()
        exercise = json.loads(raw_response)
    except (RuntimeError, ValueError, json.JSONDecodeError):
        return _fallback_ion_quick_exercise(exercise_type)

    if not isinstance(exercise, dict):
        return _fallback_ion_quick_exercise(exercise_type)

    if exercise_type == "Ordine cronologică":
        # Acceptă variantele de chei folosite frecvent de modelele AI și le
        # normalizează într-un singur format pentru interfață.
        raw_items = exercise.get("items") or exercise.get("events") or []
        if not isinstance(raw_items, list) or len(raw_items) < 4:
            return _fallback_ion_quick_exercise(exercise_type)

        items = []
        for raw_item in raw_items:
            if isinstance(raw_item, str):
                event = raw_item.strip()
                raw_position = None
            elif isinstance(raw_item, dict):
                event = str(
                    raw_item.get("event")
                    or raw_item.get("text")
                    or raw_item.get("description")
                    or ""
                ).strip()
                raw_position = (
                    raw_item.get("position")
                    or raw_item.get("order")
                    or raw_item.get("ordine")
                    or raw_item.get("number")
                )
            else:
                continue

            if event:
                try:
                    position = int(str(raw_position).strip())
                except (TypeError, ValueError):
                    position = len(items) + 1
                items.append({"event": event, "position": position})

        if len(items) < 4:
            return _fallback_ion_quick_exercise(exercise_type)

        expected_positions = list(range(1, len(items) + 1))
        if sorted(item["position"] for item in items) != expected_positions:
            # Dacă AI-ul a oferit doar lista în ordine, folosim acea ordine ca
            # soluție și o amestecăm pentru elev.
            for position, item in enumerate(items, 1):
                item["position"] = position

        exercise["items"] = items
        random.shuffle(exercise["items"])
    elif exercise_type == "Asociere":
        pairs = exercise.get("pairs", [])
        if (
            len(pairs) != 5
            or not all(isinstance(pair, dict) for pair in pairs)
            or any(not pair.get("left") or not pair.get("right") for pair in pairs)
        ):
            return _fallback_ion_quick_exercise(exercise_type)
    elif exercise_type == "Completare":
        if exercise.get("text", "").count("____") != 3 or len(exercise.get("answers", [])) != 3:
            return _fallback_ion_quick_exercise(exercise_type)
    elif exercise_type == "Alege răspunsul":
        options = exercise.get("options", [])
        if not exercise.get("question") or len(options) != 4 or exercise.get("answer") not in options:
            return _fallback_ion_quick_exercise(exercise_type)
    else:
        cards = exercise.get("cards", [])
        if (
            len(cards) != 4
            or not all(isinstance(card, dict) for card in cards)
            or any(not card.get("prompt") or not card.get("answer") for card in cards)
        ):
            return _fallback_ion_quick_exercise(exercise_type)

    return exercise


def answer_ion_node_question(
    user_question: str,
    node_title: str,
    node_content: str,
) -> str:
    barem = read_text_file(SOURCE_DIR / "barem.md")
    structura = read_text_file(SOURCE_DIR / "structura_eseu.md")
    eseu_model = read_text_file(SOURCE_DIR / "eseu_model.md")
    style_guide = read_text_file(SOURCE_DIR / "style_guide.md")

    prompt = f"""
Ești un asistent educațional pentru Bacalaureatul la Limba Română.

REGULI STRICTE:
1. Răspunzi doar despre romanul „Ion” de Liviu Rebreanu.
2. Răspunzi doar despre secțiunea curentă: {node_title}.
3. Nu genera eseul complet dacă elevul discută doar o secțiune.
4. Nu inventa citate, scene sau informații.
5. Respectă baremul, structura și ghidul de stil.
6. Folosește eseul model doar ca reper de stil, nu îl copia mecanic.
7. Răspunde clar, natural, pe nivel de elev foarte bine pregătit pentru BAC.

SECȚIUNEA CURENTĂ:
{node_title}

CONȚINUTUL SECȚIUNII, dacă există:
{node_content}

BAREM:
{barem}

STRUCTURA ESEULUI:
{structura}

ESEU MODEL:
{eseu_model}

GHID DE STIL:
{style_guide}

ÎNTREBAREA ELEVULUI:
{user_question}

Răspunde strict la întrebare. Răspunsul trebuie să fie clar, util și natural.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)


def _essay_source_context(work_id: str, blueprint: dict) -> dict[str, str]:
    source_dir = Path("data") / "sources" / work_id
    configured_model = Path(str((blueprint.get("source") or {}).get("model_essay") or ""))
    model_path = configured_model if configured_model.is_file() else source_dir / "eseu_model.md"
    return {
        "barem": read_text_file(source_dir / "barem.md"),
        "structure": read_text_file(source_dir / "structura_eseu.md"),
        "model_essay": read_text_file(model_path),
        "style_guide": read_text_file(source_dir / "style_guide.md"),
    }


def answer_essay_node_question(
    *,
    work: dict,
    blueprint: dict,
    user_question: str,
    node_title: str,
    node_content: str,
) -> str:
    work_id = str(work.get("id") or (blueprint.get("work") or {}).get("work_id") or "")
    sources = _essay_source_context(work_id, blueprint)
    policy = blueprint.get("strict_trait_policy") or {}
    accepted_traits = ", ".join(policy.get("accepted_trait_titles") or [])
    prompt = f"""
Ești un asistent educațional pentru Bacalaureatul la Limba Română.

OPERA: „{work.get('title', '')}” de {work.get('author', '')}
SECȚIUNEA CURENTĂ: {node_title}

REGULI STRICTE:
1. Răspunzi numai despre opera și secțiunea curentă.
2. Nu generezi eseul complet când elevul discută o singură secțiune.
3. Nu inventezi citate, scene sau informații.
4. Eseul-model este autoritatea pentru structura argumentării.
5. Pentru încadrarea în curent sunt corecte EXCLUSIV aceste trăsături:
   {accepted_traits}. Orice altă trăsătură trebuie respinsă ca neconformă cu modelul.
6. Răspunzi clar și natural, la nivel de Bacalaureat.

CONȚINUTUL SECȚIUNII:
{node_content}

BAREM:
{sources['barem']}

STRUCTURĂ:
{sources['structure']}

ESEU-MODEL:
{sources['model_essay']}

GHID DE STIL:
{sources['style_guide']}

ÎNTREBAREA ELEVULUI:
{user_question}
""".strip()
    return get_ai_provider().generate_text(prompt)


def generate_essay_section(
    *,
    work: dict,
    blueprint: dict,
    section_title: str,
    section_instructions: str,
    current_final_essay: str = "",
) -> str:
    work_id = str(work.get("id") or (blueprint.get("work") or {}).get("work_id") or "")
    sources = _essay_source_context(work_id, blueprint)
    policy = blueprint.get("strict_trait_policy") or {}
    accepted_traits = ", ".join(policy.get("accepted_trait_titles") or [])
    prompt = f"""
Generează DOAR secțiunea „{section_title}” din eseul de Bacalaureat despre
opera „{work.get('title', '')}” de {work.get('author', '')}.

INSTRUCȚIUNI:
{section_instructions}

REGULI STRICTE:
1. Scrie numai paragraful cerut, fără titlu markdown.
2. Nu inventa citate sau scene.
3. Folosește eseul-model ca autoritate de conținut și structură, fără copiere mecanică.
4. Pentru curent sunt permise EXCLUSIV trăsăturile: {accepted_traits}.
5. Orice altă trăsătură este interzisă, chiar dacă ar fi adevărată în general.
6. Păstrează coerența cu fragmentele deja acceptate.

ESEUL CONSTRUIT PÂNĂ ACUM:
{current_final_essay}

BAREM:
{sources['barem']}

STRUCTURĂ:
{sources['structure']}

ESEU-MODEL:
{sources['model_essay']}

GHID DE STIL:
{sources['style_guide']}
""".strip()
    return get_ai_provider().generate_text(prompt).strip()


def answer_ion_summary_question(user_question: str, summary_text: str) -> str:
    prompt = f"""
Esti un AI Profesor pentru elevi care invata romanul "Ion" de Liviu Rebreanu pentru Bacalaureat.

REGULI:
1. Raspunzi doar despre rezumatul romanului "Ion".
2. Explici clar, pe intelesul unui elev de liceu.
3. Nu inventa scene, citate sau informatii care nu sunt sustinute de rezumat.
4. Daca elevul cere o formulare mai simpla, rescrie natural si scurt.
5. Nu genera eseul complet aici; ajuta elevul sa inteleaga rezumatul.

REZUMAT:
{summary_text}

INTREBAREA ELEVULUI:
{user_question}

Raspunde util, clar si concis.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)


def explain_ion_dictionary_term(term: str, summary_text: str) -> str:
    prompt = f"""
Esti un dictionar AI pentru elevi care invata romanul "Ion" de Liviu Rebreanu.

Explica termenul sau expresia de mai jos in contextul rezumatului romanului.

REGULI:
1. Da o definitie scurta.
2. Explica sensul in contextul operei.
3. Daca termenul nu are legatura cu romanul, spune asta si ofera o explicatie generala simpla.
4. Nu inventa citate.

REZUMAT:
{summary_text}

TERMEN:
{term}

Raspunsul sa fie usor de inteles pentru un elev.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)


def answer_ion_learning_context_question(
    user_question: str,
    context_title: str,
    context_text: str,
) -> str:
    return answer_learning_context_question(
        work_title="Ion",
        work_author="Liviu Rebreanu",
        user_question=user_question,
        context_title=context_title,
        context_text=context_text,
    )


def answer_learning_context_question(
    work_title: str,
    work_author: str,
    user_question: str,
    context_title: str,
    context_text: str,
) -> str:
    prompt = f"""
Esti un AI Profesor pentru elevi care invata opera „{work_title}” de {work_author} pentru Bacalaureat.

REGULI:
1. Raspunzi doar despre opera „{work_title}”.
2. Raspunzi strict in contextul sectiunii: {context_title}.
3. Explici clar, pe intelesul unui elev de liceu.
4. Nu inventa scene, citate sau informatii.
5. Nu genera eseul complet aici; ajuta elevul sa inteleaga sectiunea.
6. Daca intrebarea nu are legatura cu aceasta sectiune, spune scurt ca poti raspunde doar despre sectiunea selectata.

CONTEXT SECTIUNE:
{context_text}

INTREBAREA ELEVULUI:
{user_question}

Raspunde util, clar si concis.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)


def answer_ion_characters_teacher_turn(
    user_message: str,
    context_text: str,
    pending_question: str = "",
    current_xp: int = 0,
) -> str:
    return answer_characters_teacher_turn(
        work_title="Ion",
        work_author="Liviu Rebreanu",
        user_message=user_message,
        context_text=context_text,
        pending_question=pending_question,
        current_xp=current_xp,
    )


def answer_characters_teacher_turn(
    work_title: str,
    work_author: str,
    user_message: str,
    context_text: str,
    pending_question: str = "",
    current_xp: int = 0,
    require_xp_followup: bool = False,
    max_xp_per_answer: int = 5,
    format_retry: bool = False,
) -> str:
    max_xp_per_answer = max(1, min(int(max_xp_per_answer), 5))
    pending_block = (
        f"""
INTREBAREA TA ANTERIOARA PENTRU ELEV:
{pending_question}

Trebuie sa verifici daca mesajul elevului raspunde la aceasta intrebare.
"""
        if pending_question
        else "Nu exista o intrebare anterioara cu XP in asteptare."
    )
    if max_xp_per_answer == 3:
        xp_rubric = """
   - 0 XP: nu raspunde la intrebare, este complet gresit sau in afara subiectului;
   - 1 XP: raspuns partial corect, simplu ori insuficient explicat, cu limbaj imprecis;
   - 2 XP: raspuns corect, dezvoltat si coerent, exprimat intr-un limbaj potrivit;
   - 3 XP: raspuns exceptional si foarte bine gandit, cu rationament nuantat,
     justificare relevanta si limbaj precis, matur si expresiv.
Nu acorda 3 XP doar pentru lungime. Conteaza complexitatea ideilor, justificarea si calitatea limbajului.
""".rstrip()
    else:
        xp_rubric = """
   - 0 XP: nu raspunde sau e complet gresit;
   - 1-2 XP: raspuns vag, partial sau confuz;
   - 3-4 XP: raspuns bun, dar incomplet;
   - 5 XP: raspuns clar, corect si bine justificat.
""".rstrip()

    followup_rule = (
        "Dupa FIECARE raspuns adresat elevului, pune obligatoriu o singura intrebare "
        "scurta, relevanta pentru discutia tocmai purtata si potrivita pentru XP. "
        "Nu incheia niciodata mesajul fara aceasta intrebare."
        if require_xp_followup
        else (
            "Dupa ce explici un concept cerut de elev, poti pune uneori o intrebare "
            "scurta si naturala despre explicatia ta, dar NU dupa fiecare mesaj."
        )
    )
    retry_instruction = (
        """
ATENTIE - REINCERCARE DE FORMAT:
Raspunsul anterior a avut campul <message> gol sau a continut numai taguri tehnice.
Completeaza obligatoriu <message> cu raspunsul explicativ adresat elevului, apoi pune
intrebarea (+XP). Nu returna niciun camp gol.
""".strip()
        if format_retry
        else ""
    )

    prompt = f"""
Esti un profesor cald si natural de limba romana. Discuti cu un elev despre personajele
din opera „{work_title}” de {work_author}.

CONTEXT PERSONAJE:
{context_text}

XP CURENT AL ELEVULUI IN ACEST CHAT:
{current_xp}

{pending_block}

MESAJUL NOU AL ELEVULUI:
{user_message}

{retry_instruction}

REGULI DE CONVERSATIE:
1. Daca exista o intrebare anterioara cu XP, evalueaza MAI INTAI raspunsul elevului la ea.
2. Acorda intre 0 si {max_xp_per_answer} XP pentru raspunsul la intrebarea anterioara:
{xp_rubric}
3. Spune natural in mesaj cate puncte a primit, de forma: "Ai primit +3 XP.".
4. Daca elevul raspunde la intrebare si apoi intreaba altceva, dupa evaluare raspunde si la nelamurirea noua.
5. Daca nu exista intrebare anterioara, nu acorda XP.
6. {followup_rule}
7. Daca pui o intrebare pentru XP, ultima propozitie trebuie sa fie intrebarea si trebuie sa se termine exact cu "(+XP)".
8. Intrebarile trebuie sa sune ca intr-o discutie reala cu un profesor, nu ca intr-un test rigid.
9. Nu inventa scene sau citate.
10. Raspunde doar despre personajele si relatiile relevante din opera „{work_title}”.
11. Raspunsul explicativ trebuie sa aiba 3-6 propozitii complete. Termina ideea si
    ultima propozitie explicativa inainte de a formula intrebarea (+XP).

FORMAT OBLIGATORIU:
<message>
Mesajul complet pentru elev. Include aici evaluarea, explicatia si eventual intrebarea finala cu (+XP).
</message>
<xp>
numar intreg intre 0 si {max_xp_per_answer} acordat ACUM pentru intrebarea anterioara; daca nu exista intrebare anterioara, scrie 0
</xp>
<next_question>
intrebarea noua pe care ai pus-o pentru XP, exact cum apare in mesaj, sau NONE
</next_question>
""".strip()

    provider = get_ai_provider()
    generate_chat_text = getattr(provider, "generate_chat_text", provider.generate_text)
    return generate_chat_text(prompt)


def explain_ion_learning_context_term(
    term: str,
    context_title: str,
    context_text: str,
) -> str:
    return explain_learning_context_term(
        work_title="Ion",
        work_author="Liviu Rebreanu",
        term=term,
        context_title=context_title,
        context_text=context_text,
    )


def explain_learning_context_term(
    work_title: str,
    work_author: str,
    term: str,
    context_title: str,
    context_text: str,
) -> str:
    prompt = f"""
Esti un dictionar AI pentru elevi care invata opera „{work_title}” de {work_author}.

Explica termenul sau expresia de mai jos in contextul sectiunii: {context_title}.

REGULI:
1. Da o definitie scurta.
2. Explica sensul in contextul operei.
3. Daca termenul nu are legatura cu sectiunea, spune asta si ofera o explicatie generala simpla.
4. Nu inventa citate.

CONTEXT SECTIUNE:
{context_text}

TERMEN:
{term}

Raspunsul sa fie usor de inteles pentru un elev.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)


def generate_ion_essay() -> str:
    barem = read_text_file(SOURCE_DIR / "barem.md")
    structura = read_text_file(SOURCE_DIR / "structura_eseu.md")
    eseu_model = read_text_file(SOURCE_DIR / "eseu_model.md")
    style_guide = read_text_file(SOURCE_DIR / "style_guide.md")

    prompt = f"""
Ești un asistent educațional specializat în eseuri pentru Bacalaureat la Limba Română.

Generează un eseu complet pentru romanul „Ion” de Liviu Rebreanu.

REGULI:
1. Eseul trebuie să respecte baremul.
2. Eseul trebuie să respecte structura standardizată.
3. Eseul trebuie să aibă stil natural, clar și matur.
4. Eseul nu trebuie să copieze mecanic eseul model.
5. Eseul trebuie să fie organizat pe secțiuni.
6. Pentru fiecare secțiune folosește titlu markdown de forma: ## Titlu secțiune.
7. Nu inventa citate.
8. Nu folosi exprimări pompoase.
9. Scenele trebuie analizate, nu doar povestite.
10. Eseul trebuie să fie potrivit pentru nivelul de Bacalaureat.

BAREM:
{barem}

STRUCTURA STANDARDIZATĂ:
{structura}

ESEU MODEL, doar ca reper de stil:
{eseu_model}

GHID DE STIL:
{style_guide}

Generează acum eseul complet.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)

def generate_ion_essay_section(
    section_title: str,
    section_instructions: str,
    current_final_essay: str = "",
) -> str:
    barem = read_text_file(SOURCE_DIR / "barem.md")
    structura = read_text_file(SOURCE_DIR / "structura_eseu.md")
    eseu_model = read_text_file(SOURCE_DIR / "eseu_model.md")
    style_guide = read_text_file(SOURCE_DIR / "style_guide.md")

    prompt = f"""
Ești un asistent educațional specializat în eseuri pentru Bacalaureat la Limba Română.

Trebuie să generezi DOAR secțiunea următoare din eseul pentru romanul „Ion” de Liviu Rebreanu:

SECȚIUNE DE GENERAT:
{section_title}

INSTRUCȚIUNI PENTRU ACEASTĂ SECȚIUNE:
{section_instructions}

REGULI STRICTE:
1. Generează doar această secțiune, nu tot eseul.
2. Nu pune titlu markdown de tipul ##.
3. Nu scrie numele secțiunii înaintea paragrafului.
4. Textul trebuie să fie gata de introdus direct în eseu.
5. Respectă baremul.
6. Respectă structura standardizată.
7. Folosește eseul model doar ca reper de stil, nu copia mecanic.
8. Respectă ghidul de stil.
9. Nu inventa citate.
10. Nu inventa scene.
11. Nu folosi exprimări pompoase.
12. Scrie natural, clar, matur, la nivel foarte bun pentru Bacalaureat.
13. Dacă există deja bucăți acceptate în eseu, păstrează coerența cu ele.

ESEU FINAL CONSTRUIT PÂNĂ ACUM:
{current_final_essay}

BAREM:
{barem}

STRUCTURA STANDARDIZATĂ:
{structura}

ESEU MODEL, doar ca reper de stil:
{eseu_model}

GHID DE STIL:
{style_guide}

Generează acum doar secțiunea cerută.
""".strip()

    provider = get_ai_provider()
    return provider.generate_text(prompt)
