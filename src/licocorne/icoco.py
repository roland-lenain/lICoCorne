from __future__ import annotations
import os
from pathlib import Path
import shutil

import medcoupling as mc
import numpy as np
import icoco
from pydantic import BaseModel


from . import procs, struct, name_enum
from .procedures.compute_power import ComputePowerRunner
from .procedures.set_boron import SetBoronRunner


class DataFile(BaseModel):
    procedure_directory: Path


class InputValue(name_enum.ICoCoNameEnum):
    FUEL_POWER_FRACTION = "FUEL_POWER_FRACTION"
    BORON_FRACTION_PPM = "BORON_FRACTION_PPM"
    POWER = "POWER"


class OutputValue(name_enum.ICoCoNameEnum):
    FUEL_POWER_FRACTION = InputValue.FUEL_POWER_FRACTION
    BORON_FRACTION_PPM = InputValue.BORON_FRACTION_PPM
    POWER = InputValue.POWER

    KEFF = "KEFF"
    REACTIVITY_STATIC = "REACTIVITY_STATIC"


class InputField(name_enum.ICoCoNameEnum):
    T_FUEL = "T-FUEL"
    D_COOL = "D-COOL"
    T_COOL = "T-COOL"


class OutputField(name_enum.ICoCoNameEnum):

    T_FUEL = InputField.T_FUEL
    D_COOL = InputField.D_COOL
    T_COOL = InputField.T_COOL

    FUEL_POWER = "FUEL_POWER"
    WATER_POWER = "WATER_POWER"


