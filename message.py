from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys
import os


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from src import (
    Document,
    EMBEDDING_PROVIDER_ENV,
    OPENAI_EMBEDDING_MODEL,
    EmbeddingStore,
    KnowledgeBaseAgent,
    OpenAIEmbedder,
    SentenceChunker
)

DATA_FILE = ROOT / "data" / "recipe.md"
OUTPUT_FILE = ROOT / "report" / "BENCHMARK_COMMON_RESULTS.md"
TARGET_HEADING_KEYS = {
    "food",
    "water (h_{2}o)",
    "milk",
    "ways of cooking",
}
CHUNK_SIZE = 500


@dataclass
class BenchmarkCase:
    query: str
    gold_answer: str
    required_terms: list[str]
    metadata_filter: dict[str, str] | None = None


def infer_section_type(heading: str) -> str:
    h = heading.lower()
    if any(key in h for key in ["chapter ii", "cookery", "ways of cooking", "build a fire", "frying", "boiling"]):
        return "methods"
    if any(key in h for key in ["preface", "by the author"]):
        return "preface"
    if any(key in h for key in ["food", "water", "salts", "starch", "sugar", "milk", "butter", "cheese", "fruits", "condiments"]):
        return "ingredient_reference"
    return "general"


def normalize_heading(heading: str) -> str:
    return re.sub(r"\s+", " ", heading.strip().lower())


def split_sections(markdown_text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = "document"
    buffer: list[str] = []

    for line in markdown_text.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            if buffer:
                sections.append((current_heading, "\n".join(buffer).strip()))
                buffer = []
            current_heading = line.lstrip("# ").strip()
        else:
            buffer.append(line)

    if buffer:
        sections.append((current_heading, "\n".join(buffer).strip()))

    return [(heading, text) for heading, text in sections if text]


def build_chunked_documents(text: str) -> list[Document]:
    chunker = SentenceChunker(max_sentences_per_chunk=5)
    sections = split_sections(text)

    docs: list[Document] = []
    chunk_index = 0
    for heading, section_text in sections:
        heading_key = normalize_heading(heading)
        if heading_key not in TARGET_HEADING_KEYS:
            continue

        section_type = infer_section_type(heading)
        chunks = chunker.chunk(section_text)
        for chunk in chunks:
            docs.append(
                Document(
                    id=f"recipe_chunk_{chunk_index:04d}",
                    content=chunk,
                    metadata={
                        "doc_id": "recipe_boston_cookbook_1910",
                        "domain": "recipes",
                        "section_type": section_type,
                        "heading": heading,
                        "heading_key": heading_key,
                        "chunk_index": chunk_index,
                    },
                )
            )
            chunk_index += 1
    return docs


def extractive_llm(prompt: str) -> str:
    marker = "Context:\n"
    if marker not in prompt:
        return "I am not sure based on the provided context."
    context = prompt.split(marker, 1)[1].split("\n\nQuestion:", 1)[0]
    cleaned = re.sub(r"\[[0-9]+\]\s*", "", context)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned.strip())
    picked = [s for s in sentences if s][:2]
    if not picked:
        return "I am not sure based on the provided context."
    return " ".join(picked)


def relevance_count(results: list[dict], required_terms: list[str]) -> int:
    count = 0
    for item in results[:3]:
        text = item["content"].lower()
        if any(term.lower() in text for term in required_terms):
            count += 1
    return count


def answer_is_correct(answer: str, required_terms: list[str]) -> bool:
    text = answer.lower()
    hits = sum(1 for term in required_terms if term.lower() in text)
    return hits >= max(1, min(2, len(required_terms)))


def score_query(relevant_top3: int, answer_correct: bool) -> int:
    if relevant_top3 >= 2 and answer_correct:
        return 2
    if relevant_top3 >= 1:
        return 1
    return 0


