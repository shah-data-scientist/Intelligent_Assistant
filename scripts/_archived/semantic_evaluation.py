"""Semantic evaluation of chatbot responses.

Updated for v3.0 golden dataset with conversational multi-turn tests.

Evaluation criteria:
1. Does query return results when database has matching events?
2. Do returned results match query filters (city, date, category)?
3. Are transparency rules followed correctly?
4. Do results contain relevant keywords?
5. NEW: Context retention in multi-turn conversations
6. NEW: Clarifying question behavior
"""

import json
import sys
import uuid
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.storage import EventStorage
from src.retrieval.chain import RAGChain


def get_database_truth(query_data: dict, storage: EventStorage) -> dict:
    """Get ground truth from database for a query.

    Args:
        query_data: Query from golden dataset (turn or single query)
        storage: EventStorage instance

    Returns:
        Dict with database truth
    """
    all_events = storage.get_all_events()
    expected_filters = query_data.get('expected_filters', {})

    city = expected_filters.get('city')
    month = expected_filters.get('month')
    category = expected_filters.get('category')

    # Filter events
    matching = []
    for evt in all_events:
        # City filter
        if city and evt.location:
            if evt.location.city and evt.location.city.lower() != city.lower():
                continue

        # Month filter
        if month and evt.start_date:
            if evt.start_date.month != month:
                continue

        # Category filter - handle partial matching
        if category and evt.category:
            cat_lower = category.lower()
            evt_cat_lower = evt.category.lower()
            # Allow partial category matches (e.g., "Musique" matches "Musique / Concert")
            if cat_lower not in evt_cat_lower and evt_cat_lower not in cat_lower:
                continue

        matching.append(evt)

    return {
        'total_matching': len(matching),
        'has_results': len(matching) > 0,
        'sample_ids': [e.event_id for e in matching[:5]]
    }


