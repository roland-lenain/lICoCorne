

from pathlib import Path

from ..procs import Procedure, ProcedureRunner
from ..struct import Fmap


class SetBoronProcedure(Procedure):
    def __init__(self):
        super().__init__(filename="SetBoron.c2m",
                         text="""***********************************************************
*                                                         *
* Procedure :  {}                               *
* Purpose   :  Set global boron parameter in L_MAP object *
*                                                         *
* CALL      :  Fmap := SetBoron Fmap :: densB ;           *
*                                                         *
***********************************************************
PARAMETER  Fmap ::
  ::: LINKED_LIST Fmap ; ;
MODULE END: RESINI: ;
DOUBLE DdensB ;
 :: >>DdensB<< ;

REAL densB := DdensB D_TO_R ;

ECHO "uniform Boron concentration=" densB ;

*--
* Cross-section database interpolation
*--
Fmap := RESINI: Fmap :: EDIT 2
  SET-PARAM 'C-BORE' <<densB>>
  ;

END: ;
""")


class SetBoronRunner(ProcedureRunner):
    def __init__(self, working_directory: Path):
        super().__init__(procedure=SetBoronProcedure(), working_directory=working_directory)

    def run(self, fmap: Fmap, cbore: float):
        return super().run(fmap=fmap.lcm, cbore=cbore)
