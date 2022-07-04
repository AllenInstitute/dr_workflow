import os 
import regex as re
from enum import Enum

import requests 

global COMP_ID, RIG_ID
# get AIBS IDs, if set
COMP_ID = os.environ.get("AIBS_COMP_ID", os.environ["COMPUTERNAME"]).upper()
RIG_ID: str = None
RIG_ID = os.environ.get("AIBS_RIG_ID",None)


while not RIG_ID:
    
    # extract RIG_ID from COMP_ID if possible
    if "NP." in COMP_ID:
        str_match = re.search(R"NP.[\d]+", COMP_ID)
        if str_match:
            RIG_ID = str_match[0]
            break
    
    # use BTVTest.1 if allowed
    # set with environ var:
    USE_TEST_RIG = os.environ.get("USE_TEST_RIG", True)
    if USE_TEST_RIG:
        RIG_ID = "BTVTest.1"
        break
    
    RIG_ID = "none"
else:
    print("Not running from an NP rig: connections to services won't be made\nTry setting env var USE_TEST_RIG=1")

print(f"Running from {COMP_ID}, connected to {RIG_ID}")



class Comp(Enum):
    SYNC = f"{RIG_ID}-Sync"
    WSE = f"{RIG_ID}-Sync"
    MON = f"{RIG_ID}-Mon"
    VIDMON = f"{RIG_ID}-Mon"
    STIM = f"{RIG_ID}-Stim"
    CAMSTIM = f"{RIG_ID}-Stim"
    ACQ = f"{RIG_ID}-Acq" # TODO add btvtest.1-Acq http://mpe-computers/
    EPHYS = f"{RIG_ID}-Acq"

class ConfigHTTP:
    server = "http://mpe-computers/v2.0"
    # all_pc = requests.get("http://mpe-computers/v2.0").json()

    @staticmethod
    def hostname(comp: Comp):
        hostname = requests.get(f"http://mpe-computers/v2.0/aibs_comp_id/{comp.value}").json()['hostname']                      
    # def port(comp: Comp):
    #     print(f"port: {comp.value}")
    # def timeout(comp: Comp):
    #     10
      
print(ConfigHTTP.hostname(Comp.SYNC))
    
def get_np_computers(self, rigs=None, comp=None):
    if rigs is None:
        rigs = [0, 1, 2]

    if not isinstance(rigs, list):
        rigs = [int(rigs)]

    if comp is None:
        comp = ['sync', 'acq', 'mon', 'stim']

    if not isinstance(comp, list):
        comp = [str(comp)]

    comp = [c.lower() for c in comp]

    np_idx = ["NP." + str(idx) for idx in rigs]

    all_pc = requests.get("http://mpe-computers/v2.0").json()
    a = {}
    for k, v in all_pc['comp_ids'].items():
        if any([sub in k for sub in np_idx]) and any([s in k.lower() for s in comp]):
            a[k] = v['hostname'].upper()
    return a
