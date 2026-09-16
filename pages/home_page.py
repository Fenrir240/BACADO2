# pages/home_page.py

import streamlit as st

from components.ui import render_app_header


def render_home_page():
    render_app_header(
        "Bac AI",
        "Alege o operă din meniul din stânga și continuă traseul de învățare de unde ai rămas.",
        "📚",
    )

    st.subheader("Spațiul tău de învățare")

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        with st.container(border=True):
            st.markdown("#### 01 · Parcurge")
            st.write("Studiază rezumatul, personajele și secvențele semnificative.")

    with col2:
        with st.container(border=True):
            st.markdown("#### 02 · Verifică")
            st.write("Rezolvă exercițiile și urmărește progresul pentru fiecare operă.")

    with col3:
        with st.container(border=True):
            st.markdown("#### 03 · Construiește")
            st.write("Folosește AI Profesor și alcătuiește eseul pe structura de Bac.")

    st.info("Operele tale sunt disponibile permanent în bara laterală.")
