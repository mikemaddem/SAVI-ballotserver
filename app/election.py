from dataclasses import dataclass
from datetime import datetime
from electionguard.ballot import BallotBoxState, PlaintextBallot
from electionguard.ballot_box import BallotBox, get_ballots
from electionguard.data_store import DataStore
from electionguard.decryption_mediator import DecryptionMediator
from electionguard.election import CiphertextElectionContext
from electionguard.election_builder import ElectionBuilder
from electionguard.encrypt import EncryptionDevice, EncryptionMediator, generate_device_uuid
from electionguard.guardian import Guardian
from electionguard.key_ceremony import CeremonyDetails, ElectionJointKey
from electionguard.key_ceremony_mediator import KeyCeremonyMediator
from electionguard.manifest import InternalManifest, Manifest
from electionguard.tally import CiphertextTally, PlaintextTally
from fastapi import APIRouter
from typing import List

from .manifest import load_manifest_from_file


@dataclass
class BallotServerElectionConfig():
    number_of_guardians: int
    quorum: int
    launch_code: int
    ballotserver_name: str
    manifest_path: str


class Election():
    """
    Class to hold the state of the election.
    Has methods to initialize and store the election state.
    
    TODO: make this not a local thing (mediators on different host)
    """
    manifest: Manifest
    internal_manifest: InternalManifest
    ceremony_details = CeremonyDetails
    guardians: List[Guardian]
    key_ceremony_mediator: KeyCeremonyMediator
    encryption_mediator: EncryptionMediator
    decryption_mediator: DecryptionMediator
    joint_public_key: ElectionJointKey
    election_context: CiphertextElectionContext
    ballotbox: BallotBox
    datastore: DataStore
    ballotserver_name: str

    def _load_manifest(self, path: str):
        self.manifest = load_manifest_from_file(path)

    def _set_ceremony_details(self, num_guardians: int, quorum: int):
        self.ceremony_details = CeremonyDetails(num_guardians, quorum)

    def _create_guardians(self):
        self.guardians = [
                Guardian(
                        f"Guardian-{i+1:02}", i+1, 
                        self.ceremony_details.number_of_guardians,
                        self.ceremony_details.quorum
                    )
                for i in range(self.ceremony_details.number_of_guardians)
            ]
    
    def _create_key_ceremony_mediator(self, id):
        self.key_ceremony_mediator = KeyCeremonyMediator(id, self.ceremony_details)
    
    def _perform_key_ceremony(self):
        # Announce each guardian
        for guardian in self.guardians:
            self.key_ceremony_mediator.announce(guardian.share_public_keys())
        
        # Each guardian saves others announced keys
        for guardian in self.guardians:
            others = self.key_ceremony_mediator.share_announced(guardian.id)
            for keys in others:
                guardian.save_guardian_public_keys(keys)

        # Each guardian generates partial key backups
        for guardian in self.guardians:
            guardian.generate_election_partial_key_backups()
            self.key_ceremony_mediator.receive_backups(guardian.share_election_partial_key_backups())

        # Each guardian receives others' partial key backups
        for guardian in self.guardians:
            backups = self.key_ceremony_mediator.share_backups(guardian.id)
            for backup in backups:
                guardian.save_election_partial_key_backup(backup)

        # Backup verifications
        for guardian in self.guardians:
            for other in self.guardians:
                verifications = list()
                if guardian.id is not other.id:
                    verifications.append(guardian.verify_election_partial_key_backup(other.id))
                self.key_ceremony_mediator.receive_backup_verifications(verifications)
        
        # Save joint public key
        self.joint_public_key = self.key_ceremony_mediator.publish_joint_key()

    def _build_election(self):
        builder = ElectionBuilder(self.ceremony_details.number_of_guardians, self.ceremony_details.quorum, self.manifest)
        builder.set_commitment_hash(self.joint_public_key.commitment_hash)
        builder.set_public_key(self.joint_public_key.joint_public_key)
        self.internal_manifest, self.election_context = builder.build()

    def _create_encryption_mediator(self, launch_code: int, location: str):
        encryption_device = EncryptionDevice(generate_device_uuid(), 1, launch_code, location)
        self.encryption_mediator = EncryptionMediator(self.internal_manifest, self.election_context, encryption_device)

    def _create_decryption_mediator(self, id: str):
        self.decryption_mediator = DecryptionMediator(id, self.election_context)

    def _make_ballotbox(self):
        self.datastore = DataStore()
        self.ballotbox = BallotBox(self.internal_manifest, self.election_context, self.datastore)

    def _create_encrypted_tally(self) -> CiphertextTally:
        return CiphertextTally(
                f"{self.ballotserver_name}-tally-{datetime.utcnow().isoformat()}",
                self.internal_manifest,
                self.election_context
            )


    def initialize_election(self, election_config: BallotServerElectionConfig):
        self.ballotserver_name = election_config.ballotserver_name
        self._load_manifest(election_config.manifest_path)
        self._set_ceremony_details(election_config.number_of_guardians, election_config.quorum)
        self._create_guardians()
        self._create_key_ceremony_mediator(f"{self.ballotserver_name}-key-ceremony-mediator")
        self._perform_key_ceremony()
        self._build_election()
        self._create_encryption_mediator(election_config.launch_code, f"{self.ballotserver_name}-encryption-mediator")
        self._create_decryption_mediator(f"{self.ballotserver_name}-decryption-mediator")
        self._make_ballotbox()

    def store_election_state(self, storage_dir: str):
        # self.manifest.to_json_file()
        # self.internal_manifest.manifest.to_json_file()
        # self.ceremony_details
        # for guardian in self.guardians:
        #     pass
        # self.key_ceremony_mediator
        # self.encryption_mediator
        # self.decryption_mediator
        # self.joint_public_key
        # self.election_context.to_json_file()
        # self.ballotbox
        # self.datastore
        pass


    def get_election_tally(self) -> PlaintextTally:
        """
        Tally up the results of the election and return the plaintext tally

        Returns:
            PlaintextTally object of the election
        
        # TODO separate out the decryption encrypted tally portion
        """
        encrypted_tally = self._create_encrypted_tally()
        cast_ballots = get_ballots(self.datastore, BallotBoxState.CAST)
        for ballot in cast_ballots.values():
            encrypted_tally.append(ballot)
        for guardian in self.guardians:
            guardian_key = guardian.share_election_public_key()
            tally_share = guardian.compute_tally_share(encrypted_tally, self.election_context)
            ballot_share = guardian.compute_ballot_shares(cast_ballots.values(), self.election_context)
            self.decryption_mediator.announce(guardian_key, tally_share, ballot_share)
        plaintext_tally = self.decryption_mediator.get_plaintext_tally(encrypted_tally)
        return plaintext_tally
    
    def challenge_ballot(self, verification_code: str) -> PlaintextBallot:
        """
        Return the proof of ballot spoiling

        Returns:
            Plaintext spoiled ballot matching verification code, None if not found

        # TODO separate out the decryption encrypted tally portion
        """
        encrypted_tally = self._create_encrypted_tally()
        spoiled_ballots = get_ballots(self.datastore, BallotBoxState.SPOILED)
        # Return before decryption if ballot isn't there to begin with
        if not spoiled_ballots.get(verification_code):
            return None
        for ballot in spoiled_ballots.values():
            encrypted_tally.append(ballot)
        for guardian in self.guardians:
            guardian_key = guardian.share_election_public_key()
            tally_share = guardian.compute_tally_share(encrypted_tally, self.election_context)
            # Only need to decrypt the one ballot
            ballot_share = guardian.compute_ballot_shares([spoiled_ballots[verification_code]], self.election_context)
            self.decryption_mediator.announce(guardian_key, tally_share, ballot_share)
        # Decrypt the ballot
        decrypted_ballots = self.decryption_mediator.get_plaintext_ballots([spoiled_ballots[verification_code]])
        return decrypted_ballots[verification_code]


router = APIRouter()

election = Election()


@router.get("/result")
async def tally():
    """
    Get the results of all election tallies.

    Returns:
        Tally results for each contest in the election
    """
    tally = election.get_election_tally()
    results = {
        "contests": [
            {
                "contest": contest,
                "selections": [
                    {
                        "selection": selection,
                        "tally": selection_details.tally
                    } for selection, selection_details in contest_details.selections.items()
                ]
            } for contest, contest_details in tally.contests.items()
        ]
    }
    return results


@router.get("/publish")
async def publish():
    return {"hi": "there"}
