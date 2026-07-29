#!/usr/bin/env python3
"""
Recommendation Engine for Orphaned Epic Program Mapping

Analyzes orphaned epics and suggests program mappings based on:
- Team match (40% weight)
- Keyword similarity (30% weight)
- Portfolio affinity (20% weight)
- Build/release match (10% weight)
"""

import json
import re
from typing import Dict, List, Tuple
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, remove special chars"""
    if not text or text == '-':
        return ''
    return re.sub(r'[^\w\s]', ' ', text.lower()).strip()


def extract_keywords(text: str) -> set:
    """Extract meaningful keywords from text, filtering out common words"""
    stopwords = {'the', 'and', 'for', 'field', 'service', 'sfs', 'fsl', 'a', 'an', 'of', 'to', 'in', 'on'}
    normalized = normalize_text(text)
    words = normalized.split()
    return {w for w in words if len(w) > 2 and w not in stopwords}


def calculate_team_match(epic_team: str, program_teams: List[str]) -> float:
    """Calculate team match score (0-1)"""
    if not epic_team or not program_teams:
        return 0.0

    epic_team_norm = normalize_text(epic_team)

    for program_team in program_teams:
        program_team_norm = normalize_text(program_team)
        if epic_team_norm == program_team_norm:
            return 1.0

        # Partial team match (e.g., "FSL - Asset" matches "FSL - Asset - 360")
        if epic_team_norm in program_team_norm or program_team_norm in epic_team_norm:
            return 0.8

    return 0.0


def calculate_keyword_match(epic_name: str, program_name: str) -> float:
    """Calculate keyword similarity score (0-1)"""
    epic_keywords = extract_keywords(epic_name)
    program_keywords = extract_keywords(program_name)

    if not epic_keywords or not program_keywords:
        return 0.0

    # Jaccard similarity
    intersection = epic_keywords.intersection(program_keywords)
    union = epic_keywords.union(program_keywords)

    if not union:
        return 0.0

    jaccard = len(intersection) / len(union)

    # Bonus for exact phrase matches
    epic_norm = normalize_text(epic_name)
    program_norm = normalize_text(program_name)
    sequence_match = SequenceMatcher(None, epic_norm, program_norm).ratio()

    # Weighted combination: 70% Jaccard, 30% sequence match
    return (jaccard * 0.7) + (sequence_match * 0.3)


def calculate_portfolio_match(epic_team: str, team_portfolios: Dict[str, List[str]], program_portfolio: str) -> float:
    """Calculate portfolio affinity score (0-1)"""
    if not epic_team or not program_portfolio or program_portfolio == '-':
        return 0.0

    # Get team's typical portfolios
    team_data = team_portfolios.get(epic_team, {})
    portfolios = team_data.get('portfolios', [])

    if not portfolios:
        return 0.0

    program_portfolio_norm = normalize_text(program_portfolio)

    for portfolio in portfolios:
        portfolio_norm = normalize_text(portfolio)
        if portfolio_norm == program_portfolio_norm:
            return 1.0
        if portfolio_norm in program_portfolio_norm or program_portfolio_norm in portfolio_norm:
            return 0.7

    return 0.0


def calculate_build_match(epic_build: str, program_name: str) -> float:
    """Calculate build/release alignment score (0-1)"""
    if not epic_build or epic_build == '-':
        return 0.0

    epic_build_norm = normalize_text(epic_build)
    program_name_norm = normalize_text(program_name)

    # Extract release number (e.g., "264", "266")
    epic_releases = re.findall(r'\b\d{3}\b', epic_build)
    program_releases = re.findall(r'\b\d{3}\b', program_name)

    if epic_releases and program_releases:
        if any(er in program_releases for er in epic_releases):
            return 1.0

    # Partial match on build string
    if epic_build_norm in program_name_norm:
        return 0.5

    return 0.0


def calculate_recommendation_score(
    epic: Dict,
    program: Dict,
    team_portfolios: Dict[str, Dict]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate overall recommendation score and component breakdown

    Returns:
        (total_score, component_scores)
    """
    # Component scores
    team_score = calculate_team_match(epic.get('team', ''), program.get('teams', []))
    keyword_score = calculate_keyword_match(epic.get('name', ''), program.get('name', ''))
    portfolio_score = calculate_portfolio_match(
        epic.get('team', ''),
        team_portfolios,
        program.get('portfolio', '')
    )
    build_score = calculate_build_match(epic.get('scheduled_build', ''), program.get('name', ''))

    # Weighted total
    weights = {
        'team': 0.40,
        'keyword': 0.30,
        'portfolio': 0.20,
        'build': 0.10
    }

    total_score = (
        team_score * weights['team'] +
        keyword_score * weights['keyword'] +
        portfolio_score * weights['portfolio'] +
        build_score * weights['build']
    )

    component_scores = {
        'team': round(team_score, 2),
        'keyword': round(keyword_score, 2),
        'portfolio': round(portfolio_score, 2),
        'build': round(build_score, 2)
    }

    return round(total_score, 3), component_scores


def get_confidence_level(score: float) -> str:
    """Determine confidence level from score"""
    if score >= 0.70:
        return 'high'
    elif score >= 0.40:
        return 'medium'
    else:
        return 'low'


