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
        r"suggérer une modification", r"Catalogues départementaux", r"Catalogue national",
        r"structures d’accueil", r"hébergement", r"Plan du site", r"Mentions légales"
    ]

    # Target category set for forced classification
    CATEGORIES = {
        "Musique": ["concert", "musique", "jazz", "opera", "récital", "chanson", "rock", "groove", "orchestre", "philharmonie"],
        "Théâtre / Spectacle": ["théâtre", "spectacle", "comédie", "tragédie", "scène", "pièce", "marionnettes", "mime", "cirque"],
        "Art / Exposition": ["exposition", "expo", "peinture", "sculpture", "galerie", "musée", "art", "vernissage", "photographie"],
        "Danse": ["danse", "dance", "ballet", "hip-hop", "contemporain", "chorégraphie", "ballerine", "spectacle de danse"],
        "Conférence / Débat": ["conférence", "débat", "rencontre", "littérature", "histoire", "colloque", "table ronde", "arpentage"],
        "Atelier / Workshop": ["atelier", "stage", "cours", "initiation", "formation", "masterclasse", "découverte"],
        "Sport / Loisirs": ["sport", "match", "compétition", "tournoi", "yoga", "parcours", "randonnée", "vtt"],
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

    def parse_date(self, date_str: str | None) -> datetime | None:
        """Parse ISO 8601 date string."""
        if not date_str:
            return None
        try:
            # Clean potential debris
            clean_str = str(date_str).strip()
            # Handle Z suffix
            if clean_str.endswith("Z"):
                clean_str = clean_str[:-1] + "+00:00"
            return datetime.fromisoformat(clean_str)
        except Exception:
            return None

    def extract_location(self, fields: dict[str, Any]) -> EventLocation | None:
        """Extract location from record fields."""
        if not fields:
            return None
            
        # Coordinates
        lat = fields.get("latitude") or fields.get("lat")
        lon = fields.get("longitude") or fields.get("lon")
        
        # Opendatasoft geom structure
        geo = fields.get("geometry") or fields.get("location_coordinates")
        if geo and isinstance(geo, dict) and "coordinates" in geo:
            try:
                lon, lat = geo["coordinates"]
            except (ValueError, TypeError):
                pass
            
        coords = None
        if lat and lon:
            try:
                coords = {"lat": float(lat), "lon": float(lon)}
            except (ValueError, TypeError):
                pass
        
        return EventLocation(
            city=fields.get("location_city") or fields.get("city"),
            postal_code=fields.get("location_postalcode") or fields.get("postal_code"),
            address=fields.get("location_address") or fields.get("address"),
            coordinates=coords
        )

    def extract_tags(self, fields: dict[str, Any]) -> list[str]:
        """Extract keywords/tags."""
        tags = fields.get("keywords_fr") or fields.get("tags") or []
        if isinstance(tags, str):
            tags = tags.split(",")
        return [str(t).strip() for t in tags if str(t).strip()]

    def process_record(self, record: dict[str, Any]) -> list[Event]:
        """Process a raw record into one or more granular Event objects (one per timing)."""
        try:
            fields = record if ("title_fr" in record or "uid" in record) else record.get("fields", {})
            
            # 1. Extraction with Basic Normalization
            base_event_id = record.get("uid") or record.get("slug") or record.get("recordid")
            if not base_event_id: return []

            title = self.clean_title(fields.get("title_fr") or fields.get("title") or "Sans titre")
            
            # 2. Description Handling
            api_desc = self.safe_normalize(fields.get("longdescription_fr") or fields.get("description_fr") or fields.get("description"))
            api_desc = self.remove_boilerplate(api_desc)
            if not api_desc:
                api_desc = None
            
            # 3. Metadata Extraction
            age_min = fields.get("age_min")
            age_max = fields.get("age_max")
            
            acc = self.safe_normalize(fields.get("accessibility_label_fr") or fields.get("accessibility"))
            if acc and "voir site" in acc.lower(): acc = ""
            
            cond = self.safe_normalize(fields.get("conditions_fr") or fields.get("conditions"))
            cond = self.remove_boilerplate(cond)

            # 4. Location
            location = self.clean_location(self.extract_location(fields))
            
            # 5. Keywords
            tags = [self.safe_normalize(t).capitalize() for t in self.extract_tags(fields) if len(t) > 1]
            tags = list(set(tags))

            # 6. Parse Timings
            import json
            raw_timings = fields.get("timings")
            parsed_timings = []
            if isinstance(raw_timings, str):
                try:
                    parsed_timings = json.loads(raw_timings)
                except Exception:
                    pass
            elif isinstance(raw_timings, list):
                parsed_timings = raw_timings

            # If no timings found, use firstdate_begin/lastdate_end as fallback
            if not parsed_timings:
                start_date = self.parse_date(fields.get("firstdate_begin") or fields.get("start_date"))
                end_date = self.parse_date(fields.get("lastdate_end") or fields.get("firstdate_end") or fields.get("end_date"))
                parsed_timings = [{"begin": start_date.isoformat() if start_date else None, 
                                   "end": end_date.isoformat() if end_date else None}]

            # 7. Create Granular Event Objects
            granular_events = []
            for idx, timing in enumerate(parsed_timings):
                start_dt = self.parse_date(timing.get("begin"))
                end_dt = self.parse_date(timing.get("end"))
                
                # Skip if no start date
                if not start_dt:
                    continue

                # Augment event_id for uniqueness
                granular_id = f"{base_event_id}_{idx}"
                
                event = Event(
                    event_id=granular_id,
                    title=title,
                    description=api_desc,
                    category=self.safe_normalize(fields.get("category")),
                    location=location,
                    start_date=start_dt,
                    end_date=end_dt,
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

                # Forced Classification
                event.category = self.classify_category(event)
                
                # Final Polish
                if event.description:
                    event.description = self.deduplicate_sentences(event.description)
                
                granular_events.append(event)

            return granular_events

        except Exception as e:
            logger.error(f"Error processing record {record.get('uid')}: {e}")
            return []

    def _classify_period(self, hour: int) -> str:
        """Classify time into period of day."""
        if hour < 12:
            return "matin"
        elif hour < 18:
            return "après-midi"
        else:
            return "soir"

    def deduplicate_events(self, events: list[Event]) -> list[Event]:
        """Deduplicate events by (title, city, date) and merge timings.

        Events occurring at multiple times on the same day are consolidated
        into a single Event with timings, periods, and is_full_day populated.
        """
        from collections import defaultdict

        # Group events by (normalized_title, city, date_only)
        groups: dict[tuple, list[Event]] = defaultdict(list)

        for event in events:
            city = event.location.city if event.location else "Unknown"
            date_str = event.start_date.strftime("%Y-%m-%d") if event.start_date else "NoDate"
            # Normalize title for robust comparison
            norm_title = "".join(filter(str.isalnum, event.title)).lower()

            key = (norm_title, city, date_str)
            groups[key].append(event)

        # Merge each group
        unique_events = []
        for key, group in groups.items():
            if len(group) == 1:
                # Single event - extract time if available
                event = group[0]
                if event.start_date:
                    time_str = event.start_date.strftime("%H:%M")
                    if time_str != "00:00":  # Not midnight (likely full day)
                        event.timings = [time_str]
                        period = self._classify_period(event.start_date.hour)
                        event.periods = [period]
                        # Set period flags
                        event.has_morning = (period == "matin")
                        event.has_afternoon = (period == "après-midi")
                        event.has_evening = (period == "soir")
                    else:
                        event.is_full_day = True
                        # Full day events are available all periods
                        event.has_morning = True
                        event.has_afternoon = True
                        event.has_evening = True
                unique_events.append(event)
            else:
                # Multiple events - merge timings
                # Keep the earliest event as primary
                group.sort(key=lambda e: e.start_date if e.start_date else datetime.max)
                primary = group[0]

                # Collect all unique times
                all_times = set()
                all_periods = set()

                for evt in group:
                    if evt.start_date:
                        time_str = evt.start_date.strftime("%H:%M")
                        if time_str != "00:00":
                            all_times.add(time_str)
                            all_periods.add(self._classify_period(evt.start_date.hour))

                if all_times:
                    primary.timings = sorted(all_times)
                    primary.periods = sorted(all_periods)
                    primary.is_full_day = False
                    # Set period flags based on collected periods
                    primary.has_morning = ("matin" in all_periods)
                    primary.has_afternoon = ("après-midi" in all_periods)
                    primary.has_evening = ("soir" in all_periods)
                else:
                    primary.is_full_day = True
                    # Full day events are available all periods
                    primary.has_morning = True
                    primary.has_afternoon = True
                    primary.has_evening = True

                # Merge conditions (keep longest)
                for evt in group[1:]:
                    if evt.conditions and len(evt.conditions) > len(primary.conditions or ""):
                        primary.conditions = evt.conditions

                unique_events.append(primary)

        logger.info(f"Deduplication: {len(events)} -> {len(unique_events)} events (merged {len(events) - len(unique_events)} same-day duplicates)")
        return unique_events

    def process_records(self, records: list[dict[str, Any]]) -> list[Event]:
        """Process multiple records and return a deduplicated list of granular Event objects."""
        all_granular_events = []
        for record in records:
            granular_events = self.process_record(record)
            all_granular_events.extend(granular_events)
        
        # Apply final deduplication across all records
        return self.deduplicate_events(all_granular_events)

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