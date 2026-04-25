from __future__ import annotations

from openenv.core.env_server.http_server import create_app

from .cadforge_environment import CadForgeCadQueryEnvironment
from .openenv_models import CadForgeAction, CadForgeObservation


app = create_app(
    CadForgeCadQueryEnvironment,
    CadForgeAction,
    CadForgeObservation,
    env_name="cadforge_cadquery",
    max_concurrent_envs=4,
)


def main(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.port == 8000:
        main()
    else:
        main(port=args.port)
