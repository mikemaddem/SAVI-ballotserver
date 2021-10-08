from fastapi import FastAPI

from .ballot import router as ballotrouter
from .election import router as electionrouter, election, BallotServerElectionConfig

from .config import MANIFEST_PATH, NUM_GUARDIANS, QUORUM, BALLOTSERVER_NAME, STORAGE_DIR
from .secret_config import LAUNCH_CODE

app = FastAPI()
app.include_router(ballotrouter, prefix="/ballot")
app.include_router(electionrouter, prefix="/election")


@app.on_event("startup")
async def initialize_election():
    config = BallotServerElectionConfig(
        NUM_GUARDIANS,
        QUORUM,
        LAUNCH_CODE,
        BALLOTSERVER_NAME,
        MANIFEST_PATH
    )
    election.initialize_election(config)


@app.on_event("shutdown")
async def store_election_state():
    election.store_election_state(STORAGE_DIR)


@app.get("/")
async def home():
    return {"version": "0.1"}
