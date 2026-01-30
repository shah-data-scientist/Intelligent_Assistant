"""Migration script to add special query keywords to search_keywords table.

This extends the existing keyword detection to include:
1. Greeting keywords (bonjour, hello, salut, etc.)
2. Capability keywords (help, aide, capabilities, etc.)
3. Off-topic keywords (weather, meteo, recipe, translate, etc.)
4. Statistical keywords (how many, combien, count, etc.)

Usage:
    python scripts/migrate_special_query_keywords.py
"""

import sqlite3
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "data/events.db"


def populate_greeting_keywords(conn: sqlite3.Connection):
    """Populate greeting-related keywords."""
    cursor = conn.cursor()

    greetings = [
        # English greetings
        {"keyword": "hello", "language": "en", "canonical": "greeting", "typos": ["helo", "hallo", "helllo", "hullo"]},
        {"keyword": "hi", "language": "en", "canonical": "greeting", "typos": ["hii", "hy"]},
        {"keyword": "hey", "language": "en", "canonical": "greeting", "typos": ["heyy", "heey"]},
        {"keyword": "good morning", "language": "en", "canonical": "greeting", "typos": ["goodmorning", "gd morning", "gud morning"]},
        {"keyword": "good afternoon", "language": "en", "canonical": "greeting", "typos": ["goodafternoon", "gd afternoon"]},
        {"keyword": "good evening", "language": "en", "canonical": "greeting", "typos": ["goodevening", "gd evening"]},
        {"keyword": "greetings", "language": "en", "canonical": "greeting", "typos": ["greetngs", "gretings"]},
        {"keyword": "howdy", "language": "en", "canonical": "greeting", "typos": ["howdee"]},

        # French greetings
        {"keyword": "bonjour", "language": "fr", "canonical": "greeting", "typos": ["bonour", "bonjor", "bojour", "bonjur", "bnjour"]},
        {"keyword": "bonsoir", "language": "fr", "canonical": "greeting", "typos": ["bonsor", "bonsoi", "bonsoire"]},
        {"keyword": "salut", "language": "fr", "canonical": "greeting", "typos": ["salu", "salue", "saluu", "slt"]},
        {"keyword": "coucou", "language": "fr", "canonical": "greeting", "typos": ["couou", "couco", "coco", "cucou"]},
        {"keyword": "bonne journee", "language": "fr", "canonical": "greeting", "typos": ["bonne journée", "bon journee"]},
    ]

    for item in greetings:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO search_keywords
                (keyword, keyword_type, language, canonical, implied_category, typos, priority)
                VALUES (?, 'greeting', ?, ?, NULL, ?, 1)
            """, (
                item["keyword"].lower(),
                item["language"],
                item["canonical"],
                json.dumps(item["typos"])
            ))
        except Exception as e:
            logger.warning(f"Failed to insert greeting keyword '{item['keyword']}': {e}")

    conn.commit()
    logger.info(f"Inserted {len(greetings)} greeting keywords")


def populate_capability_keywords(conn: sqlite3.Connection):
    """Populate capability/help-related keywords."""
    cursor = conn.cursor()

    capabilities = [
        # English capability words
        {"keyword": "help", "language": "en", "canonical": "capability", "typos": ["hlp", "halp", "hepl"]},
        {"keyword": "capabilities", "language": "en", "canonical": "capability", "typos": ["capabilites", "capabilties", "capabilitys"]},
        {"keyword": "can you", "language": "en", "canonical": "capability", "typos": ["canyou", "can u"]},
        {"keyword": "what can", "language": "en", "canonical": "capability", "typos": ["wat can"]},
        {"keyword": "what do you do", "language": "en", "canonical": "capability", "typos": ["what do u do"]},
        {"keyword": "who are you", "language": "en", "canonical": "capability", "typos": ["who r you", "who r u"]},
        {"keyword": "tell me about yourself", "language": "en", "canonical": "capability", "typos": []},
        {"keyword": "how do you work", "language": "en", "canonical": "capability", "typos": []},
        {"keyword": "functions", "language": "en", "canonical": "capability", "typos": ["functins", "funtions"]},
        {"keyword": "features", "language": "en", "canonical": "capability", "typos": ["featurs", "feautres"]},

        # French capability words
        {"keyword": "aide", "language": "fr", "canonical": "capability", "typos": ["aid", "aides"]},
        {"keyword": "aider", "language": "fr", "canonical": "capability", "typos": ["aidez", "aider"]},
        {"keyword": "capacites", "language": "fr", "canonical": "capability", "typos": ["capacités", "capicites"]},
        {"keyword": "peux-tu", "language": "fr", "canonical": "capability", "typos": ["peu tu", "peux tu"]},
        {"keyword": "pouvez-vous", "language": "fr", "canonical": "capability", "typos": ["pouvez vous", "pouvezvous"]},
        {"keyword": "tu peux", "language": "fr", "canonical": "capability", "typos": ["tu peu"]},
        {"keyword": "qui es-tu", "language": "fr", "canonical": "capability", "typos": ["qui es tu", "qui estu"]},
        {"keyword": "dis-moi", "language": "fr", "canonical": "capability", "typos": ["dis moi", "disme"]},
        {"keyword": "parle-moi de toi", "language": "fr", "canonical": "capability", "typos": []},
        {"keyword": "fonctionnalites", "language": "fr", "canonical": "capability", "typos": ["fonctionnalités", "fonctionalites"]},
        {"keyword": "comment", "language": "fr", "canonical": "capability", "typos": ["coment", "commant"]},
    ]

    for item in capabilities:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO search_keywords
                (keyword, keyword_type, language, canonical, implied_category, typos, priority)
                VALUES (?, 'capability', ?, ?, NULL, ?, 1)
            """, (
                item["keyword"].lower(),
                item["language"],
                item["canonical"],
                json.dumps(item["typos"])
            ))
        except Exception as e:
            logger.warning(f"Failed to insert capability keyword '{item['keyword']}': {e}")

    conn.commit()
    logger.info(f"Inserted {len(capabilities)} capability keywords")


