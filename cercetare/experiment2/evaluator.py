"""Evaluatorul Experimentului 2.

Extinde evaluatorul structural din Experimentul 1 cu două verificări independente:

* similaritate semantică între întrebări, calculată local cu Sentence Transformers;
* conformitatea lexicală a rezumatelor cu profilul stilistic înghețat.

Modelul de embedding nu generează text și nu primește knowledge graph-ul. El este
încărcat numai la evaluarea întrebărilor și întoarce similarități cosinus.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from text_profile import analyze_text, evaluate_profile


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESEARCH_DIR = EXPERIMENT_DIR.parent
BASE_EVALUATOR_PATH = RESEARCH_DIR / "benchmark1" / "scoring" / "evaluator.py"
SEMANTIC_CONFIG_PATH = EXPERIMENT_DIR / "inputs" / "semantic-similarity.json"
SUMMARY_MANIFEST_PATH = EXPERIMENT_DIR / "inputs" / "summary-manifest.json"


def _load_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Nu pot încărca modulul {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


base = _load_module(BASE_EVALUATOR_PATH, "experiment2_base_evaluator")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


class SimilarityBackend(Protocol):
    model_id: str

    def similarity_matrix(self, texts: Sequence[str]) -> list[list[float]]: ...


class SentenceTransformerSimilarity:
    """Adaptor minimal peste modelul local Sentence Transformers."""

    def __init__(self, model_id: str, device: str | None = None) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Lipsește pachetul sentence-transformers. Rulează instalarea din "
                "experiment2/requirements.txt înaintea evaluării oficiale."
            ) from exc
        self.model_id = model_id
        kwargs = {"device": device} if device else {}
        self.model = SentenceTransformer(model_id, **kwargs)

    def similarity_matrix(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return (embeddings @ embeddings.T).tolist()


_MODEL_CACHE: dict[tuple[str, str | None], SentenceTransformerSimilarity] = {}


def _semantic_config() -> dict[str, Any]:
    return _read_json(SEMANTIC_CONFIG_PATH)


def _default_backend(config: Mapping[str, Any]) -> SentenceTransformerSimilarity:
    key = (str(config["model_id"]), config.get("device"))
    if key not in _MODEL_CACHE:
        _MODEL_CACHE[key] = SentenceTransformerSimilarity(*key)
    return _MODEL_CACHE[key]


def compare_meaning(
    sentence_a: str,
    sentence_b: str,
    backend: SimilarityBackend | None = None,
) -> dict[str, Any]:
    """Compară două propoziții și întoarce decizia plus scorul auditabil."""

    config = _semantic_config()
    active_backend = backend or _default_backend(config)
    score = float(active_backend.similarity_matrix([sentence_a, sentence_b])[0][1])
    duplicate_threshold = float(config["duplicate_threshold"])
    review_threshold = float(config["review_threshold"])
    decision = (
        "same_meaning"
        if score >= duplicate_threshold
        else "manual_review"
        if score >= review_threshold
        else "different_meaning"
    )
    return {
        "same_meaning": score >= duplicate_threshold,
        "decision": decision,
        "similarity": round(score, 6),
        "model_id": active_backend.model_id,
        "duplicate_threshold": duplicate_threshold,
        "review_threshold": review_threshold,
    }


def _extract_questions(question_output: Any) -> list[dict[str, Any]]:
    output, error = base._safe_load_json(question_output)
    if error or output is None:
        return []
    values = output.get("questions")
    if values is None and isinstance(output.get("model_response"), Mapping):
        values = output["model_response"].get("questions")
    return [dict(item) for item in base._as_list(values) if isinstance(item, Mapping)]


def score_question_generation(
    question_output: Any,
    graph: Any,
    manifest: Any | None = None,
    similarity_backend: SimilarityBackend | None = None,
) -> dict[str, Any]:
    result = base.score_question_generation(question_output, graph, manifest)
    questions = _extract_questions(question_output)
    scored = result.get("questions") or []
    if not questions or not scored:
        return result

    config = _semantic_config()
    backend = similarity_backend or _default_backend(config)
    texts = [str(question.get("question_text", "")) for question in questions]
    matrix = backend.similarity_matrix(texts)
    duplicate_threshold = float(config["duplicate_threshold"])
    review_threshold = float(config["review_threshold"])
    distinct_points = float(config.get("distinct_points", 5.0))
    review_points = float(config.get("review_points", 2.5))
    duplicate_points = float(config.get("duplicate_points", 0.0))

    pairs: list[dict[str, Any]] = []
    for left in range(len(questions)):
        for right in range(left + 1, len(questions)):
            similarity = float(matrix[left][right])
            if similarity >= review_threshold:
                pairs.append(
                    {
                        "left_question_id": questions[left].get("question_id"),
                        "right_question_id": questions[right].get("question_id"),
                        "similarity": round(similarity, 6),
                        "decision": (
                            "same_meaning"
                            if similarity >= duplicate_threshold
                            else "manual_review"
                        ),
                    }
                )

    for index, item in enumerate(scored):
        candidates = [
            (float(matrix[index][other]), other)
            for other in range(len(questions))
            if other != index
        ]
        maximum, nearest_index = max(candidates, default=(0.0, index))
        points = (
            duplicate_points
            if maximum >= duplicate_threshold
            else review_points
            if maximum >= review_threshold
            else distinct_points
        )
        previous = float((item.get("breakdown") or {}).get("non_duplication", 0.0))
        item.setdefault("breakdown", {})["non_duplication"] = round(points, 3)
        item["score"] = round(float(item.get("score", 0.0)) - previous + points, 3)
        item["duplicate_similarity"] = round(maximum, 6)
        item["nearest_question_id"] = questions[nearest_index].get("question_id")
        if points < distinct_points:
            item.setdefault("diagnostics", []).append(
                "MiniLM: similaritate semantică maximă "
                f"{maximum:.3f} cu întrebarea "
                f"{questions[nearest_index].get('question_id')!r}."
            )

    expected_count = int(result.get("expected_question_count") or len(base.REQUIRED_BLUEPRINTS))
    question_average = sum(float(item.get("score", 0.0)) for item in scored) / expected_count
    result["question_average"] = round(question_average, 3)
    result["score"] = round(
        0.90 * question_average + 0.10 * float(result.get("set_coverage_score", 0.0)),
        3,
    )
    try:
        package_version = importlib.metadata.version("sentence-transformers")
    except importlib.metadata.PackageNotFoundError:
        package_version = "backend-injectat-pentru-test"
    result["semantic_duplication"] = {
        "model_id": backend.model_id,
        "sentence_transformers_version": package_version,
        "duplicate_threshold": duplicate_threshold,
        "review_threshold": review_threshold,
        "threshold_status": config.get("threshold_status"),
        "pairs_at_or_above_review_threshold": pairs,
    }
    return result


def _style_manifest() -> dict[str, Any]:
    return _read_json(SUMMARY_MANIFEST_PATH)


def score_chapter_1_summary(summary_output: Any, graph: Any) -> dict[str, Any]:
    result = base.score_chapter_1_summary(summary_output, graph)
    output, error = base._safe_load_json(summary_output)
    if error or output is None or not result.get("registers"):
        return result

    manifest = _style_manifest()
    constraints = manifest.get("style_constraints", {})
    max_penalty = float(manifest.get("style_evaluation", {}).get("max_penalty_per_register", 10.0))
    summaries = output.get("summaries", {}) if isinstance(output.get("summaries"), Mapping) else {}

    for register_name in ("simple", "elevated"):
        register_result = result["registers"].get(register_name, {})
        summary = summaries.get(register_name)
        if not isinstance(summary, Mapping):
            continue
        profile = analyze_text(str(summary.get("summary_text", "")), graph)
        evaluation = evaluate_profile(profile, constraints)
        penalty = max_penalty * (1.0 - float(evaluation["compliance"]))
        original_score = float(register_result.get("score", 0.0))
        register_result["pre_style_score"] = round(original_score, 3)
        register_result["style_profile"] = profile
        register_result["style_evaluation"] = evaluation
        register_result.setdefault("breakdown", {})["style_profile_penalty"] = round(-penalty, 3)
        register_result["score"] = round(max(0.0, original_score - penalty), 3)
        failed = [name for name, rule in evaluation["rules"].items() if not rule["passed"]]
        if failed:
            register_result.setdefault("diagnostics", []).append(
                "Profil stilistic în afara marjei: " + ", ".join(failed) + "."
            )

    raw_average = sum(
        float(result["registers"][name].get("score", 0.0))
        for name in ("simple", "elevated")
    ) / 2.0
    consistency_penalty = float(result.get("cross_register_penalty", 0.0))
    result["raw_register_average"] = round(raw_average, 3)
    result["score"] = round(max(0.0, min(100.0, raw_average - consistency_penalty)), 3)
    result["style_profile_id"] = manifest.get("style_profile_id")
    result["style_penalty_policy"] = {
        "max_penalty_per_register": max_penalty,
        "calculation": "max_penalty * (1 - weighted_profile_compliance)",
    }
    return result


def score_agent_submission(
    question_output: Any,
    summary_output: Any,
    graph: Any,
    manifest: Any | None = None,
    question_weight: float = 0.5,
    summary_weight: float = 0.5,
) -> dict[str, Any]:
    if question_weight < 0 or summary_weight < 0 or math.isclose(
        question_weight + summary_weight, 0.0
    ):
        raise ValueError("Ponderile trebuie să fie nenegative și să aibă suma pozitivă.")
    total = question_weight + summary_weight
    question_result = score_question_generation(question_output, graph, manifest)
    summary_result = score_chapter_1_summary(summary_output, graph)
    question_fraction = question_weight / total
    summary_fraction = summary_weight / total
    return {
        "overall_score": round(
            question_fraction * float(question_result.get("score", 0.0))
            + summary_fraction * float(summary_result.get("score", 0.0)),
            3,
        ),
        "weights": {
            "question_generation": round(question_fraction, 3),
            "chapter_1_summary": round(summary_fraction, 3),
        },
        "question_generation": question_result,
        "chapter_1_summary": summary_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluator pentru Experimentul 2.")
    parser.add_argument("--graph", type=Path)
    parser.add_argument("--questions", type=Path)
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, metavar=("TEXT_A", "TEXT_B"))
    args = parser.parse_args()

    if args.compare:
        print(json.dumps(compare_meaning(*args.compare), ensure_ascii=False, indent=2))
        return 0
    if not args.graph:
        parser.error("--graph este obligatoriu în modul de evaluare.")
    if not args.questions and not args.summary:
        parser.error("Furnizează --questions și/sau --summary.")

    if args.questions and args.summary:
        value = score_agent_submission(
            args.questions, args.summary, args.graph, args.manifest
        )
    elif args.questions:
        value = score_question_generation(args.questions, args.graph, args.manifest)
    else:
        value = score_chapter_1_summary(args.summary, args.graph)
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
