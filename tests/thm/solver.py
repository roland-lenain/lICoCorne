

import os
from pathlib import Path
import shutil

import medcoupling as mc
import numpy as np

from licocorne import struct, procs


class ThmSolver:


    def __init__(self, working_directory: Path):

        self._working_directory = working_directory.resolve()

        # data struct
        self._fmap = struct.Fmap(lcm=procs.ProcedureRunner.Type.LCM)
        self._matex = struct.Matex(lcm=procs.ProcedureRunner.Type.LCM)
        self._cpo = struct.Cpo(lcm=procs.ProcedureRunner.Type.LCM)
        self._track = struct.Track(lcm=procs.ProcedureRunner.Type.LCM)


        with os.scandir(Path(__file__).resolve().parent / "simplePOW_proc") as it:
            for entry in it:
                if entry.is_file() and entry.name.endswith(".c2m"):
                    shutil.copy2(src=entry, dst=self._working_directory / entry.name)

        proc_init = procs.ProcedureRunner(procedure="IniPowCompo",
                                          working_directory=self._working_directory)


        proc_init.run(
            Fmap=self._fmap.lcm,
            Matex=self._matex.lcm,
            )
        # recover the output LCM objects
        self._fmap = struct.Fmap(lcm=proc_init.get("Fmap"))
        self._matex = struct.Matex(lcm=proc_init.get("Matex"))

        self._mesh = mc.MEDCouplingCMesh(f"pwr900 mesh")
        self._mesh.setCoords(mc.DataArrayDouble(np.float64(self._matex.lcm['MESHX']) * 0.01),
                             mc.DataArrayDouble(np.float64(self._matex.lcm['MESHY']) * 0.01),
                             mc.DataArrayDouble(np.float64(self._matex.lcm['MESHZ']) * 0.01))

        mc.WriteField(str(self._working_directory / "thm_template.med"),
                    self._create_field("thm_template"),
                    True)



    def _create_field(self, name, nature = mc.IntensiveConservation, values: np.ndarray = None):

        mcfield = mc.MEDCouplingFieldDouble(mc.ON_CELLS, mc.ONE_TIME)
        mcfield.setName(name)
        mcfield.setTime(0., 0, 0)
        mcfield.setMesh(self._mesh)
        mcfield.setNature(nature)
        if values is not None:
            mcfield.setArray(mc.DataArrayDouble(np.float64(values)))
        else:
            mcfield.setArray(mc.DataArrayDouble([0.0] * self._mesh.getNumberOfCells()))

        return mcfield
