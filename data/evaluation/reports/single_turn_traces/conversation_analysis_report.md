# Conversation Trace Analysis Report

Generated: 2026-01-30 03:30:15

## Executive Summary

- **Total Conversations**: 15
- **Passed**: 0 (0.0%)
- **Failed**: 12 (80.0%)
- **Warnings**: 3 (20.0%)

## Conversation Results

| Session | Description | Turns | Status | Issues |
|---------|-------------|-------|--------|--------|
| conv_001 | Simple refinement: User narrows down dat... | 3 | FAIL | 5 |
| conv_002 | Topic shift: User starts with jazz, shif... | 2 | WARN | 2 |
| conv_003 | Clarifying question flow: Broad query tr... | 3 | FAIL | 5 |
| conv_004 | Complex refinement chain: Multiple incre... | 4 | FAIL | 12 |
| conv_005 | Follow-up details with comparison reques... | 3 | WARN | 3 |
| conv_006 | Ambiguous refinement requiring disambigu... | 2 | WARN | 2 |
| conv_007 | Bilingual conversation - user switches l... | 2 | FAIL | 4 |
| conv_008 | Negative refinement - user excludes opti... | 3 | FAIL | 12 |
| conv_009 | Result-based refinement - user reacts to... | 2 | FAIL | 4 |
| conv_010 | Family planning scenario - complex multi... | 3 | FAIL | 11 |
| conv_011 | Correction flow - user corrects a misund... | 2 | FAIL | 3 |
| conv_012 | Exploratory conversation - user discover... | 3 | FAIL | 6 |
| conv_013 | Date range clarification needed | 2 | FAIL | 5 |
| conv_014 | Partial topic shift - related category c... | 2 | FAIL | 7 |
| conv_015 | Accessibility requirements conversation | 2 | FAIL | 6 |

## All Issues

