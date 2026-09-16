"""The first, visual step of the essay builder."""

from pathlib import Path

import streamlit.components.v1 as components


ESSAY_MINDMAP_ASSET_VERSION = "v3"


ESSAY_MINDMAP_COMPONENT = components.declare_component(
    f"essay_mindmap_{ESSAY_MINDMAP_ASSET_VERSION}",
    path=str(Path(__file__).parent / "essay_mindmap_component"),
)


def render_essay_structure_intro(
    selected_section: str | None = None,
    *,
    fullscreen: bool = False,
    work: dict | None = None,
    composition_elements: list[dict] | None = None,
    essay_blueprint: dict | None = None,
) -> dict | None:
    """Show the map and return the section selected in the browser."""
    return ESSAY_MINDMAP_COMPONENT(
        selected_section=selected_section or "",
        fullscreen=fullscreen,
        work_title=str((work or {}).get("title") or "Opera"),
        work_author=str((work or {}).get("author") or ""),
        composition_elements=composition_elements or [],
        essay_blueprint=essay_blueprint or {},
        key=(
            f"{str((work or {}).get('id') or 'work')}_essay_mindmap_{ESSAY_MINDMAP_ASSET_VERSION}_fullscreen"
            if fullscreen
            else f"{str((work or {}).get('id') or 'work')}_essay_mindmap_{ESSAY_MINDMAP_ASSET_VERSION}"
        ),
        default=None,
    )


