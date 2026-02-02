"""Security guardrails for the RAG system with enhanced Unicode normalization."""

import logging
import re
import threading
import unicodedata
from datetime import datetime, timedelta
from typing import Dict, Optional, Set

logger = logging.getLogger(__name__)


class SecurityException(ValueError):
    """Exception raised when a security guardrail is triggered."""

    pass


class SessionBlockedException(SecurityException):
    """Exception raised when a blocked session tries to make a request."""

    pass


# ========================================
# BLOCKED SESSION MANAGER
# ========================================
# Tracks sessions that have triggered security violations.
# Blocked sessions cannot make further requests.


class BlockedSessionManager:
    """Manages blocked sessions after security violations.

    Thread-safe implementation using a lock for concurrent access.
    Sessions are blocked permanently until explicitly unblocked or
    until the block expires (configurable timeout).
    """

    # Default block duration (None = permanent until server restart)
    DEFAULT_BLOCK_DURATION_MINUTES: Optional[int] = None  # Set to e.g. 60 for 1-hour blocks

    def __init__(self):
        self._blocked_sessions: Dict[str, datetime] = {}  # session_id -> blocked_at timestamp
        self._violation_counts: Dict[str, int] = {}  # session_id -> violation count
        self._lock = threading.Lock()

    def block_session(self, session_id: str, reason: str = "security_violation") -> None:
        """Block a session from making further requests.

        Args:
            session_id: The session identifier to block
            reason: Reason for blocking (for logging)
        """
        with self._lock:
            self._blocked_sessions[session_id] = datetime.now()
            self._violation_counts[session_id] = self._violation_counts.get(session_id, 0) + 1
            logger.warning(
                f"[SECURITY] Session BLOCKED: {session_id} | "
                f"Reason: {reason} | "
                f"Violation #{self._violation_counts[session_id]}"
            )

    def is_blocked(self, session_id: str) -> bool:
        """Check if a session is currently blocked.

        Args:
            session_id: The session identifier to check

        Returns:
            True if session is blocked, False otherwise
        """
        with self._lock:
            if session_id not in self._blocked_sessions:
                return False

            blocked_at = self._blocked_sessions[session_id]

            # Check if block has expired (if timeout is configured)
            if self.DEFAULT_BLOCK_DURATION_MINUTES is not None:
                expiry = blocked_at + timedelta(minutes=self.DEFAULT_BLOCK_DURATION_MINUTES)
                if datetime.now() > expiry:
                    # Block expired - remove and allow
                    del self._blocked_sessions[session_id]
                    logger.info(f"[SECURITY] Session block expired: {session_id}")
                    return False

            return True

    def unblock_session(self, session_id: str) -> bool:
        """Manually unblock a session.

        Args:
            session_id: The session identifier to unblock

        Returns:
            True if session was unblocked, False if it wasn't blocked
        """
        with self._lock:
            if session_id in self._blocked_sessions:
                del self._blocked_sessions[session_id]
                logger.info(f"[SECURITY] Session manually unblocked: {session_id}")
                return True
            return False

    def get_violation_count(self, session_id: str) -> int:
        """Get the number of violations for a session.

        Args:
            session_id: The session identifier

        Returns:
            Number of security violations for this session
        """
        with self._lock:
            return self._violation_counts.get(session_id, 0)

    def get_blocked_sessions(self) -> Set[str]:
        """Get all currently blocked session IDs.

        Returns:
            Set of blocked session IDs
        """
        with self._lock:
            return set(self._blocked_sessions.keys())

    def clear_all_blocks(self) -> int:
        """Clear all blocked sessions (admin function).

        Returns:
            Number of sessions that were unblocked
        """
        with self._lock:
            count = len(self._blocked_sessions)
            self._blocked_sessions.clear()
            logger.info(f"[SECURITY] All session blocks cleared ({count} sessions)")
            return count


# Global singleton instance
_blocked_session_manager: Optional[BlockedSessionManager] = None


def get_blocked_session_manager() -> BlockedSessionManager:
    """Get or create the global BlockedSessionManager instance."""
    global _blocked_session_manager
    if _blocked_session_manager is None:
        _blocked_session_manager = BlockedSessionManager()
    return _blocked_session_manager


