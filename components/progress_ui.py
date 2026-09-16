from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from services.progress_service import (
    acknowledge_progress_orb,
    save_progress_orb_position,
)


PROGRESS_ORB_COMPONENT = components.declare_component(
    "progress_orb",
    path=str(Path(__file__).parent / "progress_orb_component"),
)


def render_progress_panel(work_id: str, progress: dict) -> None:
    score = max(0.0, min(100.0, float(progress.get("score", 0) or 0)))
    conversation_score = max(
        0,
        min(
            score,
            int(
                progress.get(
                    "characters_ai_xp_applied_to_score",
                    progress.get("characters_ai_xp", 0),
                )
                or 0
            ),
        ),
    )
    quick_test_score = max(0, score - conversation_score)
    acknowledged_score = max(
        0,
        min(100.0, float(progress.get("progress_orb_acknowledged_score", 0) or 0)),
    )
    event = PROGRESS_ORB_COMPONENT(
        work_id=work_id,
        score=score,
        conversation_score=conversation_score,
        quick_test_score=quick_test_score,
        current_step=progress.get("current_step", "Neinceput"),
        acknowledged_score=acknowledged_score,
        position=progress.get("progress_orb_position"),
        key=f"progress_orb_{work_id}",
        default=None,
    )

    event_id = (event or {}).get("event_id")
    if not event_id:
        return

    # A component value triggers a Streamlit run before this handler can save it.
    # Remembering the event prevents a rerun loop and lets the component receive
    # the newly saved coordinates immediately.
    handled_event_key = f"progress_orb_handled_event_{work_id}"
    if st.session_state.get(handled_event_key) == event_id:
        return

    st.session_state[handled_event_key] = event_id

    if event.get("type") == "position":
        save_progress_orb_position(work_id, event.get("position", {}))
        st.rerun()
    elif event.get("type") == "acknowledge":
        acknowledge_progress_orb(work_id)
        st.rerun()