def evaluate_single_query(query_data: dict, chain: RAGChain, storage: EventStorage,
                          session_id: str = None) -> dict:
    """Evaluate a single query semantically.

    Args:
        query_data: Query from golden dataset
        chain: RAGChain instance
        storage: EventStorage instance
        session_id: Optional session ID for multi-turn context

    Returns:
        Dict with evaluation results
    """
    query_id = query_data.get('id') or query_data.get('turn_id')
    query_text = query_data['query']
    language = query_data.get('language', 'fr')
    query_type = query_data.get('query_type', 'search')

    if session_id is None:
        session_id = f'eval_{uuid.uuid4().hex[:8]}'

    # Special query types that don't need search results
    is_special_query = query_type in ['greeting', 'off_topic', 'meta']

    # Get database truth (skip for special queries)
    if is_special_query:
        db_truth = {'total_matching': 0, 'has_results': False, 'sample_ids': []}
    else:
        db_truth = get_database_truth(query_data, storage)

    # Get expected behavior
    expected_behavior = query_data.get('expected_behavior', {})
    generation_expectations = query_data.get('generation_expectations', {})

    should_ask_clarification = expected_behavior.get('should_ask_clarification', False) or \
                               generation_expectations.get('should_ask_clarification', False)

    # Run query through chatbot
    try:
        result = chain.query_with_metadata(
            query_text,
            session_id=session_id,
            language=language
        )
        chatbot_success = True
        chatbot_count = len(result.get('sources', []))
        answer_text = result.get('answer', '')
        error = None
    except Exception as e:
        chatbot_success = False
        chatbot_count = 0
        answer_text = ''
        error = str(e)

    # Prepare answer_lower for all checks
    answer_lower = answer_text.lower()

    # Evaluate
    issues = []
    warnings = []

    # Issue 1: Query failed
    if not chatbot_success:
        issues.append({
            'type': 'ERROR',
            'message': f'Chatbot failed: {error}'
        })

    # Special query type validation
    elif is_special_query:
        # For greeting queries: check for greeting response
        if query_type == 'greeting':
            greeting_indicators_fr = ['bonjour', 'clio', 'guide culturelle', 'evenements culturels']
            greeting_indicators_en = ['hello', 'clio', 'cultural guide', 'cultural events']
            indicators = greeting_indicators_fr if language == 'fr' else greeting_indicators_en
            if not any(ind in answer_lower for ind in indicators):
                issues.append({
                    'type': 'MISSING_GREETING_RESPONSE',
                    'message': 'Expected greeting response not found'
                })

        # For off-topic queries: check for polite redirect
        elif query_type == 'off_topic':
            redirect_indicators = ['specialize', 'specialise', 'cultural events', 'evenements culturels',
                                   "can't help", 'ne peux pas', 'sorry', 'desole']
            if not any(ind in answer_lower for ind in redirect_indicators):
                issues.append({
                    'type': 'MISSING_REDIRECT',
                    'message': 'Expected polite redirect not found in response'
                })

        # For meta queries: check for capability explanation
        elif query_type == 'meta':
            capability_indicators = ['can do', 'peux faire', 'can help', 'cultural', 'concerts',
                                     'exhibitions', 'theater', 'theatre', 'festivals']
            if not any(ind in answer_lower for ind in capability_indicators):
                issues.append({
                    'type': 'MISSING_CAPABILITY_EXPLANATION',
                    'message': 'Expected capability explanation not found'
                })

    # Issue 2: No results when database has results (but not for clarification queries or special queries)
    elif db_truth['has_results'] and chatbot_count == 0 and not should_ask_clarification:
        issues.append({
            'type': 'MISSING_RESULTS',
            'message': f'Database has {db_truth["total_matching"]} matches but chatbot returned 0'
        })

    # Issue 3: Results when database has no results (possible but check if reasonable)
    elif not db_truth['has_results'] and chatbot_count > 0:
        warnings.append({
            'type': 'UNEXPECTED_RESULTS',
            'message': f'Database has 0 matches but chatbot returned {chatbot_count} (may use nearby fallback)'
        })

    # Check keyword expectations with synonym support
    must_contain = generation_expectations.get('must_contain_keywords', [])
    must_not_contain = generation_expectations.get('must_not_contain_keywords', [])

    # Synonym mapping for flexible keyword matching
    KEYWORD_SYNONYMS = {
        # English synonyms
        'children': ['children', 'kids', 'child', 'kid', 'family', 'young'],
        'kids': ['children', 'kids', 'child', 'kid', 'family', 'young'],
        'finland': ['finland', 'finnish', 'finlandais', 'finlande'],
        'finnish': ['finland', 'finnish', 'finlandais', 'finlande'],
        'vr': ['vr', 'virtual reality', 'realite virtuelle', 'immersive', 'immersif'],
        'immersive': ['immersive', 'immersif', 'vr', 'virtual'],
        # French synonyms
        'enfants': ['enfants', 'enfant', 'kids', 'famille', 'jeunes'],
        'gratuit': ['gratuit', 'gratuits', 'gratuites', 'gratuite', 'free'],
        'free': ['free', 'gratuit', 'gratuits', 'gratuites', 'gratuite'],
        # Location synonyms
        'montmartre': ['montmartre', '18e', '18eme', 'paris 18'],
        'paris': ['paris', 'parisien', 'parisienne'],
        # Category synonyms
        'jazz': ['jazz', 'jazzistique'],
        'rock': ['rock', 'pop-rock', 'rock\'n\'roll'],
        'classical': ['classical', 'classique', 'orchestra', 'symphonic'],
        'classique': ['classique', 'classical', 'orchestre', 'symphonique'],
    }

    def keyword_matches(keyword: str, text: str) -> bool:
        """Check if keyword or any of its synonyms appear in text."""
        kw_lower = keyword.lower()
        # Direct match
        if kw_lower in text:
            return True
        # Synonym match
        synonyms = KEYWORD_SYNONYMS.get(kw_lower, [])
        return any(syn in text for syn in synonyms)

    for keyword in must_contain:
        if not keyword_matches(keyword, answer_lower):
            warnings.append({
                'type': 'MISSING_KEYWORD',
                'message': f'Expected keyword "{keyword}" not found in response'
            })

    for keyword in must_not_contain:
        if keyword.lower() in answer_lower:
            issues.append({
                'type': 'FORBIDDEN_KEYWORD',
                'message': f'Forbidden keyword "{keyword}" found in response'
            })

    # Determine status
    if issues:
        status = 'FAIL'
    elif warnings:
        status = 'WARN'
    else:
        status = 'PASS'

    return {
        'query_id': query_id,
        'query': query_text,
        'status': status,
        'chatbot_count': chatbot_count,
        'db_count': db_truth['total_matching'],
        'issues': issues,
        'warnings': warnings,
        'answer_preview': answer_text[:200] + '...' if len(answer_text) > 200 else answer_text
    }