def populate_off_topic_keywords(conn: sqlite3.Connection):
    """Populate off-topic detection keywords."""
    cursor = conn.cursor()

    off_topic = [
        # Weather (English)
        {"keyword": "weather", "language": "en", "canonical": "off_topic_weather", "typos": ["wether", "wheather", "weater"]},
        {"keyword": "temperature", "language": "en", "canonical": "off_topic_weather", "typos": ["temprature", "temperture"]},
        {"keyword": "forecast", "language": "en", "canonical": "off_topic_weather", "typos": ["forcast", "forcaste"]},
        {"keyword": "rain", "language": "en", "canonical": "off_topic_weather", "typos": ["rian"]},
        {"keyword": "sunny", "language": "en", "canonical": "off_topic_weather", "typos": ["suny", "sunney"]},

        # Weather (French)
        {"keyword": "meteo", "language": "fr", "canonical": "off_topic_weather", "typos": ["météo", "meto", "metéo"]},
        {"keyword": "temperature", "language": "fr", "canonical": "off_topic_weather", "typos": ["température", "temperture"]},
        {"keyword": "previsions", "language": "fr", "canonical": "off_topic_weather", "typos": ["prévisions", "prevision"]},
        {"keyword": "pluie", "language": "fr", "canonical": "off_topic_weather", "typos": ["plui"]},
        {"keyword": "soleil", "language": "fr", "canonical": "off_topic_weather", "typos": ["solei", "soleille"]},

        # Writing/Creative (English)
        {"keyword": "poem", "language": "en", "canonical": "off_topic_writing", "typos": ["poeme", "pome"]},
        {"keyword": "story", "language": "en", "canonical": "off_topic_writing", "typos": ["storey", "storie"]},
        {"keyword": "essay", "language": "en", "canonical": "off_topic_writing", "typos": ["esay", "essai"]},
        {"keyword": "write me", "language": "en", "canonical": "off_topic_writing", "typos": ["writeme", "writ me"]},

        # Writing/Creative (French)
        {"keyword": "poeme", "language": "fr", "canonical": "off_topic_writing", "typos": ["poème", "pome"]},
        {"keyword": "histoire", "language": "fr", "canonical": "off_topic_writing", "typos": ["histoir", "hisoire"]},
        {"keyword": "ecris", "language": "fr", "canonical": "off_topic_writing", "typos": ["écris", "ecrire"]},
        {"keyword": "redige", "language": "fr", "canonical": "off_topic_writing", "typos": ["rédige", "rediger"]},

        # Translation (English)
        {"keyword": "translate", "language": "en", "canonical": "off_topic_translate", "typos": ["translat", "tranlate", "trasnlate"]},
        {"keyword": "translation", "language": "en", "canonical": "off_topic_translate", "typos": ["translaton", "traslation"]},

        # Translation (French)
        {"keyword": "traduis", "language": "fr", "canonical": "off_topic_translate", "typos": ["tradui", "traduire"]},
        {"keyword": "traduire", "language": "fr", "canonical": "off_topic_translate", "typos": ["traduir", "tradure"]},
        {"keyword": "traduction", "language": "fr", "canonical": "off_topic_translate", "typos": ["traducton", "traductoin"]},

        # Cooking/Recipe (English)
        {"keyword": "recipe", "language": "en", "canonical": "off_topic_cooking", "typos": ["reciepe", "recipee", "recepie"]},
        {"keyword": "cook", "language": "en", "canonical": "off_topic_cooking", "typos": ["cok", "coook"]},
        {"keyword": "cooking", "language": "en", "canonical": "off_topic_cooking", "typos": ["coking", "cookin"]},
        {"keyword": "bake", "language": "en", "canonical": "off_topic_cooking", "typos": ["bak"]},

        # Cooking/Recipe (French)
        {"keyword": "recette", "language": "fr", "canonical": "off_topic_cooking", "typos": ["recete", "receette"]},
        {"keyword": "cuisine", "language": "fr", "canonical": "off_topic_cooking", "typos": ["cuisne", "cuisisne"]},
        {"keyword": "cuisiner", "language": "fr", "canonical": "off_topic_cooking", "typos": ["cuisner", "cuisinier"]},

        # Math/Calculation (English)
        {"keyword": "calculate", "language": "en", "canonical": "off_topic_math", "typos": ["calculat", "calcuate", "calulate"]},
        {"keyword": "math", "language": "en", "canonical": "off_topic_math", "typos": ["maths", "matematics"]},
        {"keyword": "equation", "language": "en", "canonical": "off_topic_math", "typos": ["equasion", "equaton"]},
        {"keyword": "solve", "language": "en", "canonical": "off_topic_math", "typos": ["solv", "slove"]},

        # Math/Calculation (French)
        {"keyword": "calcul", "language": "fr", "canonical": "off_topic_math", "typos": ["calul", "calcule"]},
        {"keyword": "calculer", "language": "fr", "canonical": "off_topic_math", "typos": ["calculez", "calcuer"]},
        {"keyword": "equation", "language": "fr", "canonical": "off_topic_math", "typos": ["équation", "equasion"]},
        {"keyword": "mathematiques", "language": "fr", "canonical": "off_topic_math", "typos": ["mathématiques", "math"]},

        # Code/Programming (English)
        {"keyword": "code", "language": "en", "canonical": "off_topic_code", "typos": ["cod", "codee"]},
        {"keyword": "program", "language": "en", "canonical": "off_topic_code", "typos": ["progam", "programm"]},
        {"keyword": "python", "language": "en", "canonical": "off_topic_code", "typos": ["pyhton", "pythno"]},
        {"keyword": "javascript", "language": "en", "canonical": "off_topic_code", "typos": ["javscript", "javasript"]},
        {"keyword": "debug", "language": "en", "canonical": "off_topic_code", "typos": ["debuf", "deubg"]},

        # Code/Programming (French)
        {"keyword": "programmer", "language": "fr", "canonical": "off_topic_code", "typos": ["programer", "progammer"]},
        {"keyword": "programme", "language": "fr", "canonical": "off_topic_code", "typos": ["programe"]},

        # News/Politics (English)
        {"keyword": "news", "language": "en", "canonical": "off_topic_news", "typos": ["newss", "new"]},
        {"keyword": "politics", "language": "en", "canonical": "off_topic_news", "typos": ["politcs", "poltics"]},
        {"keyword": "president", "language": "en", "canonical": "off_topic_news", "typos": ["presidant", "presiden"]},

        # News/Politics (French)
        {"keyword": "actualite", "language": "fr", "canonical": "off_topic_news", "typos": ["actualité", "actulite"]},
        {"keyword": "actualites", "language": "fr", "canonical": "off_topic_news", "typos": ["actualités", "actulites"]},
        {"keyword": "politique", "language": "fr", "canonical": "off_topic_news", "typos": ["politque", "politiqe"]},
        {"keyword": "president", "language": "fr", "canonical": "off_topic_news", "typos": ["président", "presidant"]},

        # Medical/Health (English)
        {"keyword": "medical", "language": "en", "canonical": "off_topic_medical", "typos": ["medicall", "medcal"]},
        {"keyword": "health", "language": "en", "canonical": "off_topic_medical", "typos": ["helth", "heatlh"]},
        {"keyword": "doctor", "language": "en", "canonical": "off_topic_medical", "typos": ["docter", "doctr"]},
        {"keyword": "symptoms", "language": "en", "canonical": "off_topic_medical", "typos": ["symtoms", "symptomes"]},
        {"keyword": "medicine", "language": "en", "canonical": "off_topic_medical", "typos": ["medicin", "medecine"]},

        # Medical/Health (French)
        {"keyword": "medical", "language": "fr", "canonical": "off_topic_medical", "typos": ["médical", "medicale"]},
        {"keyword": "sante", "language": "fr", "canonical": "off_topic_medical", "typos": ["santé", "santee"]},
        {"keyword": "medecin", "language": "fr", "canonical": "off_topic_medical", "typos": ["médecin", "medcin"]},
        {"keyword": "symptomes", "language": "fr", "canonical": "off_topic_medical", "typos": ["symptômes", "symtomes"]},

        # Legal (English)
        {"keyword": "legal", "language": "en", "canonical": "off_topic_legal", "typos": ["legall", "leagal"]},
        {"keyword": "lawyer", "language": "en", "canonical": "off_topic_legal", "typos": ["laywer", "lawer"]},
        {"keyword": "attorney", "language": "en", "canonical": "off_topic_legal", "typos": ["attorny", "atorney"]},
        {"keyword": "lawsuit", "language": "en", "canonical": "off_topic_legal", "typos": ["lawsuite", "law suit"]},

        # Legal (French)
        {"keyword": "juridique", "language": "fr", "canonical": "off_topic_legal", "typos": ["juridiqu", "juridque"]},
        {"keyword": "avocat", "language": "fr", "canonical": "off_topic_legal", "typos": ["avoca", "avocatt"]},
        {"keyword": "proces", "language": "fr", "canonical": "off_topic_legal", "typos": ["procès", "processe"]},

        # Finance (English)
        {"keyword": "stock", "language": "en", "canonical": "off_topic_finance", "typos": ["stok", "stockk"]},
        {"keyword": "invest", "language": "en", "canonical": "off_topic_finance", "typos": ["invset", "invist"]},
        {"keyword": "investment", "language": "en", "canonical": "off_topic_finance", "typos": ["investement", "invesment"]},
        {"keyword": "finance", "language": "en", "canonical": "off_topic_finance", "typos": ["financ", "finanace"]},
        {"keyword": "trading", "language": "en", "canonical": "off_topic_finance", "typos": ["tradng", "traiding"]},

        # Finance (French)
        {"keyword": "bourse", "language": "fr", "canonical": "off_topic_finance", "typos": ["bours", "bourrse"]},
        {"keyword": "investir", "language": "fr", "canonical": "off_topic_finance", "typos": ["investire", "invetir"]},
        {"keyword": "investissement", "language": "fr", "canonical": "off_topic_finance", "typos": ["investissment", "investisement"]},

        # General knowledge questions (English)
        {"keyword": "capital of", "language": "en", "canonical": "off_topic_geography", "typos": ["captial of", "capitol of"]},
        {"keyword": "population of", "language": "en", "canonical": "off_topic_geography", "typos": ["populaton of"]},
        {"keyword": "flag of", "language": "en", "canonical": "off_topic_geography", "typos": ["flaf of"]},
        {"keyword": "currency of", "language": "en", "canonical": "off_topic_geography", "typos": ["curreny of"]},
        {"keyword": "history of", "language": "en", "canonical": "off_topic_geography", "typos": ["histroy of"]},
        {"keyword": "geography", "language": "en", "canonical": "off_topic_geography", "typos": ["geograpy", "geaography"]},

        # General knowledge questions (French)
        {"keyword": "capitale de", "language": "fr", "canonical": "off_topic_geography", "typos": ["captiale de"]},
        {"keyword": "population de", "language": "fr", "canonical": "off_topic_geography", "typos": ["populaton de"]},
        {"keyword": "drapeau de", "language": "fr", "canonical": "off_topic_geography", "typos": ["drapeua de"]},
        {"keyword": "monnaie de", "language": "fr", "canonical": "off_topic_geography", "typos": ["monaie de"]},
        {"keyword": "histoire de", "language": "fr", "canonical": "off_topic_geography", "typos": ["histoir de"]},
        {"keyword": "geographie", "language": "fr", "canonical": "off_topic_geography", "typos": ["géographie", "geographi"]},

        # Transport directions (English)
        {"keyword": "how to get to", "language": "en", "canonical": "off_topic_directions", "typos": ["how to get too"]},
        {"keyword": "directions to", "language": "en", "canonical": "off_topic_directions", "typos": ["directons to"]},
        {"keyword": "route to", "language": "en", "canonical": "off_topic_directions", "typos": ["rout to"]},

        # Transport directions (French)
        {"keyword": "comment aller", "language": "fr", "canonical": "off_topic_directions", "typos": ["coment aller"]},
        {"keyword": "comment se rendre", "language": "fr", "canonical": "off_topic_directions", "typos": ["coment se rendre"]},
        {"keyword": "itineraire", "language": "fr", "canonical": "off_topic_directions", "typos": ["itinéraire", "itinerair"]},
    ]

    for item in off_topic:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO search_keywords
                (keyword, keyword_type, language, canonical, implied_category, typos, priority)
                VALUES (?, 'off_topic', ?, ?, NULL, ?, 1)
            """, (
                item["keyword"].lower(),
                item["language"],
                item["canonical"],
                json.dumps(item["typos"])
            ))
        except Exception as e:
            logger.warning(f"Failed to insert off_topic keyword '{item['keyword']}': {e}")

    conn.commit()
    logger.info(f"Inserted {len(off_topic)} off_topic keywords")


def populate_statistical_keywords(conn: sqlite3.Connection):
    """Populate statistical query detection keywords."""
    cursor = conn.cursor()

    statistical = [
        # English statistical words
        {"keyword": "how many", "language": "en", "canonical": "statistical", "typos": ["how meny", "how manny"]},
        {"keyword": "number of", "language": "en", "canonical": "statistical", "typos": ["numbr of", "numbre of"]},
        {"keyword": "count", "language": "en", "canonical": "statistical", "typos": ["cont", "coutn"]},
        {"keyword": "total", "language": "en", "canonical": "statistical", "typos": ["totall", "totla"]},
        {"keyword": "statistics", "language": "en", "canonical": "statistical", "typos": ["statisitcs", "statisitics"]},
        {"keyword": "average", "language": "en", "canonical": "statistical", "typos": ["averge", "avrage"]},

        # French statistical words
        {"keyword": "combien", "language": "fr", "canonical": "statistical", "typos": ["combein", "conbien", "combine"]},
        {"keyword": "nombre de", "language": "fr", "canonical": "statistical", "typos": ["nombr de", "nmbre de"]},
        {"keyword": "comptez", "language": "fr", "canonical": "statistical", "typos": ["compter", "comtez"]},
        {"keyword": "total de", "language": "fr", "canonical": "statistical", "typos": ["totall de"]},
        {"keyword": "statistiques", "language": "fr", "canonical": "statistical", "typos": ["statistique", "statisitques"]},
        {"keyword": "moyenne", "language": "fr", "canonical": "statistical", "typos": ["moyene", "moynne"]},
    ]

    for item in statistical:
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO search_keywords
                (keyword, keyword_type, language, canonical, implied_category, typos, priority)
                VALUES (?, 'statistical', ?, ?, NULL, ?, 1)
            """, (
                item["keyword"].lower(),
                item["language"],
                item["canonical"],
                json.dumps(item["typos"])
            ))
        except Exception as e:
            logger.warning(f"Failed to insert statistical keyword '{item['keyword']}': {e}")

    conn.commit()
    logger.info(f"Inserted {len(statistical)} statistical keywords")


def main():
    """Run the migration."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        logger.error(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)

    try:
        # Populate new keyword types
        populate_greeting_keywords(conn)
        populate_capability_keywords(conn)
        populate_off_topic_keywords(conn)
        populate_statistical_keywords(conn)

        # Verify counts
        cursor = conn.cursor()
        cursor.execute("SELECT keyword_type, COUNT(*) FROM search_keywords GROUP BY keyword_type")
        counts = cursor.fetchall()

        logger.info("=" * 50)
        logger.info("Migration complete! Keyword counts by type:")
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
