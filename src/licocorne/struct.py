from __future__ import annotations
from dataclasses import dataclass

import lcm
import numpy as np


@dataclass
class Param:
    """IGE344, p. 174."""

    lcm: lcm.new

    @property
    def parameter_nb(self) -> int:
        return self.lcm.len()

    def get_name(self, index) -> np.ndarray:
        return self.lcm[index]["P-NAME"].strip()

    @property
    def names(self):
        return [self.get_name(index) for index in range(self.parameter_nb)]

    def get_index(self, name: str):
        for index, par_name in enumerate(self.names):
            if par_name == name:
                return index
        else:
            raise ValueError(f"{name=} not found in {self.names}")

    def get_type(self, name) -> np.ndarray:
        return self.lcm[self.get_index(name)]["P-TYPE"]

    def get_values(self, name) -> np.ndarray:
        return self.lcm[self.get_index(name)]["P-VALUE"]

    def set_values(self, name, values: np.ndarray):
        self.lcm[self.get_index(name)]["P-VALUE"] = values

    def set_type(self, name, values: np.ndarray):
        self.lcm[self.get_index(name)]["P-TYPE"] = values


@dataclass
class GeoMap:
    """IGE344, p. 178."""

    lcm: lcm.new

    @property
    def meshx(self) -> np.ndarray:
        return self.lcm['MESHX']

    @property
    def meshy(self) -> np.ndarray:
        return self.lcm['MESHY']

    @property
    def meshz(self) -> np.ndarray:
        return self.lcm['MESHZ']

    @property
    def cell_type_index(self) -> np.ndarray:
        return self.lcm['MIX']


@dataclass
class Fmap:

    lcm: lcm.new

    @property
    def fuel_bundle_nb_per_channel(self) -> int:
        """The number of fuel bundles per channel."""
        return self.lcm["STATE-VECTOR"][0]
    @property
    def fuel_channel_nb(self) -> int:
        """The number of fuel channels."""
        return self.lcm["STATE-VECTOR"][1]
    @property
    def fuel_type_number(self) -> int:
        """The number of fuel types"""
        return self.lcm["STATE-VECTOR"][6]
    @property
    def parameter_nb(self) -> int:
        """The number of recorded parameters"""
        return self.lcm["STATE-VECTOR"][7]

    @property
    def param(self) -> Param:
        return Param(self.lcm["PARAM"])

    @property
    def geo_map(self) -> GeoMap:
        return GeoMap(self.lcm["GEOMAP"])


@dataclass
class Matex:

    lcm: lcm.new

    @property
    def ng(self) -> int:
        return self.lcm['STATE-VECTOR'][0]

    @property
    def nr(self) -> int:
        return self.lcm['STATE-VECTOR'][6]

    @property
    def nx(self) -> int:
        return self.lcm['STATE-VECTOR'][7]

    @property
    def ny(self) -> int:
        return self.lcm['STATE-VECTOR'][8]

    @property
    def nz(self) -> int:
        return self.lcm['STATE-VECTOR'][9]

    @property
    def nb_refl_types(self) -> int:
        return self.lcm['STATE-VECTOR'][2]

    @property
    def nb_fuel_types(self) -> int:
        return self.lcm['STATE-VECTOR'][3]

    @property
    def fuel_indexes(self) -> np.ndarray:
        """The fuel-type mixture indices, as defined in the reactor geometry.
        """
        return self.lcm['FMIX']

    @property
    def meshx(self) -> np.ndarray:
        return self.lcm['MESHX']

    @property
    def meshy(self) -> np.ndarray:
        return self.lcm['MESHY']

    @property
    def meshz(self) -> np.ndarray:
        return self.lcm['MESHZ']


@dataclass
class Cpo:

    lcm: lcm.new


@dataclass
class Track:

    lcm: lcm.new


@dataclass
class Flux:
    """IGE351, p. 116."""

    lcm: lcm.new

    @property
    def n_group(self) -> float:
        return self.lcm["FLUX"].len()

    @property
    def mg_flux(self) -> np.ndarray:
        flux = self.lcm["FLUX"]
        return np.stack([flux[g] for g in range(self.n_group)])

    @property
    def keff(self) -> float:
        return self.lcm["K-EFFECTIVE"][0]

    @property
    def rho(self) -> float:
        return (self.keff - 1.0) / self.keff * 1e5



@dataclass
class Power:
    """IGE344, p. 192."""

    lcm: lcm.new

    @property
    def total_power(self) -> float:
        """Power in W."""
        return self.lcm["PTOT"][0] * 1e6

    @property
    def distribution(self) -> np.ndarray:
        """Power in W."""
        return self.lcm["POWER-DISTR"]