class Problem(icoco.Problem):
    """Minimal implementation of ICoCo"""

    def __init__(self, working_directory: Path) -> None:
        super().__init__()
        self._working_directory = working_directory
        self._time: float = 0.0
        self._dt: float = 0.0
        self._stationary_mode: bool = False
        self._datafile: Path = None

        # data struct
        self._fmap = struct.Fmap(lcm=procs.ProcedureRunner.Type.LCM)
        self._matex = struct.Matex(lcm=procs.ProcedureRunner.Type.LCM)
        self._cpo = struct.Cpo(lcm=procs.ProcedureRunner.Type.LCM)
        self._track = struct.Track(lcm=procs.ProcedureRunner.Type.LCM)

        # result struct
        self._flux = struct.Flux(lcm=procs.ProcedureRunner.Type.LCM)
        self._power = struct.Power(lcm=procs.ProcedureRunner.Type.LCM)

        # I/O
        self._fields: dict[str, mc.MEDCouplingFieldDouble] = {}
        self._values: dict[str, float | int | str] = {}

    def setDataFile(self, datafile):
        self._datafile = Path(datafile)

    def initialize(self) -> bool:

        if not self._working_directory.exists():
            FileNotFoundError(f"{self._working_directory} not found.")

        data_file = DataFile.model_validate_json(self._datafile.read_text())

        with os.scandir(data_file.procedure_directory) as it:
            for entry in it:
                if entry.is_file():
                    shutil.copy2(src=entry, dst=self._working_directory / entry.name)
                # if not entry.name.startswith('.') and entry.is_file():
                #     print(entry.name)

        # Declare procdures
        proc_init = procs.ProcedureRunner(procedure='IniPowCompo', working_directory=self._working_directory)
        self._proc_solve = ComputePowerRunner(working_directory=self._working_directory)
        self._proc_boron = SetBoronRunner(working_directory=self._working_directory)

        # Initialize
        proc_init.run(
            Fmap=self._fmap.lcm,
            Matex=self._matex.lcm,
            Cpo=self._cpo.lcm,
            Track=self._track.lcm,
            )

        # recover the output LCM objects
        self._fmap = struct.Fmap(lcm=proc_init.get("Fmap"))
        self._matex = struct.Matex(lcm=proc_init.get("Matex"))
        self._cpo = struct.Cpo(lcm=proc_init.get("Cpo"))
        self._track = struct.Track(lcm=proc_init.get("Track"))

        # empty the Lifo stack
        proc_init.clean()

        # allocate 1 parameter value per fuel zone
        myIntPtr = np.array([2, ], dtype='i')
        for pname in self._fmap.param.names:
            myArray = np.resize(self._fmap.param.get_values(pname),
                                self._fmap.fuel_bundle_nb_per_channel * self._fmap.fuel_channel_nb)
            if pname in [OutputField.T_FUEL, OutputField.D_COOL, OutputField.T_COOL]:
                self._fmap.param.set_values(pname, myArray)
                self._fmap.param.set_type(pname, myIntPtr)
        self._fmap.lcm.val()

        # define MED Mesh
        self._mesh = mc.MEDCouplingCMesh(f"pwr900 mesh")
        self._mesh.setCoords(mc.DataArrayDouble(np.float64(self._matex.lcm['MESHX']) * 0.01),
                                mc.DataArrayDouble(np.float64(self._matex.lcm['MESHY']) * 0.01),
                                mc.DataArrayDouble(np.float64(self._matex.lcm['MESHZ']) * 0.01))

        self._values[InputValue.FUEL_POWER_FRACTION] = 0.974
        self._values[InputValue.BORON_FRACTION_PPM] = 2000.0
        self._values[InputValue.POWER] = 17.3e6 # W
        return True


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

    def terminate(self) -> None:
        self.__init__(self._working_directory)

    def presentTime(self) -> float:
        return self._time

    def computeTimeStep(self) -> tuple[float, bool]:
        return (0.1, False)

    def initTimeStep(self, dt: float) -> bool:
        self._dt = dt
        return True

    def solveTimeStep(self) -> bool:

        print("call SetBoron procedure", flush=True)
        self._proc_boron.run(fmap=self._fmap,
                             cbore=self._values[InputValue.BORON_FRACTION_PPM])
        print("SetBoron execution completed", flush=True)

        print("call PowField procedure", flush=True)
        self._proc_solve.run(
            fmap=self._fmap,
            matex=self._matex,
            flux=self._flux,
            cpo=self._cpo,
            track=self._track,
            power=self._values[InputValue.POWER] * 1e-6,
            cbore=self._values[InputValue.BORON_FRACTION_PPM],
            )
        print("PowField execution completed", flush=True)
        self._flux = self._proc_solve.get_flux()
        self._power = self._proc_solve.get_power()
        self._values[OutputValue.KEFF] = self._flux.keff
        self._values[OutputValue.REACTIVITY_STATIC] = self._flux.rho

        if OutputField.FUEL_POWER in self._fields:
            self._fields[OutputField.FUEL_POWER].setArray(mc.DataArrayDouble(np.float64(self._power.distribution)))
            self._fields[OutputField.WATER_POWER].setArray(mc.DataArrayDouble(np.float64(self._power.distribution)))
        else:
            self._fields[OutputField.FUEL_POWER] = self._create_field(OutputField.FUEL_POWER, values=self._power.distribution)
            self._fields[OutputField.WATER_POWER] = self._create_field(OutputField.WATER_POWER, values=self._power.distribution)

        frac = self._values[InputValue.FUEL_POWER_FRACTION]
        self._fields[OutputField.FUEL_POWER] = self._fields[OutputField.FUEL_POWER] * frac
        self._fields[OutputField.WATER_POWER] = self._fields[OutputField.WATER_POWER] * (1.0 - frac)

        print(f"POW: ------------- Keffective={self._flux.keff=}",
              f"densB={self._values[OutputValue.BORON_FRACTION_PPM]}", flush=True)

        return True

    def validateTimeStep(self) -> None:
        self._time += self._dt
        self._dt = None

        self._proc_boron.clean()
        self._proc_solve.clean()

    def setStationaryMode(self, stationaryMode: bool) -> None:
        self._stationary_mode = stationaryMode

    def getStationaryMode(self) -> bool:
        return self._stationary_mode

    def setInputDoubleValue(self, name: str, val: float) -> None:
        if name in InputValue:
            self._values[name] = val
            return
        raise icoco.exception.WrongArgument(prob="LICoCorne",
                                            arg="name",
                                            method="setInputDoubleValue",
                                            condition=f"{name=} nor in {InputValue}")

    def getOutputDoubleValue(self, name: str) -> float:
        if name in OutputValue:
            return self._values[name]
        raise icoco.exception.WrongArgument(prob="LICoCorne",
                                            arg="name",
                                            method="getOutputDoubleValue",
                                            condition=f"{name=} nor in {OutputValue}")

    def getInputMEDDoubleFieldTemplate(self, name):

        if name in InputField:
            field = self._create_field(name=name)
            for pname in self._fmap.param.names:
                if pname == name:
                    np_array = self._fmap.param.get_values(name)
                    mc_array = field.getArray()
                    param_index = 0
                    for index, zone_type in enumerate(self._fmap.geo_map.cell_type_index):
                        if zone_type in self._matex.fuel_indexes:
                            mc_array[index] = float(np_array[param_index])
                            param_index += 1
                        else:
                            mc_array[index] = 0.0
                    if name == InputField.D_COOL:
                        mc_array *= 1000.0
                    field.setArray(mc_array)
                    break

            self._fmap.lcm.val()

            return field
        raise icoco.exception.WrongArgument(prob="LICoCorne",
                                            arg="name",
                                            method="getInputMEDDoubleFieldTemplate",
                                            condition=f"{name=} nor in {InputField}")

    def setInputMEDDoubleField(self, name, afield):
        if name in InputField:

            myIntPtr = np.array([2, ], dtype='i')
            for pname in self._fmap.param.names:
                if pname == name:
                    np_array = self._fmap.param.get_values(name)
                    mc_array = afield.getArray()
                    if name == InputField.D_COOL:
                        mc_array /= 1000.0
                    param_index = 0
                    for index, zone_type in enumerate(self._fmap.geo_map.cell_type_index):
                        if zone_type in self._matex.fuel_indexes:
                            np_array[param_index] = mc_array[index]
                            param_index += 1
                    self._fmap.param.set_values(name, np_array)
                    self._fmap.param.set_type(name, myIntPtr)
                    break

            self._fmap.lcm.val()

            return

        raise icoco.exception.WrongArgument(prob="LICoCorne",
                                            arg="name",
                                            method="setInputMEDDoubleField",
                                            condition=f"{name=} nor in {InputField}")

    def getOutputMEDDoubleField(self, name):

        if name in OutputField:
            if name in [OutputField.D_COOL, OutputField.T_COOL, OutputField.T_FUEL, ]:
                return self.getInputMEDDoubleFieldTemplate(name)
            return self._fields[name]

        raise icoco.exception.WrongArgument(prob="LICoCorne",
                                            arg="name",
                                            method="getOutputMEDDoubleField",
                                            condition=f"{name=} nor in {OutputField}")

    def updateOutputMEDDoubleField(self, name, afield):

        if name in OutputField:
            array = self._fields[name].getArray().deepCopy()
            afield.setArray(array)
            return

        raise icoco.exception.WrongArgument(prob="LICoCorne",
                                            arg="name",
                                            method="updateOutputMEDDoubleField",
                                            condition=f"{name=} nor in {OutputField}")


def get_problem(working_directory: Path) -> Problem:

    return Problem(working_directory)

