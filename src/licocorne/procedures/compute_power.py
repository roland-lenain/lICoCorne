
from pathlib import Path

from ..procs import Procedure, ProcedureRunner
from ..struct import Cpo, Flux, Fmap, Matex, Track, Power


class ComputePowerProcedure(Procedure):
    def __init__(self):
        super().__init__(filename="PowField.c2m",
                         text="""****************************************************************
*                                                              *
* Procedure :  {}                                *
* Purpose   :  Reactor Physics component                       *
* Author    :  A. Hebert                                       *
*                                                              *
* CALL      :                                                  *
*  Fmap Matex Flux Power := PowComponent Fmap Matex Flux       *
*                                        Power Cpo Track       *
*    :: <<iter>> <<powi>> <<densB>> ;                          *
*                                                              *
****************************************************************
PARAMETER  Fmap Matex Flux Power Cpo Track ::
  ::: LINKED_LIST Fmap Matex Flux Power Cpo Track ; ;
MODULE NCR: MACINI: TRIVAA: FLUD: FLPOW: GREP: DELETE: END: ;
LINKED_LIST MacroF System Macro1 Macro2 ;
INTEGER init ;
 :: >>init<< ;
DOUBLE Dpowi DdensB ;
 :: >>Dpowi<< >>DdensB<< ;

REAL powi := Dpowi D_TO_R ;
REAL densB := DdensB D_TO_R ;

STRING  Dir := "EDI2B" ;
REAL keffn ;

*--
* Reference parameter values
*--
REAL pbore_0 temp_comb_0 temp_mode_0 dens_mode_0 :=
    500.0 800.0 600.0 0.659 ;
*--
* Cross-section database interpolation
*--
ECHO "uniform Boron concentration=" densB ;
MacroF := NCR: Cpo Fmap ::
             EDIT 0
             MACRO LINEAR
             TABLE Cpo <<Dir>> 'burnup'
               MIX 1 INST-BURN
                     SET LINEAR 'burnup' MAP
                     SET LINEAR 'ppmBore' <<pbore_0>>
                     SET CUBIC 'TF' <<temp_comb_0>>
                     SET CUBIC 'TCA' <<temp_mode_0>>
                     SET CUBIC 'DCA' <<dens_mode_0>>
                     ADD 'ppmBore' <<pbore_0>> MAP
                        REF 'burnup' SAMEASREF
                            'TF' <<temp_comb_0>>
                            'TCA' <<temp_mode_0>>
                            'DCA' <<dens_mode_0>>
                        ENDREF
                     ADD 'TCA' <<temp_mode_0>> MAP
                        REF 'burnup' SAMEASREF
                            'ppmBore' <<pbore_0>>
                            'TF' <<temp_comb_0>>
                            'DCA' <<dens_mode_0>>
                        ENDREF
                     ADD 'TF' <<temp_comb_0>> MAP
                        REF 'burnup' SAMEASREF
                            'ppmBore' <<pbore_0>>
                            'TCA' <<temp_mode_0>>
                            'DCA' <<dens_mode_0>>
                        ENDREF
                     ADD 'DCA' <<dens_mode_0>> MAP
                        REF 'burnup' SAMEASREF
                            'ppmBore' <<pbore_0>>
                            'TCA' <<temp_mode_0>>
                            'TF' <<temp_comb_0>>
                        ENDREF
               ENDMIX
;

Macro1 := NCR: Cpo ::
*            dummy reflector -- please use more realistic data
             EDIT 0
             MACRO LINEAR NMIX 2
             COMPO Cpo <<Dir>>
               MIX 2 SET LINEAR 'burnup' 15000.0
                       SET LINEAR 'ppmBore' <<densB>>
                       SET CUBIC 'TF' <<temp_comb_0>>
                       SET CUBIC 'TCA' <<temp_mode_0>>
                       SET CUBIC 'DCA' <<dens_mode_0>>
               ENDMIX
;

Macro2 Matex := MACINI: Matex Macro1 MacroF ;
*--
* Steady-state diffusion calculation
*--
System := TRIVAA: Macro2 Track ;

IF init 1 = THEN
  Flux := FLUD: System Track ::
    EDIT 1 ADI 4 ACCE 5 3 ;
ELSE
  Flux := FLUD: Flux System Track ::
    EDIT 1 ;
ENDIF ;

System MacroF Macro1 Macro2 := DELETE: System MacroF Macro1 Macro2 ;
*--
* Power distribution calculation
*--
ECHO "total reactor power=" powi "MW" ;
Power Fmap := FLPOW: Fmap Flux Track Matex
                :: EDIT 0 PTOT <<powi>> ;

! Power := DELETE: Power ;
GREP: Flux   ::
  GETVAL 'K-EFFECTIVE ' 1  >>keffn<<   ;
ECHO "K-effective = " keffn " densB=" densB ;

END: ;
""")


class ComputePowerRunner(ProcedureRunner):
    def __init__(self, working_directory: Path):
        super().__init__(procedure=ComputePowerProcedure(), working_directory=working_directory)

    def run(self, fmap: Fmap, matex: Matex, flux: Flux, cpo: Cpo, track: Track, power: float, cbore: float):
        return super().run(
            Fmap=fmap.lcm,
            Matex=matex.lcm,
            Flux=flux.lcm,
            Power=ProcedureRunner.Type.LCM,
            Cpo=cpo.lcm,
            Track=track.lcm,
            init=1 if isinstance(flux.lcm, ProcedureRunner.Type) else 0,
            Dpowi=power,
            DdensB=cbore
            )

    def get_power(self) -> Power:
        return Power(self.get("Power"))

    def get_flux(self) -> Flux:
        return Flux(self.get("Flux"))
