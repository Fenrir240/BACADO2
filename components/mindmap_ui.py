# components/mindmap_ui.py

import streamlit as st


def render_mindmap_for_work(work: dict):
    st.subheader(f'Mind map — {work["title"]}')

    st.info(
        "Mind map-ul este disponibil din prima. Eseul complet se deblochează doar după verificare."
    )

    nodes = [
        "Introducere",
        "Încadrare în curent",
        "Tema operei",
        "Secvența 1",
        "Secvența 2",
        "Elemente de compoziție",
        "Concluzie",
    ]

    for node in nodes:
        with st.container(border=True):
            st.markdown(f"### 🧩 {node}")
            st.write("Click aici va deschide chat-ul dedicat acestui nod.")