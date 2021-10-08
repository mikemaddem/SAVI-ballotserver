from electionguard.manifest import Manifest
from os.path import dirname, split, splitext


def load_manifest_from_file(path: str) -> Manifest:
    """
    Given a filepath, import an election manifest.
    Exists because the implementations from electionguard are a bit weird.
        (Seem to be designed with the idea of having many manifests in one folder)

    Args:
        path: filepath to manifest JSON file
    Returns:
        Manifest object created from JSON file
    """
    file_path = dirname(path)
    file_name = splitext(split(path)[1])[0]
    manifest = Manifest.from_json_file(file_name=file_name, file_path=file_path)
    return manifest


def generate_ballot_style_contests(manifest: Manifest, ballot_style_id: str) -> dict:
    """
    Generate the dict structure for the relevant contests for a given ballot style.

    Args:
        manifest: election manifest
        ballot_style_id: ballot style to reference from the manifest
    Returns:
        Dict with relevent contest IDs and sequence order
    Raises:
        ValueError if ballot_style is not in the manifest
    """
    # Get ballot style object from manifest based by id
    try:
        ballot_style_object = next(filter(lambda b: b.object_id == ballot_style_id, manifest.ballot_styles))
    except StopIteration:
        raise ValueError("Ballot style not found")

    # Get all regions related for ballot style
    regions = ballot_style_object.geopolitical_unit_ids

    # Filter out contests for ballot style regions
    relevant_contests = list(filter(lambda c: c.electoral_district_id in regions, manifest.contests))

    # Create ballot dictionary with contests and style
    ballot = {
        "style_id": ballot_style_id,
        "contests": [
            {
                "object_id": contest.object_id,
                "sequence_order": contest.sequence_order
            }
            for contest in relevant_contests
        ]
    }

    return ballot


def get_candidate_info(manifest: Manifest, candidate_id: str) -> dict:
    """
    Get relevant information for a candidate.

    Args:
        manifest: election manifest
        candidate_id: candidate to query for in the manifest
    Returns:
        dict with information on candidate such as name, party (if there is one), and ID
    """
    candidate_object = next(filter(lambda c: c.object_id == candidate_id, manifest.candidates))

    candidate = dict()

    if candidate_object.name.text:
        candidate["name"] = candidate_object.name.text
    else:
        candidate["name"] = candidate_object.object_id

    if candidate_object.party_id:
        candidate["party"] = next(filter(lambda p: p.object_id == candidate.party_id, manifest.parties))
    else:
        candidate["party"] = "N/A"

    candidate["object_id"] = candidate_object.object_id

    return candidate


def get_contest_info(manifest: Manifest, contest_id: str) -> dict:
    """
    Get relevant contest information.

    Args:
        manifest: election manifest
        contest_id: contest to query for in the manifest
    Returns:
        Contest name id and the contest candidates and their info
    """
    contest_object = next(filter(lambda c: c.object_id == contest_id, manifest.contests))
    candidates = [get_candidate_info(manifest, c.candidate_id) for c in contest_object.ballot_selections]
    return {
        "name": contest_object.name,
        "object_id": contest_object.object_id,
        "candidates": candidates
    }


def get_selection_info(manifest: Manifest, contest_id: str, candidate_id: str) -> dict:
    """
    Get information required to fill out ballot selection for contest.

    Args:
        manifest: election manifest
        contest_id: ID of the contest to query for in the manifest
        candidate_id: ID of the candidate to query for in the manifest
    Returns:
        Marking data for a ballot selection
    Raises:
        ValueError if selection is not valid for contest
    
    TODO check number of votes and weights
    """
    try:
        # Get contest from manifest
        contest = next(filter(lambda c: c.object_id == contest_id, manifest.contests))
        # Get ballot selection for candidate
        candidate = next(filter(lambda s: s.candidate_id == candidate_id, contest.ballot_selections))
        # Object ID and sequence order
        return {
            "object_id": candidate.object_id,
            "sequence_order": candidate.sequence_order,
            "vote": 1
        }
    except StopIteration:
        raise ValueError("Invalid Selection")