- **conv_001**: [MEDIUM] Turn 1: Latency exceeds SLA (29898ms > 5000ms)
- **conv_001**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_001**: [HIGH] Turn 2: Missing filter 'category' (expected: Musique)
- **conv_001**: [MEDIUM] Turn 2: Latency exceeds SLA (33397ms > 5000ms)
- **conv_001**: [MEDIUM] Turn 3: Latency exceeds SLA (5810ms > 5000ms)
- **conv_002**: [MEDIUM] Turn 1: Latency exceeds SLA (26938ms > 5000ms)
- **conv_002**: [MEDIUM] Turn 2: Latency exceeds SLA (33496ms > 5000ms)
- **conv_003**: [MEDIUM] Turn 1: Latency exceeds SLA (8301ms > 5000ms)
- **conv_003**: [MEDIUM] Turn 2: Latency exceeds SLA (105397ms > 5000ms)
- **conv_003**: [MEDIUM] Turn 3: Filter mismatch for 'city' (expected: Paris, got: March)
- **conv_003**: [HIGH] Turn 3: Missing filter 'category' (expected: Art / Exposition)
- **conv_003**: [MEDIUM] Turn 3: Latency exceeds SLA (151051ms > 5000ms)
- **conv_004**: [MEDIUM] Turn 1: Latency exceeds SLA (33703ms > 5000ms)
- **conv_004**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_004**: [HIGH] Turn 2: Missing filter 'category' (expected: Art / Exposition)
- **conv_004**: [HIGH] Turn 2: Missing filter 'price' (expected: 0)
- **conv_004**: [MEDIUM] Turn 2: Latency exceeds SLA (32458ms > 5000ms)
- **conv_004**: [HIGH] Turn 3: Missing filter 'city' (expected: Paris)
- **conv_004**: [HIGH] Turn 3: Missing filter 'category' (expected: Art / Exposition)
- **conv_004**: [HIGH] Turn 3: Missing filter 'price' (expected: 0)
- **conv_004**: [MEDIUM] Turn 3: Latency exceeds SLA (32161ms > 5000ms)
- **conv_004**: [HIGH] Turn 4: Missing filter 'category' (expected: Art / Exposition)
- **conv_004**: [HIGH] Turn 4: Missing filter 'price' (expected: 0)
- **conv_004**: [MEDIUM] Turn 4: Latency exceeds SLA (58232ms > 5000ms)
- **conv_005**: [MEDIUM] Turn 1: Latency exceeds SLA (62322ms > 5000ms)
- **conv_005**: [MEDIUM] Turn 2: Latency exceeds SLA (45703ms > 5000ms)
- **conv_005**: [MEDIUM] Turn 3: Latency exceeds SLA (6887ms > 5000ms)
- **conv_006**: [MEDIUM] Turn 1: Latency exceeds SLA (28048ms > 5000ms)
- **conv_006**: [MEDIUM] Turn 2: Latency exceeds SLA (28833ms > 5000ms)
- **conv_007**: [MEDIUM] Turn 1: Latency exceeds SLA (25405ms > 5000ms)
- **conv_007**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_007**: [HIGH] Turn 2: Missing filter 'category' (expected: Danse)
- **conv_007**: [MEDIUM] Turn 2: Latency exceeds SLA (34423ms > 5000ms)
- **conv_008**: [MEDIUM] Turn 1: Latency exceeds SLA (86184ms > 5000ms)
- **conv_008**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_008**: [HIGH] Turn 2: Missing filter 'category' (expected: Art / Exposition)
- **conv_008**: [HIGH] Turn 2: Missing filter 'month' (expected: 2)
- **conv_008**: [HIGH] Turn 2: Missing filter 'price' (expected: 0)
- **conv_008**: [MEDIUM] Turn 2: Latency exceeds SLA (38720ms > 5000ms)
- **conv_008**: [HIGH] Turn 3: Missing filter 'city' (expected: Paris)
- **conv_008**: [HIGH] Turn 3: Missing filter 'category' (expected: Art / Exposition)
- **conv_008**: [HIGH] Turn 3: Missing filter 'month' (expected: 2)
- **conv_008**: [HIGH] Turn 3: Missing filter 'price' (expected: 0)
- **conv_008**: [HIGH] Turn 3: Missing filter 'exclude_neighborhood' (expected: Montmartre)
- **conv_008**: [MEDIUM] Turn 3: Latency exceeds SLA (5985ms > 5000ms)
- **conv_009**: [MEDIUM] Turn 1: Latency exceeds SLA (62252ms > 5000ms)
- **conv_009**: [HIGH] Turn 2: Missing filter 'region' (expected: nearby_Nanterre)
- **conv_009**: [HIGH] Turn 2: Missing filter 'month' (expected: 1)
- **conv_009**: [MEDIUM] Turn 2: Latency exceeds SLA (46602ms > 5000ms)
- **conv_010**: [MEDIUM] Turn 1: Latency exceeds SLA (13060ms > 5000ms)
- **conv_010**: [MEDIUM] Turn 2: Filter mismatch for 'audience' (expected: family, got: kids)
- **conv_010**: [HIGH] Turn 2: Missing filter 'age_min' (expected: 5)
- **conv_010**: [HIGH] Turn 2: Missing filter 'age_max' (expected: 8)
- **conv_010**: [MEDIUM] Turn 2: Latency exceeds SLA (29223ms > 5000ms)
- **conv_010**: [HIGH] Turn 3: Missing filter 'city' (expected: Paris)
- **conv_010**: [HIGH] Turn 3: Missing filter 'audience' (expected: family)
- **conv_010**: [HIGH] Turn 3: Missing filter 'age_min' (expected: 5)
- **conv_010**: [HIGH] Turn 3: Missing filter 'age_max' (expected: 8)
- **conv_010**: [HIGH] Turn 3: Missing filter 'price' (expected: 0)
- **conv_010**: [MEDIUM] Turn 3: Latency exceeds SLA (41208ms > 5000ms)
- **conv_011**: [MEDIUM] Turn 1: Latency exceeds SLA (18482ms > 5000ms)
- **conv_011**: [HIGH] Turn 2: Missing filter 'category' (expected: Musique)
- **conv_011**: [MEDIUM] Turn 2: Latency exceeds SLA (38086ms > 5000ms)
- **conv_012**: [MEDIUM] Turn 1: Latency exceeds SLA (5548ms > 5000ms)
- **conv_012**: [HIGH] Turn 2: Missing filter 'neighborhood' (expected: Montmartre)
- **conv_012**: [MEDIUM] Turn 2: Latency exceeds SLA (29677ms > 5000ms)
- **conv_012**: [HIGH] Turn 3: Missing filter 'genre' (expected: jazz)
- **conv_012**: [HIGH] Turn 3: Missing filter 'neighborhood' (expected: Montmartre)
- **conv_012**: [MEDIUM] Turn 3: Latency exceeds SLA (34947ms > 5000ms)
- **conv_013**: [MEDIUM] Turn 1: Latency exceeds SLA (35971ms > 5000ms)
- **conv_013**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_013**: [HIGH] Turn 2: Missing filter 'category' (expected: Art / Exposition)
- **conv_013**: [HIGH] Turn 2: Missing filter 'date_range' (expected: next_week)
- **conv_013**: [MEDIUM] Turn 2: Latency exceeds SLA (35810ms > 5000ms)
- **conv_014**: [MEDIUM] Turn 1: Filter mismatch for 'category' (expected: Musique, got: Théâtre / Spectacle)
- **conv_014**: [HIGH] Turn 1: Missing filter 'genre' (expected: opera)
- **conv_014**: [MEDIUM] Turn 1: Latency exceeds SLA (54669ms > 5000ms)
- **conv_014**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_014**: [HIGH] Turn 2: Missing filter 'genre' (expected: ballet)
- **conv_014**: [HIGH] Turn 2: Missing filter 'month' (expected: 3)
- **conv_014**: [MEDIUM] Turn 2: Latency exceeds SLA (53520ms > 5000ms)
- **conv_015**: [HIGH] Turn 1: Missing filter 'accessibility' (expected: wheelchair)
- **conv_015**: [MEDIUM] Turn 1: Latency exceeds SLA (32359ms > 5000ms)
- **conv_015**: [HIGH] Turn 2: Missing filter 'city' (expected: Paris)
- **conv_015**: [HIGH] Turn 2: Missing filter 'category' (expected: Théâtre / Spectacle)
- **conv_015**: [HIGH] Turn 2: Missing filter 'accessibility' (expected: ['wheelchair', 'audio_description'])
- **conv_015**: [MEDIUM] Turn 2: Latency exceeds SLA (37896ms > 5000ms)
