import streamlit as st

from components.learning_path_ui import render_learning_path, render_quick_test
from components.progress_ui import render_progress_panel
from components.essay_ui import render_essay_for_work
from services.progress_service import get_work_progress, reset_work_progress

try:
    from services.works_service import move_work
except ImportError:
    move_work = None


def render_opera_page(work: dict) -> None:
    work_id = work["id"]
    progress = get_work_progress(work_id)

    st.markdown('<div class="opera-workspace-marker"></div>', unsafe_allow_html=True)
    render_sidebar_actions(work)

    tab_labels = [
        "Înțelege opera",
        "Testare rapidă",
        "Construiește eseu",
    ]
    tab_default_key = f"{work_id}_preferred_workspace_tab"
    tab_understand, tab_quick_test, tab_essay = st.tabs(
        tab_labels,
        default=st.session_state.get(tab_default_key, tab_labels[0]),
    )

    with tab_understand:
        render_learning_path(work, progress)

    with tab_quick_test:
        render_quick_test(work, progress)

    with tab_essay:
        render_essay_for_work(work, progress)

    render_progress_panel(work_id, progress)


def render_sidebar_actions(work: dict) -> None:
    with st.sidebar.popover(
        "⋮",
        key=f"opera_actions_{work['id']}",
        help="Acțiuni opera",
    ):
        render_move_button(work)
        if st.button(
            "Resetează progresul",
            key=f"reset_{work['id']}",
            use_container_width=True,
            help="Șterge progresul salvat pentru această operă",
        ):
            reset_work_progress(work["id"])
            st.rerun()


def render_top_actions(work: dict) -> None:
    col1, col2, _ = st.columns([1, 1, 2.5])

    with col1:
        render_move_button(work)

    with col2:
        if st.button(
            "Resetează progresul",
            key=f"reset_{work['id']}",
            use_container_width=True,
            help="Șterge progresul salvat pentru această operă",
        ):
            reset_work_progress(work["id"])
            st.rerun()


def render_move_button(work: dict) -> None:
    if move_work is None:
        return

    current_category = work.get("category", "my")

    if current_category == "my":
        target_category = "other"
        button_text = "Mută în Alte opere"
        help_text = "Opera va fi mutată din Operele mele în Alte opere."
    else:
        target_category = "my"
        button_text = "Mută în Operele mele"
        help_text = "Opera va fi mutată din Alte opere în Operele mele."

    if st.button(
        button_text,
        help=help_text,
        key=f"move_{work['id']}",
        use_container_width=True,
    ):
        move_work(work["id"], target_category)
        st.success("Opera a fost mutată.")
        st.rerun()