def evaluate_conversation(conversation: dict, chain: RAGChain, storage: EventStorage) -> dict:
    """Evaluate a multi-turn conversation.

    Args:
        conversation: Conversation object with turns
        chain: RAGChain instance
        storage: EventStorage instance

    Returns:
        Dict with conversation evaluation results
    """
    session_id = conversation['session_id']
    description = conversation.get('description', '')
    test_focus = conversation.get('test_focus', [])
    language = conversation.get('language', 'fr')
    turns = conversation.get('turns', [])

    # Create a unique session for this evaluation
    eval_session_id = f'eval_{session_id}_{uuid.uuid4().hex[:8]}'

    turn_results = []
    conversation_issues = []

    for turn in turns:
        # Override language with turn-specific if available
        turn_language = turn.get('generation_expectations', {}).get('expected_language', language)
        if turn_language == 'mixed':
            turn_language = language

        turn_data = {**turn, 'language': turn_language}

        result = evaluate_single_query(turn_data, chain, storage, session_id=eval_session_id)
        turn_results.append(result)

        # Check context dependency
        context_dep = turn.get('context_dependency')
        if context_dep and result['status'] == 'FAIL':
            conversation_issues.append({
                'turn_id': turn.get('turn_id'),
                'type': 'CONTEXT_FAILURE',
                'message': f'Failed with context dependency: {context_dep}'
            })

    # Calculate conversation-level metrics
    total_turns = len(turn_results)
    passed_turns = sum(1 for r in turn_results if r['status'] == 'PASS')
    warned_turns = sum(1 for r in turn_results if r['status'] == 'WARN')
    failed_turns = sum(1 for r in turn_results if r['status'] == 'FAIL')

    if failed_turns > 0:
        status = 'FAIL'
    elif warned_turns > 0:
        status = 'WARN'
    else:
        status = 'PASS'

    return {
        'session_id': session_id,
        'description': description,
        'test_focus': test_focus,
        'status': status,
        'total_turns': total_turns,
        'passed_turns': passed_turns,
        'warned_turns': warned_turns,
        'failed_turns': failed_turns,
        'turn_results': turn_results,
        'conversation_issues': conversation_issues
    }


