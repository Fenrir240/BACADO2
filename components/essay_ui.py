import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from components.ai_status_ui import ai_thinking
from components.essay_mindmap import render_essay_structure_intro
from services.annotation_service import get_scene_annotations, save_scene_annotations
from services.composition_service import selected_elements_for_essay
from services.essay_builder_service import load_essay_blueprint
from services.essay_quote_service import (
    ensure_quotes_present,
    quote_instructions,
    quotes_for_essay_section,
)
from services.essay_service import load_essay_state, save_essay_state

try:
    from services.ai_service import (
        answer_essay_node_question,
        generate_essay_section,
    )
except ImportError:
    answer_essay_node_question = None
    generate_essay_section = None


ION_ESSAY_PLAN = [
    {
        "id": "introducere",
        "title": "Introducere",
        "instructions": """
Scrie introducerea eseului. Trebuie să menționezi clar autorul Liviu Rebreanu, romanul „Ion”, anul publicării 1920, perioada interbelică și încadrarea în realism.
Menționează și minimum două alte opere ale autorului, precum „Răscoala” și „Pădurea spânzuraților”.
""",
    },
    {
        "id": "trasatura_1_realism",
        "title": "Veridicitatea întâmplărilor",
        "instructions": """
Prezintă exclusiv prima trăsătură realistă din eseul-model: veridicitatea întâmplărilor, susținută prin geneza romanului și situațiile tipice valorificate din realitate.
""",
    },
    {
        "id": "trasatura_2_realism",
        "title": "Caracterul tipologic al personajelor",
        "instructions": """
Prezintă exclusiv a doua trăsătură realistă din eseul-model: caracterul tipologic al personajelor, ilustrat prin protagonist și intelectualii satului.
""",
    },
    {
        "id": "tema",
        "title": "Tema romanului",
        "instructions": """
Prezintă tema romanului: setea de pământ și efectele ei asupra personajului principal.
""",
    },
    {
        "id": "scena_cositul",
        "title": "Secvența 1: Cositul",
        "instructions": """
Analizează secvența cositului din capitolul al II-lea, „Zvârcolirea”, prezentată în secțiunea „Înțelege opera”. Explică „glasul pământului”, alternanța dintre sentimentul micimii și mândria de stăpân, personificarea pământului și felul în care scena evidențiază obsesia lui Ion.
""",
    },
    {
        "id": "scena_sarutarea",
        "title": "Secvența 2: Sărutarea pământului",
        "instructions": """
Analizează secvența sărutării pământului din capitolul al IX-lea, „Sărutarea”, prezentată în secțiunea „Înțelege opera”. Explică gestul îngenuncherii și al sărutului, imaginile senzoriale, comparația pământului cu o iubită și semnificația mănușilor de doliu, arătând atât împlinirea, cât și caracterul tragic al obsesiei lui Ion.
""",
    },
    {
        "id": "element_conflict",
        "title": "Element de compoziție: conflictul",
        "instructions": """
Prezintă conflictul social, interior și erotic din roman.
""",
    },
    {
        "id": "element_incipit_final",
        "title": "Element de compoziție: incipit și final",
        "instructions": """
Prezintă relația dintre incipit și final și imaginea drumului.
""",
    },
    {
        "id": "element_title",
        "title": "Element de compoziție: titlul",
        "instructions": """
Prezintă semnificația titlului și legătura sa cu personajele, temele și mesajul operei.
""",
    },
    {
        "id": "concluzie",
        "title": "Concluzie",
        "instructions": """
Scrie concluzia eseului într-o formulare clară, matură și naturală.
""",
    },
]

ESSAY_PARAGRAPH_MAX_CHARS = 2000


ESSAY_ANNOTATOR_COMPONENT = components.declare_component(
    "essay_full_annotator_v2",
    path=str(Path(__file__).parent / "scene_annotator_component"),
)
FULL_ESSAY_ANNOTATION_ID = "full_essay"


def render_essay_for_work(work: dict, progress: dict) -> None:
    try:
        blueprint = load_essay_blueprint(work["id"])
    except (FileNotFoundError, ValueError, json.JSONDecodeError):
        blueprint = _legacy_ion_blueprint() if work["id"] == "ion" else None
    if blueprint is None:
        st.subheader(f"Eseu — {work['title']}")
        st.info(
            "Secțiunea «Construiește eseul» nu a fost generată încă. Rulează "
            "scripts/eseu.py cu knowledge graph-ul și eseul-model al operei."
        )
        return
    _set_essay_runtime(work, blueprint)
    render_essay_builder(work, progress)


