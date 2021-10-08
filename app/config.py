from os import environ
from os.path import dirname, abspath, join


_CONFIG_PATH = dirname(abspath(__file__))
MANIFEST_PATH = environ.get("MANIFEST_PATH", join(_CONFIG_PATH, "data/manifest.json"))
NUM_GUARDIANS = int(environ.get("NUM_GUARDIANS", 2))
QUORUM = int(environ.get("QUORUM", 2))
BALLOTSERVER_NAME = environ.get("BALLOTSERVER_NAME", "example_ballot_mediator_server")
STORAGE_DIR = environ.get("STORAGE_DIR", join(_CONFIG_PATH, "data/storage"))
