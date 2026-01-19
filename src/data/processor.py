"""Advanced data processing and normalization for cultural events.
Follows strict production-grade rules:
1. UTF-8 preservation (no loss of French characters).
2. Boilerplate and technical junk removal.
3. Sentence deduplication.
4. Forced semantic classification (no 'Other').
"""

import logging
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any

from src.data.models import Event, EventLocation

logger = logging.getLogger(__name__)

class EventProcessor:
    """Production-grade processor for cultural event data."""

    # Blacklist of technical junk found in scraped/API data
    JUNK_PHRASES = [
        r"voir plus", r"lire la suite", r"plus d’informations", 
        r"inscription obligatoire", r"partager cet événement", r"cliquez ici", 
        r"powered by openagenda", r"cet événement est proposé par",
        r"les acceptez-vous", r"accepter", r"refuser", r"matomo",
        r"tous les événements", r"partager / exporter", r"outils d'inscription",
        r"s'inscrire / réserver", r"information additionnelle", r"aucune saisie",
        r"suggérer une modification"
    ]

    # Target category set for forced classification
    CATEGORIES = {
        "Musique": ["concert", "musique", "jazz", "opera", "récital", "chanson", "rock", "groove", "orchestre", "philharmonie"],
        "Théâtre / Spectacle": ["théâtre", "spectacle", "comédie", "tragédie", "scène", "pièce", "marionnettes", "mime", "cirque"],
        "Art / Exposition": ["exposition", "expo", "peinture", "sculpture", "galerie", "musée", "art", "vernissage", "photographie"],
        "Conférence / Débat": ["conférence", "débat", "rencontre", "littérature", "histoire", "colloque", "table ronde", "arpentage"],
        "Atelier / Workshop": ["atelier", "stage", "cours", "initiation", "formation", "masterclasse", "découverte"],
        "Sport / Loisirs": ["sport", "match", "compétition", "tournoi", "danse", "yoga", "parcours", "randonnée", "vtt"],
        "Jeunesse / Famille": ["jeunesse", "famille", "enfant", "scolaire", "bébé", "vacances", "jeune public", "kids"],
        "Festival": ["festival", "fête", "biennale", "salon"],
        "Patrimoine": ["patrimoine", "château", "visite guidée", "monument", "archives", "historique"],
        "Formation / Emploi": ["formation", "recrutement", "emploi", "métier", "entreprise", "job dating", "alternance", "jpo", "portes ouvertes"],
        "Vie associative": ["associative", "bénévolat", "quartier", "citoyenneté", "social", "solidarité"]
    }

    def safe_normalize(self, text: str | None) -> str:
        """Normalize unicode to NFC without losing French characters."""
        if not text: return ""
        # Convert to string if not already (e.g. lists)
        if isinstance(text, list):
            text = ", ".join(str(item) for item in text)
        
        # Unicode NFC normalization (é remains é)
        normalized = unicodedata.normalize('NFC', str(text))
        
        # Basic cleanup: remove double spaces, fix common punctuation spacing
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.replace(" .", ".").replace(" ,", ",").replace("( ", "(").replace(" )", ")")
        
        return normalized.strip()

    def remove_boilerplate(self, text: str) -> str:
        """Remove technical junk and repetitive boilerplate."""
        if not text: return ""
        
        cleaned = text
        for phrase in self.JUNK_PHRASES:
            cleaned = re.sub(phrase, "", cleaned, flags=re.IGNORECASE)
        
        # Remove URLs
        cleaned = re.sub(r'http\S+', '', cleaned)
        
        return cleaned.strip()

    def deduplicate_sentences(self, text: str) -> str:
        """Remove redundant sentences within a block of text."""
        if not text: return ""
        
        # Split into sentences (simple logic)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        seen = set()
        unique_sentences = []
        
        for s in sentences:
            s_clean = s.strip().lower()
            if s_clean and s_clean not in seen:
                seen.add(s_clean)
                unique_sentences.append(s.strip())
        
        return " ".join(unique_sentences)

    def clean_title(self, title: str) -> str:
        """Fix encoding, shouting, and trailing duplicates."""
        t = self.safe_normalize(title)
        # Fix shouting (ALL CAPS)
        if t.isupper():
            t = t.capitalize()
        # Remove emojis (common in titles)
        t = re.sub(r'[^\w\s,.;:!?\'"]', '', t) # Removed éèêëàâîïôùûçœæ-
        return t.strip()

    def clean_location(self, loc: EventLocation | None) -> EventLocation | None:
        """Standardize location and fix city naming."""
        if not loc: return None
        
        loc.city = self.safe_normalize(loc.city).title() if loc.city else None
        loc.address = self.safe_normalize(loc.address)
        
        # Remove city duplication in address if present
        if loc.address and loc.city and loc.city.lower() in loc.address.lower():
            # Only remove if it looks like a suffix duplication
            loc.address = re.sub(rf",\s*{loc.city}.*$", "", loc.address, flags=re.IGNORECASE).strip()
            
        return loc

    def clean_organizer(self, name: str | None) -> str | None:
        """Normalize name and remove technical noise."""
        if not name: return None
        n = self.safe_normalize(name)
        # Remove emails/phones
        n = re.sub(r'\S+@\S+', '', n)
        n = re.sub(r'\d{10,}', '', n)
        # Remove common legal suffixes
        n = re.sub(r'\b(SAS|SARL|EURL|ASSOCIATION)\b', '', n, flags=re.IGNORECASE)
        return n.strip() or None

    def classify_category(self, event: Event) -> str:
        """Forced semantic classification. Never returns 'Other'."""
        search_text = f"{event.title} {event.description or ''} {event.scraped_content or ''} {' '.join(event.tags)}".lower()
        
        best_cat = "Vie associative" # Robust fallback
        max_matches = -1
        
        for cat, keywords in self.CATEGORIES.items():
            matches = sum(1 for kw in keywords if kw in search_text)
            if matches > max_matches:
                max_matches = matches
                best_cat = cat
        
        return best_cat

    def process_record(self, record: dict[str, Any]) -> Event | None:
        """Process a raw record using the strict production pipeline."""
        try:
            fields = record if ("title_fr" in record or "uid" in record) else record.get("fields", {})
            
            # 1. Extraction with Basic Normalization
            event_id = record.get("uid") or record.get("slug") or record.get("recordid")
            if not event_id: return None

            title = self.clean_title(fields.get("title_fr") or fields.get("title") or "Sans titre")
            
            # 2. Description Handling (Merge API and Scraper if needed)
            api_desc = self.safe_normalize(fields.get("longdescription_fr") or fields.get("description_fr") or fields.get("description"))
            api_desc = self.remove_boilerplate(api_desc)
            if not api_desc:
                api_desc = None
            
            # Scraped content will be handled in separate enrichment step, 
            # but we define placeholders for the model here.
            
            # 3. Metadata Extraction
            age_min = fields.get("age_min")
            age_max = fields.get("age_max")
            
            acc = self.safe_normalize(fields.get("accessibility_label_fr") or fields.get("accessibility"))
            if acc and "voir site" in acc.lower(): acc = ""
            
            cond = self.safe_normalize(fields.get("conditions_fr") or fields.get("conditions"))
            cond = self.remove_boilerplate(cond)

            # 4. Location & Dates
            location = self.clean_location(self.extract_location(fields))
            
            # Standard Date Parsing (unchanged from legacy logic)
            start_date = self.parse_date(fields.get("firstdate_begin") or fields.get("start_date"))
            end_date = self.parse_date(fields.get("lastdate_end") or fields.get("firstdate_end") or fields.get("end_date"))

            # 5. Keywords
            tags = [self.safe_normalize(t).capitalize() for t in self.extract_tags(fields) if len(t) > 1]
            tags = list(set(tags))

            # Create Event Object
            event = Event(
                event_id=str(event_id),
                title=title,
                description=api_desc,
                category=self.safe_normalize(fields.get("category")),
                location=location,
                start_date=start_date,
                end_date=end_date,
                organizer=self.clean_organizer(fields.get("organizer") or fields.get("organisateur")),
                url=fields.get("canonicalurl") or fields.get("url") or fields.get("link"),
                image_url=fields.get("image") or fields.get("photo") or fields.get("image_url") ,
                tags=tags,
                raw_data=record,
                age_min=age_min,
                age_max=age_max,
                accessibility=acc or None,
                conditions=cond or None
            )

            # 6. Forced Classification
            event.category = self.classify_category(event)
            
            # 7. Final Polish of semantic fields
            if event.description:
                event.description = self.deduplicate_sentences(event.description)

            return event

        except Exception as e:
            logger.error(f"Error processing record {record.get('uid')}: {e}")
            return None

    # Helper methods (legacy compatibility or internal use)
    @staticmethod
    def parse_date(date_str: str | None) -> datetime | None:
        if not date_str: return None
        date_str_clean = date_str.split("+")[0].replace("Z", "") if ("+" in date_str or "Z" in date_str) else date_str
        formats = ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        for fmt in formats:
            try: return datetime.strptime(date_str_clean, fmt)
            except ValueError: continue
        return None

    @staticmethod
    def extract_location(fields: dict[str, Any]) -> EventLocation | None:
        location_data = {}
        if addr := (fields.get("location_address") or fields.get("address") or fields.get("address_fr") ): location_data["address"] = addr
        if city := (fields.get("location_city") or fields.get("city") or fields.get("ville") or fields.get("ville_fr") ): location_data["city"] = city
        if pc := (fields.get("location_postalcode") or fields.get("postal_code") or fields.get("code_postal") ): location_data["postal_code"] = pc
        
        coords = fields.get("location_coordinates") or fields.get("coordinates") or fields.get("geo_point_2d")
        if coords:
            if isinstance(coords, dict) and "lat" in coords and "lon" in coords:
                location_data["coordinates"] = {"lat": coords["lat"], "lon": coords["lon"]}
            elif isinstance(coords, list) and len(coords) >= 2:
                # Some APIs use [lat, lon], some [lon, lat]. Standardize here.
                # Assuming [lat, lon] if not specified, but check test expectations.
                # test_extract_location uses {"lat": 48.8656, "lon": 2.3212}
                location_data["coordinates"] = {"lat": coords[0], "lon": coords[1]}
                
        if not location_data: return None
        return EventLocation(**location_data)

    @staticmethod
    def extract_tags(fields: dict[str, Any]) -> list[str]:
        tags = []
        for field in ["keywords_fr", "keywords", "tags", "mots_cles"]:
            if value := fields.get(field):
                if isinstance(value, list): tags.extend(str(tag) for tag in value)
                elif isinstance(value, str): tags.extend(tag.strip() for tag in value.split(","))
        return list(set(tags))

    def process_records(self, records: list[dict[str, Any]]) -> list[Event]:
        events = []
        for record in records:
            if event := self.process_record(record): events.append(event)
        return events

    def filter_paris_events(self, events: list[Event]) -> list[Event]:
        """Filter events that take place in Paris."""
        return [
            e for e in events 
            if e.location and e.location.city and "paris" in e.location.city.lower()
        ]

    def filter_by_date_range(
        self, 
        events: list[Event], 
        start_date: datetime, 
        end_date: datetime
    ) -> list[Event]:
        """Filter events within a specific date range."""
        return [
            e for e in events 
            if e.start_date and start_date <= e.start_date <= end_date
        ]

    def filter_ile_de_france_events(self, events: list[Event]) -> list[Event]:
        idf_postal_prefixes = {"75", "77", "78", "91", "92", "93", "94", "95"}
        return [e for e in events if e.location and e.location.postal_code and e.location.postal_code[:2] in idf_postal_prefixes]

    def redistribute_events_seasonally(self, events: list[Event], start_date: datetime | None = None) -> list[Event]:
        if start_date is None: start_date = datetime.now()
        for event in events:
            if not event.start_date: continue
            duration = (event.end_date - event.start_date) if event.end_date else timedelta(hours=2)
            try:
                candidate = event.start_date.replace(year=start_date.year)
                if candidate < start_date: candidate = candidate.replace(year=start_date.year + 1)
                event.start_date, event.end_date = candidate, candidate + duration
            except ValueError: pass # Leap year
        return events