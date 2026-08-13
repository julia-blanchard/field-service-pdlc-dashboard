#!/usr/bin/env python3
"""
Recommendation Engine for Orphaned Epic Program Mapping

Analyzes orphaned epics and suggests program mappings based on:
- Team match (40% weight)
- Keyword similarity (30% weight)
- Portfolio affinity (20% weight)
- Build/release match (10% weight)

Project-level scoring additionally weighs how well the epic's title and
Description__c body overlap with the candidate project's Project_Summary__c.
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
    """
    Extract meaningful keywords from text, filtering out common words.
    Pure-digit tokens (e.g. "264", "266") are excluded -- release numbers are
    already a dedicated signal (calculate_build_match); leaving them in here
    would double-count a build-number match as if it were topical overlap.
    """
    stopwords = {'the', 'and', 'for', 'field', 'service', 'sfs', 'fsl', 'a', 'an', 'of', 'to', 'in', 'on'}
    normalized = normalize_text(text)
    words = normalized.split()
    return {w for w in words if len(w) > 2 and w not in stopwords and not w.isdigit()}


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


def calculate_title_keyword_match(epic_name: str, target_name: str) -> float:
    """Phrase-level similarity between an epic title and a program/project name (0-1)"""
    epic_keywords = extract_keywords(epic_name)
    target_keywords = extract_keywords(target_name)

    if not epic_keywords or not target_keywords:
        return 0.0

    # Jaccard similarity
    intersection = epic_keywords.intersection(target_keywords)
    union = epic_keywords.union(target_keywords)

    if not union:
        return 0.0

    jaccard = len(intersection) / len(union)

    # Bonus for exact phrase matches
    epic_norm = normalize_text(epic_name)
    target_norm = normalize_text(target_name)
    sequence_match = SequenceMatcher(None, epic_norm, target_norm).ratio()

    # Weighted combination: 70% Jaccard, 30% sequence match
    return (jaccard * 0.7) + (sequence_match * 0.3)


def calculate_description_keyword_match(epic_description: str, target_name: str) -> float:
    """
    Coverage of a program/project name's own keywords found anywhere in the
    epic's Description__c body (0-1). Names are short (a handful of words)
    and descriptions are long, so a plain Jaccard/sequence comparison (as
    used for the title) would understate real overlap -- this instead asks
    "how many of the name's defining terms actually show up in what this
    epic is about," which is the direction that matters when one side of
    the comparison is much longer than the other.
    """
    target_keywords = extract_keywords(target_name)
    description_keywords = extract_keywords(epic_description)

    if not target_keywords or not description_keywords:
        return 0.0

    intersection = target_keywords.intersection(description_keywords)
    return len(intersection) / len(target_keywords)


def calculate_keyword_match(epic_name: str, target_name: str, epic_description: str = '') -> float:
    """
    Combined keyword similarity score (0-1): the stronger of a title-phrase
    match or a description-coverage match. Using max() rather than a blend
    means a strong title match isn't diluted when the epic has no
    description, and a weak/unrelated title doesn't block a match when the
    description substantively discusses the same terms as the project name.
    """
    title_score = calculate_title_keyword_match(epic_name, target_name)
    description_score = calculate_description_keyword_match(epic_description, target_name)
    return max(title_score, description_score)


PILLAR_KEYWORDS = {
    'mobile': ['mobile'],
    'workforce_scheduling': ['workforce scheduling'],
    'scheduling_optimization': ['scheduling & optimization', 'scheduling and optimization', 's&o', 'fs s&o'],
    'foundations': ['foundations'],
}


def get_pillar_key(portfolio_name: str) -> str:
    """
    Map a portfolio name to a canonical FY27 pillar key. Legacy portfolios
    ("264 Field Service Mobile") and FY27 portfolios ("FY27 FS Mobile") use
    different naming conventions but refer to the same pillar -- without
    this, portfolio-affinity scoring can't connect a team's legacy portfolio
    to its FY27 pillar Trust program, since plain substring match never
    overlaps between the two naming styles.
    """
    norm = normalize_text(portfolio_name)
    # Check workforce_scheduling before scheduling_optimization -- both can
    # contain "scheduling" but workforce scheduling is the more specific match.
    for key in ['workforce_scheduling', 'scheduling_optimization', 'mobile', 'foundations']:
        for kw in PILLAR_KEYWORDS[key]:
            if normalize_text(kw) in norm:
                return key
    return ''


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
    program_pillar = get_pillar_key(program_portfolio)

    for portfolio in portfolios:
        portfolio_norm = normalize_text(portfolio)
        if portfolio_norm == program_portfolio_norm:
            return 1.0
        if portfolio_norm in program_portfolio_norm or program_portfolio_norm in portfolio_norm:
            return 0.7

    # Pillar-key match bridges legacy ("264 Field Service Mobile") and FY27
    # ("FY27 FS Mobile") naming conventions for the same pillar. Some teams
    # are dual-listed across two pillar portfolios (e.g. both S&O and
    # Workforce Scheduling) -- treat the first-listed portfolio as the
    # team's primary pillar so ties break toward it instead of scoring both
    # pillars identically.
    primary_pillar = next((get_pillar_key(p) for p in portfolios if get_pillar_key(p)), '')
    if program_pillar:
        if program_pillar == primary_pillar:
            return 0.9
        if program_pillar in {get_pillar_key(p) for p in portfolios}:
            return 0.5

    return 0.0


def get_release_group(text: str) -> str:
    """
    Bucket a release number into the same 264 vs 266+ groups the Orphaned
    Work tab's toggle uses, so Trust programs only surface under the
    matching toggle (264 programs for 264 epics, 266/268/270/272 for 266+).
    Returns '' if no release number is present (ungated -- no restriction).
    """
    if not text:
        return ''
    match = re.search(r'\b(264|266|268|270|272)\b', text)
    if not match:
        return ''
    return '264' if match.group(1) == '264' else '266+'


def get_epic_release_groups(epic: Dict) -> set:
    """
    All release groups implied by this epic -- from Scheduled_Build__c AND
    from its own name. These usually agree (singleton set), but data-entry
    lag can leave them out of sync (e.g. a title renamed to "266 ..." before
    Scheduled_Build__c catches up, or vice versa). When they disagree, treat
    the epic as spanning both groups instead of silently trusting one field,
    matching the same build-OR-name logic the Orphaned tab's 264/266 toggle
    already uses to decide which epics to display.
    """
    groups = set()
    build_group = get_release_group(epic.get('scheduled_build', ''))
    name_group = get_release_group(epic.get('name', ''))
    if build_group:
        groups.add(build_group)
    if name_group:
        groups.add(name_group)
    return groups


def get_program_release_groups(program: Dict) -> set:
    """All release groups referenced anywhere in a program's or its projects' names."""
    groups = set()
    prog_group = get_release_group(program.get('name', ''))
    if prog_group:
        groups.add(prog_group)
    for project in program.get('projects', []):
        proj_group = get_release_group(project.get('name', ''))
        if proj_group:
            groups.add(proj_group)
    return groups


def calculate_summary_match(epic_name: str, epic_description: str, project_summary: str) -> float:
    """
    Coverage of the epic's keywords -- drawn from its title AND its
    Description__c body, not just the title -- found anywhere in the
    project's Project_Summary__c text. Jaccard would understate this since
    summaries/descriptions are much longer than epic titles, so this
    measures epic-keyword coverage instead of set overlap.
    """
    if not project_summary:
        return 0.0

    # Descriptions run far longer than titles and would otherwise swamp the
    # title's keywords in the combined set, so cap how much they contribute.
    epic_keywords = extract_keywords(epic_name)
    description_keywords = extract_keywords(epic_description)
    if len(description_keywords) > 40:
        description_keywords = set(list(description_keywords)[:40])
    epic_keywords = epic_keywords | description_keywords

    summary_keywords = extract_keywords(project_summary)

    if not epic_keywords or not summary_keywords:
        return 0.0

    intersection = epic_keywords.intersection(summary_keywords)
    return len(intersection) / len(epic_keywords)


def calculate_program_build_match(epic_build: str, program: Dict) -> float:
    """
    Program-level build match that also checks project names, not just the
    program's own name. Some programs (e.g. "S&O Trust", left unprefixed
    pending a rename) have release-tagged projects ("[266] S&O Trust: ...")
    under an untagged program name -- checking the program name alone would
    always score 0 and unfairly lose to sibling pillar programs whose name
    happens to carry the release number.
    """
    best = calculate_build_match(epic_build, program.get('name', ''))
    for project in program.get('projects', []):
        best = max(best, calculate_build_match(epic_build, project.get('name', '')))
    return best


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
    keyword_score = calculate_keyword_match(epic.get('name', ''), program.get('name', ''), epic.get('description', ''))
    portfolio_score = calculate_portfolio_match(
        epic.get('team', ''),
        team_portfolios,
        program.get('portfolio', '')
    )
    build_score = calculate_program_build_match(epic.get('scheduled_build', ''), program)

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


def extract_project_teams(project: Dict) -> List[str]:
    """Extract all unique team names from a single project's epics"""
    teams = set()
    for epic in project.get('epics', []):
        team = epic.get('team', '')
        if team and team != '-':
            teams.add(team)
    return list(teams)