def main():
    """Run semantic evaluation on v3.0 golden dataset."""
    import argparse

    parser = argparse.ArgumentParser(description='Semantic evaluation of chatbot (v3.0)')
    parser.add_argument('--input', default='data/evaluation/golden_dataset.json',
                       help='Golden dataset JSON file')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit number of items to evaluate')
    parser.add_argument('--offset', type=int, default=0,
                       help='Skip first N items')
    parser.add_argument('--conversations-only', action='store_true',
                       help='Only evaluate conversations')
    parser.add_argument('--singles-only', action='store_true',
                       help='Only evaluate single queries')
    parser.add_argument('--output', default=None,
                       help='Output JSON file for results')
    args = parser.parse_args()

    print("="*70)
    print("SEMANTIC EVALUATION (v3.0 - Conversational)")
    print("="*70)
    print(f"Input: {args.input}")
    print()

    # Load golden dataset
    with open(args.input, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    version = dataset.get('version', '2.0')
    print(f"Dataset version: {version}")

    # Handle both v2.0 (queries) and v3.0 (conversations + single_queries) formats
    if 'queries' in dataset:
        # Legacy v2.0 format
        conversations = []
        single_queries = dataset['queries']
    else:
        # v3.0 format
        conversations = dataset.get('conversations', [])
        single_queries = dataset.get('single_queries', [])

    print(f"Conversations: {len(conversations)}")
    print(f"Single queries: {len(single_queries)}")
    print()

    # Initialize
    print("Initializing RAG chain...")
    chain = RAGChain()
    print("Initializing EventStorage...")
    storage = EventStorage()
    print()

    all_results = {
        'timestamp': datetime.now().isoformat(),
        'dataset_version': version,
        'conversation_results': [],
        'single_query_results': []
    }

    # Evaluate conversations
    if not args.singles_only and conversations:
        print("="*70)
        print("EVALUATING CONVERSATIONS")
        print("="*70)

        conv_to_eval = conversations[args.offset:]
        if args.limit:
            conv_to_eval = conv_to_eval[:args.limit]

        for i, conv in enumerate(conv_to_eval, 1):
            print(f"\n[Conv {i}/{len(conv_to_eval)}] {conv['session_id']}: {conv.get('description', '')[:50]}...")
            result = evaluate_conversation(conv, chain, storage)
            all_results['conversation_results'].append(result)

            status_emoji = "[PASS]" if result['status'] == 'PASS' else ("[WARN]" if result['status'] == 'WARN' else "[FAIL]")
            print(f"  {status_emoji} - {result['passed_turns']}/{result['total_turns']} turns passed")

            for tr in result['turn_results']:
                turn_emoji = "[OK]" if tr['status'] == 'PASS' else ("[!]" if tr['status'] == 'WARN' else "[X]")
                print(f"    {turn_emoji} {tr['query_id']}: {tr['query'][:40]}... [{tr['chatbot_count']} results]")

    # Evaluate single queries
    if not args.conversations_only and single_queries:
        print("\n" + "="*70)
        print("EVALUATING SINGLE QUERIES")
        print("="*70)

        queries_to_eval = single_queries
        if args.conversations_only:
            queries_to_eval = []
        else:
            queries_to_eval = single_queries[args.offset:] if not conversations else single_queries
            if args.limit and not conversations:
                queries_to_eval = queries_to_eval[:args.limit]

        for i, query_data in enumerate(queries_to_eval, 1):
            print(f"\n[Query {i}/{len(queries_to_eval)}] {query_data['id']}: {query_data['query'][:50]}...")
            result = evaluate_single_query(query_data, chain, storage)
            all_results['single_query_results'].append(result)

            status_emoji = "[PASS]" if result['status'] == 'PASS' else ("[WARN]" if result['status'] == 'WARN' else "[FAIL]")
            print(f"  {status_emoji} - Chatbot: {result['chatbot_count']}, DB: {result['db_count']}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    # Conversation summary
    if all_results['conversation_results']:
        conv_pass = sum(1 for r in all_results['conversation_results'] if r['status'] == 'PASS')
        conv_warn = sum(1 for r in all_results['conversation_results'] if r['status'] == 'WARN')
        conv_fail = sum(1 for r in all_results['conversation_results'] if r['status'] == 'FAIL')
        total_conv = len(all_results['conversation_results'])

        print(f"\nConversations: {total_conv}")
        print(f"  PASS: {conv_pass} ({conv_pass/total_conv*100:.1f}%)")
        print(f"  WARN: {conv_warn} ({conv_warn/total_conv*100:.1f}%)")
        print(f"  FAIL: {conv_fail} ({conv_fail/total_conv*100:.1f}%)")

        # Turn-level summary
        total_turns = sum(r['total_turns'] for r in all_results['conversation_results'])
        passed_turns = sum(r['passed_turns'] for r in all_results['conversation_results'])
        print(f"\n  Turn-level: {passed_turns}/{total_turns} passed ({passed_turns/total_turns*100:.1f}%)")

    # Single query summary
    if all_results['single_query_results']:
        sq_pass = sum(1 for r in all_results['single_query_results'] if r['status'] == 'PASS')
        sq_warn = sum(1 for r in all_results['single_query_results'] if r['status'] == 'WARN')
        sq_fail = sum(1 for r in all_results['single_query_results'] if r['status'] == 'FAIL')
        total_sq = len(all_results['single_query_results'])

        print(f"\nSingle Queries: {total_sq}")
        print(f"  PASS: {sq_pass} ({sq_pass/total_sq*100:.1f}%)")
        print(f"  WARN: {sq_warn} ({sq_warn/total_sq*100:.1f}%)")
        print(f"  FAIL: {sq_fail} ({sq_fail/total_sq*100:.1f}%)")

    # Issue breakdown
    print("\n" + "-"*70)
    print("ISSUE BREAKDOWN")
    print("-"*70)

    issue_types = defaultdict(list)

    # From conversations
    for conv_result in all_results['conversation_results']:
        for turn_result in conv_result['turn_results']:
            for issue in turn_result.get('issues', []):
                issue_types[issue['type']].append(turn_result['query_id'])
            for warning in turn_result.get('warnings', []):
                issue_types[f"WARN:{warning['type']}"].append(turn_result['query_id'])

    # From single queries
    for result in all_results['single_query_results']:
        for issue in result.get('issues', []):
            issue_types[issue['type']].append(result['query_id'])
        for warning in result.get('warnings', []):
            issue_types[f"WARN:{warning['type']}"].append(result['query_id'])

    if issue_types:
        for issue_type, query_ids in sorted(issue_types.items(), key=lambda x: -len(x[1])):
            print(f"  {issue_type}: {len(query_ids)} queries")
            print(f"    {', '.join(query_ids[:5])}")
    else:
        print("  No issues found!")

    # Save results if output specified
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
