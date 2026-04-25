from __future__ import annotations

from openenv.core.env_server.http_server import create_app

from .mechforge_environment import MechForgeEnvironment
from .openenv_models import MechForgeAction, MechForgeObservation


_SHARED_ENV = MechForgeEnvironment()


app = create_app(
    lambda: _SHARED_ENV,
    MechForgeAction,
    MechForgeObservation,
    env_name="mechforge_3d",
    max_concurrent_envs=1,
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
