"""Run the frozen G2/Wuji traction candidate in simulation, including pickup.

Default is the demonstrated .35/.35 N brake-capacity profile. These are
configuration capacities, not measured thumb traction or real knife forces.
Initial geometry estimates use the existing common adaptation and certificates.
"""
import sys
from pathlib import Path
from scripts.run_wuji_wrap_selected import main

if __name__=='__main__':
    selection=Path(__file__).resolve().parents[1]/'research/traction-20261005/FROZEN-CANDIDATE-V13.json'
    sys.argv+=['--selection',str(selection)]
    main()
