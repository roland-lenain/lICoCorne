

import os
from pathlib import Path
import shutil

import medcoupling as mc
import numpy as np

from licocorne import name_enum, struct, procs, icoco

class OutputField(name_enum.ICoCoNameEnum):
    T_FUEL = icoco.InputField.T_FUEL
    D_COOL = icoco.InputField.D_COOL
    T_COOL = icoco.InputField.T_COOL


class InputField(name_enum.ICoCoNameEnum):

    FUEL_POWER = icoco.OutputField.FUEL_POWER
    WATER_POWER = icoco.OutputField.WATER_POWER


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

        # empty the Lifo stack
        proc_init.clean()

        # allocate 1 parameter value per fuel zone
        myIntPtr = np.array([2, ], dtype='i')
        for pname in self._fmap.param.names:
            myArray = np.resize(self._fmap.param.get_values(pname),
                                self._fmap.fuel_bundle_nb_per_channel * self._fmap.fuel_channel_nb)
            if pname in [icoco.OutputField.T_FUEL, icoco.OutputField.D_COOL, icoco.OutputField.T_COOL]:
                self._fmap.param.set_values(pname, myArray)
                self._fmap.param.set_type(pname, myIntPtr)
        self._fmap.lcm.val()

        self._cart_mesh = mc.MEDCouplingCMesh(f"pwr900 mesh")
        self._cart_mesh.setCoords(mc.DataArrayDouble(np.float64(self._matex.lcm['MESHX']) * 0.01),
                                  mc.DataArrayDouble(np.float64(self._matex.lcm['MESHY']) * 0.01),
                                  mc.DataArrayDouble(np.float64(self._matex.lcm['MESHZ']) * 0.01))

        fuel_ids = np.array([0] * self._cart_mesh.getNumberOfCells())
        for index, zone_type in enumerate(self._fmap.geo_map.cell_type_index):
            if zone_type in self._matex.fuel_indexes:
                fuel_ids[index] = 1
            else:
                fuel_ids[index] = 0

        mesh = self._cart_mesh.buildUnstructured()

        # valeurs du champ
        vals = fuel_ids # fuel_mesh.getArray().toNumPyArray().ravel()

        # ids des cellules à garder (valeur non nulle)
        ids_keep = np.where(vals != 0)[0]

        # convertir en DataArrayInt
        ids_da = mc.DataArrayInt(ids_keep.tolist())

        # nouveau maillage
        self._mesh = mesh.buildPartOfMySelf(ids_da)

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
