import streamlit as st
import streamlit.components.v1 as components

from services.auth_service import (
    authenticate_user,
    create_access_token,
    create_user,
    get_user_from_token,
    init_auth_db,
)


TOKEN_KEY = "auth_token"
USER_KEY = "auth_user"
TOKEN_QUERY_PARAM = "token"
AUTH_STORAGE_KEY = "bac_ai_auth_token"
LOGO_PATH = "assets/bacorado-logo.jpeg"


def require_auth() -> bool:
    init_auth_db()
    render_auth_token_bridge()
    restore_user_from_token()

    if st.session_state.get(USER_KEY):
        render_logged_in_user()
        return True

    render_auth_screen()
    return False


def restore_user_from_token() -> None:
    token = st.session_state.get(TOKEN_KEY) or get_token_from_query_params()

    if not token:
        return

    user = get_user_from_token(token)

    if user is None:
        st.session_state.pop(TOKEN_KEY, None)
        st.session_state.pop(USER_KEY, None)
        clear_token_query_param()
        return

    st.session_state[TOKEN_KEY] = token
    st.session_state[USER_KEY] = user


def render_logged_in_user() -> None:
    user = st.session_state[USER_KEY]

    with st.sidebar:
        st.divider()
        st.caption("CONTUL MEU")
        st.markdown(f"**{user.get('name') or user['email']}**")
        if user.get("name"):
            st.caption(user["email"])

        if st.button("Deconectare", use_container_width=True, help="Ieși din cont"):
            st.session_state.pop(TOKEN_KEY, None)
            st.session_state.pop(USER_KEY, None)
            st.session_state["clear_auth_storage"] = True
            clear_token_query_param()
            st.rerun()


def render_auth_screen() -> None:
    left_space, auth_col, right_space = st.columns([1, 1.05, 1])

    with auth_col:
        logo_left, logo_col, logo_right = st.columns([1, 2.9, 1])
        with logo_col:
            st.image(LOGO_PATH, use_container_width=True)

        st.markdown(
            """
            <div class="auth-brand">
                <p>Învață organizat, păstrează-ți progresul și lucrează cu AI Profesor.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        login_tab, register_tab = st.tabs(["Conectare", "Cont nou"])

        with login_tab:
            render_login_form()

        with register_tab:
            render_register_form()


def render_login_form() -> None:
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="nume@exemplu.ro")
        password = st.text_input("Parolă", type="password", placeholder="Parola ta")
        submitted = st.form_submit_button(
            "Conectare",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    try:
        user = authenticate_user(email, password)
        login_user(user)
        st.rerun()
    except ValueError as error:
        st.error(str(error))


def render_register_form() -> None:
    with st.form("register_form"):
        name = st.text_input("Nume", placeholder="Numele tău")
        email = st.text_input("Email", placeholder="nume@exemplu.ro")
        password = st.text_input("Parolă", type="password", placeholder="Minimum 8 caractere")
        submitted = st.form_submit_button(
            "Creează cont",
            type="primary",
            use_container_width=True,
        )

    if not submitted:
        return

    try:
        user = create_user(email=email, password=password, name=name)
        login_user(user)
        st.rerun()
    except ValueError as error:
        st.error(str(error))


def login_user(user: dict) -> None:
    token = create_access_token(user)
    st.session_state[USER_KEY] = user
    st.session_state[TOKEN_KEY] = token
    st.query_params[TOKEN_QUERY_PARAM] = token
    st.session_state["persist_auth_token"] = token


def get_token_from_query_params() -> str:
    token = st.query_params.get(TOKEN_QUERY_PARAM, "")

    if isinstance(token, list):
        return token[0] if token else ""

    return token


def clear_token_query_param() -> None:
    if TOKEN_QUERY_PARAM in st.query_params:
        del st.query_params[TOKEN_QUERY_PARAM]


def render_auth_token_bridge() -> None:
    token_to_persist = st.session_state.pop("persist_auth_token", "")
    should_clear = st.session_state.pop("clear_auth_storage", False)

    components.html(
        f"""
        <script>
        (function() {{
            const storageKey = {AUTH_STORAGE_KEY!r};
            const tokenParam = {TOKEN_QUERY_PARAM!r};
            const tokenToPersist = {token_to_persist!r};
            const shouldClear = {str(should_clear).lower()};

            try {{
                if (shouldClear) {{
                    window.localStorage.removeItem(storageKey);
                    return;
                }}

                const parentUrl = new URL(window.parent.location.href);
                const queryToken = parentUrl.searchParams.get(tokenParam);

                if (tokenToPersist) {{
                    window.localStorage.setItem(storageKey, tokenToPersist);
                    return;
                }}

                if (queryToken) {{
                    window.localStorage.setItem(storageKey, queryToken);
                    return;
                }}

                const storedToken = window.localStorage.getItem(storageKey);
                if (!storedToken) {{
                    return;
                }}

                parentUrl.searchParams.set(tokenParam, storedToken);
                window.parent.history.replaceState(null, "", parentUrl.toString());
                window.parent.location.reload();
            }} catch (error) {{
                console.warn("Auth token bridge failed", error);
            }}
        }})();
        </script>
        """,
        height=0,
    )