def _legacy_ion_blueprint() -> dict:
    return {
        "schema_version": 1,
        "work": {"work_id": "ion", "title": "Ion", "author": "Liviu Rebreanu"},
        "movement": {"name": "Realism"},
        "strict_trait_policy": {
            "mode": "model_essay_only",
            "reject_unlisted_traits": True,
            "accepted_trait_ids": ["trasatura_1_realism", "trasatura_2_realism"],
            "accepted_trait_titles": [
                "Veridicitatea întâmplărilor",
                "Caracterul tipologic al personajelor",
            ],
        },
        "mindmap": {
            "movement_name": "Realism",
            "traits": [
                {"id": "trasatura_1_realism", "title": "Veridicitatea întâmplărilor"},
                {"id": "trasatura_2_realism", "title": "Caracterul tipologic al personajelor"},
            ],
            "theme": {"id": "tema", "title": "Relația mistică dintre țăran și pământ"},
            "sequences": [
                {"id": "scena_cositul", "title": "Cositul"},
                {"id": "scena_sarutarea", "title": "Sărutarea pământului"},
            ],
        },
        "sections": ION_ESSAY_PLAN,
        "validation": {"valid": True},
    }


def _set_essay_runtime(work: dict, blueprint: dict) -> None:
    sections = []
    for raw_section in blueprint.get("sections") or ION_ESSAY_PLAN:
        section = dict(raw_section)
        if not str(section.get("instructions") or "").strip():
            section["instructions"] = str(section.get("prompt_instruction") or "").strip()
        sections.append(section)
    movement_id = str((blueprint.get("movement") or {}).get("id") or "curent_literar")
    if not any(section.get("id") == movement_id for section in sections):
        movement_name = str(
            (blueprint.get("movement") or {}).get("name")
            or (blueprint.get("mindmap") or {}).get("movement_name")
            or "Curentul literar"
        )
        trait_titles = [
            str(item.get("title") or "").strip()
            for item in (blueprint.get("mindmap") or {}).get("traits", [])
            if str(item.get("title") or "").strip()
        ]
        traits_note = (
            " Leagă încadrarea de trăsăturile studiate: "
            + "; ".join(trait_titles)
            + "."
            if trait_titles
            else ""
        )
        movement_section = {
            "id": movement_id,
            "kind": "literary_movement",
            "title": f"Curent literar — {movement_name}",
            "instructions": (
                f"Scrie câteva rânduri despre {movement_name}: definește succint curentul, "
                f"precizează perioada și principiile sale esențiale, apoi încadrează opera "
                f"«{work['title']}» de {work['author']} în acest curent."
                + traits_note
            ),
            "max_chars": ESSAY_PARAGRAPH_MAX_CHARS,
            "editor_height": 180,
        }
        introduction_index = next(
            (index for index, section in enumerate(sections) if section.get("id") == "introducere"),
            -1,
        )
        sections.insert(introduction_index + 1, movement_section)
    st.session_state["active_essay_runtime"] = {
        "work": work,
        "blueprint": blueprint,
        "sections": sections,
    }


def _essay_runtime() -> dict:
    return st.session_state.get("active_essay_runtime") or {
        "work": {"id": "ion", "title": "Ion", "author": "Liviu Rebreanu"},
        "blueprint": _legacy_ion_blueprint(),
        "sections": ION_ESSAY_PLAN,
    }


def _active_work() -> dict:
    return _essay_runtime()["work"]


def _essay_plan() -> list[dict]:
    return _essay_runtime()["sections"]


def _essay_key(suffix: str) -> str:
    return f"{_active_work()['id']}_{suffix}"


def render_essay_builder(work: dict, progress: dict) -> None:
    initialize_essay_state(work["id"])
    action_spacer, action_col = st.columns([4.2, 1])
    with action_col:
        if st.button(
            "Vezi eseul",
            key=_essay_key("open_full_essay_dialog"),
            type="primary",
            use_container_width=True,
        ):
            render_full_essay_dialog(work)

    composition_elements = selected_elements_for_essay(work["id"], progress)
    selected_composition_sections = {
        element["section_id"] for element in composition_elements
    }
    all_composition_sections = {
        str(section.get("id"))
        for section in _essay_plan()
        if section.get("kind") == "composition"
        or str(section.get("id") or "").startswith("element_")
    }
    removed_sections = all_composition_sections - selected_composition_sections
    removed_saved_text = False
    for section_id in removed_sections:
        if st.session_state[_essay_key("final_sections")].pop(section_id, None) is not None:
            removed_saved_text = True
    if removed_saved_text:
        rebuild_final_essay_from_sections()
    active_node_key = _essay_key("essay_active_node")
    selected_node = st.session_state.get(active_node_key)
    if selected_node in all_composition_sections - selected_composition_sections:
        st.session_state.pop(active_node_key, None)
        selected_node = None
    fullscreen_key = _essay_key("essay_mindmap_fullscreen")

    if st.session_state.get(fullscreen_key):
        render_fullscreen_essay_mindmap(
            selected_node, work, composition_elements, _essay_runtime()["blueprint"]
        )
    else:
        event = render_essay_structure_intro(
            selected_node,
            work=work,
            composition_elements=composition_elements,
            essay_blueprint=_essay_runtime()["blueprint"],
        )
        if isinstance(event, dict) and event.get("type") == "select_section":
            st.session_state[fullscreen_key] = False
        handle_essay_mindmap_event(event, active_node_key, fullscreen_key)

    active_section_id = st.session_state.get(active_node_key)
    if not active_section_id:
        render_essay_map_start_prompt()
    elif active_section_id == "introducere":
        render_introduction_workspace()
    elif any(
        element["section_id"] == active_section_id
        for element in composition_elements
    ):
        render_composition_essay_workspace(
            next(
                element
                for element in composition_elements
                if element["section_id"] == active_section_id
            )
        )
    elif any(section["id"] == active_section_id for section in _essay_plan()):
        render_essay_section_workspace(_get_essay_section(active_section_id))