# Message shown to blocked sessions
BLOCKED_SESSION_MESSAGE = (
    "Your session has been blocked due to a previous security violation. "
    "Please start a new session to continue.\n\n"
    "Votre session a été bloquée suite à une violation de sécurité. "
    "Veuillez démarrer une nouvelle session pour continuer."
)

# Refusal message for inappropriate language
REFUSAL_MESSAGE = (
    "I cannot process your request because it contains inappropriate or abusive language. "
    "Please use respectful language when interacting with the assistant.\n\n"
    "Je ne peux pas traiter votre demande car elle contient un langage inapproprié ou abusif. "
    "Merci d'utiliser un langage respectueux lors de vos échanges avec l'assistant."
)

# Expanded patterns indicative of prompt injection or malicious intent (20+ patterns)
# OPTIMIZATION: Pre-compiled at module load time for ~10% faster matching
_MALICIOUS_PATTERNS_RAW = [
    # =====================================================
    # ENGLISH - Instruction overrides
    # =====================================================
    r"ignore (previous|all|your) instructions?",
    r"disregard (previous|all) (instructions?|prompts?|rules?)",
    r"forget (your|previous|all) (instructions?|rules?|context)",
    r"override (previous|system|safety|security) (instructions?|rules?|settings?)",
    # =====================================================
    # FRENCH - Instruction overrides (SEC003 fix)
    # =====================================================
    r"oublie[sz]? (tes|les|vos|toutes? les) (r[eè]gles?|instructions?|consignes?)",
    r"ignore[sz]? (tes|les|vos|toutes? les) (r[eè]gles?|instructions?|consignes?)",
    r"ne (tiens?|tenez) (plus |pas )?(compte|aucun compte) (de |des )(tes|les|vos) (r[eè]gles?|instructions?)",
    r"fais? comme si (tu n'avais|vous n'aviez) (pas |plus )?(de |d')?(r[eè]gles?|instructions?|limites?)",
    # =====================================================
    # ENGLISH - Jailbreak attempts
    # =====================================================
    r"you are now",
    r"pretend (you are|to be|that you're)",
    r"act as if you (are|were)",
    r"(developer|debug|admin|god|root|sudo) mode",
    r"bypass (your|the) (rules?|restrictions?|filters?|safety)",
    r"jailbreak",
    # =====================================================
    # FRENCH - Jailbreak attempts
    # =====================================================
    r"tu es maintenant",
    r"fais (semblant|comme si) (d'[eê]tre|que tu es)",
    r"agis comme (si tu [eé]tais|un)",
    r"mode (d[eé]veloppeur|debug|admin|dieu|root)",
    r"contourne[sz]? (tes|les|vos) (r[eè]gles?|restrictions?|filtres?|limites?)",
    # =====================================================
    # ENGLISH - Role manipulation
    # =====================================================
    r"you must (now|always|only)",
    r"from now on",
    r"new (role|personality|character|instructions?)",
    # =====================================================
    # FRENCH - Role manipulation
    # =====================================================
    r"tu dois (maintenant|toujours|seulement)",
    r"[aà] partir de maintenant",
    r"nouve(au|lle) (r[oô]le|personnalit[eé]|personnage|instructions?)",
    # =====================================================
    # ENGLISH - Data exfiltration attempts
    # =====================================================
    r"(show|print|display|reveal|output) (system|internal|hidden) (data|prompt|instructions?)",
    r"what (are|were) your (original|system|hidden) (instructions?|prompts?|rules?)",
    # =====================================================
    # FRENCH - Data exfiltration attempts
    # =====================================================
    r"(montre|affiche|r[eé]v[eè]le|donne)[\s-]*(moi |nous )?(le |la |les |ton |ta |tes )?(prompt|instructions?|r[eè]gles?) (syst[eè]me|cach[eé]e?s?|interne?s?|originale?s?)",
    r"(quel|quelles?) (sont|[eé]taient) (tes|les|vos) (instructions?|r[eè]gles?|prompts?) (originale?s?|syst[eè]me|cach[eé]e?s?)",
    # =====================================================
    # SQL/Command injection
    # =====================================================
    r"(delete|drop|truncate|alter)\s+(table|database|schema)",
    r"union\s+select",
    r";\s*drop\s+table",
    r"<\s*script",
    r"javascript\s*:",
    # =====================================================
    # System manipulation
    # =====================================================
    r"system\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
]
MALICIOUS_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _MALICIOUS_PATTERNS_RAW]