def calculate_project_score(epic: Dict, program: Dict, project: Dict, team_portfolios: Dict[str, Dict]) -> float:
    """
    Score how well an epic fits a specific project within its recommended
    program. Epics link to GUS via Project, not Program directly, so once a
    program has multiple projects the program-level score alone can't say
    which one to map to.
    """
    project_teams = extract_project_teams(project)
    team_score = calculate_team_match(epic.get('team', ''), project_teams)

    # Dilute team credit for "catch-all" projects that span many teams --
    # matching 1 of 5 teams in a project is weaker signal than matching
    # the only team in a single-team project.
    if len(project_teams) > 1:
        team_score = team_score / len(project_teams)

    keyword_score = calculate_keyword_match(epic.get('name', ''), project.get('name', ''), epic.get('description', ''))
    portfolio_score = calculate_portfolio_match(
        epic.get('team', ''), team_portfolios, program.get('portfolio', '')
    )
    build_score = calculate_build_match(epic.get('scheduled_build', ''), project.get('name', ''))
    summary_score = calculate_summary_match(epic.get('name', ''), epic.get('description', ''), project.get('summary', ''))

    weights = {'team': 0.40, 'keyword': 0.30, 'portfolio': 0.10, 'build': 0.10, 'summary': 0.10}
    total = (
        team_score * weights['team'] +
        keyword_score * weights['keyword'] +
        portfolio_score * weights['portfolio'] +
        build_score * weights['build'] +
        summary_score * weights['summary']
    )
    return round(total, 3)


