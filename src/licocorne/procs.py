from __future__ import annotations
from contextlib import contextmanager
from enum import Enum
import os
from pathlib import Path

import cle2000
import lifo


@contextmanager
def change_wd(wd):
    cwd = os.getcwd()
    os.chdir(wd)
    print(f"Entering {wd}")
    try:
        yield
    finally:
        print(f"Leaving {wd}")
        os.chdir(cwd)


class Procedure:

    def __init__(self, filename: str, text: str) -> None:
        self._filename: str = filename
        self._text: str = text
        for index, line in enumerate(text.splitlines()):
            if len(line) > 72:
                raise ValueError(f"Error {filename} line {index} of : length is > 72")

    @property
    def filename(self):
        return self._filename

    @property
    def name(self):
        return str(Path(self._filename).stem)

    @property
    def text(self):
        return self._text.format(self._filename)

    def write(self, working_directory: Path):
        # print(f"write proc {working_directory / self.filename}")
        (working_directory / self.filename).write_text(data=self.text, encoding='utf-8')


class ProcedureRunner:
    class Type(Enum):
        LCM = "LCM"
        BOOL = "B"
        INTEGER = "I"

    def __init__(self, procedure: str | Procedure, working_directory: Path):

        self._lifo = lifo.new()
        self._working_directory = working_directory
        self._procedure_name = procedure if isinstance(procedure, str) else procedure.name
        if isinstance(procedure, Procedure):
            procedure.write(working_directory)

    @property
    def lifo(self) -> lifo.new:
        return self._lifo

    def run(self, **kwargs) -> lifo.new:

        with change_wd(self._working_directory):
            for name, value in kwargs.items():
                if isinstance(value, ProcedureRunner.Type):
                    self._lifo.pushEmpty(name, value.value)
                else:
                    self._lifo.push(value)
            proc = cle2000.new(self._procedure_name, self.lifo, 5)
            proc.exec()

    def get(self, name: str) -> Any:
        return self._lifo.node(name)

    def clean(self):
        while self._lifo.getMax() > 0:
            self._lifo.pop()
