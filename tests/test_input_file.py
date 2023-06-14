
import os
from pathlib import Path
import shutil
import sys
import lifo
import lcm
import cle2000
import numpy as np

from licocorne.procedures import set_boron


def setup_config(name, data_dir: Path = None):

    work_dir = (Path(__file__).parent / "results" / Path(__file__).stem).absolute()
    print(work_dir, flush=True)

    if work_dir.exists():
        shutil.rmtree(work_dir)

    work_dir.parent.mkdir(exist_ok=True, parents=True)

    if data_dir is None:
        data_dir = Path(cle2000.__file__).parent.parent.parent.parent / "data"

    print(data_dir, flush=True)

    proc_dir = f"{name}_proc"
    shutil.copytree(src=data_dir / proc_dir, dst=work_dir)

    boron_proc_file = work_dir / set_boron.SetBoronProcedure().filename
    boron_proc_file.write_text(data=set_boron.SetBoronProcedure().text, encoding='utf-8')

    os.chdir(work_dir)
    # sys.exit (0)

def test():

    setup_config("simplePOW")

    #
    # simplePOW: a simple multiphysics example with THM: module
    #

    # construct the Lifo stack for IniPowCompo
    ipLifo1=lifo.new()
    ipLifo1.pushEmpty("Fmap", "LCM")
    ipLifo1.pushEmpty("Matex", "LCM")
    ipLifo1.pushEmpty("Cpo", "LCM")
    ipLifo1.pushEmpty("Track", "LCM")

    # call IniPowCompo Cle-2000 procedure
    IniPowCompo = cle2000.new('IniPowCompo', ipLifo1, 1)
    IniPowCompo.exec()
    print("IniPowCompo execution completed", flush=True)

    # recover the output LCM objects
    Fmap = ipLifo1.node("Fmap")
    Matex = ipLifo1.node("Matex")
    Cpo = ipLifo1.node("Cpo")
    Track = ipLifo1.node("Track")
    stateVector = Fmap["STATE-VECTOR"]
    mylength = stateVector[0]*stateVector[1]
    npar = stateVector[7]

    # empty the Lifo stack
    while ipLifo1.getMax() > 0:
        ipLifo1.pop()

    # iteration loop
    iter = 0
    continueLoop = 1
    powi = 17.3 # Reference at 17.3 MW
    densB = 1000.0
    b_range = [0.0, 2000.0]
    dbdr = None
    ipLifo2 = lifo.new()
    ipLifo3 = lifo.new()
    PowComponent = cle2000.new('PowComponent', ipLifo2, 1)
    ThmComponent = cle2000.new('ThmComponent', ipLifo3, 1)
    conv = False
    while not conv:
        iter += 1
        if iter > 20:
            raise Exception("simplePOW: maximum number of iterations is reached")

        print("POW: ITERATION NUMBER:", iter)

        # construct the Lifo stack for PowComponent
        ipLifo2.push(Fmap)
        ipLifo2.push(Matex)
        if iter == 1:
            Flux = ipLifo2.pushEmpty("Flux", "LCM")
        else:
            ipLifo2.push(Flux)

        ipLifo2.push(Cpo)
        ipLifo2.push(Track)
        ipLifo2.push(iter)
        ipLifo2.push(powi)
        ipLifo2.push(densB)

        # call PowComponent Cle-2000 procedure
        ipLifo4 = lifo.new()
        ipLifo4.push(Fmap)
        ipLifo4.push(densB)
        print("call SetBoron procedure", flush=True)
        cle2000.new('SetBoron', ipLifo4, 1).exec()
        print("SetBoron execution completed", flush=True)
        print("call PowComponent procedure", flush=True)
        # PowComponent = cle2000.new('PowComponent', ipLifo2, 1)
        PowComponent.exec()
        print("PowComponent execution completed", flush=True)
        Flux = ipLifo2.node("Flux")
        Keff_conv = Flux["K-EFFECTIVE"][0]
        print("POW: iter=", iter, " ------------- Keffective=", Keff_conv, "densB=", densB, flush=True)

        # construct the Lifo stack for ThmComponent
        ipLifo3.push(Fmap)
        if iter == 1:
            Thm = ipLifo3.pushEmpty("Thm", "LCM")
        else:
            ipLifo3.push(Thm)

        ipLifo3.push(iter)
        ipLifo3.push(densB)
        ipLifo3.pushEmpty("CONV", "B")

        # call ThmComponent Cle-2000 procedure
        print("call ThmComponent procedure")
        ThmComponent.exec()
        conv_th = ipLifo3.node("CONV")

        print("ThmComponent execution completed. conv=", conv_th, flush=True)

        rho = (Keff_conv - 1.0) / 1.0 * 1.e5
        if True:
            if -1.0 < rho < 1.0:
                conv = True
            else:
                if rho > 0.0:
                    b_range[0] = densB
                else:
                    b_range[1] = densB
                densB = (b_range[1] + b_range[0]) / 2.0
        conv = conv_th and (b_range[1] - b_range[0] < 0.1)
        print("convergence status:", conv, rho, Keff_conv, densB, flush=True)

        # recover thermo-hydraulics information
        Thm = ipLifo3.node("Thm")
        Jpmap = Fmap["PARAM"]
        myIntPtr = np.array([2, ], dtype='i')
        for ipar in range(0, npar):
            Kpmap = Jpmap[ipar]
            pname = Kpmap["P-NAME"]
            # if pname == "T-FUEL":
            #     continue
            ptype = Kpmap["P-TYPE"]
            myArray = Kpmap["P-VALUE"]
            if pname.strip() == "T-FUEL":
                Kpmap["P-VALUE"] = myArray
                Kpmap["P-TYPE"] = myIntPtr
            elif pname.strip() == "D-COOL":
                Kpmap["P-VALUE"] = myArray
                Kpmap["P-TYPE"] = myIntPtr
            elif pname.strip() == "T-COOL":
                Kpmap["P-VALUE"] = myArray
                Kpmap["P-TYPE"] = myIntPtr

        Fmap.val()

        # empty the ipLifo2 Lifo stack
        while ipLifo2.getMax() > 0:
            ipLifo2.pop()

        # empty the ipLifo3 Lifo stack
        while ipLifo3.getMax() > 0:
            ipLifo3.pop()

    print("POW: converged K-effective=", Keff_conv)
    assert abs(Keff_conv - 1.011134) < 1e-4
    print("test simplePOW completed")


    print("POW: converged K-effective=", Keff_conv, flush=True)
    print("test simplePOW completed", flush=True)

    assert conv

    # import pdb
    # pdb.set_trace()

if __name__ == "__main__":
    test()
