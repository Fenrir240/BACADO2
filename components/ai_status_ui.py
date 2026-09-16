"""Indicator vizual comun pentru apelurile interactive către AI Profesor."""

from contextlib import contextmanager
from collections.abc import Iterator

import streamlit as st


@contextmanager
def ai_thinking(label: str = "AI Profesor se gândește") -> Iterator[None]:
    """Afișează un balon de chat animat cât timp răspunsul AI este generat."""
    with st.chat_message("assistant", avatar="✨"):
        placeholder = st.empty()
        placeholder.markdown(
            f"""
            <style>
              @keyframes ai-thinking-bounce {{
                0%, 60%, 100% {{ transform: translateY(0); opacity: .42; }}
                30% {{ transform: translateY(-5px); opacity: 1; }}
              }}
              .ai-thinking-indicator {{
                display: inline-flex;
                align-items: center;
                gap: .55rem;
                min-height: 2.35rem;
                padding: .55rem .8rem;
                border: 1px solid #d8e8e5;
                border-radius: 14px;
                background: #f4faf8;
                color: #315d58;
                font-size: .9rem;
                font-weight: 650;
              }}
              .ai-thinking-dots {{ display: inline-flex; gap: .22rem; }}
              .ai-thinking-dots span {{
                width: .42rem;
                height: .42rem;
                border-radius: 50%;
                background: #25856f;
                animation: ai-thinking-bounce 1.2s infinite ease-in-out;
              }}
              .ai-thinking-dots span:nth-child(2) {{ animation-delay: .16s; }}
              .ai-thinking-dots span:nth-child(3) {{ animation-delay: .32s; }}
            </style>
            <div class="ai-thinking-indicator" role="status" aria-live="polite">
              <span>{label}</span>
              <span class="ai-thinking-dots" aria-hidden="true">
                <span></span><span></span><span></span>
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        try:
            yield
        finally:
            placeholder.empty()