def _build_essay_structure_html() -> str:
    return """
    <!doctype html>
    <html lang="ro">
    <head>
      <meta charset="utf-8">
      <style>
        :root {
          --ink: #203242;
          --muted: #627788;
          --line: #9ebbc7;
          --root: #236d79;
          --root-dark: #195761;
          --card: #ffffff;
          --selected: #e9f5f1;
        }

        * { box-sizing: border-box; }
        html, body { margin: 0; overflow: hidden; background: transparent; }
        body { font-family: "Aptos", "Segoe UI", sans-serif; }

        .map {
          position: relative;
          height: 238px;
          min-height: 238px;
          overflow: hidden;
          border: 1px solid #dce8eb;
          border-radius: 22px;
          background:
            radial-gradient(circle at 50% 50%, rgba(220, 239, 238, 0.95), transparent 34%),
            linear-gradient(135deg, #fcfefe, #f3f8f8);
          isolation: isolate;
        }

        .map::before {
          position: absolute;
          inset: 0;
          z-index: -1;
          background-image: radial-gradient(#c4d8dc 0.75px, transparent 0.75px);
          background-size: 18px 18px;
          content: "";
          opacity: 0.4;
        }

        .eyebrow {
          position: absolute;
          top: 11px;
          left: 15px;
          z-index: 4;
          color: var(--muted);
          font-size: 0.62rem;
          font-weight: 750;
          letter-spacing: 0.1em;
          text-transform: uppercase;
        }

        .connectors {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          pointer-events: none;
        }
        .connector {
          fill: none;
          stroke: var(--line);
          stroke-linecap: round;
          stroke-width: 1.7;
          opacity: 0;
          stroke-dasharray: 280;
          stroke-dashoffset: 280;
          transition: opacity 220ms ease, stroke-dashoffset 560ms ease;
        }

        button.node {
          position: absolute;
          display: flex;
          align-items: center;
          gap: 9px;
          min-height: 29px;
          padding: 6px 9px;
          border: 1px solid #d6e3e6;
          border-radius: 10px;
          background: var(--card);
          box-shadow: 0 8px 18px rgba(38, 75, 89, 0.09);
          color: var(--ink);
          cursor: pointer;
          font: 650 0.68rem/1.15 "Aptos", "Segoe UI", sans-serif;
          text-align: left;
          transition: transform 200ms ease, opacity 280ms ease, border-color 180ms ease,
            background 180ms ease, box-shadow 180ms ease;
        }
        button.node:hover,
        button.node:focus-visible {
          border-color: #78a8ad;
          box-shadow: 0 10px 24px rgba(29, 95, 104, 0.16);
          outline: none;
          transform: translateY(-2px);
        }
        button.node:focus-visible { box-shadow: 0 0 0 3px rgba(35, 109, 121, 0.22); }
        button.node::after {
          display: grid;
          width: 14px;
          height: 14px;
          border-radius: 50%;
          background: #e9f4f3;
          color: var(--root);
          content: "›";
          font-size: 0.82rem;
          font-weight: 800;
          line-height: 1;
          place-items: center;
        }

        .root {
          top: 50%;
          left: 50%;
          z-index: 3;
          min-height: 48px !important;
          padding: 11px 14px !important;
          border: 0 !important;
          border-radius: 13px !important;
          background: linear-gradient(135deg, var(--root), #318a91) !important;
          box-shadow: 0 16px 34px rgba(24, 87, 96, 0.27) !important;
          color: white !important;
          font-size: 0.84rem !important;
          transform: translate(-50%, -50%) scale(1.08);
          transition: left 740ms cubic-bezier(0.18, 0.9, 0.3, 1.08),
            top 740ms cubic-bezier(0.18, 0.9, 0.3, 1.08),
            transform 740ms cubic-bezier(0.18, 0.9, 0.3, 1.08), box-shadow 180ms ease;
        }
        .root::after { background: rgba(255, 255, 255, 0.18) !important; color: white !important; content: "+" !important; }
        .root[aria-expanded="true"]::after { content: "−" !important; }

        .map.intro-playing .root { animation: root-arrival 730ms cubic-bezier(0.18, 0.9, 0.25, 1.22); }

        .branch {
          left: 27%;
          z-index: 2;
          min-width: 160px;
          opacity: 0;
          pointer-events: none;
          transform: translateX(-18px) scale(0.96);
        }
        .branch-1 { top: 28px; }
        .branch-2 { top: 65px; }
        .branch-3 { top: 102px; }
        .branch-4 { top: 139px; }
        .branch-5 { top: 176px; }
        .branch.selected {
          border-color: #65a597;
          background: var(--selected);
          box-shadow: 0 10px 24px rgba(28, 105, 91, 0.16);
        }

        .map.compact .root {
          top: 112px;
          left: 3%;
          transform: translate(0, -50%) scale(0.58);
        }
        .map.open .connector { opacity: 1; stroke-dashoffset: 0; }
        .map.open .branch { opacity: 1; pointer-events: auto; transform: translateX(0) scale(1); animation: branch-pop 520ms cubic-bezier(0.18, 0.9, 0.25, 1.18) both; }
        .map.open .branch-1 { transition-delay: 70ms; animation-delay: 65ms; }
        .map.open .branch-2 { transition-delay: 125ms; animation-delay: 120ms; }
        .map.open .branch-3 { transition-delay: 180ms; animation-delay: 175ms; }
        .map.open .branch-4 { transition-delay: 235ms; animation-delay: 230ms; }
        .map.open .branch-5 { transition-delay: 290ms; animation-delay: 285ms; }
        .map.compact:not(.open) .connector { opacity: 0; stroke-dashoffset: 280; }
        .map.compact:not(.open) .branch { opacity: 0; pointer-events: none; transform: translateX(-18px) scale(0.96); }

        @media (max-width: 610px) {
          .eyebrow { left: 14px; }
          .map.compact .root { top: 112px; left: 10px; transform: translate(0, -50%) scale(0.54); }
          .branch { left: 37%; min-width: min(160px, 59vw); font-size: 0.66rem !important; }
        }

        @keyframes root-arrival {
          0% { opacity: 0; transform: translate(-50%, -50%) scale(0.38) rotate(-5deg); }
          66% { opacity: 1; transform: translate(-50%, -50%) scale(1.23) rotate(1deg); }
          100% { opacity: 1; transform: translate(-50%, -50%) scale(1.08) rotate(0); }
        }

        @keyframes branch-pop {
          0% { opacity: 0; transform: translateX(-38px) scale(0.72); }
          68% { opacity: 1; transform: translateX(5px) scale(1.04); }
          100% { opacity: 1; transform: translateX(0) scale(1); }
        }

        @media (prefers-reduced-motion: reduce) {
          *, *::before, *::after { transition-duration: 0.01ms !important; }
        }
      </style>
    </head>
    <body>
      <main class="map" id="essay-map" aria-label="Schema interactivă a eseului pentru romanul Ion">
        <div class="eyebrow">Schema eseului</div>
        <svg class="connectors" viewBox="0 0 1000 238" preserveAspectRatio="none" aria-hidden="true">
          <path class="connector" d="M 130 112 C 190 112, 196 43, 270 43" />
          <path class="connector" d="M 130 112 C 190 112, 196 80, 270 80" />
          <path class="connector" d="M 130 112 C 190 112, 196 117, 270 117" />
          <path class="connector" d="M 130 112 C 190 112, 196 154, 270 154" />
          <path class="connector" d="M 130 112 C 190 112, 196 191, 270 191" />
        </svg>

        <button class="node root" id="work-root" type="button" aria-expanded="false">Ion — Liviu Rebreanu</button>
        <button class="node branch branch-1" type="button" data-node="Introducere">Introducere</button>
        <button class="node branch branch-2" type="button" data-node="Trăsături de curent">Trăsături de curent</button>
        <button class="node branch branch-3" type="button" data-node="Tema">Tema</button>
        <button class="node branch branch-4" type="button" data-node="Secvențe relevante">Secvențe relevante</button>
        <button class="node branch branch-5" type="button" data-node="Elemente de compoziție">Elemente de compoziție</button>

      </main>
      <script>
        const map = document.getElementById("essay-map");
        const root = document.getElementById("work-root");
        const branches = [...document.querySelectorAll(".branch")];
        let animationStarted = false;

        function setOpen(open) {
          map.classList.toggle("open", open);
          root.setAttribute("aria-expanded", String(open));
        }

        function startIntro() {
          if (animationStarted) return;
          animationStarted = true;
          map.classList.add("intro-playing");
          window.setTimeout(() => {
            map.classList.add("compact");
            setOpen(true);
          }, 980);
        }

        root.addEventListener("click", () => setOpen(!map.classList.contains("open")));
        branches.forEach((branch) => {
          branch.addEventListener("click", () => {
            branches.forEach((item) => item.classList.toggle("selected", item === branch));
          });
        });

        const observer = new IntersectionObserver((entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            startIntro();
            observer.disconnect();
          }
        }, { threshold: 0.35 });
        observer.observe(map);
      </script>
    </body>
    </html>
    """
