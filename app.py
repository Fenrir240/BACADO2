import streamlit as st

from components.auth_ui import require_auth
from components.ui import setup_page
from pages.home_page import render_home_page
from pages.opera_page import render_opera_page
from services.works_service import get_my_works, get_other_works


setup_page("Bac AI", "assets/bacorado-logo.jpeg")
st.logo(
    "assets/bacorado-logo.jpeg",
    size="large",
    icon_image="assets/bacorado-logo.jpeg",
)

if not require_auth():
    st.stop()


def make_opera_page(work: dict):
    def page():
        render_opera_page(work)

    return page


my_works = get_my_works()
other_works = get_other_works()


pages = {
    "General": [
        st.Page(
            render_home_page,
            title="Acasă",
            icon="🏠",
            url_path="home",
        )
    ],
    "Operele mele": [
        st.Page(
            make_opera_page(work),
            title=work["title"],
            icon=work["icon"],
            url_path=f"opera-{work['id']}",
        )
        for work in my_works
    ],
    "Alte opere": [
        st.Page(
            make_opera_page(work),
            title=work["title"],
            icon=work["icon"],
            url_path=f"opera-{work['id']}",
        )
        for work in other_works
    ],
}


current_page = st.navigation(pages)
current_page.run()