def extract_program_teams(program: Dict) -> List[str]:
    """Extract all unique team names from program's nested structure"""
    teams = set()
    for project in program.get('projects', []):
        for epic in project.get('epics', []):
            team = epic.get('team', '')
            if team and team != '-':
                teams.add(team)
    return list(teams)


def generate_recommendations(
    orphaned_epics: List[Dict],
    programs: List[Dict],
    teams_data: Dict
) -> Dict[str, List[Dict]]:
    """
    Generate program recommendations for all orphaned epics

    Returns:
        {epic_id: [recommendations sorted by score]}
    """
    # Build team portfolios lookup
    team_portfolios = {}
    for team_entry in teams_data.get('teams', []):
        team_name = team_entry.get('name', '')
        team_portfolios[team_name] = {
            'portfolios': team_entry.get('portfolios', [])
        }

    # Enrich programs with extracted teams
    enriched_programs = []
    for program in programs:
        enriched = program.copy()
        enriched['teams'] = extract_program_teams(program)
        enriched_programs.append(enriched)

    recommendations = {}

    for epic in orphaned_epics:
        epic_id = epic.get('id')
        if not epic_id:
            continue

        epic_recommendations = []

        for program in enriched_programs:
            score, components = calculate_recommendation_score(epic, program, team_portfolios)

            # Only include if score > 0.20 (filter out very weak matches)
            if score > 0.20:
                epic_recommendations.append({
                    'program_id': program.get('id'),
                    'program_name': program.get('name'),
                    'program_portfolio': program.get('portfolio', '-'),
                    'score': score,
                    'confidence': get_confidence_level(score),
                    'components': components,
                    'reasoning': generate_reasoning(epic, program, components)
                })

        # Sort by score descending
        epic_recommendations.sort(key=lambda x: x['score'], reverse=True)

        # Keep top 5 recommendations
        recommendations[epic_id] = epic_recommendations[:5]

    return recommendations


def generate_reasoning(epic: Dict, program: Dict, components: Dict[str, float]) -> str:
    """Generate human-readable reasoning for recommendation"""
    reasons = []

    if components['team'] >= 0.8:
        reasons.append(f"Team match: {epic.get('team', 'Unknown')}")

    if components['keyword'] >= 0.5:
        reasons.append("Strong keyword similarity")

    if components['portfolio'] >= 0.7:
        reasons.append(f"Portfolio: {program.get('portfolio', 'Unknown')}")

    if components['build'] >= 0.5:
        build = epic.get('scheduled_build', '-')
        if build != '-':
            reasons.append(f"Build {build} alignment")

    if not reasons:
        return "Weak match based on available signals"

    return " • ".join(reasons)


def main():
    """Load data and generate recommendations"""
    import sys

    # Load data files
    with open('data/unallocated_data.json', 'r') as f:
        unallocated_data = json.load(f)

    with open('data/execution_data.json', 'r') as f:
        execution_data = json.load(f)

    with open('data/teams_data.json', 'r') as f:
        teams_data = json.load(f)

    # Get orphaned epics
    orphaned_epics = unallocated_data.get('epics', [])
    programs = execution_data.get('programs', [])

    print(f"Analyzing {len(orphaned_epics)} orphaned epics...")
    print(f"Against {len(programs)} programs...")

    # Generate recommendations
    recommendations = generate_recommendations(orphaned_epics, programs, teams_data)

    # Save to file
    output = {
        'last_updated': unallocated_data.get('last_updated'),
        'recommendations': recommendations
    }

    with open('data/epic_recommendations.json', 'w') as f:
        json.dump(output, f, indent=2)

    # Print summary
    total_epics = len(recommendations)
    high_confidence = sum(1 for recs in recommendations.values() if recs and recs[0]['confidence'] == 'high')
    medium_confidence = sum(1 for recs in recommendations.values() if recs and recs[0]['confidence'] == 'medium')
    low_confidence = sum(1 for recs in recommendations.values() if recs and recs[0]['confidence'] == 'low')
    no_recommendation = total_epics - high_confidence - medium_confidence - low_confidence

    print(f"\nRecommendations generated:")
    print(f"  High confidence (≥70%): {high_confidence}")
    print(f"  Medium confidence (40-69%): {medium_confidence}")
    print(f"  Low confidence (<40%): {low_confidence}")
    print(f"  No recommendation: {no_recommendation}")
    print(f"\nSaved to data/epic_recommendations.json")

    # Show sample recommendations
    if '--sample' in sys.argv and recommendations:
        print("\nSample recommendations:")
        for epic_id, recs in list(recommendations.items())[:3]:
            if recs:
                epic = next((e for e in orphaned_epics if e['id'] == epic_id), None)
                if epic:
                    print(f"\n  Epic: {epic.get('name', 'Unknown')}")
                    print(f"  Team: {epic.get('team', 'Unknown')}")
                    print(f"  Top recommendation:")
                    top_rec = recs[0]
                    print(f"    → {top_rec['program_name']}")
                    print(f"    Score: {top_rec['score']:.0%} ({top_rec['confidence']} confidence)")
                    print(f"    Reasoning: {top_rec['reasoning']}")


if __name__ == '__main__':
    main()
