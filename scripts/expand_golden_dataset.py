"""Expand golden dataset from 50 to 100 queries with more complex test cases."""

import logging
from src.evaluation.datasets.golden_dataset import GoldenDataset, Query, GenerationExpectations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Complex test cases to add
NEW_QUERIES = [
    # Multi-criteria searches (complex filters)
    Query(
        id="Q051",
        query="Expositions d'art contemporain gratuites et accessibles PMR à Paris en mars",
        language="fr",
        query_type="metadata_heavy",
        complexity="high",
        expected_entities=["art", "contemporain", "exposition"],
        expected_categories=["Art"],
        expected_filters={"city": "Paris", "month": 3, "price": 0, "accessibility": ["wheelchair"]},
        generation_expectations=GenerationExpectations(
            must_contain_keywords=["exposition", "art"], expected_language="fr"
        ),
    ),
    Query(
        id="Q052",
        query="Concerts classiques pour enfants de 6-12 ans le week-end dans le 75",
        language="fr",
        query_type="metadata_heavy",
        complexity="high",
        expected_entities=["concert", "classique", "enfants"],
        expected_categories=["Musique"],
        expected_filters={"city": "Paris", "age_min": 6, "age_max": 12},
        generation_expectations=GenerationExpectations(
            must_contain_keywords=["concert", "enfants"], expected_language="fr"
        ),
    ),
    # Temporal complexity
    Query(
        id="Q053",
        query="Quels événements culturels ont lieu le premier weekend de février 2026?",
        language="fr",
        query_type="temporal_complex",
        complexity="high",
        expected_entities=[],
        expected_categories=[],
        expected_filters={"month": 2, "year": 2026},
        generation_expectations=GenerationExpectations(must_contain_keywords=["février"], expected_language="fr"),
    ),
    Query(
        id="Q054",
        query="Shows running from mid-January to end of February in Versailles",
        language="en",
        query_type="temporal_complex",
        complexity="high",
        expected_entities=["shows"],
        expected_categories=[],
        expected_filters={"city": "Versailles", "month": 1},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="en"),
    ),
    Query(
        id="Q055",
        query="Événements nocturnes après 20h dans le Marais",
        language="fr",
        query_type="temporal_complex",
        complexity="medium",
        expected_entities=["nocturne", "soir"],
        expected_categories=[],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["Marais"], expected_language="fr"),
    ),
    # Geographic complexity
    Query(
        id="Q056",
        query="Cultural events in suburbs near Gare du Nord accessible by metro",
        language="en",
        query_type="geographic_complex",
        complexity="high",
        expected_entities=["cultural", "events"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="en"),
    ),
    Query(
        id="Q057",
        query="Festivals en plein air dans les parcs de l'ouest parisien",
        language="fr",
        query_type="geographic_complex",
        complexity="high",
        expected_entities=["festival", "plein air", "parc"],
        expected_categories=[],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(
            must_contain_keywords=["festival", "parc"], expected_language="fr"
        ),
    ),
    Query(
        id="Q058",
        query="Museums and exhibitions within walking distance of Louvre",
        language="en",
        query_type="geographic_complex",
        complexity="medium",
        expected_entities=["museum", "exhibition", "Louvre"],
        expected_categories=["Art"],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["museum"], expected_language="en"),
    ),
    # Multi-language and cultural nuance
    Query(
        id="Q059",
        query="Spectacles bilingues français-anglais pour familles internationales",
        language="fr",
        query_type="language_mix",
        complexity="high",
        expected_entities=["spectacle", "bilingue"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["bilingue"], expected_language="fr"),
    ),
    Query(
        id="Q060",
        query="Traditional Japanese cultural events or tea ceremonies in Paris",
        language="en",
        query_type="entity_specific",
        complexity="medium",
        expected_entities=["Japanese", "Japan", "tea ceremony"],
        expected_categories=["Culture"],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["Japan"], expected_language="en"),
    ),
    # Negation and exclusion
    Query(
        id="Q061",
        query="Concerts NOT jazz or classical, something modern and experimental",
        language="en",
        query_type="negation",
        complexity="high",
        expected_entities=["concert", "modern", "experimental"],
        expected_categories=["Musique"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["concert"], expected_language="en"),
    ),
    Query(
        id="Q062",
        query="Événements culturels sans réservation obligatoire, entrée libre",
        language="fr",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["entrée libre", "gratuit"],
        expected_categories=[],
        expected_filters={"price": 0},
        generation_expectations=GenerationExpectations(must_contain_keywords=["gratuit"], expected_language="fr"),
    ),
    # Comparative and ranking
    Query(
        id="Q063",
        query="Top 5 most popular art exhibitions this month based on attendance",
        language="en",
        query_type="ranking",
        complexity="high",
        expected_entities=["art", "exhibition"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["exhibition"], expected_language="en"),
    ),
    Query(
        id="Q064",
        query="Comparez les théâtres dans le 9ème arrondissement: programmation, tarifs, accessibilité",
        language="fr",
        query_type="comparison",
        complexity="high",
        expected_entities=["théâtre"],
        expected_categories=["Théâtre"],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["théâtre"], expected_language="fr"),
    ),
    # Conditional and hypothetical
    Query(
        id="Q065",
        query="If it rains this weekend, what indoor cultural activities are available in Paris?",
        language="en",
        query_type="conditional",
        complexity="medium",
        expected_entities=["indoor", "cultural"],
        expected_categories=[],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["indoor"], expected_language="en"),
    ),
    Query(
        id="Q066",
        query="Activités culturelles adaptées en cas de canicule (climatisé, frais)",
        language="fr",
        query_type="conditional",
        complexity="medium",
        expected_entities=["climatisé", "intérieur"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="fr"),
    ),
    # Combined entity types
    Query(
        id="Q067",
        query="Workshops or masterclasses by renowned artists visiting from abroad",
        language="en",
        query_type="entity_specific",
        complexity="high",
        expected_entities=["workshop", "masterclass", "artist"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["workshop"], expected_language="en"),
    ),
    Query(
        id="Q068",
        query="Rencontres avec auteurs et dédicaces dans les librairies indépendantes",
        language="fr",
        query_type="entity_specific",
        complexity="medium",
        expected_entities=["auteur", "dédicace", "librairie"],
        expected_categories=["Littérature"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["auteur"], expected_language="fr"),
    ),
    # Budget-conscious queries
    Query(
        id="Q069",
        query="Free or under 10€ cultural events suitable for students in February",
        language="en",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["free", "cheap", "student"],
        expected_categories=[],
        expected_filters={"month": 2},
        generation_expectations=GenerationExpectations(must_contain_keywords=["free"], expected_language="en"),
    ),
    Query(
        id="Q070",
        query="Tarif réduit pour demandeurs d'emploi dans les musées parisiens",
        language="fr",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["tarif réduit", "musée"],
        expected_categories=["Art"],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["musée"], expected_language="fr"),
    ),
    # Follow-up and conversational
    Query(
        id="Q071",
        query="Tell me more about the first event you mentioned",
        language="en",
        query_type="follow_up",
        complexity="high",
        expected_entities=[],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="en"),
    ),
    Query(
        id="Q072",
        query="Donne-moi des alternatives si le concert est complet",
        language="fr",
        query_type="follow_up",
        complexity="medium",
        expected_entities=["concert", "alternative"],
        expected_categories=["Musique"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["concert"], expected_language="fr"),
    ),
    # Ambiguous or underspecified
    Query(
        id="Q073",
        query="Something interesting this weekend",
        language="en",
        query_type="vague",
        complexity="high",
        expected_entities=[],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="en"),
    ),
    Query(
        id="Q074",
        query="Ça existe des trucs culturels pour ce soir?",
        language="fr",
        query_type="vague",
        complexity="medium",
        expected_entities=["culturel", "soir"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="fr"),
    ),
    # Technical and format-specific
    Query(
        id="Q075",
        query="VR or immersive digital art experiences in Île-de-France",
        language="en",
        query_type="entity_specific",
        complexity="medium",
        expected_entities=["VR", "digital", "immersive"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["digital"], expected_language="en"),
    ),
    Query(
        id="Q076",
        query="Projections cinéma en plein air ou sur rooftop cet été",
        language="fr",
        query_type="temporal_complex",
        complexity="medium",
        expected_entities=["cinéma", "plein air", "rooftop"],
        expected_categories=["Cinéma"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["cinéma"], expected_language="fr"),
    ),
    # Accessibility-focused (important for inclusivity)
    Query(
        id="Q077",
        query="Events with sign language interpretation for deaf community",
        language="en",
        query_type="metadata_heavy",
        complexity="high",
        expected_entities=["sign language", "deaf", "accessible"],
        expected_categories=[],
        expected_filters={"accessibility": ["sign_language"]},
        generation_expectations=GenerationExpectations(must_contain_keywords=["sign"], expected_language="en"),
    ),
    Query(
        id="Q078",
        query="Spectacles avec audiodescription pour personnes malvoyantes",
        language="fr",
        query_type="metadata_heavy",
        complexity="high",
        expected_entities=["audiodescription", "malvoyant"],
        expected_categories=[],
        expected_filters={"accessibility": ["audio_description"]},
        generation_expectations=GenerationExpectations(
            must_contain_keywords=["audiodescription"], expected_language="fr"
        ),
    ),
    # Age-specific beyond children
    Query(
        id="Q079",
        query="Senior-friendly cultural activities with seating and nearby parking",
        language="en",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["senior", "elderly"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=[], expected_language="en"),
    ),
    Query(
        id="Q080",
        query="Activités pour adolescents 13-17 ans sans parents",
        language="fr",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["adolescent", "jeune"],
        expected_categories=[],
        expected_filters={"age_min": 13, "age_max": 17},
        generation_expectations=GenerationExpectations(must_contain_keywords=["adolescent"], expected_language="fr"),
    ),
    # Genre-specific music
    Query(
        id="Q081",
        query="Electronic music festivals or techno clubs in Paris suburbs",
        language="en",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["electronic", "techno", "festival"],
        expected_categories=["Musique"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["electronic"], expected_language="en"),
    ),
    Query(
        id="Q082",
        query="Concerts de musique du monde: africaine, latino, orientale",
        language="fr",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["musique du monde", "africaine", "latino"],
        expected_categories=["Musique"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["musique"], expected_language="fr"),
    ),
    # Art movements and periods
    Query(
        id="Q083",
        query="Impressionist or post-impressionist art exhibitions currently showing",
        language="en",
        query_type="entity_specific",
        complexity="medium",
        expected_entities=["impressionist", "art", "exhibition"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["impressionist"], expected_language="en"),
    ),
    Query(
        id="Q084",
        query="Expositions d'art moderne et contemporain du XXe siècle",
        language="fr",
        query_type="entity_specific",
        complexity="medium",
        expected_entities=["art moderne", "contemporain", "exposition"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(
            must_contain_keywords=["art", "exposition"], expected_language="fr"
        ),
    ),
    # Performance types
    Query(
        id="Q085",
        query="Street performances, buskers, or free outdoor shows in Montmartre",
        language="en",
        query_type="geographic_complex",
        complexity="medium",
        expected_entities=["street", "outdoor", "Montmartre"],
        expected_categories=[],
        expected_filters={"city": "Paris"},
        generation_expectations=GenerationExpectations(must_contain_keywords=["Montmartre"], expected_language="en"),
    ),
    Query(
        id="Q086",
        query="Spectacles de danse contemporaine ou ballet classique",
        language="fr",
        query_type="simple_search",
        complexity="low",
        expected_entities=["danse", "contemporaine", "ballet"],
        expected_categories=["Danse"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["danse"], expected_language="fr"),
    ),
    # Educational and workshops
    Query(
        id="Q087",
        query="Photography workshops or courses for beginners in February",
        language="en",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["photography", "workshop", "course"],
        expected_categories=[],
        expected_filters={"month": 2},
        generation_expectations=GenerationExpectations(must_contain_keywords=["photography"], expected_language="en"),
    ),
    Query(
        id="Q088",
        query="Ateliers d'écriture créative ou cours de théâtre amateur",
        language="fr",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["atelier", "écriture", "théâtre"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["atelier"], expected_language="fr"),
    ),
    # Historical and heritage
    Query(
        id="Q089",
        query="Guided tours of historical monuments with English commentary",
        language="en",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["guided tour", "historical", "monument"],
        expected_categories=["Culture"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["tour"], expected_language="en"),
    ),
    Query(
        id="Q090",
        query="Visites guidées patrimoine industriel ou architecture haussmannienne",
        language="fr",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["visite", "patrimoine", "architecture"],
        expected_categories=["Culture"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["visite"], expected_language="fr"),
    ),
    # Seasonal and thematic
    Query(
        id="Q091",
        query="Valentine's Day romantic events: candlelit concerts or couple activities",
        language="en",
        query_type="temporal_complex",
        complexity="medium",
        expected_entities=["Valentine", "romantic", "concert"],
        expected_categories=[],
        expected_filters={"month": 2},
        generation_expectations=GenerationExpectations(must_contain_keywords=["Valentine"], expected_language="en"),
    ),
    Query(
        id="Q092",
        query="Événements pour la Journée Internationale de la Femme (8 mars)",
        language="fr",
        query_type="temporal_complex",
        complexity="medium",
        expected_entities=["Journée de la Femme", "8 mars"],
        expected_categories=[],
        expected_filters={"month": 3},
        generation_expectations=GenerationExpectations(must_contain_keywords=["femme"], expected_language="fr"),
    ),
    # Food and culture combination
    Query(
        id="Q093",
        query="Cultural events with food tastings or wine pairings included",
        language="en",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["food", "tasting", "wine"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["food"], expected_language="en"),
    ),
    Query(
        id="Q094",
        query="Festivals gastronomiques ou marchés culturels avec artisanat local",
        language="fr",
        query_type="simple_search",
        complexity="medium",
        expected_entities=["gastronomique", "festival", "marché"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["festival"], expected_language="fr"),
    ),
    # Night-time specific
    Query(
        id="Q095",
        query="Nuit Blanche or other all-night cultural events in October",
        language="en",
        query_type="entity_specific",
        complexity="medium",
        expected_entities=["Nuit Blanche", "night", "nocturne"],
        expected_categories=[],
        expected_filters={"month": 10},
        generation_expectations=GenerationExpectations(must_contain_keywords=["night"], expected_language="en"),
    ),
    Query(
        id="Q096",
        query="Soirées culturelles ou nocturnes des musées première semaine du mois",
        language="fr",
        query_type="temporal_complex",
        complexity="high",
        expected_entities=["soirée", "nocturne", "musée"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["musée"], expected_language="fr"),
    ),
    # Pet-friendly
    Query(
        id="Q097",
        query="Dog-friendly outdoor cultural events or exhibitions allowing pets",
        language="en",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["dog", "pet", "outdoor"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["dog"], expected_language="en"),
    ),
    Query(
        id="Q098",
        query="Événements acceptant les animaux de compagnie en extérieur",
        language="fr",
        query_type="metadata_heavy",
        complexity="medium",
        expected_entities=["animaux", "extérieur"],
        expected_categories=[],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["animaux"], expected_language="fr"),
    ),
    # Emerging/trending
    Query(
        id="Q099",
        query="NFT exhibitions, crypto art, or blockchain cultural events",
        language="en",
        query_type="entity_specific",
        complexity="high",
        expected_entities=["NFT", "crypto", "blockchain", "digital art"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(must_contain_keywords=["NFT"], expected_language="en"),
    ),
    Query(
        id="Q100",
        query="Intelligence artificielle et art: expositions sur l'art génératif ou IA créative",
        language="fr",
        query_type="entity_specific",
        complexity="high",
        expected_entities=["intelligence artificielle", "IA", "art génératif"],
        expected_categories=["Art"],
        expected_filters={},
        generation_expectations=GenerationExpectations(
            must_contain_keywords=["intelligence", "artificielle"], expected_language="fr"
        ),
    ),
]


def main():
    logger.info("Loading existing golden dataset...")
    dataset = GoldenDataset.load("data/evaluation/golden_dataset.json")

    current_count = len(dataset.queries)
    logger.info(f"Current dataset size: {current_count} queries")

    logger.info(f"Adding {len(NEW_QUERIES)} new complex queries...")
    dataset.queries.extend(NEW_QUERIES)

    logger.info(f"New dataset size: {len(dataset.queries)} queries")
    dataset.save("data/evaluation/golden_dataset.json")

    logger.info("✓ Dataset expansion complete!")
    logger.info(f"  - Added: {len(NEW_QUERIES)} complex queries")
    logger.info(f"  - Total: {len(dataset.queries)} queries")
    logger.info("  - Complexity breakdown:")

    complexity_counts = {}
    for q in dataset.queries:
        complexity_counts[q.complexity] = complexity_counts.get(q.complexity, 0) + 1

    for complexity, count in sorted(complexity_counts.items()):
        logger.info(f"    - {complexity}: {count} queries")


if __name__ == "__main__":
    main()
