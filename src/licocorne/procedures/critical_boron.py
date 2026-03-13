
from pathlib import Path

from ..struct import Cpo, Flux, Fmap, Matex, Track

from .compute_power import ComputePowerRunner
from .set_boron import SetBoronRunner


class CriticalBoronRunner(ComputePowerRunner):

    def __init__(self, working_directory: Path):
        super().__init__(working_directory)

        self._set_boron = SetBoronRunner(working_directory)
        self._cbore = None

    def run(self,
            fmap: Fmap, matex: Matex, flux: Flux, cpo: Cpo, track: Track,
            power: float, cbore: float, target: float, prec: float = 1.0):
        conv = False
        b_range = [0.0, 2000.0]
        while not conv:
            self._set_boron.run(fmap=fmap, cbore=cbore)
            self._set_boron.clean()
            super().clean()
            super().run(
                fmap=fmap, matex=matex, flux=flux, cpo=cpo, track=track, power=power, cbore=cbore)
            keff = flux.keff

            rho = (keff - target) / target * 1.e5
            if -prec < rho < prec:
                break
            else:
                if rho > 0.0:
                    b_range[0] = cbore
                else:
                    b_range[1] = cbore
                cbore = (b_range[1] + b_range[0]) * 0.5
                if abs(cbore - b_range[0]) < prec * 0.1 or abs(cbore - b_range[1]) < prec * 0.1:
                    raise AssertionError(
                        f"Critical boron can't be reached: cb={cbore}, rho = {rho}")
            print("convergence status:", conv, rho, keff, cbore, flush=True)

        self._cbore = cbore

    def get_cbore(self) -> float:
        return self._cbore
