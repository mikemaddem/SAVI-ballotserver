from os import environ
from os.path import dirname, abspath, join


_CONFIG_PATH = dirname(abspath(__file__))
MANIFEST_PATH = environ.get("MANIFEST_PATH", join(_CONFIG_PATH, "data/manifest.json"))
NUM_GUARDIANS = int(environ.get("NUM_GUARDIANS", 2))
QUORUM = int(environ.get("QUORUM", 2))
BALLOTSERVER_NAME = environ.get("BALLOTSERVER_NAME", "example_ballot_mediator_server")
STORAGE_DIR = environ.get("STORAGE_DIR", join(_CONFIG_PATH, "data/storage"))
RECEIVED_HASH_FILE = environ.get("RECEIVED_HASH_FILE", "received_hashes.txt")
COUNTED_HASH_FILE = environ.get("COUNTED_HASH_FILE", "counted_hashes.txt")

def store_hash(hash: str, filename: str) -> None:
    """
    appends a ballot hash to the end of a file
    :param hash: string of the ballot hash to record
    :param filename: filename within config.STORAGE_DIR to write to
    :return: None
    """
    with open(join(STORAGE_DIR, filename), "a") as f:
        f.write(hash + "\n")