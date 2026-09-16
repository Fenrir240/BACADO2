"""Rulează Experimentul 3 reutilizând infrastructura stabilă din Experimentul 1."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = EXPERIMENT_DIR.parent
BASE_RUNNER_PATH = RESEARCH_DIR / "experiment1" / "run_openrouter_experiment.py"

# Runnerul de bază importă `prepare_inputs`; asigurăm că primește varianta Experimentului 2.
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))


def _load_base_runner() -> Any:
    spec = importlib.util.spec_from_file_location("experiment3_base_runner", BASE_RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca runnerul {BASE_RUNNER_PATH}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


base = _load_base_runner()
base.EXPERIMENT_NAME = "Experimentul 3"
base.DEFAULT_SUMMARY_REASONING_EFFORT = "high"
base.EXPERIMENT_DIR = EXPERIMENT_DIR
base.RESEARCH_DIR = RESEARCH_DIR
base.GRAPH_PATH = RESEARCH_DIR / "graf1" / "knowledge-graph.json"
base.QUESTION_PROMPT_PATH = EXPERIMENT_DIR / "prompts" / "prompt-generare-intrebari.md"
base.SUMMARY_PROMPT_PATH = EXPERIMENT_DIR / "prompts" / "prompt-rezumat-capitolul-1.md"
base.EVALUATOR_PATH = EXPERIMENT_DIR / "evaluator.py"
base.QUESTION_MANIFEST_PATH = EXPERIMENT_DIR / "inputs" / "question-manifest.json"
base.QUESTION_BLUEPRINTS_PATH = EXPERIMENT_DIR / "inputs" / "question-blueprints.json"
base.SUMMARY_MANIFEST_PATH = EXPERIMENT_DIR / "inputs" / "summary-manifest.json"
base.DEFAULT_CONFIG_PATH = EXPERIMENT_DIR / "config.local.env"

semantic_config_path = EXPERIMENT_DIR / "inputs" / "semantic-similarity.json"
reference_profile_path = EXPERIMENT_DIR / "inputs" / "reference-style-profile.json"
base.EXTRA_METADATA = {
    "semantic_similarity_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "semantic_similarity_config_sha256": _sha256(semantic_config_path),
    "summary_manifest_sha256": _sha256(base.SUMMARY_MANIFEST_PATH),
    "reference_style_profile_sha256": _sha256(reference_profile_path),
    "base_runner_sha256": _sha256(BASE_RUNNER_PATH),
}


def semantic_preflight() -> None:
    spec = importlib.util.spec_from_file_location(
        "experiment3_runtime_evaluator", base.EVALUATOR_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca evaluatorul {base.EVALUATOR_PATH}.")
    evaluator_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = evaluator_module
    spec.loader.exec_module(evaluator_module)
    config = json.loads(semantic_config_path.read_text(encoding="utf-8"))
    backend = evaluator_module._default_backend(config)
    score = backend.similarity_matrix(
        ["verificare semantică locală", "verificare semantică locală"]
    )[0][1]
    if float(score) < 0.999:
        raise RuntimeError(
            f"Preflight MiniLM nereușit: textul identic are similaritatea {score}."
        )
    base.load_evaluator = lambda: evaluator_module
    print(f"Model semantic local verificat: {backend.model_id}")


base.PREFLIGHT_HOOK = semantic_preflight
# Registrul Excel este întreținut exclusiv manual. Runnerul actualizează doar CSV-ul.
base.RESULTS_WORKBOOK_SYNC_HOOK = None


_base_generate_run_report = base.generate_run_report


def generate_run_report(
    run_dir: Path,
    metadata: dict[str, Any],
    scores: dict[str, Any],
    runs: dict[str, dict[str, Any]],
) -> Path:
    report_path = _base_generate_run_report(run_dir, metadata, scores, runs)
    question_semantics = (scores.get("question_generation") or {}).get(
        "semantic_duplication", {}
    )
    summary_registers = (scores.get("chapter_1_summary") or {}).get("registers", {})
    additions = [
        "",
        "## Verificările specifice Experimentului 3",
        "",
        "### Similaritatea semantică a întrebărilor",
        "",
        f"- Model local: `{question_semantics.get('model_id', 'indisponibil')}`",
        f"- Prag duplicat: `{question_semantics.get('duplicate_threshold', '—')}`",
        f"- Prag revizuire manuală: `{question_semantics.get('review_threshold', '—')}`",
        "",
        "### Profilul stilistic al rezumatelor",
        "",
        "| Registru | Conformitate | Conectori | Expresii de umplutură | Nume personaje | Penalizare |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for register_name in ("simple", "elevated"):
        value = summary_registers.get(register_name, {})
        profile = value.get("style_profile") or {}
        evaluation = value.get("style_evaluation") or {}
        penalty = -float((value.get("breakdown") or {}).get("style_profile_penalty", 0.0))
        additions.append(
            "| "
            + " | ".join(
                (
                    register_name,
                    f"{100 * float(evaluation.get('compliance', 0.0)):.1f}%",
                    f"{100 * float(profile.get('discourse_connector_ratio', 0.0)):.2f}%",
                    f"{100 * float(profile.get('filler_word_ratio', 0.0)):.2f}%",
                    f"{100 * float(profile.get('character_name_token_ratio', 0.0)):.2f}%",
                    f"{penalty:.3f}",
                )
            )
            + " |"
        )
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "\n".join(additions) + "\n",
        encoding="utf-8",
    )
    return report_path


base.generate_run_report = generate_run_report


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(base.main())