# Full-word profanity phrases (to avoid Scunthorpe problem)
# NOTE: These work WITH normalize_text_for_profanity() which handles:
#   - Homoglyphs (Cyrillic с → c, etc.)
#   - Accented chars (ü → u, é → e)
#   - Leetspeak numbers (0→o, 1→i, 3→e, 4→a, 5→s)
# But normalization does NOT handle: repeated chars, spaces, or symbol substitution
# So we need explicit patterns for those evasions below.
# OPTIMIZATION: Pre-compiled at module load time
# COMPREHENSIVE profanity/insult list for English and French
_PROFANITY_PHRASES_RAW = [
    # =====================================================
    # ENGLISH PROFANITY (SEVERE)
    # =====================================================
    r"\bfuck\b",
    r"\bfucking\b",
    r"\bfucker\b",
    r"\bfucked\b",
    r"\bfucks\b",
    r"\bshit\b",
    r"\bshitty\b",
    r"\bshits\b",
    r"\bshitting\b",
    r"\bbullshit\b",
    r"\basshole\b",
    r"\bassholes\b",
    r"\bass\b",
    r"\bbitch\b",
    r"\bbitches\b",
    r"\bbitchy\b",
    r"\bson of a bitch\b",
    r"\bcunt\b",
    r"\bcunts\b",
    r"\bdick\b",
    r"\bdicks\b",
    r"\bdickhead\b",
    r"\bpussy\b",
    r"\bpussies\b",
    r"\bbastard\b",
    r"\bbastards\b",
    r"\bmotherfucker\b",
    r"\bmotherfucking\b",
    r"\bmotherfuckers\b",
    r"\bcock\b",
    r"\bcocks\b",
    r"\bcocksucker\b",
    r"\bslut\b",
    r"\bsluts\b",
    r"\bslutty\b",
    r"\bwhore\b",
    r"\bwhores\b",
    r"\bdamn\b",
    r"\bdamned\b",
    r"\bgoddam\b",
    r"\bgoddamn\b",
    r"\bhell\b",  # context-dependent but often abusive
    r"\bcrap\b",
    r"\bcrappy\b",
    r"\bpiss\b",
    r"\bpissed\b",
    r"\bpissing\b",
    r"\bwanker\b",
    r"\bwankers\b",
    r"\btit\b",
    r"\btits\b",
    r"\bboob\b",
    r"\bboobs\b",
    r"\banus\b",
    r"\banal\b",
    r"\bdouche\b",
    r"\bdouchebag\b",
    r"\bjackass\b",
    r"\bjerk\b",
    r"\bjerks\b",
    r"\bscumbag\b",
    r"\bscum\b",
    r"\bprick\b",
    r"\bpricks\b",
    r"\btwat\b",
    r"\btwats\b",
    r"\bbollocks\b",
    r"\bbloody\b",
    r"\barse\b",
    r"\barsehole\b",
    r"\bfag\b",
    r"\bfaggot\b",
    r"\bfags\b",  # slurs
    r"\bdyke\b",
    r"\bdykes\b",  # slurs
    r"\bnigger\b",
    r"\bnigga\b",
    r"\bniggas\b",  # racial slurs
    r"\bchink\b",
    r"\bspic\b",
    r"\bwetback\b",  # racial slurs
    r"\bkike\b",
    r"\bgook\b",
    r"\bslant\b",  # racial slurs
    r"\bretard\b",
    r"\bretarded\b",
    r"\bretards\b",  # ableist slurs
    # =====================================================
    # ENGLISH INSULTS (MILDER BUT ABUSIVE)
    # =====================================================
    r"\bidiot\b",
    r"\bidiots\b",
    r"\bidiotic\b",
    r"\bstupid\b",
    r"\bstupidity\b",
    r"\bmoron\b",
    r"\bmorons\b",
    r"\bmoronic\b",
    r"\bimbecile\b",
    r"\bimbeciles\b",
    r"\bdumb\b",
    r"\bdumbass\b",
    r"\bdumbasses\b",
    r"\bloser\b",
    r"\blosers\b",
    r"\bpathetic\b",
    r"\bugly\b",  # personal attack
    r"\bfat\b",  # body shaming (context-dependent)
    r"\blame\b",  # ableist
    r"\bfreak\b",
    r"\bfreaks\b",
    r"\bcreep\b",
    r"\bcreeps\b",
    r"\bcreepy\b",
    r"\bnerd\b",
    r"\bnerds\b",  # context-dependent
    r"\bgeek\b",  # context-dependent
    r"\btrash\b",  # when directed at person
    r"\bgarbage\b",  # when directed at person
    r"\bworthless\b",
    r"\buseless\b",
    r"\bhate you\b",
    r"\bi hate\b",
    r"\bshut up\b",
    r"\bgo to hell\b",
    r"\bgo die\b",
    r"\bkill yourself\b",
    r"\bkys\b",  # "kill yourself" abbreviation
    # =====================================================
    # FRENCH PROFANITY (SEVERE) - Gros mots
    # =====================================================
    r"\bmerde\b",
    r"\bmerdes\b",
    r"\bmerdeux\b",
    r"\bmerdeuse\b",
    r"\bmerdique\b",
    r"\bputain\b",
    r"\bputains\b",
    r"\bcon\b",
    r"\bcons\b",
    r"\bconne\b",
    r"\bconnes\b",
    r"\bconnerie\b",
    r"\bconneries\b",
    r"\bconnard\b",
    r"\bconnards\b",
    r"\bconnasse\b",
    r"\bconnasses\b",
    r"\bsalope\b",
    r"\bsalopes\b",
    r"\bsaloperie\b",
    r"\bsalaud\b",
    r"\bsalauds\b",
    r"\bsalaude\b",
    r"\benculé\b",
    r"\bencule\b",
    r"\benculer\b",
    r"\benculés\b",
    r"\bniquer\b",
    r"\bnique\b",
    r"\bniqué\b",
    r"\bnique ta mere\b",
    r"\bpute\b",
    r"\bputes\b",
    r"\bbordel\b",
    r"\bchier\b",
    r"\bchié\b",
    r"\bchiotte\b",
    r"\bchiottes\b",
    r"\bfoutre\b",
    r"\bfoutue\b",
    r"\bfoutu\b",
    r"\bje m'en fous\b",
    r"\bbite\b",
    r"\bbites\b",  # vulgar for penis
    r"\bcouille\b",
    r"\bcouilles\b",  # vulgar for testicles
    r"\bchatte\b",  # vulgar for vagina
    r"\bbranleur\b",
    r"\bbranleuse\b",
    r"\bbranleurs\b",
    r"\benfoiré\b",
    r"\benfoire\b",
    r"\benfoirés\b",
    r"\benfoirée\b",
    r"\bpétasse\b",
    r"\bpetasse\b",
    r"\bpouffiasse\b",
    r"\bpoufiasse\b",
    r"\btrou du cul\b",
    r"\btrou de cul\b",
    r"\bta gueule\b",
    r"\bferme ta gueule\b",
    r"\bgueule\b",
    r"\bva te faire\b",
    r"\bva te faire foutre\b",
    r"\bfils de pute\b",
    r"\bbâtard\b",
    r"\bbatard\b",
    r"\bbâtards\b",
    r"\bordure\b",  # vulgar insult
    # =====================================================
    # FRENCH INSULTS (MILDER BUT ABUSIVE) - Insultes
    # =====================================================
    r"\bbête\b",
    r"\bbete\b",
    r"\bbêtes\b",  # stupid
    r"\bidiot\b",
    r"\bidiote\b",
    r"\bidiots\b",
    r"\bidioties\b",
    r"\bimbécile\b",
    r"\bimbecile\b",
    r"\bimbéciles\b",
    r"\bstupide\b",
    r"\bstupides\b",
    r"\bstupidité\b",
    r"\bnul\b",
    r"\bnulle\b",
    r"\bnuls\b",
    r"\bnulles\b",
    r"\bnullité\b",
    r"\bdébile\b",
    r"\bdebile\b",
    r"\bdébiles\b",
    r"\bcrétin\b",
    r"\bcretin\b",
    r"\bcrétins\b",
    r"\bcrétine\b",
    r"\babruti\b",
    r"\babrutie\b",
    r"\babrutis\b",
    r"\bgourd\b",
    r"\bgourde\b",
    r"\bempote\b",
    r"\bempoté\b",
    r"\bempotée\b",
    r"\bnavet\b",  # insult meaning "talentless"
    r"\bnaze\b",
    r"\bnases\b",  # lame/worthless
    r"\bbouffon\b",
    r"\bbouffons\b",
    r"\bbouffonne\b",
    r"\bclown\b",  # when used as insult
    r"\bpauvre type\b",
    r"\bpauvre con\b",
    r"\bminable\b",
    r"\bminables\b",
    r"\blamentable\b",
    r"\bpathétique\b",
    r"\bpathetique\b",
    r"\bmoche\b",  # ugly
    r"\bgrosse\b",
    r"\bgros\b",  # fat (when insulting)
    r"\bmaigre\b",  # skinny (when insulting)
    r"\bperdant\b",
    r"\bperdante\b",  # loser
    r"\branafoux\b",
    r"\bringard\b",  # outdated/lame
    r"\btarée\b",
    r"\btare\b",
    r"\btaré\b",  # crazy/insane (pejorative)
    r"\bcinglé\b",
    r"\bcingle\b",
    r"\bcinglée\b",  # crazy
    r"\bfou\b",
    r"\bfolle\b",  # crazy (context-dependent)
    r"\bmalade\b",  # sick (when used as insult)
    r"\bje te déteste\b",
    r"\bje te deteste\b",  # I hate you
    r"\bje te hais\b",  # I hate you
    r"\btais-toi\b",
    r"\btais toi\b",  # shut up
    r"\bla ferme\b",  # shut up
    r"\bva mourir\b",
    r"\bcrève\b",
    r"\bcreve\b",  # go die
    r"\bsuicide\b",  # sensitive topic
    # =====================================================
    # EVASION PATTERNS (symbol substitution, spacing, etc.)
    # =====================================================
    # Repeated characters (fuuuck, shiiiit)
    r"\bf+u+c+k+\b",
    r"\bs+h+i+t+\b",
    r"\ba+s+s+\b",
    r"\bm+e+r+d+e+\b",
    r"\bp+u+t+a+i+n+\b",
    # Symbol substitution (f*ck, f@ck, sh!t)
    r"\bf[\*@#\$]ck\b",
    r"\bs[\*@#\$]t\b",
    r"\ba[\*@#\$\$]\b",
    r"\bb[\*@#]tch\b",
    r"\bc[\*@#]nt\b",
    # Spaced characters (f u c k, s h i t)
    r"\bf\s+u\s+c\s+k\b",
    r"\bs\s+h\s+i\s+t\b",
    r"\bm\s+e\s+r\s+d\s+e\b",
    r"\bp\s+u\s+t\s+a\s+i\s+n\b",
    r"\bc\s+o\s+n\b",
    r"\bb\s+i\s+t\s+e\b",
    # =====================================================
    # LEETSPEAK PATTERNS (SEC006 fix: "f4ck", "sh1t", etc.)
    # NOTE: HOMOGLYPH_MAP converts 4→a, but f4ck means fuck not fack
    # So we need explicit patterns for common leetspeak profanity
    # =====================================================
    # English leetspeak
    r"\bf[4a][ck]+\b",  # f4ck, fack, fuck variants
    r"\bf[uv][ck]+\b",  # fvck variant
    r"\bph[uv4][ck]+\b",  # phuck, ph4ck variants
    r"\bs[h#][1i!][t7]+\b",  # sh1t, sh!t variants
    r"\b[s5][h#][1i!][t7]+\b",  # 5hit variants
    r"\bb[1i!][t7]ch\b",  # b1tch, b!tch variants
    r"\b[a@4][s5][s5]\b",  # @ss, 4ss variants
    r"\bc[uv][n][t7]\b",  # cvnt variants
    r"\bd[1i!]ck\b",  # d1ck variants
    r"\bpr[1i!]ck\b",  # pr1ck variants
    # French leetspeak
    r"\bm[3e]rd[3e]\b",  # m3rde variants
    r"\bput[4a][1i]n\b",  # put4in, puta1n variants
    r"\bc[0o]n\b",  # c0n variant
    r"\b[s5][4a]l[0o]p[3e]\b",  # s4lope, 5alope variants
]
PROFANITY_PHRASES = [re.compile(p, re.IGNORECASE) for p in _PROFANITY_PHRASES_RAW]