def close_fullscreen_essay_mindmap() -> None:
    st.session_state[_essay_key("essay_mindmap_fullscreen")] = False
    st.session_state[f"{_active_work()['id']}_preferred_workspace_tab"] = "Construiește eseu"
    st.rerun()


@st.dialog("Eseul complet", width="large")
def render_full_essay_dialog(work: dict) -> None:
    st.markdown(
        """
        <style>
          div[role="dialog"] { width:min(96vw,1500px)!important; max-width:96vw!important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "Editează, subliniază și evidențiază eseul complet. Fragmentele se "
        "adaugă din atelierul fiecărei secțiuni."
    )
    _render_full_essay_annotation_editor(work)


def _save_full_essay_text(work_id: str, new_text: str) -> bool:
    old_text = str(st.session_state.get(_essay_key("final_essay_manual"), ""))
    clean_text = str(new_text).strip()
    if clean_text != old_text:
        annotations = get_scene_annotations(work_id, FULL_ESSAY_ANNOTATION_ID)
        adjusted = _adjust_annotations_after_text_edit(
            old_text, clean_text, annotations
        )
        save_scene_annotations(work_id, FULL_ESSAY_ANNOTATION_ID, adjusted)
    st.session_state[_essay_key("final_essay_manual")] = clean_text
    st.session_state[_essay_key("final_essay_editor")] = clean_text
    return _persist_essay_state(work_id)


def _add_draft_to_full_essay(
    work_id: str,
    section_id: str,
    draft: str,
) -> str:
    """Adaugă sau actualizează un fragment fără să piardă editările manuale."""
    clean_draft = str(draft).strip()
    current = str(st.session_state.get(_essay_key("final_essay_manual"), "")).strip()
    previous = str(
        st.session_state.get(_essay_key("final_sections"), {}).get(section_id, "")
    ).strip()

    if previous and previous in current:
        if previous == clean_draft:
            return "exists"
        updated = current.replace(previous, clean_draft, 1)
        result = "updated"
    elif clean_draft in current:
        result = "exists"
        updated = current
    else:
        updated = "\n\n".join(
            value for value in (current, clean_draft) if value
        )
        result = "added"

    st.session_state[_essay_key("final_sections")][section_id] = clean_draft
    _save_full_essay_text(work_id, updated)
    return result


def _adjust_annotations_after_text_edit(
    old_text: str,
    new_text: str,
    annotations: list[dict],
) -> list[dict]:
    """Păstrează marcajele din afara porțiunii modificate și deplasează restul."""
    if old_text == new_text:
        return annotations
    prefix = 0
    common_limit = min(len(old_text), len(new_text))
    while prefix < common_limit and old_text[prefix] == new_text[prefix]:
        prefix += 1
    suffix = 0
    old_remaining = len(old_text) - prefix
    new_remaining = len(new_text) - prefix
    while (
        suffix < old_remaining
        and suffix < new_remaining
        and old_text[len(old_text) - suffix - 1]
        == new_text[len(new_text) - suffix - 1]
    ):
        suffix += 1
    old_change_end = len(old_text) - suffix
    delta = len(new_text) - len(old_text)
    adjusted = []
    for annotation in annotations:
        start = int(annotation.get("start", -1))
        end = int(annotation.get("end", -1))
        if end <= prefix:
            adjusted.append(annotation)
        elif start >= old_change_end:
            moved = dict(annotation)
            moved["start"] = start + delta
            moved["end"] = end + delta
            moved["text"] = new_text[moved["start"] : moved["end"]]
            adjusted.append(moved)
        # Un marcaj care intersectează textul modificat este eliminat: intervalul
        # lui nu mai poate fi asociat sigur cu formularea nouă.
    return adjusted


def _render_full_essay_annotation_editor(work: dict) -> None:
    essay_text = str(st.session_state.get(_essay_key("final_essay_manual"), "")).strip()
    annotations = get_scene_annotations(work["id"], FULL_ESSAY_ANNOTATION_ID)
    event = ESSAY_ANNOTATOR_COMPONENT(
        work_id=work["id"],
        sequence_id=FULL_ESSAY_ANNOTATION_ID,
        title="Eseul meu",
        chapter="Varianta completă editabilă",
        source="Text construit de elev",
        text=essay_text,
        annotations=annotations,
        editable=True,
        key=f"full_essay_annotator_{work['id']}",
        default=None,
    )
    text_was_saved = _handle_full_essay_annotation_event(work, essay_text, event)
    if text_was_saved:
        st.session_state[_essay_key("full_essay_save_notice")] = True
        st.rerun(scope="fragment")
    if st.session_state.pop(_essay_key("full_essay_save_notice"), False):
        st.success("Eseul a fost salvat în baza de date.")
    if st.session_state.get(_essay_key("full_essay_annotation_ai")):
        st.info(st.session_state[_essay_key("full_essay_annotation_ai")])


def _handle_full_essay_annotation_event(
    work: dict,
    essay_text: str,
    event: dict | None,
) -> bool:
    if not isinstance(event, dict) or not event.get("event_id"):
        return False
    processed_key = _essay_key("full_essay_processed_annotation_event")
    if st.session_state.get(processed_key) == event["event_id"]:
        return False
    if event.get("type") == "text_changed":
        clean_text = str(event.get("text") or "").strip()
        _save_full_essay_text(work["id"], clean_text)
        save_scene_annotations(
            work["id"], FULL_ESSAY_ANNOTATION_ID, event.get("annotations", [])
        )
        st.session_state[processed_key] = event["event_id"]
        return True
    elif event.get("type") == "annotations_changed":
        save_scene_annotations(
            work["id"], FULL_ESSAY_ANNOTATION_ID, event.get("annotations", [])
        )
    elif event.get("type") == "ask_ai":
        selected_text = str(event.get("selected_text") or "").strip()
        if selected_text:
            section = {
                "id": "full_essay",
                "title": "Eseul complet",
                "instructions": "Evaluează coerența și corectitudinea eseului de Bacalaureat.",
            }
            st.session_state[_essay_key("full_essay_annotation_ai")] = answer_section_question(
                section,
                (
                    "Explică și evaluează fragmentul selectat din eseul meu, indicând "
                    f"succint ce este bun și ce trebuie îmbunătățit:\n\n{selected_text}\n\n"
                    f"ESEUL COMPLET PENTRU CONTEXT:\n{essay_text}"
                ),
            )
    st.session_state[processed_key] = event["event_id"]
    return False


@st.dialog(
    "Schema eseului",
    width="large",
    dismissible=True,
    on_dismiss=close_fullscreen_essay_mindmap,
)
def render_fullscreen_essay_mindmap(
    selected_node: str | None,
    work: dict,
    composition_elements: list[dict],
    essay_blueprint: dict,
) -> None:
    st.markdown(
        """
        <style>
          div[role="dialog"] { width: min(96vw, 1760px) !important; max-width: 96vw !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    event = render_essay_structure_intro(
        selected_node,
        fullscreen=True,
        work=work,
        composition_elements=composition_elements,
        essay_blueprint=essay_blueprint,
    )
    handle_essay_mindmap_event(
        event,
        active_node_key=_essay_key("essay_active_node"),
        fullscreen_key=_essay_key("essay_mindmap_fullscreen"),
    )


def handle_essay_mindmap_event(
    event: dict | None,
    active_node_key: str,
    fullscreen_key: str,
) -> None:
    if not isinstance(event, dict):
        return

    event_type = event.get("type")
    if event_type == "toggle_fullscreen":
        st.session_state[f"{_active_work()['id']}_preferred_workspace_tab"] = "Construiește eseu"
        st.session_state[fullscreen_key] = not st.session_state.get(fullscreen_key, False)
        st.rerun()

    if event_type != "select_section":
        return

    section_id = str(event.get("section") or "").strip()
    if not section_id or not any(
        section.get("id") == section_id for section in _essay_plan()
    ):
        return

    event_id = event.get("event_id") or f"select_section:{section_id}"
    handled_event_key = _essay_key("essay_handled_mindmap_event")
    if st.session_state.get(handled_event_key) != event_id:
        st.session_state[handled_event_key] = event_id
        st.session_state[active_node_key] = section_id
        st.rerun()


def render_essay_map_start_prompt() -> None:
    st.markdown(
        """
        <style>
          .essay-map-start-prompt {
            margin: 2.2rem auto 0;
            max-width: 760px;
            color: #2b6872;
            font-size: 50px !important;
            font-weight: 750;
            letter-spacing: -0.025em;
            line-height: 1.25;
            text-align: center;
          }
        </style>
        <p class="essay-map-start-prompt" style="font-size: 50px !important;">Apasă pe orice secțiune din mind map pentru a începe.</p>
        """,
        unsafe_allow_html=True,
    )


def _get_essay_section(section_id: str) -> dict:
    return next(section for section in _essay_plan() if section["id"] == section_id)


def _quotes_selected_for_section(section: dict) -> list[dict]:
    return quotes_for_essay_section(
        _active_work()["id"], section, _essay_plan()
    )


def render_composition_essay_workspace(element: dict) -> None:
    """Deschide atelierul de redactare pentru elementul ales de elev."""
    section = dict(_get_essay_section(element["section_id"]))
    section["title"] = element["title"]
    if element.get("central_idea"):
        section["instructions"] = (
            section["instructions"].strip()
            + "\n\nIdee centrală din schema studiată:\n"
            + element["central_idea"]
        )
    render_essay_section_workspace(section)


def render_essay_section_workspace(section: dict) -> None:
    """Atelier comun pentru trăsături, secvențe și elemente compoziționale."""
    draft_key = _essay_draft_key(section["id"])
    max_chars = int(section.get("max_chars") or ESSAY_PARAGRAPH_MAX_CHARS)
    editor_height = int(section.get("editor_height") or 255)
    draft_col, teacher_col = st.columns([1.12, 0.88], gap="medium")

    with draft_col:
        with st.container(border=True):
            title_col, hint_col = st.columns([1, 0.72])
            with title_col:
                st.markdown(f"#### {section['title']}")
            with hint_col:
                with st.popover("💡 Indicație", use_container_width=True):
                    st.markdown("**În acest paragraf:**")
                    st.write(section["instructions"].strip())

            selected_quotes = _quotes_selected_for_section(section)
            if selected_quotes:
                with st.expander(
                    f"💬 {len(selected_quotes)} "
                    f"{'citat selectat' if len(selected_quotes) == 1 else 'citate selectate'} — "
                    "vor fi integrate automat",
                ):
                    for quote in selected_quotes:
                        st.markdown(f"> {quote['text']}")

            draft = st.text_area(
                f"Scrie paragraful pentru {section['title']}",
                key=draft_key,
                height=editor_height,
                max_chars=max_chars,
                placeholder="Scrie aici paragraful tău...",
                label_visibility="collapsed",
                on_change=_persist_essay_state,
                args=(_active_work()["id"],),
            )
            st.caption(f"{len(draft)}/{max_chars} caractere")

            evaluate_col, add_col = st.columns(2, gap="small")
            with evaluate_col:
                if st.button(
                    "Evaluează",
                    key=_essay_key(f"evaluate_{section['id']}"),
                    type="primary",
                    use_container_width=True,
                ):
                    if not draft.strip():
                        st.warning(
                            "Scrie mai întâi paragraful pe care vrei să îl evaluez."
                        )
                    else:
                        history = ensure_chat_history(section)
                        history.append(
                            {
                                "role": "user",
                                "content": f"Te rog să evaluezi paragraful meu pentru «{section['title']}».",
                            }
                        )
                        with st.spinner("Profesorul AI evaluează paragraful..."):
                            evaluation = answer_section_question(
                                section,
                                _build_section_evaluation_request(section, draft),
                            )
                        history.append(
                            {"role": "assistant", "content": evaluation}
                        )
                        st.rerun()
            with add_col:
                if st.button(
                    "Adaugă în eseu",
                    key=_essay_key(f"add_{section['id']}_to_essay"),
                    use_container_width=True,
                ):
                    if not draft.strip():
                        st.warning(
                            "Scrie mai întâi paragraful pe care vrei să îl adaugi."
                        )
                    else:
                        result = _add_draft_to_full_essay(
                            _active_work()["id"], section["id"], draft
                        )
                        if result == "exists":
                            st.info("Acest fragment există deja în eseul complet.")
                        elif result == "updated":
                            st.success("Fragmentul a fost actualizat în eseul complet.")
                        else:
                            st.success("Fragmentul a fost adăugat în eseul complet.")

    with teacher_col:
        render_section_teacher_chat(section)


def render_section_teacher_chat(section: dict) -> None:
    with st.container(border=True):
        st.markdown("#### ✨ Profesor AI")
        st.caption(f"Te ajută să redactezi corect secțiunea «{section['title']}».")
        history = ensure_chat_history(section)

        with st.container(height=220, border=False):
            for index, message in enumerate(history):
                with st.chat_message(message["role"]):
                    st.write(message["content"])
                    if message["role"] == "assistant" and index == 0:
                        if st.button(
                            "Nu știi cum să formulezi? Lasă-mă să te ajut.",
                            key=_essay_key(f"generate_help_{section['id']}"),
                            use_container_width=True,
                        ):
                            generated_text = generate_section_paragraph(section)
                            if generated_text:
                                history.append(
                                    {"role": "assistant", "content": generated_text}
                                )
                                st.rerun()

        with st.form(_essay_key(f"teacher_form_{section['id']}"), clear_on_submit=True):
            input_col, send_col = st.columns([5, 1])
            with input_col:
                user_message = st.text_input(
                    "Întreabă profesorul AI",
                    placeholder="Scrie întrebarea ta...",
                    label_visibility="collapsed",
                )
            with send_col:
                submitted = st.form_submit_button("➜", use_container_width=True)

        if submitted and user_message.strip():
            history.append({"role": "user", "content": user_message.strip()})
            with ai_thinking():
                answer = answer_section_question(section, user_message.strip())
            history.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
            st.rerun()


def _build_section_evaluation_request(section: dict, draft: str) -> str:
    work = _active_work()
    trait_policy = _essay_runtime()["blueprint"].get("strict_trait_policy", {})
    strict_rule = ""
    if section.get("kind") == "literary_trait" or section["id"].startswith("trasatura_"):
        accepted = ", ".join(trait_policy.get("accepted_trait_titles") or [])
        strict_rule = (
            "\nREGULĂ OBLIGATORIE: sunt acceptate exclusiv trăsăturile din eseul-model: "
            f"{accepted}. Orice altă trăsătură trebuie semnalată ca incorectă.\n"
        )
    return f"""
Evaluează strict paragraful elevului pentru secțiunea „{section['title']}” a eseului de
Bacalaureat despre opera „{work['title']}” de {work['author']}.

Verifică dacă paragraful respectă această indicație:
{section['instructions'].strip()}
{strict_rule}

Răspunde direct elevului. Începe cu verdictul „Este suficient de bun” sau
„Mai trebuie îmbunătățit”. Apoi precizează succint ce este corect și ce trebuie completat
sau reformulat. Nu rescrie integral paragraful decât dacă elevul cere explicit acest lucru.

PARAGRAFUL ELEVULUI:
{draft}
""".strip()


def render_introduction_workspace() -> None:
    """Render the student draft and the dedicated teacher chat for Introduction."""
    section = _get_essay_section("introducere")
    draft_col, teacher_col = st.columns([1.12, 0.88], gap="medium")

    with draft_col:
        with st.container(border=True):
            title_col, hint_col = st.columns([1, 0.72])
            with title_col:
                st.markdown("#### ① Introducere")
            with hint_col:
                with st.popover("💡 Indicație", use_container_width=True):
                    st.markdown("**În introducere menționează:**")
                    checklist = section.get("checklist") or [
                        item.strip()
                        for item in section["instructions"].splitlines()
                        if item.strip()
                    ]
                    for item in checklist:
                        st.markdown(f"- {item}")

            draft = st.text_area(
                "Scrie introducerea eseului tău",
                key=_essay_draft_key("introducere"),
                height=255,
                max_chars=ESSAY_PARAGRAPH_MAX_CHARS,
                placeholder="Scrie introducerea eseului tău...",
                label_visibility="collapsed",
                on_change=_persist_essay_state,
                args=(_active_work()["id"],),
            )
            st.caption(f"{len(draft)}/{ESSAY_PARAGRAPH_MAX_CHARS} caractere")

            evaluate_col, add_col = st.columns(2, gap="small")
            with evaluate_col:
                if st.button(
                    "Evaluează",
                    key=_essay_key("evaluate_introduction"),
                    type="primary",
                    use_container_width=True,
                ):
                    if not draft.strip():
                        st.warning(
                            "Scrie mai întâi introducerea pe care vrei să o evaluez."
                        )
                    else:
                        history = ensure_chat_history(section)
                        evaluation_request = _build_introduction_evaluation_request(
                            draft
                        )
                        history.append(
                            {
                                "role": "user",
                                "content": "Te rog să evaluezi introducerea pe care am scris-o.",
                            }
                        )
                        with st.spinner("Profesorul AI evaluează introducerea..."):
                            evaluation = answer_section_question(
                                section, evaluation_request
                            )
                        history.append(
                            {"role": "assistant", "content": evaluation}
                        )
                        st.rerun()
            with add_col:
                if st.button(
                    "Adaugă în eseu",
                    key=_essay_key("add_introduction_to_essay"),
                    use_container_width=True,
                ):
                    if not draft.strip():
                        st.warning(
                            "Scrie mai întâi introducerea pe care vrei să o adaugi."
                        )
                    else:
                        result = _add_draft_to_full_essay(
                            _active_work()["id"], section["id"], draft
                        )
                        if result == "exists":
                            st.info("Introducerea există deja în eseul complet.")
                        elif result == "updated":
                            st.success("Introducerea a fost actualizată în eseul complet.")
                        else:
                            st.success("Introducerea a fost adăugată în eseul complet.")

    with teacher_col:
        render_introduction_teacher_chat(section)


def render_introduction_teacher_chat(section: dict) -> None:
    with st.container(border=True):
        st.markdown("#### ✨ Profesor AI")
        st.caption("Te ajută să formulezi o introducere clară și captivantă.")

        history = ensure_chat_history(section)
        with st.container(height=220, border=False):
            for index, message in enumerate(history):
                with st.chat_message(message["role"]):
                    st.write(message["content"])

                    if message["role"] == "assistant" and index == 0:
                        if st.button(
                            "Nu știi cum să formulezi? Lasă-mă să te ajut.",
                            key=_essay_key("generate_introduction_help"),
                            use_container_width=True,
                        ):
                            generated_text = generate_section_paragraph(section)
                            if generated_text:
                                history.append(
                                    {
                                        "role": "assistant",
                                        "content": generated_text,
                                    }
                                )
                                st.rerun()

        with st.form(_essay_key("introduction_teacher_form"), clear_on_submit=True):
            input_col, send_col = st.columns([5, 1])
            with input_col:
                user_message = st.text_input(
                    "Întreabă profesorul AI",
                    placeholder="Scrie întrebarea ta...",
                    label_visibility="collapsed",
                )
            with send_col:
                submitted = st.form_submit_button("➜", use_container_width=True)

        if submitted and user_message.strip():
            history.append({"role": "user", "content": user_message.strip()})
            with ai_thinking():
                answer = answer_section_question(section, user_message.strip())
            history.append(
                {
                    "role": "assistant",
                    "content": answer,
                }
            )
            st.rerun()


def _build_introduction_evaluation_request(draft: str) -> str:
    work = _active_work()
    section = _get_essay_section("introducere")
    checklist = "\n".join(
        f"{index}. {item}"
        for index, item in enumerate(section.get("checklist") or [], start=1)
    ) or section["instructions"].strip()
    return f"""
Evaluează strict introducerea de mai jos pentru un eseu de Bacalaureat despre
opera „{work['title']}” de {work['author']}.

Verifică strict acest checklist extras din eseul-model:
{checklist}

Răspunde direct elevului. Începe cu un verdict scurt: „Este suficient de bună” sau
„Mai trebuie îmbunătățită”. Dacă lipsește ceva ori formularea nu este bună, explică exact
ce să îmbunătățească într-o listă scurtă cu liniuțe. Nu rescrie paragraful complet decât dacă
elevul îți cere explicit asta.

INTRODUCEREA ELEVULUI:
{draft}
""".strip()


def _essay_draft_key(section_id: str) -> str:
    return (
        _essay_key("introduction_draft")
        if section_id == "introducere"
        else _essay_key(f"essay_draft_{section_id}")
    )


def _persist_essay_state(work_id: str = "ion") -> bool:
    drafts = {
        section["id"]: str(
            st.session_state.get(_essay_draft_key(section["id"]), "")
        )
        for section in _essay_plan()
    }
    return save_essay_state(
        work_id=work_id,
        essay_text=str(st.session_state.get(_essay_key("final_essay_manual"), "")),
        sections=st.session_state.get(_essay_key("final_sections"), {}),
        drafts=drafts,
    )


def initialize_essay_state(work_id: str) -> None:
    user = st.session_state.get("auth_user") or {}
    user_identity = str(user.get("id") or "anonymous")
    load_marker_key = _essay_key("essay_loaded_for_user")
    current_marker = f"{user_identity}:{work_id}"
    previous_marker_exists = load_marker_key in st.session_state

    if st.session_state.get(load_marker_key) != current_marker:
        saved = load_essay_state(work_id)
        if saved.get("exists"):
            st.session_state[_essay_key("final_sections")] = saved["sections"]
            st.session_state[_essay_key("final_essay_manual")] = saved["essay_text"]
            st.session_state[_essay_key("final_essay_editor")] = saved["essay_text"]
            for section in _essay_plan():
                st.session_state[_essay_draft_key(section["id"])] = saved[
                    "drafts"
                ].get(section["id"], "")
        elif not previous_marker_exists:
            # Migrează în DB un eseu care exista deja în sesiunea curentă înainte
            # de introducerea persistenței, fără să îl suprascrie cu un șablon gol.
            st.session_state.setdefault(_essay_key("final_sections"), {})
            st.session_state.setdefault(_essay_key("final_essay_manual"), "")
            st.session_state.setdefault(
                _essay_key("final_essay_editor"),
                st.session_state[_essay_key("final_essay_manual")],
            )
            for section in _essay_plan():
                st.session_state.setdefault(_essay_draft_key(section["id"]), "")
            _persist_essay_state(work_id)
        else:
            # La schimbarea contului nu transportăm textul fostului utilizator.
            st.session_state[_essay_key("final_sections")] = {}
            st.session_state[_essay_key("final_essay_manual")] = ""
            st.session_state[_essay_key("final_essay_editor")] = ""
            for section in _essay_plan():
                st.session_state[_essay_draft_key(section["id"])] = ""
        st.session_state[load_marker_key] = current_marker

    st.session_state.setdefault(
        _essay_key("selected_section_id"), _essay_plan()[0]["id"]
    )
    st.session_state.setdefault(_essay_key("final_sections"), {})
    st.session_state.setdefault(_essay_key("final_essay_manual"), "")
    st.session_state.setdefault(
        _essay_key("final_essay_editor"),
        st.session_state[_essay_key("final_essay_manual")],
    )


def get_selected_section() -> dict:
    selected_id = st.session_state[_essay_key("selected_section_id")]

    for section in _essay_plan():
        if section["id"] == selected_id:
            return section

    return _essay_plan()[0]


def get_chat_history_key(section_id: str) -> str:
    return _essay_key(f"essay_chat_{section_id}")


def ensure_chat_history(section: dict) -> list[dict]:
    history_key = get_chat_history_key(section["id"])

    if history_key not in st.session_state:
        st.session_state[history_key] = [
            {
                "role": "assistant",
                "content": (
                    f"Lucrăm acum doar pe secțiunea **{section['title']}**. "
                    "Poți să-mi ceri să generez paragraful, să-l simplific, să-l fac mai elegant "
                    "sau să verific dacă respectă baremul."
                ),
            }
        ]

    return st.session_state[history_key]


def render_section_list() -> None:
    st.markdown("### Secțiuni eseu")

    for index, section in enumerate(_essay_plan(), start=1):
        section_id = section["id"]
        is_selected = st.session_state[_essay_key("selected_section_id")] == section_id
        is_final = section_id in st.session_state[_essay_key("final_sections")]

        if is_final:
            status = "✅"
        elif is_selected:
            status = "🔴"
        else:
            status = "⭕"

        label = f"{status} {index}. {section['title']}"

        if st.button(
            label,
            key=_essay_key(f"select_section_{section_id}"),
            use_container_width=True,
        ):
            st.session_state[_essay_key("selected_section_id")] = section_id
            st.rerun()


def render_chat_workspace() -> None:
    section = get_selected_section()
    history = ensure_chat_history(section)

    st.markdown(f"### {section['title']}")

    with st.expander("Instrucțiuni pentru această secțiune"):
        st.write(section["instructions"])

    chat_box = st.container(height=430, border=True)

    with chat_box:
        for idx, message in enumerate(history):
            with st.chat_message(message["role"]):
                st.write(message["content"])

                if message["role"] == "assistant" and idx != 0:
                    if st.button(
                        "Păstrează ca variantă finală",
                        key=_essay_key(f"save_message_{section['id']}_{idx}"),
                    ):
                        st.session_state[_essay_key("final_sections")][section["id"]] = message["content"]
                        rebuild_final_essay_from_sections()
                        st.success("Varianta a fost adăugată în eseul final.")
                        st.rerun()

    user_message = st.chat_input(
        f"Întreabă despre {section['title']}",
        key=_essay_key(f"chat_input_{section['id']}"),
    )

    if user_message:
        history.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        with ai_thinking():
            answer = answer_section_question(section, user_message)

        history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.rerun()

    if st.button(
        "Generează paragraf",
        key=_essay_key(f"generate_paragraph_{section['id']}"),
        type="primary",
        use_container_width=True,
    ):
        generated_text = generate_section_paragraph(section)

        if generated_text:
            history.append(
                {
                    "role": "assistant",
                    "content": generated_text,
                }
            )
            st.rerun()


def answer_section_question(section: dict, user_message: str) -> str:
    if answer_essay_node_question is None:
        return (
            "AI-ul nu este încă legat. Verifică funcția `answer_essay_node_question` "
            "din `services/ai_service.py`."
        )

    accepted_text = st.session_state[_essay_key("final_sections")].get(section["id"], "")
    selected_quotes = _quotes_selected_for_section(section)
    selected_quote_instructions = quote_instructions(selected_quotes)

    node_content = f"""
Instrucțiuni secțiune:
{section["instructions"]}

{selected_quote_instructions}

Varianta finală curentă pentru această secțiune:
{accepted_text}
""".strip()

    try:
        answer = answer_essay_node_question(
            work=_active_work(),
            blueprint=_essay_runtime()["blueprint"],
            user_question=user_message,
            node_title=section["title"],
            node_content=node_content,
        )
        return ensure_quotes_present(answer, selected_quotes)
    except Exception as error:
        return f"A apărut o eroare la apelul AI: {error}"


def generate_section_paragraph(section: dict) -> str:
    if generate_essay_section is None:
        st.error(
            "Funcția `generate_essay_section` nu există în `services/ai_service.py`."
        )
        return ""

    current_final_essay = st.session_state.get(
        _essay_key("final_essay_manual"), ""
    ).strip()
    selected_quotes = _quotes_selected_for_section(section)
    selected_quote_instructions = quote_instructions(selected_quotes)
    section_instructions = "\n\n".join(
        part
        for part in (section["instructions"].strip(), selected_quote_instructions)
        if part
    )

    with ai_thinking(f"AI Profesor generează secțiunea «{section['title']}»"):
        try:
            generated = generate_essay_section(
                work=_active_work(),
                blueprint=_essay_runtime()["blueprint"],
                section_title=section["title"],
                section_instructions=section_instructions,
                current_final_essay=current_final_essay,
            ).strip()
            return ensure_quotes_present(generated, selected_quotes)
        except Exception as error:
            st.error(f"A apărut o eroare la generare: {error}")
            return ""


def rebuild_final_essay_from_sections() -> None:
    parts = []

    for section in _essay_plan():
        section_id = section["id"]
        if section_id in st.session_state[_essay_key("final_sections")]:
            parts.append(st.session_state[_essay_key("final_sections")][section_id])

    final_essay = "\n\n".join(parts).strip()
    _save_full_essay_text(_active_work()["id"], final_essay)


def clear_final_essay() -> None:
    st.session_state[_essay_key("final_essay_manual")] = ""
    st.session_state[_essay_key("final_essay_editor")] = ""
    st.session_state[_essay_key("final_sections")] = {}
    _persist_essay_state(_active_work()["id"])


def render_final_essay_box() -> None:
    st.markdown("### Eseu final")

    st.text_area(
        "Eseu complet editabil",
        height=420,
        key=_essay_key("final_essay_editor"),
        placeholder="Pe măsură ce alegi variante finale pentru secțiuni, ele vor apărea aici.",
        on_change=_sync_legacy_final_essay_editor,
    )

    st.button(
        "Șterge eseul final",
        use_container_width=True,
        on_click=clear_final_essay,
    )


def _sync_legacy_final_essay_editor() -> None:
    _save_full_essay_text(
        _active_work()["id"],
        str(st.session_state.get(_essay_key("final_essay_editor"), "")),
    )
