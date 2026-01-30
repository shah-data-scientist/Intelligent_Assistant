"""Centralized clarification question templates.

This module provides a SINGLE SOURCE OF TRUTH for clarification questions
used when queries are too broad.

STRICT 3-CRITERIA SYSTEM:
Every search requires: City + Event Type + Date/Timeframe
If any criterion is missing, we ask for clarification.
"""

from typing import Dict, List, Optional, Tuple

# ========================================
# CLARIFICATION QUESTIONS BY REASON
# ========================================
# Key: reason string from UnifiedAnalyzer (missing_criteria list joined with "+")
# Format: "missing_<criterion1>+<criterion2>+..."
# Value: dict with 'fr' and 'en' question templates

CLARIFICATION_QUESTIONS: Dict[str, Dict[str, Dict[str, any]]] = {
    # ========================================
    # SINGLE MISSING CRITERION
    # ========================================
    "missing_city": {
        "fr": {
            "prefix": "Super ! Pour trouver les meilleurs evenements :\n",
            "questions": [
                "Dans quelle zone cherches-tu ? (Paris, Versailles, Montreuil, ou toute l'Ile-de-France...)"
            ]
        },
        "en": {
            "prefix": "Great! To find the best events:\n",
            "questions": [
                "Which area are you looking in? (Paris, Versailles, Montreuil, or all of Ile-de-France...)"
            ]
        }
    },
    "missing_event_type": {
        "fr": {
            "prefix": "Parfait ! Pour affiner ta recherche :\n",
            "questions": [
                "Quel type d'evenement t'interesse ? (Concert, expo, theatre, festival, atelier...)"
            ]
        },
        "en": {
            "prefix": "Perfect! To refine your search:\n",
            "questions": [
                "What type of event interests you? (Concert, exhibition, theater, festival, workshop...)"
            ]
        }
    },
    "missing_date": {
        "fr": {
            "prefix": "Genial ! Pour te proposer des evenements pertinents :\n",
            "questions": [
                "Pour quelle periode cherches-tu ? (Ce week-end, en fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "Excellent! To suggest relevant events:\n",
            "questions": [
                "What timeframe are you looking at? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },
    # ALIAS: UnifiedAnalyzer outputs "timeframe" not "date"
    "missing_timeframe": {
        "fr": {
            "prefix": "Genial ! Pour te proposer des evenements pertinents :\n",
            "questions": [
                "Pour quelle periode cherches-tu ? (Ce week-end, en fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "Excellent! To suggest relevant events:\n",
            "questions": [
                "What timeframe are you looking at? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },

    # ========================================
    # TWO MISSING CRITERIA
    # ========================================
    "missing_city+event_type": {
        "fr": {
            "prefix": "Pour t'aider, j'ai besoin de quelques precisions :\n",
            "questions": [
                "Dans quelle zone ? (Paris, Versailles, ou toute l'Ile-de-France...)",
                "Quel type d'evenement ? (Concert, expo, theatre...)"
            ]
        },
        "en": {
            "prefix": "To help you, I need a few details:\n",
            "questions": [
                "Which area? (Paris, Versailles, or all of Ile-de-France...)",
                "What type of event? (Concert, exhibition, theater...)"
            ]
        }
    },
    "missing_city+date": {
        "fr": {
            "prefix": "Pour affiner ta recherche :\n",
            "questions": [
                "Dans quelle zone ? (Paris, Versailles, ou toute l'Ile-de-France...)",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "To narrow down your search:\n",
            "questions": [
                "Which area? (Paris, Versailles, or all of Ile-de-France...)",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },
    # ALIAS: UnifiedAnalyzer outputs "timeframe" not "date"
    "missing_city+timeframe": {
        "fr": {
            "prefix": "Pour affiner ta recherche :\n",
            "questions": [
                "Dans quelle zone ? (Paris, Versailles, ou toute l'Ile-de-France...)",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "To narrow down your search:\n",
            "questions": [
                "Which area? (Paris, Versailles, or all of Ile-de-France...)",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },
    "missing_event_type+date": {
        "fr": {
            "prefix": "Pour te proposer les meilleurs evenements :\n",
            "questions": [
                "Quel type d'evenement t'interesse ?",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "To suggest the best events:\n",
            "questions": [
                "What type of event interests you?",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },
    # ALIAS: UnifiedAnalyzer outputs "timeframe" not "date"
    "missing_event_type+timeframe": {
        "fr": {
            "prefix": "Pour te proposer les meilleurs evenements :\n",
            "questions": [
                "Quel type d'evenement t'interesse ?",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "To suggest the best events:\n",
            "questions": [
                "What type of event interests you?",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },

    # ========================================
    # ALL THREE MISSING (very vague query)
    # ========================================
    "missing_city+event_type+date": {
        "fr": {
            "prefix": "Je serais ravi de t'aider ! Pour trouver des evenements parfaits, dis-moi :\n",
            "questions": [
                "Dans quelle zone ? (Paris, Versailles, ou toute l'Ile-de-France...)",
                "Quel type d'evenement ? (Concert, expo, theatre...)",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "I'd love to help! To find perfect events, tell me:\n",
            "questions": [
                "Which area? (Paris, Versailles, or all of Ile-de-France...)",
                "What type of event? (Concert, exhibition, theater...)",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },
    # ALIAS: UnifiedAnalyzer outputs "timeframe" not "date"
    "missing_city+event_type+timeframe": {
        "fr": {
            "prefix": "Je serais ravi de t'aider ! Pour trouver des evenements parfaits, dis-moi :\n",
            "questions": [
                "Dans quelle zone ? (Paris, Versailles, ou toute l'Ile-de-France...)",
                "Quel type d'evenement ? (Concert, expo, theatre...)",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "I'd love to help! To find perfect events, tell me:\n",
            "questions": [
                "Which area? (Paris, Versailles, or all of Ile-de-France...)",
                "What type of event? (Concert, exhibition, theater...)",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },
    # ALIAS: different order variant
    "missing_city+timeframe+event_type": {
        "fr": {
            "prefix": "Je serais ravi de t'aider ! Pour trouver des evenements parfaits, dis-moi :\n",
            "questions": [
                "Dans quelle zone ? (Paris, Versailles, ou toute l'Ile-de-France...)",
                "Quel type d'evenement ? (Concert, expo, theatre...)",
                "Pour quelle periode ? (Ce week-end, fevrier, le 15/02/2026, l'annee prochaine...)"
            ]
        },
        "en": {
            "prefix": "I'd love to help! To find perfect events, tell me:\n",
            "questions": [
                "Which area? (Paris, Versailles, or all of Ile-de-France...)",
                "What type of event? (Concert, exhibition, theater...)",
                "What timeframe? (This weekend, February, 15/02/2026, next year...)"
            ]
        }
    },

    "city_only": {
        "fr": {
            "prefix": "Super choix de ville ! Pour mieux t'aider :\n",
            "questions": [
                "Quel type d'evenement t'interesse ?",
                "Pour quelle periode cherches-tu ?"
            ]
        },
        "en": {
            "prefix": "Great city choice! To help you better:\n",
            "questions": [
                "What type of event interests you?",
                "What timeframe are you looking at?"
            ]
        }
    },
    "event_type_only": {
        "fr": {
            "prefix": "Genial ! Pour affiner ta recherche :\n",
            "questions": [
                "Dans quelle ville cherches-tu ?",
                "Pour quelle periode ?"
            ]
        },
        "en": {
            "prefix": "Great! To narrow down your search:\n",
            "questions": [
                "Which city are you looking in?",
                "What timeframe?"
            ]
        }
    },
    "date_only": {
        "fr": {
            "prefix": "Parfait pour la periode ! Pour t'aider :\n",
            "questions": [
                "Quel type d'evenement cherches-tu ?",
                "Dans quelle ville ?"
            ]
        },
        "en": {
            "prefix": "Perfect timing! To help you:\n",
            "questions": [
                "What type of event are you looking for?",
                "Which city?"
            ]
        }
    },

    # ========================================
    # SPECIAL CASES
    # ========================================
    "kids_no_age": {
        "fr": {
            "prefix": "Pour trouver des evenements adaptes :\n",
            "questions": [
                "Quel age ont tes enfants ? Ca m'aide a trouver des evenements adaptes !"
            ]
        },
        "en": {
            "prefix": "To find age-appropriate events:\n",
            "questions": [
                "How old are your children? It helps me find age-appropriate events!"
            ]
        }
    }
}


def get_clarification_response(reason: str, language: str = "en") -> Tuple[Optional[str], Optional[List[str]]]:
    """Get clarification prefix and questions for a given reason.

    Args:
        reason: The reason string from UnifiedAnalyzer (e.g., "missing_city+event_type")
        language: Language code ("fr" or "en")

    Returns:
        Tuple of (prefix, questions_list) or (None, None) if reason unknown
    """
    if reason not in CLARIFICATION_QUESTIONS:
        return None, None

    lang_data = CLARIFICATION_QUESTIONS[reason].get(language, CLARIFICATION_QUESTIONS[reason]["en"])
    return lang_data["prefix"], lang_data["questions"]
