"""Public API for the compliance NLP POC."""

from .config import (
    load_generic_detection_rules,
    load_whitelist_terms,
    refresh_spacy_synonyms_from_forbidden_words,
)
from .notebook import findings_to_records, results_to_dataframe, summarize_results
from .pipeline import analyze_directory, analyze_file, load_results, save_results

__all__ = [
    "analyze_directory",
    "analyze_file",
    "findings_to_records",
    "load_generic_detection_rules",
    "load_results",
    "load_whitelist_terms",
    "refresh_spacy_synonyms_from_forbidden_words",
    "results_to_dataframe",
    "save_results",
    "summarize_results",
]
