"""Migration script to create and populate the search_keywords table.

This table provides a database-backed lookup for:
1. Date keywords (months, days, relative dates) with typo tolerance
2. Event descriptors (genres, styles, activities) that imply categories

Usage:
    python scripts/migrate_search_keywords.py
"""

import sqlite3
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/events.db"


def create_table(conn: sqlite3.Connection):
    """Create the search_keywords table."""
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS search_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            keyword_type TEXT NOT NULL,
            language TEXT DEFAULT 'both',
            canonical TEXT,
            implied_category TEXT,
            typos TEXT,
            priority INTEGER DEFAULT 1,
            UNIQUE(keyword, keyword_type, language)
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_type ON search_keywords(keyword_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON search_keywords(keyword)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_keywords_canonical ON search_keywords(canonical)")

    conn.commit()
    logger.info("Created search_keywords table with indexes")


def populate_date_keywords(conn: sqlite3.Connection):
    """Populate date-related keywords."""
    cursor = conn.cursor()

    # ========================================
    # MONTHS - French and English
    # ========================================
    months = [
        # English months
        {"keyword": "january", "language": "en", "canonical": "january", "typos": ["janury", "januray", "jan"]},
        {"keyword": "february", "language": "en", "canonical": "february", "typos": ["febuary", "febrary", "feb"]},
        {"keyword": "march", "language": "en", "canonical": "march", "typos": ["marh", "mar"]},
        {"keyword": "april", "language": "en", "canonical": "april", "typos": ["apirl", "apr"]},
        {"keyword": "may", "language": "en", "canonical": "may", "typos": []},
        {"keyword": "june", "language": "en", "canonical": "june", "typos": ["jun"]},
        {"keyword": "july", "language": "en", "canonical": "july", "typos": ["jully", "jul"]},
        {"keyword": "august", "language": "en", "canonical": "august", "typos": ["augst", "aug"]},
        {"keyword": "september", "language": "en", "canonical": "september", "typos": ["septmber", "sept", "sep"]},
        {"keyword": "october", "language": "en", "canonical": "october", "typos": ["octber", "oct"]},
        {"keyword": "november", "language": "en", "canonical": "november", "typos": ["novmber", "nov"]},
        {"keyword": "december", "language": "en", "canonical": "december", "typos": ["decmber", "dec"]},

        # French months
        {"keyword": "janvier", "language": "fr", "canonical": "january", "typos": ["janv", "janiver"]},
        {"keyword": "février", "language": "fr", "canonical": "february", "typos": ["fevrier", "fev", "fevr"]},
        {"keyword": "mars", "language": "fr", "canonical": "march", "typos": []},
        {"keyword": "avril", "language": "fr", "canonical": "april", "typos": ["avrl"]},
        {"keyword": "mai", "language": "fr", "canonical": "may", "typos": []},
        {"keyword": "juin", "language": "fr", "canonical": "june", "typos": []},
        {"keyword": "juillet", "language": "fr", "canonical": "july", "typos": ["juil", "juilet"]},
        {"keyword": "août", "language": "fr", "canonical": "august", "typos": ["aout", "aou"]},
        {"keyword": "septembre", "language": "fr", "canonical": "september", "typos": ["sept", "septmbre"]},
        {"keyword": "octobre", "language": "fr", "canonical": "october", "typos": ["oct", "octbre"]},
        {"keyword": "novembre", "language": "fr", "canonical": "november", "typos": ["nov", "novmbre"]},
        {"keyword": "décembre", "language": "fr", "canonical": "december", "typos": ["decembre", "dec", "decmbre"]},
    ]

    # ========================================
    # DAYS OF WEEK - French and English
    # ========================================
    days = [
        # English days
        {"keyword": "monday", "language": "en", "canonical": "monday", "typos": ["munday", "mondy"]},
        {"keyword": "tuesday", "language": "en", "canonical": "tuesday", "typos": ["tusday", "tueday"]},
        {"keyword": "wednesday", "language": "en", "canonical": "wednesday", "typos": ["wensday", "wednsday"]},
        {"keyword": "thursday", "language": "en", "canonical": "thursday", "typos": ["thurday", "thrusday"]},
        {"keyword": "friday", "language": "en", "canonical": "friday", "typos": ["firday", "frday"]},
        {"keyword": "saturday", "language": "en", "canonical": "saturday", "typos": ["saterday", "satruday"]},
        {"keyword": "sunday", "language": "en", "canonical": "sunday", "typos": ["sundy", "suday"]},

        # French days
        {"keyword": "lundi", "language": "fr", "canonical": "monday", "typos": ["lundis"]},
        {"keyword": "mardi", "language": "fr", "canonical": "tuesday", "typos": ["mardis"]},
        {"keyword": "mercredi", "language": "fr", "canonical": "wednesday", "typos": ["mercredis", "mercrdi"]},
        {"keyword": "jeudi", "language": "fr", "canonical": "thursday", "typos": ["jeudis"]},
        {"keyword": "vendredi", "language": "fr", "canonical": "friday", "typos": ["vendredis", "vendrdi"]},
        {"keyword": "samedi", "language": "fr", "canonical": "saturday", "typos": ["samedis", "samdi"]},
        {"keyword": "dimanche", "language": "fr", "canonical": "sunday", "typos": ["dimanches", "dimnche"]},
    ]

    # ========================================
    # RELATIVE DATES - French and English
    # ========================================
    relative_dates = [
        # English relative dates
        {"keyword": "today", "language": "en", "canonical": "today", "typos": ["tody", "toady"]},
        {"keyword": "tomorrow", "language": "en", "canonical": "tomorrow", "typos": ["tomorow", "tommorow", "tommorrow"]},
        {"keyword": "yesterday", "language": "en", "canonical": "yesterday", "typos": ["yesteday", "yesturday"]},
        {"keyword": "tonight", "language": "en", "canonical": "tonight", "typos": ["tonite", "tongiht"]},
        {"keyword": "weekend", "language": "en", "canonical": "weekend", "typos": ["wekend", "weeknd", "week end"]},
        {"keyword": "this weekend", "language": "en", "canonical": "this_weekend", "typos": ["this wekend", "this weeknd"]},
        {"keyword": "next weekend", "language": "en", "canonical": "next_weekend", "typos": ["next wekend"]},
        {"keyword": "this week", "language": "en", "canonical": "this_week", "typos": ["this wek"]},
        {"keyword": "next week", "language": "en", "canonical": "next_week", "typos": ["next wek"]},
        {"keyword": "this month", "language": "en", "canonical": "this_month", "typos": ["this mounth"]},
        {"keyword": "next month", "language": "en", "canonical": "next_month", "typos": ["next mounth"]},
        {"keyword": "morning", "language": "en", "canonical": "morning", "typos": ["moring", "morining"]},
        {"keyword": "afternoon", "language": "en", "canonical": "afternoon", "typos": ["afternon", "afternnon"]},
        {"keyword": "evening", "language": "en", "canonical": "evening", "typos": ["evning", "evenig"]},
        {"keyword": "night", "language": "en", "canonical": "night", "typos": ["nite", "nigth"]},

        # French relative dates
        {"keyword": "aujourd'hui", "language": "fr", "canonical": "today", "typos": ["aujourdhui", "aujourdui", "aujoud'hui"]},
        {"keyword": "demain", "language": "fr", "canonical": "tomorrow", "typos": ["deman", "dmain"]},
        {"keyword": "hier", "language": "fr", "canonical": "yesterday", "typos": []},
        {"keyword": "ce soir", "language": "fr", "canonical": "tonight", "typos": ["cesoir"]},
        {"keyword": "week-end", "language": "fr", "canonical": "weekend", "typos": ["weekend", "week end", "wk-end"]},
        {"keyword": "ce week-end", "language": "fr", "canonical": "this_weekend", "typos": ["ce weekend", "ce wk-end"]},
        {"keyword": "prochain week-end", "language": "fr", "canonical": "next_weekend", "typos": ["prochain weekend"]},
        {"keyword": "cette semaine", "language": "fr", "canonical": "this_week", "typos": ["cet semaine"]},
        {"keyword": "semaine prochaine", "language": "fr", "canonical": "next_week", "typos": ["semain prochaine"]},
        {"keyword": "ce mois", "language": "fr", "canonical": "this_month", "typos": ["ce moi"]},
        {"keyword": "mois prochain", "language": "fr", "canonical": "next_month", "typos": ["moi prochain"]},
        {"keyword": "matin", "language": "fr", "canonical": "morning", "typos": ["mattin"]},
        {"keyword": "après-midi", "language": "fr", "canonical": "afternoon", "typos": ["apres-midi", "apres midi", "apresmidi"]},
        {"keyword": "soir", "language": "fr", "canonical": "evening", "typos": []},
        {"keyword": "nuit", "language": "fr", "canonical": "night", "typos": []},

        # Time indicators (both languages)
        {"keyword": "soon", "language": "en", "canonical": "soon", "typos": ["soo"]},
        {"keyword": "bientôt", "language": "fr", "canonical": "soon", "typos": ["bientot", "biento"]},
        {"keyword": "upcoming", "language": "en", "canonical": "upcoming", "typos": ["upcomming"]},
        {"keyword": "prochain", "language": "fr", "canonical": "next", "typos": ["prochaine", "prochian"]},
        {"keyword": "prochaine", "language": "fr", "canonical": "next", "typos": ["prochian"]},
    ]

    # ========================================
    # DATE FORMAT PATTERNS (for regex detection)
    # ========================================
    date_patterns = [
        # These are regex patterns stored for reference
        {"keyword": "DD/MM/YYYY", "language": "both", "canonical": "date_format", "typos": []},
        {"keyword": "DD-MM-YYYY", "language": "both", "canonical": "date_format", "typos": []},
        {"keyword": "YYYY-MM-DD", "language": "both", "canonical": "date_format", "typos": []},
        {"keyword": "DD month", "language": "both", "canonical": "date_format", "typos": []},
        {"keyword": "month DD", "language": "both", "canonical": "date_format", "typos": []},
    ]

    # Insert all date keywords
    all_dates = months + days + relative_dates + date_patterns

    for item in all_dates:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO search_keywords
                (keyword, keyword_type, language, canonical, implied_category, typos, priority)
                VALUES (?, 'date', ?, ?, NULL, ?, 1)
            """, (
                item["keyword"].lower(),
                item["language"],
                item["canonical"],
                json.dumps(item["typos"])
            ))
        except Exception as e:
            logger.warning(f"Failed to insert date keyword '{item['keyword']}': {e}")

    conn.commit()
    logger.info(f"Inserted {len(all_dates)} date keywords")


def populate_event_descriptors(conn: sqlite3.Connection):
    """Populate event type descriptors that imply categories."""
    cursor = conn.cursor()

    # ========================================
    # MUSIQUE (Music) - Genres, styles, instruments
    # ========================================
    music_descriptors = [
        # Genres
        {"keyword": "jazz", "typos": ["jaz", "jass", "jazzy"]},
        {"keyword": "rock", "typos": ["rok", "roc"]},
        {"keyword": "pop", "typos": []},
        {"keyword": "classical", "language": "en", "typos": ["classicle", "clasical"]},
        {"keyword": "classique", "language": "fr", "typos": ["clasique", "classiq"]},
        {"keyword": "hip-hop", "typos": ["hiphop", "hip hop", "hipop"]},
        {"keyword": "rap", "typos": []},
        {"keyword": "electro", "typos": ["électro", "elektro"]},
        {"keyword": "electronic", "language": "en", "typos": ["electronik"]},
        {"keyword": "électronique", "language": "fr", "typos": ["electronique"]},
        {"keyword": "techno", "typos": ["tekno"]},
        {"keyword": "house", "typos": []},
        {"keyword": "metal", "typos": ["métal", "metall"]},
        {"keyword": "punk", "typos": []},
        {"keyword": "reggae", "typos": ["regae", "réggae"]},
        {"keyword": "blues", "typos": ["blus"]},
        {"keyword": "soul", "typos": []},
        {"keyword": "funk", "typos": ["fonk"]},
        {"keyword": "r&b", "typos": ["rnb", "r and b"]},
        {"keyword": "country", "typos": []},
        {"keyword": "folk", "typos": ["folklorique"]},
        {"keyword": "world music", "language": "en", "typos": ["world muzic"]},
        {"keyword": "musique du monde", "language": "fr", "typos": []},
        {"keyword": "chanson française", "language": "fr", "typos": ["chanson francaise"]},
        {"keyword": "french song", "language": "en", "typos": []},
        {"keyword": "variété", "language": "fr", "typos": ["variete", "varieté"]},
        {"keyword": "gospel", "typos": []},
        {"keyword": "choral", "typos": ["chorale"]},
        {"keyword": "chorale", "language": "fr", "typos": ["choral"]},
        {"keyword": "choir", "language": "en", "typos": ["chor", "quire"]},
        {"keyword": "acapella", "typos": ["a capella", "a cappella"]},
        {"keyword": "acoustic", "language": "en", "typos": ["accoustic", "acoustik"]},
        {"keyword": "acoustique", "language": "fr", "typos": ["accoustique"]},
        {"keyword": "live music", "language": "en", "typos": ["live muzic"]},
        {"keyword": "musique live", "language": "fr", "typos": []},
        {"keyword": "orchestra", "language": "en", "typos": ["orchstra", "orkestra"]},
        {"keyword": "orchestre", "language": "fr", "typos": ["orchèstre"]},
        {"keyword": "symphony", "language": "en", "typos": ["symphoni", "simphony"]},
        {"keyword": "symphonie", "language": "fr", "typos": ["symphonnie"]},
        {"keyword": "chamber music", "language": "en", "typos": []},
        {"keyword": "musique de chambre", "language": "fr", "typos": []},
        {"keyword": "opera", "typos": ["opéra"]},
        {"keyword": "opéra", "language": "fr", "typos": ["opera"]},
        {"keyword": "operetta", "language": "en", "typos": []},
        {"keyword": "opérette", "language": "fr", "typos": ["operette"]},
        {"keyword": "recital", "typos": ["récital"]},
        {"keyword": "récital", "language": "fr", "typos": ["recital"]},

        # Instruments/performers
        {"keyword": "piano", "typos": ["pano"]},
        {"keyword": "guitar", "language": "en", "typos": ["guiter", "gitar"]},
        {"keyword": "guitare", "language": "fr", "typos": ["guitar", "guitarre"]},
        {"keyword": "violin", "language": "en", "typos": ["violen", "violon"]},
        {"keyword": "violon", "language": "fr", "typos": ["violin"]},
        {"keyword": "cello", "language": "en", "typos": ["chello"]},
        {"keyword": "violoncelle", "language": "fr", "typos": []},
        {"keyword": "drums", "language": "en", "typos": ["drumms"]},
        {"keyword": "batterie", "language": "fr", "typos": ["baterie"]},
        {"keyword": "saxophone", "typos": ["saxo", "sax"]},
        {"keyword": "trumpet", "language": "en", "typos": ["trumpett"]},
        {"keyword": "trompette", "language": "fr", "typos": ["trumpet"]},
        {"keyword": "flute", "typos": ["flûte"]},
        {"keyword": "flûte", "language": "fr", "typos": ["flute"]},
        {"keyword": "harp", "language": "en", "typos": []},
        {"keyword": "harpe", "language": "fr", "typos": []},
        {"keyword": "dj", "typos": ["deejay", "disc jockey"]},
        {"keyword": "band", "language": "en", "typos": ["bnad"]},
        {"keyword": "groupe", "language": "fr", "typos": []},
        {"keyword": "singer", "language": "en", "typos": ["singr"]},
        {"keyword": "chanteur", "language": "fr", "typos": ["chanteure"]},
        {"keyword": "chanteuse", "language": "fr", "typos": []},
        {"keyword": "musician", "language": "en", "typos": ["musicien"]},
        {"keyword": "musicien", "language": "fr", "typos": ["musician"]},
    ]

    # ========================================
    # ART / EXPOSITION - Visual arts
    # ========================================
    art_descriptors = [
        # Art forms
        {"keyword": "painting", "language": "en", "typos": ["panting", "paintng"]},
        {"keyword": "peinture", "language": "fr", "typos": ["painture", "penture"]},
        {"keyword": "sculpture", "typos": ["sculture", "sculptur"]},
        {"keyword": "photography", "language": "en", "typos": ["photgraphy", "photogaphy"]},
        {"keyword": "photographie", "language": "fr", "typos": ["photgraphie"]},
        {"keyword": "photo", "typos": ["foto"]},
        {"keyword": "drawing", "language": "en", "typos": ["drwing", "drawng"]},
        {"keyword": "dessin", "language": "fr", "typos": ["desin"]},
        {"keyword": "illustration", "typos": ["ilustration"]},
        {"keyword": "print", "language": "en", "typos": []},
        {"keyword": "gravure", "language": "fr", "typos": ["gravur"]},
        {"keyword": "engraving", "language": "en", "typos": ["engrving"]},
        {"keyword": "watercolor", "language": "en", "typos": ["watercolour", "water color"]},
        {"keyword": "aquarelle", "language": "fr", "typos": ["aquarel"]},
        {"keyword": "oil painting", "language": "en", "typos": []},
        {"keyword": "peinture à l'huile", "language": "fr", "typos": ["peinture a l'huile"]},
        {"keyword": "abstract", "language": "en", "typos": ["abstact"]},
        {"keyword": "abstrait", "language": "fr", "typos": ["abstrai"]},
        {"keyword": "contemporary art", "language": "en", "typos": ["contempory art"]},
        {"keyword": "art contemporain", "language": "fr", "typos": ["art contemporan"]},
        {"keyword": "modern art", "language": "en", "typos": ["moden art"]},
        {"keyword": "art moderne", "language": "fr", "typos": []},
        {"keyword": "street art", "typos": ["streetart", "steet art"]},
        {"keyword": "graffiti", "typos": ["grafiti", "graffitti"]},
        {"keyword": "installation", "typos": ["instalation"]},
        {"keyword": "video art", "language": "en", "typos": []},
        {"keyword": "art vidéo", "language": "fr", "typos": ["art video"]},
        {"keyword": "digital art", "language": "en", "typos": ["digitl art"]},
        {"keyword": "art numérique", "language": "fr", "typos": ["art numerique"]},
        {"keyword": "mixed media", "language": "en", "typos": []},
        {"keyword": "technique mixte", "language": "fr", "typos": []},
        {"keyword": "collage", "typos": ["colage"]},
        {"keyword": "ceramics", "language": "en", "typos": ["ceramiks"]},
        {"keyword": "céramique", "language": "fr", "typos": ["ceramique"]},
        {"keyword": "pottery", "language": "en", "typos": ["potery"]},
        {"keyword": "poterie", "language": "fr", "typos": []},
        {"keyword": "textile", "typos": ["textil"]},
        {"keyword": "tapestry", "language": "en", "typos": ["tapestri"]},
        {"keyword": "tapisserie", "language": "fr", "typos": []},
        {"keyword": "mosaic", "language": "en", "typos": ["mosiac"]},
        {"keyword": "mosaïque", "language": "fr", "typos": ["mosaique"]},
        {"keyword": "stained glass", "language": "en", "typos": []},
        {"keyword": "vitrail", "language": "fr", "typos": []},

        # Exhibition types
        {"keyword": "exhibition", "language": "en", "typos": ["exibition", "exhibtion"]},
        {"keyword": "exposition", "language": "fr", "typos": ["expostion", "expo"]},
        {"keyword": "expo", "typos": []},
        {"keyword": "gallery", "language": "en", "typos": ["galery", "gallerie"]},
        {"keyword": "galerie", "language": "fr", "typos": ["galery"]},
        {"keyword": "museum", "language": "en", "typos": ["musem", "musuem"]},
        {"keyword": "musée", "language": "fr", "typos": ["musee", "museum"]},
        {"keyword": "vernissage", "typos": ["vernisage"]},
        {"keyword": "opening", "language": "en", "typos": ["opning"]},
        {"keyword": "retrospective", "typos": ["retrospectiv"]},
        {"keyword": "rétrospective", "language": "fr", "typos": ["retrospective"]},
        {"keyword": "solo show", "language": "en", "typos": []},
        {"keyword": "exposition personnelle", "language": "fr", "typos": []},
        {"keyword": "group show", "language": "en", "typos": []},
        {"keyword": "exposition collective", "language": "fr", "typos": []},
    ]

    # ========================================
    # DANSE (Dance)
    # ========================================
    dance_descriptors = [
        {"keyword": "ballet", "typos": ["balet", "balley", "balllet"]},
        {"keyword": "contemporary dance", "language": "en", "typos": ["contempory dance"]},
        {"keyword": "danse contemporaine", "language": "fr", "typos": ["dance contemporaine"]},
        {"keyword": "modern dance", "language": "en", "typos": ["moden dance"]},
        {"keyword": "danse moderne", "language": "fr", "typos": []},
        {"keyword": "hip-hop dance", "language": "en", "typos": ["hiphop dance"]},
        {"keyword": "danse hip-hop", "language": "fr", "typos": ["danse hiphop"]},
        {"keyword": "breakdance", "typos": ["break dance", "break-dance"]},
        {"keyword": "flamenco", "typos": ["flamenko"]},
        {"keyword": "tango", "typos": []},
        {"keyword": "salsa", "typos": []},
        {"keyword": "waltz", "language": "en", "typos": ["walz"]},
        {"keyword": "valse", "language": "fr", "typos": []},
        {"keyword": "folk dance", "language": "en", "typos": []},
        {"keyword": "danse folklorique", "language": "fr", "typos": []},
        {"keyword": "ballroom", "language": "en", "typos": ["balroom"]},
        {"keyword": "danse de salon", "language": "fr", "typos": []},
        {"keyword": "choreography", "language": "en", "typos": ["choregraphy", "coreography"]},
        {"keyword": "chorégraphie", "language": "fr", "typos": ["choregraphie"]},
        {"keyword": "dancer", "language": "en", "typos": ["dancr"]},
        {"keyword": "danseur", "language": "fr", "typos": []},
        {"keyword": "danseuse", "language": "fr", "typos": []},
        {"keyword": "performance", "typos": ["performace"]},
    ]

    # ========================================
    # THEATRE / SPECTACLE
    # ========================================
    theatre_descriptors = [
        # Theatre forms
        {"keyword": "theater", "language": "en", "typos": ["theatre", "theather", "teater"]},
        {"keyword": "theatre", "language": "en", "typos": ["theater", "theather"]},
        {"keyword": "théâtre", "language": "fr", "typos": ["theatre", "theater", "teatre"]},
        {"keyword": "play", "language": "en", "typos": []},
        {"keyword": "pièce", "language": "fr", "typos": ["piece", "piéce"]},
        {"keyword": "drama", "language": "en", "typos": ["dramma"]},
        {"keyword": "drame", "language": "fr", "typos": []},
        {"keyword": "comedy", "language": "en", "typos": ["comedi", "commedy"]},
        {"keyword": "comédie", "language": "fr", "typos": ["comedie"]},
        {"keyword": "tragedy", "language": "en", "typos": ["tragedi"]},
        {"keyword": "tragédie", "language": "fr", "typos": ["tragedie"]},
        {"keyword": "musical", "typos": ["musicale", "musikal"]},
        {"keyword": "comédie musicale", "language": "fr", "typos": ["comedie musicale"]},
        {"keyword": "one-man show", "typos": ["one man show", "oneman show"]},
        {"keyword": "seul en scène", "language": "fr", "typos": ["seul en scene"]},
        {"keyword": "monologue", "typos": ["monolog"]},
        {"keyword": "improvisation", "typos": ["improv", "improvisation"]},
        {"keyword": "improv", "language": "en", "typos": []},
        {"keyword": "sketch", "typos": ["skech"]},
        {"keyword": "stand-up", "typos": ["standup", "stand up"]},
        {"keyword": "humor", "language": "en", "typos": ["humour"]},
        {"keyword": "humour", "language": "fr", "typos": ["humor"]},
        {"keyword": "burlesque", "typos": []},
        {"keyword": "cabaret", "typos": ["caberet"]},
        {"keyword": "vaudeville", "typos": []},
        {"keyword": "mime", "typos": []},
        {"keyword": "pantomime", "typos": ["pantomim"]},
        {"keyword": "puppetry", "language": "en", "typos": ["pupetry"]},
        {"keyword": "marionnette", "language": "fr", "typos": ["marionette", "marionettes"]},
        {"keyword": "puppet", "language": "en", "typos": ["pupper"]},

        # Circus/magic
        {"keyword": "circus", "language": "en", "typos": ["cirque", "circuss"]},
        {"keyword": "cirque", "language": "fr", "typos": ["circus"]},
        {"keyword": "acrobatics", "language": "en", "typos": ["acrobatic"]},
        {"keyword": "acrobatie", "language": "fr", "typos": []},
        {"keyword": "magic", "language": "en", "typos": ["majic", "magik"]},
        {"keyword": "magie", "language": "fr", "typos": ["magic"]},
        {"keyword": "magician", "language": "en", "typos": ["magicion"]},
        {"keyword": "magicien", "language": "fr", "typos": []},
        {"keyword": "illusion", "typos": ["ilusion"]},
        {"keyword": "clown", "typos": ["clow"]},
        {"keyword": "juggling", "language": "en", "typos": ["jugling"]},
        {"keyword": "jonglage", "language": "fr", "typos": []},
        {"keyword": "contortionist", "language": "en", "typos": []},
        {"keyword": "contorsionniste", "language": "fr", "typos": []},
        {"keyword": "trapeze", "typos": ["trapèze"]},
        {"keyword": "trapèze", "language": "fr", "typos": ["trapeze"]},

        # Show/performance
        {"keyword": "show", "language": "en", "typos": ["shw"]},
        {"keyword": "spectacle", "language": "fr", "typos": ["spectacl"]},
        {"keyword": "performance", "typos": ["performace"]},
        {"keyword": "act", "language": "en", "typos": []},
        {"keyword": "actor", "language": "en", "typos": ["acter"]},
        {"keyword": "acteur", "language": "fr", "typos": []},
        {"keyword": "actress", "language": "en", "typos": ["actres"]},
        {"keyword": "actrice", "language": "fr", "typos": []},
        {"keyword": "comedian", "language": "en", "typos": ["commedian"]},
        {"keyword": "comédien", "language": "fr", "typos": ["comedien"]},
        {"keyword": "comédienne", "language": "fr", "typos": ["comedienne"]},
    ]

    # ========================================
    # CINEMA / FILM
    # ========================================
    cinema_descriptors = [
        {"keyword": "cinema", "typos": ["cinéma"]},
        {"keyword": "cinéma", "language": "fr", "typos": ["cinema"]},
        {"keyword": "film", "typos": ["filme"]},
        {"keyword": "movie", "language": "en", "typos": ["moive", "movee"]},
        {"keyword": "screening", "language": "en", "typos": ["screeing"]},
        {"keyword": "projection", "language": "fr", "typos": ["projecton"]},
        {"keyword": "documentary", "language": "en", "typos": ["documentry"]},
        {"keyword": "documentaire", "language": "fr", "typos": ["documentair"]},
        {"keyword": "short film", "language": "en", "typos": ["shortfilm"]},
        {"keyword": "court-métrage", "language": "fr", "typos": ["court metrage"]},
        {"keyword": "feature film", "language": "en", "typos": []},
        {"keyword": "long-métrage", "language": "fr", "typos": ["long metrage"]},
        {"keyword": "animation", "typos": ["animaton"]},
        {"keyword": "animated", "language": "en", "typos": ["animted"]},
        {"keyword": "anime", "typos": ["animé"]},
        {"keyword": "silent film", "language": "en", "typos": []},
        {"keyword": "film muet", "language": "fr", "typos": []},
        {"keyword": "premiere", "typos": ["première"]},
        {"keyword": "première", "language": "fr", "typos": ["premiere"]},
        {"keyword": "avant-première", "language": "fr", "typos": ["avant premiere"]},
        {"keyword": "preview", "language": "en", "typos": []},
    ]

    # ========================================
    # ATELIER / WORKSHOP
    # ========================================
    workshop_descriptors = [
        {"keyword": "workshop", "language": "en", "typos": ["workshp", "workship"]},
        {"keyword": "atelier", "language": "fr", "typos": ["attelier", "atellier"]},
        {"keyword": "class", "language": "en", "typos": ["clas"]},
        {"keyword": "cours", "language": "fr", "typos": ["cour"]},
        {"keyword": "lesson", "language": "en", "typos": ["leson"]},
        {"keyword": "leçon", "language": "fr", "typos": ["lecon"]},
        {"keyword": "masterclass", "typos": ["master class", "master-class"]},
        {"keyword": "tutorial", "language": "en", "typos": ["tutoral"]},
        {"keyword": "tutoriel", "language": "fr", "typos": []},
        {"keyword": "training", "language": "en", "typos": ["trainning"]},
        {"keyword": "formation", "language": "fr", "typos": ["formaton"]},
        {"keyword": "hands-on", "language": "en", "typos": ["hands on"]},
        {"keyword": "pratique", "language": "fr", "typos": []},
        {"keyword": "creative", "language": "en", "typos": ["creativee"]},
        {"keyword": "créatif", "language": "fr", "typos": ["creatif"]},
        {"keyword": "diy", "typos": ["d.i.y.", "do it yourself"]},
        {"keyword": "craft", "language": "en", "typos": ["crafte"]},
        {"keyword": "bricolage", "language": "fr", "typos": []},
    ]

    # ========================================
    # CONFERENCE / LECTURE
    # ========================================
    conference_descriptors = [
        {"keyword": "conference", "language": "en", "typos": ["confrence", "conferance"]},
        {"keyword": "conférence", "language": "fr", "typos": ["conference"]},
        {"keyword": "lecture", "language": "en", "typos": ["lectur"]},
        {"keyword": "talk", "language": "en", "typos": []},
        {"keyword": "presentation", "typos": ["présentation", "presentaton"]},
        {"keyword": "présentation", "language": "fr", "typos": ["presentation"]},
        {"keyword": "seminar", "language": "en", "typos": ["seminaire"]},
        {"keyword": "séminaire", "language": "fr", "typos": ["seminaire"]},
        {"keyword": "debate", "language": "en", "typos": ["debat"]},
        {"keyword": "débat", "language": "fr", "typos": ["debat"]},
        {"keyword": "discussion", "typos": ["discusion"]},
        {"keyword": "panel", "typos": []},
        {"keyword": "symposium", "typos": []},
        {"keyword": "colloquium", "language": "en", "typos": []},
        {"keyword": "colloque", "language": "fr", "typos": []},
        {"keyword": "forum", "typos": []},
    ]

    # ========================================
    # LECTURE / READING (Literary)
    # ========================================
    reading_descriptors = [
        {"keyword": "reading", "language": "en", "typos": ["reeding"]},
        {"keyword": "lecture", "language": "fr", "typos": []},  # Note: French "lecture" = reading
        {"keyword": "poetry", "language": "en", "typos": ["poetri"]},
        {"keyword": "poésie", "language": "fr", "typos": ["poesie"]},
        {"keyword": "poetry reading", "language": "en", "typos": []},
        {"keyword": "lecture de poésie", "language": "fr", "typos": []},
        {"keyword": "author", "language": "en", "typos": ["auther"]},
        {"keyword": "auteur", "language": "fr", "typos": []},
        {"keyword": "writer", "language": "en", "typos": ["writter"]},
        {"keyword": "écrivain", "language": "fr", "typos": ["ecrivain"]},
        {"keyword": "book signing", "language": "en", "typos": []},
        {"keyword": "dédicace", "language": "fr", "typos": ["dedicace"]},
        {"keyword": "storytelling", "language": "en", "typos": ["story telling"]},
        {"keyword": "conte", "language": "fr", "typos": []},
        {"keyword": "slam", "typos": []},
        {"keyword": "spoken word", "language": "en", "typos": []},
    ]

    # ========================================
    # FESTIVAL
    # ========================================
    festival_descriptors = [
        {"keyword": "festival", "typos": ["festivl", "festivel"]},
        {"keyword": "fest", "typos": []},
        {"keyword": "fête", "language": "fr", "typos": ["fete"]},
        {"keyword": "celebration", "language": "en", "typos": ["celebraton"]},
        {"keyword": "célébration", "language": "fr", "typos": ["celebration"]},
        {"keyword": "carnival", "language": "en", "typos": ["carneval"]},
        {"keyword": "carnaval", "language": "fr", "typos": []},
        {"keyword": "fair", "language": "en", "typos": []},
        {"keyword": "foire", "language": "fr", "typos": []},
        {"keyword": "market", "language": "en", "typos": ["markt"]},
        {"keyword": "marché", "language": "fr", "typos": ["marche"]},
        {"keyword": "brocante", "language": "fr", "typos": []},
        {"keyword": "flea market", "language": "en", "typos": []},
        {"keyword": "parade", "typos": []},
        {"keyword": "défilé", "language": "fr", "typos": ["defile"]},
    ]

    # ========================================
    # JEUNE PUBLIC (Young audience / Family)
    # ========================================
    family_descriptors = [
        {"keyword": "kids", "language": "en", "typos": ["childrens"]},
        {"keyword": "children", "language": "en", "typos": ["childern", "childrens"]},
        {"keyword": "enfants", "language": "fr", "typos": ["enfant"]},
        {"keyword": "family", "language": "en", "typos": ["familly"]},
        {"keyword": "famille", "language": "fr", "typos": ["famile"]},
        {"keyword": "young audience", "language": "en", "typos": []},
        {"keyword": "jeune public", "language": "fr", "typos": []},
        {"keyword": "toddler", "language": "en", "typos": ["todler"]},
        {"keyword": "tout-petit", "language": "fr", "typos": ["tout petit"]},
        {"keyword": "baby", "language": "en", "typos": []},
        {"keyword": "bébé", "language": "fr", "typos": ["bebe"]},
        {"keyword": "teens", "language": "en", "typos": ["teenns"]},
        {"keyword": "adolescents", "language": "fr", "typos": ["adolescent"]},
        {"keyword": "educational", "language": "en", "typos": ["educationnal"]},
        {"keyword": "éducatif", "language": "fr", "typos": ["educatif"]},
        {"keyword": "interactive", "typos": ["interactif"]},
        {"keyword": "interactif", "language": "fr", "typos": ["interactive"]},
    ]

    # ========================================
    # VISITE / TOUR
    # ========================================
    visit_descriptors = [
        {"keyword": "visit", "language": "en", "typos": ["visite"]},
        {"keyword": "visite", "language": "fr", "typos": ["visit"]},
        {"keyword": "tour", "typos": []},
        {"keyword": "guided tour", "language": "en", "typos": ["guided tur"]},
        {"keyword": "visite guidée", "language": "fr", "typos": ["visite guidee"]},
        {"keyword": "walking tour", "language": "en", "typos": []},
        {"keyword": "balade", "language": "fr", "typos": ["ballade"]},
        {"keyword": "promenade", "language": "fr", "typos": []},
        {"keyword": "heritage", "language": "en", "typos": ["heritag"]},
        {"keyword": "patrimoine", "language": "fr", "typos": []},
        {"keyword": "architecture", "typos": ["architecure"]},
        {"keyword": "historic", "language": "en", "typos": ["historik"]},
        {"keyword": "historique", "language": "fr", "typos": []},
        {"keyword": "open doors", "language": "en", "typos": []},
        {"keyword": "portes ouvertes", "language": "fr", "typos": []},
    ]

    # Build category mapping
    category_mapping = [
        ("Musique", music_descriptors),
        ("Art", art_descriptors),
        ("Danse", dance_descriptors),
        ("Spectacle", theatre_descriptors),
        ("Cinéma", cinema_descriptors),
        ("Atelier", workshop_descriptors),
        ("Conférence", conference_descriptors),
        ("Lecture", reading_descriptors),
        ("Festival", festival_descriptors),
        ("Jeune Public", family_descriptors),
        ("Visite", visit_descriptors),
    ]

    total_inserted = 0
    for category, descriptors in category_mapping:
        for item in descriptors:
            try:
                language = item.get("language", "both")
                cursor.execute("""
                    INSERT OR REPLACE INTO search_keywords
                    (keyword, keyword_type, language, canonical, implied_category, typos, priority)
                    VALUES (?, 'event', ?, ?, ?, ?, 1)
                """, (
                    item["keyword"].lower(),
                    language,
                    item["keyword"].lower(),  # canonical is the keyword itself
                    category,
                    json.dumps(item["typos"])
                ))
                total_inserted += 1
            except Exception as e:
                logger.warning(f"Failed to insert event descriptor '{item['keyword']}': {e}")

    conn.commit()
    logger.info(f"Inserted {total_inserted} event descriptors across {len(category_mapping)} categories")


def main():
    """Run the migration."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        # Create table
        create_table(conn)

        # Populate date keywords
        populate_date_keywords(conn)

        # Populate event descriptors
        populate_event_descriptors(conn)

        # Verify counts
        cursor = conn.cursor()
        cursor.execute("SELECT keyword_type, COUNT(*) FROM search_keywords GROUP BY keyword_type")
        counts = cursor.fetchall()

        logger.info("=" * 50)
        logger.info("Migration complete! Keyword counts:")
        for ktype, count in counts:
            logger.info(f"  {ktype}: {count}")

        cursor.execute("SELECT COUNT(*) FROM search_keywords")
        total = cursor.fetchone()[0]
        logger.info(f"  TOTAL: {total}")
        logger.info("=" * 50)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