# Homoglyph mapping (Cyrillic → Latin, etc.)
HOMOGLYPH_MAP = {
    # Cyrillic lookalikes
    "а": "a",
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "х": "x",
    "у": "y",
    "і": "i",
    "ј": "j",
    # Leetspeak
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "8": "b",
    "9": "g",
    # Accented variants
    "à": "a",
    "á": "a",
    "â": "a",
    "ã": "a",
    "ä": "a",
    "è": "e",
    "é": "e",
    "ê": "e",
    "ë": "e",
    "ì": "i",
    "í": "i",
    "î": "i",
    "ï": "i",
    "ò": "o",
    "ó": "o",
    "ô": "o",
    "õ": "o",
    "ö": "o",
    "ù": "u",
    "ú": "u",
    "û": "u",
    "ü": "u",
    "ū": "u",
}


def normalize_text_for_profanity(text: str) -> str:
    """Normalize text to detect Unicode/homoglyph evasions.

    This function:
    1. Converts to NFD Unicode normalization
    2. Replaces homoglyphs (Cyrillic, leetspeak, accents)
    3. Converts to lowercase

    Example:
        normalize_text_for_profanity("fück") → "fuck"
        normalize_text_for_profanity("fuсk") → "fuck" (Cyrillic 'с')
        normalize_text_for_profanity("f4ck") → "fack"

    Args:
        text: Input text to normalize

    Returns:
        Normalized text with homoglyphs replaced
    """
    # NFD normalization (decompose accented characters)
    normalized = unicodedata.normalize("NFD", text)

    # Remove combining diacritics (accents)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))

    # Replace homoglyphs
    for orig, repl in HOMOGLYPH_MAP.items():
        normalized = normalized.replace(orig, repl)

    # Lowercase
    normalized = normalized.lower()

    return normalized


