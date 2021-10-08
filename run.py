from logging import log
from app import app
from uvicorn import run


def runserver(host_address: str="0.0.0.0", port: int=8000, log_level: str="info"):
    """
    Run the ballotserver API.

    Args:
        host_address: address to bind to
        port: port number to bind to
        debug: toggle debug mode
    """
    run(app, host=host_address, port=port, log_level=log_level, lifespan="on")


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", help="Available actions")

    runserver_parser = subparsers.add_parser("runserver", help="Run the application")
    runserver_parser.add_argument("-l", "--log-level", type=str, default="info", help="Run app at specified logging level")
    runserver_parser.add_argument("-a", "--addr", type=str, default="0.0.0.0", help="Host to bind app to")
    runserver_parser.add_argument("-p", "--port", type=int, default=8000, help="Port to bind app to")

    args = parser.parse_args()

    if args.action == "runserver":
        runserver(host_address=args.addr, port=args.port, log_level=args.log_level)
