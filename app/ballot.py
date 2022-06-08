from electionguard.ballot import PlaintextBallot
from electionguard.group import int_to_q
from fastapi import APIRouter
from pydantic import BaseModel
from uuid import uuid4
import hashlib
import json

from .election import election
from .manifest import generate_ballot_style_contests, get_contest_info, get_selection_info

router = APIRouter()


class BallotInfoRequest(BaseModel):
    ballot_style: str


class BallotMarkingRequest(BaseModel):
    ballot_style: str
    selections: dict


class BallotEncryptionRequest(BaseModel):
    ballot: dict
    action: str


class BallotChallengeRequest(BaseModel):
    verification_code: str


@router.post("/info")
async def gen_ballot_info(ballot_info_params: BallotInfoRequest):
    """
    Given a ballot style, compile and return relevant election information
    
    Args:
        ballot_info_paramse: BallotInfoRequest containing ballot style
    Returns:
        JSON structure for ballot_style with returned from get_contest_info
    """
    # Get base ballot info
    ballot_info = generate_ballot_style_contests(election.manifest, ballot_info_params.ballot_style)

    for contest in ballot_info["contests"]:
        # Get contest info
        contest_info = get_contest_info(election.manifest, contest["object_id"])
        # Populate information
        contest.update(contest_info)

    return ballot_info


@router.post("/mark")
async def mark_ballot(ballot_marking_params: BallotMarkingRequest):
    """
    Mark all selections on a ballot.

    Args:
        ballot_marking_params: ballot_style and voter selections
    Returns:
        Marked ballot JSON returned by get_selection_info()

    TODO: handle errors gracefully
    TODO: check number of votes and weights
    """
    # Get base ballot info
    ballot = generate_ballot_style_contests(election.manifest, ballot_marking_params.ballot_style)

    # Give ballot unique ID
    ballot["object_id"] = f"ballot-{uuid4()}"

    # Mark mark each selection
    for contest in ballot["contests"]:
        contest_id = contest["object_id"]
        selected_candidate_id = ballot_marking_params.selections.get(contest_id)
        selection_info = get_selection_info(election.manifest, contest_id, selected_candidate_id)
        contest["ballot_selections"] = [selection_info]
    return ballot


@router.post("/submit")
async def encrypt_ballot(ballot_encryption_params: BallotEncryptionRequest):
    """
    Encrypt a ballot and generate a receipt

    Args:
        ballot_encryption_params: ballot JSON
    Returns:
        receipt JSON with verification code, hashes, and timestamp
    """
    # Assert that action is valid before processing ballot
    assert ballot_encryption_params.action == "CAST" or ballot_encryption_params.action == "SPOIL"

    # ballot_encryption_params.ballot is a dict, which we convert to a JSON string
    # call .encode() on the string and feed it into sha256
    unenc_hash = hashlib.sha256(json.dumps(ballot_encryption_params.ballot).encode()).hexdigest()

    # Make and encrypt ballot object
    ballot = PlaintextBallot.from_json_object(ballot_encryption_params.ballot)
    encrypted_ballot = election.encryption_mediator.encrypt(ballot)

    # the ballot type has a function to run it through sha256 with something prepended to it
    # this returns an ElementModQ, a variety of BigInteger, which has .to_hex() to make a hex string
    enc_hash = encrypted_ballot.crypto_hash_with(int_to_q(0)).to_hex()

    # Cast or spoil ballot depending on action
    if ballot_encryption_params.action == "CAST":
        election.ballotbox.cast(encrypted_ballot)
    else:
        election.ballotbox.spoil(encrypted_ballot)

    # Return verification code and timestamp
    return {
        "verification_code": encrypted_ballot.object_id,
        "timestamp": encrypted_ballot.timestamp,
        "unenc_hash": unenc_hash,
        "enc_hash": enc_hash
    }


@router.post("/challenge")
async def challenge(ballot_challenge_request: BallotChallengeRequest):
    challenged = election.challenge_ballot(ballot_challenge_request.verification_code)

    if challenged:
        ballot = {
            "ballot_id": challenged.object_id,
            "contests": [
                {
                    "object_id": contest.object_id,
                    "ballot_selections": [
                        {
                            "object_id": selection.object_id,
                            "tally": selection.tally
                        }
                        for selection in contest.selections.values() if selection.tally > 0
                    ]
                }
                for contest in challenged.contests.values()
            ]
        }
    else:
        ballot = {}
    
    return ballot