def check_safety(query: str, session_id: Optional[str] = None) -> None:
    """Check if the query contains malicious patterns or toxic content.

    Enhanced with:
    - Unicode normalization to detect evasions (fück, fuсk, f4ck, f u c k)
    - Session blocking: blocks session after any security violation
    - Pre-check: rejects queries from already-blocked sessions

    Args:
        query: User input string
        session_id: Optional session identifier for blocking functionality

    Raises:
        SessionBlockedException: If session is already blocked
        SecurityException: If safety check fails (also blocks the session)
    """
    # ========================================
    # 0. CHECK IF SESSION IS ALREADY BLOCKED
    # ========================================
    if session_id:
        manager = get_blocked_session_manager()
        if manager.is_blocked(session_id):
            violation_count = manager.get_violation_count(session_id)
            logger.warning(
                f"[SECURITY] Blocked session attempted query: {session_id} " f"(violations: {violation_count})"
            )
            raise SessionBlockedException(BLOCKED_SESSION_MESSAGE)

    query_lower = query.lower()

    # Normalize for profanity detection (detect Unicode/homoglyph evasions)
    normalized_query = normalize_text_for_profanity(query)

    # ========================================
    # 1. CHECK FOR PROMPT INJECTION PATTERNS
    # ========================================
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(query_lower):
            logger.warning(f"Blocked malicious query (prompt injection): {query}")
            # Block the session
            if session_id:
                manager = get_blocked_session_manager()
                manager.block_session(session_id, reason="prompt_injection")
            raise SecurityException("Request rejected: Potential prompt injection detected.")

    # ========================================
    # 2. CHECK FOR PROFANITY PHRASES
    # ========================================
    for phrase_pattern in PROFANITY_PHRASES:
        if phrase_pattern.search(normalized_query):
            logger.warning(f"Blocked profanity query (phrase match): {query}")
            # Block the session
            if session_id:
                manager = get_blocked_session_manager()
                manager.block_session(session_id, reason="profanity")
            raise SecurityException(REFUSAL_MESSAGE)

    logger.debug("Query passed safety check.")
