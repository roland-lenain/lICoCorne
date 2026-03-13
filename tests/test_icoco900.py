
from pathlib import Path
import shutil
import cle2000

from licocorne import icoco

import medcoupling as mc

def setup_config(working_dir: Path, name, data_dir: Path = None) -> Path:

    if data_dir is None:
        data_dir = Path(cle2000.__file__).parent.parent.parent.parent / "data"

    print(data_dir, flush=True)

    proc_dir = f"{name}_proc"
    shutil.copytree(src=data_dir / proc_dir, dst=working_dir)

    data_file =icoco.DataFile(
        procedure_directory=data_dir / proc_dir,
        init_proc_name='IniPowCompo'
        )

    data_file_path = working_dir / "icoco_neutro_900.json"
    data_file_path.write_text(data_file.model_dump_json(indent=4))

    return data_file_path


def test():

    work_dir = (Path(__file__).parent / "results" / Path(__file__).stem).absolute()
    print(work_dir, flush=True)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.parent.mkdir(exist_ok=True, parents=True)

    data_file_path = setup_config(work_dir, "simplePOW")

    problem = icoco.Problem(work_dir)

    problem.setDataFile(datafile=str(data_file_path))

    problem.initialize()

    def compute_keff(problem: icoco.Problem, densB):
        problem.setInputDoubleValue(icoco.InputValue.BORON_FRACTION_PPM, densB)

        problem.initTimeStep(dt=0.0)
        problem.solveTimeStep()
        problem.validateTimeStep()
        problem.setInputMEDDoubleField(
            icoco.InputField.D_COOL,
            problem.getOutputMEDDoubleField(icoco.OutputField.D_COOL))
        return problem.getOutputDoubleValue(icoco.OutputValue.KEFF)


    results = {}
    for densB in [500., 1000., 2000.]:
        results[densB] = compute_keff(problem, densB)

    def critical_boron(problem):

        problem.setInputStringValue(icoco.InputValue.STEADY_STATE_MODE, icoco.ValueEnum.SteadyStateMode.CRITCAL_BORON)
        keff = compute_keff(problem, 1000.0)
        cbore = problem.getOutputDoubleValue(icoco.OutputValue.BORON_FRACTION_PPM)
        problem.setInputStringValue(icoco.InputValue.STEADY_STATE_MODE, icoco.ValueEnum.SteadyStateMode.STEADY_STATE)
        return cbore, keff

    cbore, keff = critical_boron(problem)
    results[cbore] = keff

    print(f"results = {results}")

    mc.WriteField(str(work_dir / "neutro_power.med"),
                  problem.getOutputMEDDoubleField(icoco.OutputField.FUEL_POWER),
                  True)

    mc.WriteField(str(work_dir / "neutro_d_cool.med"),
                  problem.getOutputMEDDoubleField(icoco.OutputField.D_COOL),
                  True)

    print(results)
    refs = {500.0: 1.0262353, 1000.0: 1.0101584, 2000.0: 0.9800086, 1328.125: 1.0}
    for densB, keff in results.items():
        assert abs(refs[densB] - keff) < 2.e-5, densB


    def diff_effects(problem, delta, name):

        keff_0 = compute_keff(problem, densB)
        field = problem.getOutputMEDDoubleField(name)
        field += delta
        problem.setInputMEDDoubleField(name, field)
        keff_1 = compute_keff(problem, densB)
        return (keff_1 - keff_0) / keff_0 * 1e5 / delta

    drho = diff_effects(problem, 10.0, icoco.OutputField.T_FUEL)
    print(f"fuel delta rho / K = {drho}")
    assert abs(-3.128065 - drho) < 1.e-3

    drho = diff_effects(problem, 10.0, icoco.OutputField.T_COOL)
    print(f"water delta rho / K = {drho}")
    assert abs(0.6254509 - drho) < 1.e-3

    drho = diff_effects(problem, 50.0, icoco.OutputField.D_COOL)
    print(f"water delta rho / d = {drho}")
    assert abs(28.18082459270954 - drho) < 1.0

    compute_keff(problem, 500.0)
    problem.setInputStringValue(icoco.InputValue.STEADY_STATE_MODE, icoco.ValueEnum.SteadyStateMode.CRITCAL_BORON)
    keff = compute_keff(problem, 500.0)
    assert abs(1.0 - keff) < 1.e-4

if __name__ == "__main__":
    test()
