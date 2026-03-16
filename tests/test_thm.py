
from pathlib import Path
import shutil

from thm.solver import ThmSolver


def test():

    work_dir = (Path(__file__).parent / "results" / Path(__file__).stem).absolute()
    print(f"{work_dir=}", flush=True)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(exist_ok=True, parents=True)
    assert work_dir.is_dir()

    solver = ThmSolver(work_dir)