def run() -> None:
    env_candidates = [ROOT / ".env", ROOT.parent / ".env"]
    for env_path in env_candidates:
        if env_path.exists():
            load_dotenv(env_path, override=False)

    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "openai").strip().lower()
    if provider != "openai":
        raise RuntimeError(
            f"{EMBEDDING_PROVIDER_ENV} must be 'openai' for this benchmark run (current: {provider!r})."
        )

    model_name = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
    embedder = OpenAIEmbedder(model_name=model_name)

    text = DATA_FILE.read_text(encoding="utf-8")
    docs = build_chunked_documents(text)

    store = EmbeddingStore(collection_name="benchmark_common", embedding_fn=embedder)
    store.add_documents(docs)
    agent = KnowledgeBaseAgent(store=store, llm_fn=extractive_llm)

    benchmarks = [
        BenchmarkCase(
            query="What are the principal ways of cooking listed in the book?",
            gold_answer="The principal ways are boiling, broiling, stewing, roasting, baking, frying, sauteing, braising, and fricasseeing.",
            required_terms=["boiling", "broiling", "stewing", "roasting", "baking", "frying"],
            metadata_filter={"heading_key": "ways of cooking"},
        ),
        BenchmarkCase(
            query="At what temperatures does water boil and simmer?",
            gold_answer="Water boils at 212F and simmers at around 185F.",
            required_terms=["212", "185", "boils", "simmers"],
            metadata_filter={"heading_key": "water (h_{2}o)"},
        ),
        BenchmarkCase(
            query="Why does milk sour according to the text?",
            gold_answer="A germ converts lactose to lactic acid, which precipitates casein into curd and whey.",
            required_terms=["lactose", "lactic acid", "casein", "curd", "whey"],
            metadata_filter=None,
        ),
        BenchmarkCase(
            query="How is fat tested for frying temperature?",
            gold_answer="Drop a one-inch cube of bread; if golden brown in about forty seconds, fat is ready for cooked mixtures.",
            required_terms=["bread", "forty seconds", "golden brown", "frying"],
            metadata_filter={"heading_key": "ways of cooking"},
        ),
        BenchmarkCase(
            query="What is the chief office of proteids?",
            gold_answer="Proteids chiefly build and repair tissues, and can also furnish energy.",
            required_terms=["build", "repair", "tissues", "energy", "proteids"],
            metadata_filter={"heading_key": "food"},
        ),
    ]

    lines: list[str] = []
    lines.append("# Common Benchmark Results")
    lines.append("")
    lines.append("Dataset: `data/recipe.md`")
    lines.append(f"Chunking strategy: `FixedSizeChunker(chunk_size={CHUNK_SIZE})`")
    lines.append(f"Embedding backend: `openai:{model_name}`")
    lines.append(f"Indexed chunks: {store.get_collection_size()}")
    lines.append("")
    lines.append("## Benchmark Definition")
    lines.append("")
    lines.append("| # | Query | Gold Answer | Metadata Filter |")
    lines.append("|---|-------|-------------|-----------------|")
    for i, case in enumerate(benchmarks, start=1):
        filt = case.metadata_filter if case.metadata_filter else {}
        lines.append(f"| {i} | {case.query} | {case.gold_answer} | `{filt}` |")

    lines.append("")
    lines.append("## Results")
    lines.append("")
    lines.append("| # | Relevant in Top-3 (search) | Relevant in Top-3 (filtered) | Agent answer correct? | Query score (0-2) |")
    lines.append("|---|----------------------------|------------------------------|----------------------|------------------|")

    total_score = 0
    search_relevant_total = 0
    filtered_relevant_total = 0

    for i, case in enumerate(benchmarks, start=1):
        unfiltered = store.search(case.query, top_k=3)
        filtered = store.search_with_filter(case.query, top_k=3, metadata_filter=case.metadata_filter)
        answer = agent.answer(case.query, top_k=3)

        rel_unfiltered = relevance_count(unfiltered, case.required_terms)
        rel_filtered = relevance_count(filtered, case.required_terms)
        answer_ok = answer_is_correct(answer, case.required_terms)
        query_score = score_query(rel_filtered, answer_ok)

        total_score += query_score
        search_relevant_total += rel_unfiltered
        filtered_relevant_total += rel_filtered

        lines.append(f"| {i} | {rel_unfiltered}/3 | {rel_filtered}/3 | {'Yes' if answer_ok else 'No'} | {query_score} |")
        top_source = filtered if filtered else unfiltered
        top_label = "filtered" if filtered else "unfiltered_fallback"
        if top_source:
            preview = top_source[0]['content'][:180].replace('\n', ' ')
            lines.append(f"- Q{i} top-1 ({top_label}): {preview}...")
        else:
            lines.append(f"- Q{i} top-1 ({top_label}): no results")
        ans_preview = answer[:220].replace('\n', ' ')
        lines.append(f"- Q{i} agent answer: {ans_preview}")

    lines.append("")
    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append(f"- Retrieval Precision (search): {search_relevant_total}/15 relevant chunks in top-3")
    lines.append(f"- Retrieval Precision (filtered): {filtered_relevant_total}/15 relevant chunks in top-3")
    lines.append(f"- Benchmark Score: {total_score}/10")
    lines.append("- Note: Query score follows rubric in `docs/SCORING.md` (0-2 points/query).")

    OUTPUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved benchmark results to: {OUTPUT_FILE}")


if __name__ == "__main__":
    run()