def find_best_project(epic: Dict, program: Dict, team_portfolios: Dict[str, Dict]) -> Dict:
    """
    Pick the best-matching project within a program for this epic.
    Returns {} if the program has no projects (nothing to recommend).
    """
    projects = program.get('projects', [])
    if not projects:
        return {}

    # Release-scope candidate projects the same way programs are scoped --
    # catch-all programs (e.g. "[264] Unified Workforce Management") mix
    # [264] and [266] sub-projects, so gating only at the program level
    # would still let a 266 epic get matched to a [264]-only project.
    epic_release_groups = get_epic_release_groups(epic)
    if epic_release_groups:
        scoped = [p for p in projects if not get_release_group(p.get('name', '')) or get_release_group(p.get('name', '')) in epic_release_groups]
        if scoped:
            projects = scoped

    scored = [(calculate_project_score(epic, program, p, team_portfolios), p) for p in projects]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_project = scored[0]

    return {
        'project_id': best_project.get('id'),
        'project_name': best_project.get('name'),
        'project_score': best_score
    }


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
        epic_release_groups = get_epic_release_groups(epic)

        for program in enriched_programs:
            # Release-scope Trust programs so a 264 epic only sees 264 Trust
            # options and a 266+ epic only sees 266/268/270/272 Trust options.
            # Programs with no release number in their name (or in any of
            # their projects' names) are ungated and stay candidates for any
            # epic -- this only restricts release-specific Trust buckets.
            # An epic can imply more than one group if its Scheduled_Build__c
            # and its own name disagree (data-entry lag) -- in that case it's
            # a candidate for either group rather than silently picking one.
            program_release_groups = get_program_release_groups(program)
            if program_release_groups and epic_release_groups:
                if not (epic_release_groups & program_release_groups):
                    continue

            score, components = calculate_recommendation_score(epic, program, team_portfolios)

            # Only include if score > 0.20 (filter out very weak matches)
            if score > 0.20:
                recommendation = {
                    'program_id': program.get('id'),
                    'program_name': program.get('name'),
                    'program_portfolio': program.get('portfolio', '-'),
                    'score': score,
                    'confidence': get_confidence_level(score),
                    'components': components,
                    'reasoning': generate_reasoning(epic, program, components)
                }

                best_project = find_best_project(epic, program, team_portfolios)
                if best_project:
                    recommendation.update(best_project)

                epic_recommendations.append(recommendation)

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
