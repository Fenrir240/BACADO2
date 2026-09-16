import streamlit as st


def setup_page(title: str, icon: str = "📚") -> None:
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="auto",
    )

    inject_global_css()


def inject_global_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                color-scheme: light;
                --bac-bg: #f4f8f7;
                --bac-bg-blue: #f3f7fc;
                --bac-panel: #ffffff;
                --bac-panel-soft: #f7faf9;
                --bac-line: #dce8e5;
                --bac-line-strong: #bfd5d1;
                --bac-text: #153249;
                --bac-heading: #0e293d;
                --bac-muted: #607789;
                --bac-soft: #8a9ca9;
                --bac-teal: #137c80;
                --bac-teal-dark: #0f656a;
                --bac-blue: #2767c7;
                --bac-blue-soft: #eaf2ff;
                --bac-green: #16875f;
                --bac-green-soft: #e8f7f0;
                --bac-warning: #b76b12;
                --bac-warning-soft: #fff7e8;
                --bac-danger: #bd3b4b;
                --bac-danger-soft: #fff0f2;
                --bac-shadow: 0 12px 32px rgba(27, 73, 72, 0.08);
                --bac-shadow-sm: 0 5px 16px rgba(27, 73, 72, 0.07);
            }

            * {
                box-sizing: border-box;
                scrollbar-color: #a9c9c5 #edf3f2;
                scrollbar-width: thin;
            }

            *::-webkit-scrollbar {
                width: 9px;
                height: 9px;
            }

            *::-webkit-scrollbar-track {
                background: #edf3f2;
            }

            *::-webkit-scrollbar-thumb {
                border: 2px solid #edf3f2;
                border-radius: 8px;
                background: #a9c9c5;
            }

            *::-webkit-scrollbar-thumb:hover {
                background: #77aaa5;
            }

            html,
            body,
            [data-testid="stAppViewContainer"],
            .stApp {
                color: var(--bac-text);
                background: var(--bac-bg);
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            }

            [data-testid="stAppViewContainer"] > .main {
                background:
                    linear-gradient(90deg, rgba(22, 135, 95, 0.025), transparent 24%, transparent 76%, rgba(39, 103, 199, 0.025)),
                    var(--bac-bg);
            }

            [data-testid="stHeader"] {
                background: rgba(244, 248, 247, 0.88);
                backdrop-filter: blur(12px);
                border-bottom: 1px solid rgba(220, 232, 229, 0.8);
            }

            [data-testid="stDecoration"] {
                height: 3px;
                background: linear-gradient(90deg, var(--bac-green) 0 48%, var(--bac-blue) 48% 100%);
            }

            [data-testid="stToolbar"] {
                right: 1rem;
            }

            [data-testid="stToolbar"] button,
            [data-testid="collapsedControl"] button {
                color: var(--bac-text);
            }

            .block-container {
                max-width: 1640px;
                padding-top: 1.7rem;
                padding-bottom: 3rem;
                padding-left: clamp(1.1rem, 2.2vw, 2.4rem);
                padding-right: clamp(1.1rem, 2.2vw, 2.4rem);
            }

            [data-testid="stSidebar"] {
                background: #fbfdfc;
                border-right: 1px solid var(--bac-line);
                box-shadow: 8px 0 30px rgba(27, 73, 72, 0.035);
            }

            [data-testid="stSidebar"] > div:first-child {
                padding-top: 2.45rem;
            }

            [data-testid="stSidebar"] [data-testid="stSidebarNav"] {
                padding-top: 0.45rem;
            }

            /* Streamlit reserves only one header row for st.logo. Make that
               header tall enough and target the actual sidebar logo image. */
            [data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
                height: 190px !important;
                justify-content: center !important;
                align-items: center !important;
                margin-bottom: 0.3rem !important;
            }

            [data-testid="stSidebar"] img[data-testid="stSidebarLogo"] {
                width: min(210px, calc(100% - 0.75rem)) !important;
                height: 175px !important;
                max-width: 100% !important;
                max-height: none !important;
                margin: 0 !important;
                object-fit: contain !important;
                object-position: center !important;
            }

            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] span,
            [data-testid="stSidebar"] label {
                color: var(--bac-muted);
            }

            [data-testid="stSidebarNav"] ul {
                gap: 0.15rem;
            }

            [data-testid="stSidebarNav"] a {
                min-height: 42px;
                border: 1px solid transparent;
                border-radius: 8px;
                color: var(--bac-muted);
                font-weight: 650;
                transform: translateX(0);
                transition: transform 180ms cubic-bezier(0.2, 0.85, 0.35, 1.2), color 150ms ease, background 150ms ease, border-color 150ms ease;
            }

            [data-testid="stSidebarNav"] a:hover {
                transform: translateX(4px);
                color: var(--bac-teal-dark);
                background: #eef7f4;
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                color: #0f5f63;
                border-color: #cbe2dd;
                background: #e8f5f1;
                box-shadow: inset 3px 0 0 var(--bac-green);
                animation: bacNavSelect 360ms cubic-bezier(0.2, 0.9, 0.35, 1.25);
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                anchor-name: --active-opera-link;
                padding-right: 2.5rem;
            }

            [data-testid="stSidebar"] div[class*="st-key-opera_actions_"] {
                position: fixed;
                position-anchor: --active-opera-link;
                top: anchor(top);
                right: anchor(right);
                z-index: 1001;
                width: 2rem;
                margin-top: 0.33rem;
                margin-right: 0.28rem;
                opacity: 0;
                transition: opacity 150ms ease, transform 150ms ease;
                transform: scale(0.92);
            }

            [data-testid="stSidebar"]:has([data-testid="stSidebarNav"] a[aria-current="page"]:hover) div[class*="st-key-opera_actions_"],
            [data-testid="stSidebar"] div[class*="st-key-opera_actions_"]:hover {
                opacity: 1;
                transform: scale(1);
            }

            [data-testid="stSidebar"] div[class*="st-key-opera_actions_"] button {
                min-height: 1.85rem;
                padding: 0.1rem 0.35rem;
                border-color: transparent;
                border-radius: 6px;
                background: transparent;
                box-shadow: none;
                font-size: 1.2rem;
                line-height: 1;
            }

            [data-testid="stSidebar"] div[class*="st-key-opera_actions_"] button:hover {
                background: #d7ebe5;
                color: var(--bac-teal-dark);
            }

            h1,
            h2,
            h3,
            h4,
            h5,
            h6 {
                color: var(--bac-heading);
                letter-spacing: 0;
            }

            h1 {
                font-size: clamp(1.8rem, 2.5vw, 2.45rem);
                line-height: 1.15;
            }

            h2,
            h3 {
                line-height: 1.25;
            }

            p,
            li,
            label,
            span {
                color: inherit;
            }

            a {
                color: var(--bac-blue);
            }

            hr {
                border-color: var(--bac-line);
                margin: 1.35rem 0;
            }

            [data-testid="stCaptionContainer"],
            .stCaptionContainer {
                color: var(--bac-muted);
            }

            div[data-testid="stVerticalBlockBorderWrapper"],
            div[data-testid="stExpander"],
            div[data-testid="stForm"],
            div[data-testid="stChatMessage"] {
                border-color: var(--bac-line) !important;
                border-radius: 8px !important;
                background: var(--bac-panel) !important;
                box-shadow: var(--bac-shadow-sm);
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:hover,
            div[data-testid="stExpander"]:hover {
                transform: translateY(-3px);
                border-color: var(--bac-line-strong) !important;
                box-shadow: 0 12px 25px rgba(27, 73, 72, 0.11);
            }

            div[data-testid="stVerticalBlockBorderWrapper"],
            div[data-testid="stExpander"] {
                transition: transform 210ms cubic-bezier(0.2, 0.85, 0.35, 1.15), border-color 180ms ease, box-shadow 180ms ease;
            }

            div[data-testid="stExpander"] details summary {
                min-height: 48px;
                border-radius: 8px;
                color: var(--bac-text);
                background: #fbfdfc;
            }

            div[data-testid="stExpander"] details summary:hover {
                background: #f1f7f5;
            }

            div[data-testid="stExpander"] details[open] summary {
                color: var(--bac-teal-dark);
                animation: bacTabPop 260ms cubic-bezier(0.2, 0.9, 0.35, 1.3);
            }

            .stButton > button,
            .stDownloadButton > button,
            .stFormSubmitButton > button,
            button[kind="primary"],
            button[data-testid="baseButton-primary"] {
                min-height: 42px;
                border: 1px solid var(--bac-teal);
                border-radius: 8px;
                color: #ffffff;
                background: var(--bac-teal);
                box-shadow: 0 4px 0 #0c5d61, 0 8px 18px rgba(19, 124, 128, 0.17);
                font-weight: 750;
                overflow: hidden;
                position: relative;
                transform: translateY(0);
                transition: transform 170ms cubic-bezier(0.2, 0.85, 0.35, 1.25), border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover,
            .stFormSubmitButton > button:hover,
            button[kind="primary"]:hover,
            button[data-testid="baseButton-primary"]:hover {
                transform: translateY(-2px);
                border-color: var(--bac-teal-dark);
                color: #ffffff;
                background: var(--bac-teal-dark);
                box-shadow: 0 6px 0 #0a5659, 0 12px 23px rgba(19, 124, 128, 0.22);
            }

            .stButton > button:active,
            .stDownloadButton > button:active,
            .stFormSubmitButton > button:active,
            button[kind="primary"]:active,
            button[data-testid="baseButton-primary"]:active {
                transform: translateY(3px) scale(0.99);
                box-shadow: 0 1px 0 #0a5659, 0 4px 10px rgba(19, 124, 128, 0.16);
                transition-duration: 70ms;
            }

            button[kind="primary"]::after,
            button[data-testid="baseButton-primary"]::after {
                content: "";
                position: absolute;
                inset: -35% auto -35% -45%;
                width: 28%;
                background: rgba(255, 255, 255, 0.2);
                transform: skewX(-18deg) translateX(0);
                transition: transform 430ms ease;
                pointer-events: none;
            }

            button[kind="primary"]:hover::after,
            button[data-testid="baseButton-primary"]:hover::after {
                transform: skewX(-18deg) translateX(570%);
            }

            button[kind="secondary"],
            button[data-testid="baseButton-secondary"] {
                min-height: 42px;
                border: 1px solid #cbdedb;
                border-radius: 8px;
                color: #31566a;
                background: #ffffff;
                box-shadow: 0 3px 0 #c3d8d4;
                font-weight: 750;
                transform: translateY(0);
                transition: transform 170ms cubic-bezier(0.2, 0.85, 0.35, 1.25), color 150ms ease, border-color 150ms ease, background 150ms ease, box-shadow 150ms ease;
            }

            button[kind="secondary"]:hover,
            button[data-testid="baseButton-secondary"]:hover {
                transform: translateY(-2px);
                color: var(--bac-blue);
                border-color: #9dbce8;
                background: #f3f7fd;
                box-shadow: 0 5px 0 #bfd0e6, 0 9px 18px rgba(39, 103, 199, 0.1);
            }

            button[kind="secondary"]:active,
            button[data-testid="baseButton-secondary"]:active {
                transform: translateY(2px) scale(0.99);
                box-shadow: 0 1px 0 #bfd0e6;
                transition-duration: 70ms;
            }

            button:focus-visible {
                outline: 3px solid rgba(39, 103, 199, 0.2) !important;
                outline-offset: 2px;
            }

            button:disabled,
            button[disabled] {
                transform: none !important;
                color: #96a8b3 !important;
                border-color: #dce6e4 !important;
                background: #edf2f1 !important;
                box-shadow: none !important;
            }

            .stTextInput input,
            .stTextArea textarea,
            .stNumberInput input,
            [data-baseweb="input"] input,
            [data-baseweb="textarea"] textarea {
                border: 1px solid #cbdedb;
                border-radius: 8px;
                color: var(--bac-text);
                background: #ffffff;
                caret-color: var(--bac-teal);
                transition: border-color 150ms ease, box-shadow 150ms ease, background 150ms ease;
            }

            .stTextInput input:focus,
            .stTextArea textarea:focus,
            .stNumberInput input:focus,
            [data-baseweb="input"] input:focus,
            [data-baseweb="textarea"] textarea:focus {
                border-color: #57999b;
                background: #ffffff;
                box-shadow: 0 0 0 3px rgba(19, 124, 128, 0.12);
                animation: bacFocusPop 220ms cubic-bezier(0.2, 0.9, 0.35, 1.2);
            }

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {
                color: #91a2ae;
            }

            [data-baseweb="select"] > div {
                border-color: #cbdedb;
                border-radius: 8px;
                color: var(--bac-text);
                background: #ffffff;
            }

            [data-baseweb="select"] > div:hover,
            [data-baseweb="select"] > div:focus-within {
                border-color: #57999b;
                background: #ffffff;
                box-shadow: 0 0 0 3px rgba(19, 124, 128, 0.12);
            }

            [data-baseweb="popover"],
            [data-baseweb="menu"],
            [role="listbox"] {
                color: var(--bac-text);
                background: #ffffff !important;
            }

            [data-baseweb="popover"] {
                border: 1px solid #b9d9d2;
                border-radius: 14px;
                box-shadow: 0 16px 36px rgba(20, 67, 75, 0.18);
                max-height: calc(100vh - 8rem);
                overflow-x: visible;
                overflow-y: auto;
            }

            [data-baseweb="popover"] > div {
                border-radius: 13px;
            }

            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) .block-container {
                padding-top: 0.38rem;
                padding-bottom: 0.45rem;
            }

            .opera-workspace-marker {
                display: none;
            }

            [data-testid="stElementContainer"][class*="st-key-progress_orb_"],
            [data-testid="stElementContainer"]:has(iframe[title="components.progress_ui.progress_orb"]) {
                position: fixed !important;
                left: calc(50vw - 43px);
                top: calc(50vh - 43px);
                bottom: auto;
                z-index: 2147483647;
                width: 86px !important;
                height: 86px !important;
                margin: 0 !important;
                overflow: visible !important;
            }

            [data-testid="stElementContainer"][class*="st-key-progress_orb_"] iframe[title="components.progress_ui.progress_orb"],
            [data-testid="stElementContainer"]:has(iframe[title="components.progress_ui.progress_orb"]) iframe[title="components.progress_ui.progress_orb"] {
                width: 86px !important;
                height: 86px !important;
                z-index: 2147483647 !important;
                border: 0 !important;
                background: transparent !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
            }

            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) [data-baseweb="tab-list"] {
                gap: 0.18rem;
                padding: 0.16rem;
                border-radius: 7px;
            }

            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) button[data-baseweb="tab"] {
                min-height: 34px;
                padding: 0.24rem 0.52rem;
                border-radius: 6px;
                font-size: 0.86rem;
            }

            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) div[class*="st-key-open_learning_"] button {
                min-height: 34px;
                padding: 0.2rem 0.5rem;
                font-size: 0.8rem;
            }

            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) h2 {
                margin-top: 0.45rem;
                margin-bottom: 0.35rem;
                font-size: 1.45rem;
            }

            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) h3,
            [data-testid="stAppViewContainer"]:has(.opera-workspace-marker) h4 {
                margin-top: 0.35rem;
                margin-bottom: 0.3rem;
            }

            [role="option"]:hover,
            [role="option"][aria-selected="true"] {
                background: #edf7f4 !important;
            }

            [data-baseweb="tab-list"] {
                gap: 0.35rem;
                padding: 0.3rem;
                border: 1px solid var(--bac-line);
                border-radius: 8px;
                background: #eaf1ef;
            }

            button[data-baseweb="tab"] {
                min-height: 42px;
                border-radius: 7px;
                color: var(--bac-muted);
                background: transparent;
                font-weight: 750;
                transform: translateY(0) scale(1);
                transition: transform 180ms cubic-bezier(0.2, 0.85, 0.35, 1.25), color 150ms ease, background 150ms ease, box-shadow 150ms ease;
            }

            button[data-baseweb="tab"]:hover {
                transform: translateY(-2px);
                color: var(--bac-teal-dark);
                background: rgba(255, 255, 255, 0.6);
            }

            button[data-baseweb="tab"][aria-selected="true"] {
                color: var(--bac-teal-dark);
                background: #ffffff;
                box-shadow: 0 3px 10px rgba(27, 73, 72, 0.09);
                animation: bacTabPop 280ms cubic-bezier(0.2, 0.9, 0.35, 1.3);
            }

            [data-baseweb="tab-highlight"] {
                background: transparent;
            }

            .stRadio [role="radiogroup"] {
                gap: 0.35rem;
            }

            .stRadio label,
            .stCheckbox label,
            .stToggle label {
                color: var(--bac-text);
            }

            [data-testid="stProgress"] > div {
                background: #dfeae7;
            }

            .stProgress > div > div > div {
                background: linear-gradient(105deg, var(--bac-green) 0%, #27a978 35%, var(--bac-blue) 65%, #4c83d3 100%);
                background-size: 220% 100%;
                animation: bacProgressFlow 2.8s linear infinite;
            }

            [data-testid="stMetric"] {
                min-height: 112px;
                padding: 0.9rem 1rem;
                border: 1px solid var(--bac-line);
                border-radius: 8px;
                background: #ffffff;
                box-shadow: var(--bac-shadow-sm);
                transform: translateY(0) scale(1);
                transition: transform 220ms cubic-bezier(0.2, 0.85, 0.35, 1.15), border-color 180ms ease, box-shadow 180ms ease;
                animation: bacCardIn 420ms cubic-bezier(0.18, 0.9, 0.3, 1.18) both;
            }

            [data-testid="stMetric"]:hover {
                transform: translateY(-4px) scale(1.015);
                border-color: #b8d7d0;
                box-shadow: 0 13px 26px rgba(27, 73, 72, 0.12);
            }

            [data-testid="stMetric"]:nth-of-type(2) {
                animation-delay: 45ms;
            }

            [data-testid="stMetric"]:nth-of-type(3) {
                animation-delay: 90ms;
            }

            [data-testid="stMetricLabel"] {
                color: var(--bac-muted);
            }

            [data-testid="stMetricValue"] {
                color: var(--bac-heading);
                font-size: 1.42rem;
                line-height: 1.2;
                font-weight: 800;
            }

            [data-testid="stMetricValue"] > div {
                overflow: visible;
                white-space: normal;
                text-overflow: clip;
                overflow-wrap: anywhere;
            }

            [data-testid="stAlert"] {
                border: 1px solid var(--bac-line);
                border-radius: 8px;
                color: var(--bac-text);
                background: #ffffff;
                box-shadow: var(--bac-shadow-sm);
                animation: bacAlertIn 380ms cubic-bezier(0.18, 0.9, 0.3, 1.18);
            }

            [data-testid="stNotificationContentInfo"] {
                background: var(--bac-blue-soft);
            }

            [data-testid="stNotificationContentSuccess"] {
                background: var(--bac-green-soft);
            }

            [data-testid="stNotificationContentWarning"] {
                background: var(--bac-warning-soft);
            }

            [data-testid="stNotificationContentError"] {
                background: var(--bac-danger-soft);
            }

            [data-testid="stChatMessage"] {
                padding: 0.9rem 1rem;
                box-shadow: none;
                animation: bacMessageIn 320ms cubic-bezier(0.18, 0.9, 0.3, 1.1) both;
            }

            [data-testid="stChatMessage"]:nth-child(even) {
                animation-delay: 55ms;
            }

            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
                border-color: #c9ded8 !important;
                background: #eef8f5 !important;
            }

            [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
                border-color: #d4e1f3 !important;
                background: #f2f7fd !important;
            }

            [data-testid="stChatInput"] {
                border-color: var(--bac-line);
                background: #ffffff;
            }

            .stMarkdown p {
                line-height: 1.65;
            }

            .app-header {
                position: relative;
                overflow: hidden;
                padding: 1.35rem 1.5rem 1.35rem 1.75rem;
                border: 1px solid var(--bac-line);
                border-radius: 8px;
                background: #ffffff;
                box-shadow: var(--bac-shadow);
                margin-bottom: 1.35rem;
                animation: bacHeaderIn 470ms cubic-bezier(0.18, 0.9, 0.3, 1.18) both;
            }

            .app-header::before {
                content: "";
                position: absolute;
                inset: 0 auto 0 0;
                width: 5px;
                background: linear-gradient(180deg, var(--bac-green), var(--bac-blue));
            }

            .app-header::after {
                content: "";
                position: absolute;
                width: 190px;
                height: 5px;
                right: 1.5rem;
                top: 0;
                background: linear-gradient(90deg, var(--bac-green), var(--bac-blue));
                transform-origin: right center;
                animation: bacHeaderLine 650ms 180ms cubic-bezier(0.2, 0.9, 0.3, 1.1) both;
            }

            .app-header-title {
                color: var(--bac-heading);
                font-size: clamp(1.55rem, 2.1vw, 2rem);
                line-height: 1.2;
                font-weight: 850;
                margin-bottom: 0.35rem;
            }

            .app-header-subtitle {
                max-width: 820px;
                color: var(--bac-muted);
                font-size: 0.98rem;
                line-height: 1.5;
            }

            .info-card {
                padding: 1.05rem 1.2rem;
                border: 1px solid var(--bac-line);
                border-radius: 8px;
                background: #ffffff;
                box-shadow: var(--bac-shadow-sm);
                margin-bottom: 1rem;
                transform: translateY(0);
                transition: transform 210ms cubic-bezier(0.2, 0.85, 0.35, 1.15), border-color 180ms ease, box-shadow 180ms ease;
                animation: bacCardIn 390ms cubic-bezier(0.18, 0.9, 0.3, 1.18) both;
            }

            .info-card:hover {
                transform: translateY(-4px);
                border-color: #b8d7d0;
                box-shadow: 0 13px 26px rgba(27, 73, 72, 0.12);
            }

            .info-card h3 {
                margin-top: 0;
                margin-bottom: 0.45rem;
            }

            .info-card p {
                margin-bottom: 0;
            }

            .small-muted {
                color: var(--bac-muted);
                font-size: 0.9rem;
            }

            .badge {
                display: inline-flex;
                align-items: center;
                min-height: 26px;
                padding: 0.2rem 0.55rem;
                border: 1px solid #cbdcf4;
                border-radius: 999px;
                color: #2b5b9e;
                background: var(--bac-blue-soft);
                font-size: 0.78rem;
                font-weight: 750;
                transition: transform 180ms cubic-bezier(0.2, 0.85, 0.35, 1.25), box-shadow 180ms ease;
            }

            .badge:hover {
                transform: translateY(-2px) scale(1.04);
                box-shadow: 0 5px 12px rgba(39, 103, 199, 0.12);
            }

            .badge-success {
                color: #116443;
                border-color: #bde0d0;
                background: var(--bac-green-soft);
            }

            .badge-warning {
                color: #89500f;
                border-color: #ecd7ad;
                background: var(--bac-warning-soft);
            }

            .badge-danger {
                color: #a12f3e;
                border-color: #e8c1c7;
                background: var(--bac-danger-soft);
            }

            .auth-brand {
                margin: 2vh 0 1.2rem;
                text-align: center;
            }

            .auth-brand-mark {
                display: inline-grid;
                place-items: center;
                width: 48px;
                height: 48px;
                margin-bottom: 0.7rem;
                border: 1px solid #bcdcd5;
                border-radius: 8px;
                color: #ffffff;
                background: var(--bac-teal);
                box-shadow: 0 8px 20px rgba(19, 124, 128, 0.2);
                font-size: 1.35rem;
                font-weight: 850;
                animation: bacMascotBounce 760ms 140ms cubic-bezier(0.18, 0.9, 0.3, 1.2) both;
            }

            .auth-brand h1 {
                margin: 0;
                font-size: 2rem;
            }

            .auth-brand p {
                margin: 0.45rem auto 0;
                color: var(--bac-muted);
                line-height: 1.55;
            }

            .stApp:has(.auth-brand) [data-testid="stSidebar"],
            .stApp:has(.auth-brand) [data-testid="collapsedControl"] {
                display: none !important;
            }

            @keyframes bacPageIn {
                from {
                    opacity: 0;
                    transform: translateY(8px);
                }

                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes bacCardIn {
                0% {
                    opacity: 0;
                    transform: translateY(10px) scale(0.975);
                }

                72% {
                    opacity: 1;
                    transform: translateY(-2px) scale(1.008);
                }

                100% {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            @keyframes bacHeaderIn {
                0% {
                    opacity: 0;
                    transform: translateY(-9px) scale(0.985);
                }

                70% {
                    opacity: 1;
                    transform: translateY(2px) scale(1.003);
                }

                100% {
                    opacity: 1;
                    transform: translateY(0) scale(1);
                }
            }

            @keyframes bacHeaderLine {
                from { transform: scaleX(0); }
                to { transform: scaleX(1); }
            }

            @keyframes bacTabPop {
                0% { transform: scale(0.96); }
                68% { transform: scale(1.035); }
                100% { transform: scale(1); }
            }

            @keyframes bacFocusPop {
                0% { box-shadow: 0 0 0 0 rgba(19, 124, 128, 0); }
                75% { box-shadow: 0 0 0 5px rgba(19, 124, 128, 0.15); }
                100% { box-shadow: 0 0 0 3px rgba(19, 124, 128, 0.12); }
            }

            @keyframes bacProgressFlow {
                from { background-position: 100% 0; }
                to { background-position: -120% 0; }
            }

            @keyframes bacAlertIn {
                0% { opacity: 0; transform: translateX(10px) scale(0.985); }
                72% { opacity: 1; transform: translateX(-2px) scale(1.005); }
                100% { opacity: 1; transform: translateX(0) scale(1); }
            }

            @keyframes bacMessageIn {
                from { opacity: 0; transform: translateY(7px) scale(0.985); }
                to { opacity: 1; transform: translateY(0) scale(1); }
            }

            @keyframes bacNavSelect {
                0% { transform: translateX(-5px) scale(0.98); }
                70% { transform: translateX(2px) scale(1.01); }
                100% { transform: translateX(0) scale(1); }
            }

            @keyframes bacMascotBounce {
                0% { opacity: 0; transform: translateY(-14px) rotate(-5deg) scale(0.86); }
                58% { opacity: 1; transform: translateY(4px) rotate(3deg) scale(1.08); }
                78% { transform: translateY(-2px) rotate(-1deg) scale(0.98); }
                100% { opacity: 1; transform: translateY(0) rotate(0) scale(1); }
            }

            main .block-container {
                animation: bacPageIn 300ms ease-out both;
            }

            [data-testid="stVerticalBlockBorderWrapper"] {
                animation: bacCardIn 360ms cubic-bezier(0.18, 0.9, 0.3, 1.15) both;
            }

            @media (prefers-reduced-motion: reduce) {
                *,
                *::before,
                *::after {
                    scroll-behavior: auto !important;
                    animation-duration: 0.01ms !important;
                    animation-delay: 0ms !important;
                    animation-iteration-count: 1 !important;
                    transition-duration: 0.01ms !important;
                }
            }

            @media (max-width: 900px) {
                [data-testid="stMetric"] {
                    min-height: 96px;
                }
            }

            @media (max-width: 640px) {
                .block-container {
                    padding-top: 1.1rem;
                    padding-left: 0.85rem;
                    padding-right: 0.85rem;
                }

                .app-header {
                    padding: 1.15rem 1rem 1.15rem 1.3rem;
                }

                [data-baseweb="tab-list"] {
                    overflow-x: auto;
                }

                button[data-baseweb="tab"] {
                    flex: 0 0 auto;
                    padding-left: 0.8rem;
                    padding-right: 0.8rem;
                }
            }
            .bac-progress-dock {
                position: fixed;
                left: 1rem;
                bottom: 1rem;
                z-index: 1000;
                width: 170px;
                padding: 0.62rem 0.72rem;
                border: 1px solid var(--bac-line-strong);
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.94);
                box-shadow: var(--bac-shadow-sm);
                backdrop-filter: blur(12px);
                animation: bacCardIn 420ms ease both;
            }

            .bac-progress-dock__top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                color: var(--bac-muted);
                font-size: 0.72rem;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
            }

            .bac-progress-dock__top strong { color: var(--bac-teal-dark); font-size: 0.82rem; }
            .bac-progress-dock__track { height: 5px; margin: 0.42rem 0 0.28rem; overflow: hidden; border-radius: 999px; background: #e4efec; }
            .bac-progress-dock__track span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--bac-green), var(--bac-blue)); transition: width 360ms ease; }
            .bac-progress-dock small { display: block; overflow: hidden; color: var(--bac-soft); font-size: 0.68rem; text-overflow: ellipsis; white-space: nowrap; }

            @media (max-width: 720px) {
                .bac-progress-dock { left: 0.6rem; bottom: 0.6rem; width: 145px; }
            }
            div[class*="st-key-open_learning_"] button {
                min-height: 2.45rem;
                padding: 0.42rem 0.65rem;
                border-radius: 8px;
                font-size: 0.84rem;
                font-weight: 700;
                white-space: nowrap;
            }

            div[class*="st-key-open_learning_"] button[kind="secondary"] {
                border-color: transparent;
                background: transparent;
                box-shadow: none;
                color: var(--bac-muted);
            }

            div[class*="st-key-open_learning_"] button[kind="secondary"]:hover {
                border-color: var(--bac-line);
                background: var(--bac-panel-soft);
                color: var(--bac-teal-dark);
            }

            /* Compact workspace used by the quick-test tab. */
            .quick-test-marker {
                height: 0;
                margin: -0.25rem 0 0;
            }

            .quick-test-section-title {
                margin: 0 0 0.08rem;
                color: var(--bac-teal-dark);
                font-size: 0.82rem;
                font-weight: 850;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }

            .quick-test-section-caption {
                margin-bottom: 0.38rem;
                color: var(--bac-muted);
                font-size: 0.7rem;
                line-height: 1.25;
            }

            div[class*="st-key-quick_"],
            div[class*="st-key-more_flashcards_"],
            div[class*="st-key-more_exercises_"] {
                font-size: 0.76rem;
            }

            div[class*="st-key-quick_"] button,
            div[class*="st-key-more_flashcards_"] button,
            div[class*="st-key-more_exercises_"] button {
                min-height: 30px;
                padding: 0.2rem 0.38rem;
                border-radius: 6px;
                font-size: 0.72rem;
                line-height: 1.15;
                box-shadow: 0 2px 0 rgba(12, 93, 97, 0.45);
            }

            div[class*="st-key-quick_card_"] label,
            div[class*="st-key-quick_answer_"] label,
            div[class*="st-key-quick_test_answer_"] label {
                min-height: 19px;
                font-size: 0.72rem;
                line-height: 1.18;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-quick_card_"]) {
                padding: 0.35rem 0.48rem;
                border-radius: 6px !important;
                box-shadow: none !important;
            }

            div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-quick_card_"]) p {
                margin: 0 0 0.22rem;
                font-size: 0.73rem;
                line-height: 1.25;
            }

            div[class*="st-key-quick_"] [data-baseweb="select"] > div,
            div[class*="st-key-quick_"] [data-baseweb="input"] input {
                min-height: 30px;
                font-size: 0.72rem;
            }

            div[class*="st-key-quick_"] [data-testid="stWidgetLabel"] p {
                margin-bottom: 0.12rem;
                font-size: 0.72rem;
                line-height: 1.2;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(title: str, subtitle: str, icon: str = "📚") -> None:
    st.markdown(
        f"""
        <div class="app-header">
            <div class="app-header-title">{icon} {title}</div>
            <div class="app-header-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_card(title: str, text: str, icon: str = "ℹ️") -> None:
    st.markdown(
        f"""
        <div class="info-card">
            <h3>{icon} {title}</h3>
            <p>{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_badge(text: str, status: str = "default") -> None:
    css_class = "badge"

    if status == "success":
        css_class += " badge-success"
    elif status == "warning":
        css_class += " badge-warning"
    elif status == "danger":
        css_class += " badge-danger"

    st.markdown(
        f'<span class="{css_class}">{text}</span>',
        unsafe_allow_html=True,
    )


def render_locked_message(score: int, required_score: int = 70) -> None:
    st.warning(
        f"Eseul este blocat momentan. Ai nevoie de minimum {required_score}/100 pentru deblocare."
    )

    st.write(f"Scor actual: **{score}/100**")
    st.progress(score / 100)

    remaining = max(required_score - score, 0)

    if remaining > 0:
        st.info(f"Mai ai nevoie de **{remaining} puncte** pentru a debloca eseul.")


def render_empty_state(title: str, message: str, icon: str = "📝") -> None:
    st.markdown(
        f"""
        <div class="info-card">
            <h3>{icon} {title}</h3>
            <p class="small-muted">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
