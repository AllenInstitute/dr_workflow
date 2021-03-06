import json
import logging
import socket
import sys
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

import requests

sys.path.append("..")
try:
    # get protobufs module if available, for Router implementation
    from np.services import ephys_edi_pb2 as ephys_messages
except:
    ...

class Ephys(ABC):
    """ Base class for communication with open ephys """
    
    @abstractmethod
    def start_ecephys_recording():
        pass
    
    @abstractmethod
    def stop_ecephys_recording():
        pass

    @abstractmethod
    def start_ecephys_acquisition():
        pass

    @abstractmethod
    def stop_ecephys_acquisition():
        pass

    @abstractmethod
    def set_open_ephys_name(path):
        pass

    @abstractmethod
    def clear_open_ephys_name():
        pass

    @abstractmethod
    def request_open_ephys_status():
        pass

    @abstractmethod
    def reset_open_ephys():
        pass
    
    
class EphysRouter(Ephys):
    """ Original ZMQ protobuf implementation - requires ephys_edi_pb2.py output from ephys_edi.proto """ 
    
    @staticmethod
    def start_ecephys_recording():
        return ephys_messages.recording(command=1)

    @staticmethod
    def stop_ecephys_recording():
        return ephys_messages.recording(command=0)

    @staticmethod
    def start_ecephys_acquisition():
        return ephys_messages.acquisition(command=1)

    @staticmethod
    def stop_ecephys_acquisition():
        return ephys_messages.acquisition(command=0)

    @staticmethod
    def set_open_ephys_name(path):
        return ephys_messages.set_data_file_path(path=path)

    @staticmethod
    def clear_open_ephys_name():
        return ephys_messages.set_data_file_path(path='')

    @staticmethod
    def request_open_ephys_status():
        return ephys_messages.request_system_status(path='')

    @staticmethod
    def reset_open_ephys():
        EphysRouter.clear_open_ephys_name()
        time.sleep(.5)
        EphysRouter.start_ecephys_recording()
        time.sleep(3)
        EphysRouter.stop_ecephys_recording()
        time.sleep(.5)


class EphysHTTP(Ephys):
    """ Interface for HTTP server introduced in open ephys v0.6.0 (2022) """
    #TODO wait on return msgs from requests between chaning modes etc
    # we don't want to send multiple put requests so quickly that the server can't respond
    
    #? is it necessary to transition idle>acquire>record (and reverse)? is idle>record possible?
    #? can we set rec dir name while in acquire mode?
    
    #TODO get broadcast message working to put plugin settings
    
    try:
        hostname = config["components"]["OpenEphys"]["host"]
    except (NameError,KeyError):
        pc = socket.gethostname()
        acq = {
            "W10DTSM112719":"W10DT05515", # NP0
            "W10DTSM18306":"W10DT05501", # NP1
            "W10DTSM18307":"W10DT05517", # NP2
            "W10DTMJ0AK6GM":"W10SV108131", #ben-desktop:btTest
        }
        hostname = acq.get(pc,"localhost")
    
    server = f"http://{hostname}:37497/api"
    status_endpoint = f"{server}/status"
    recording_endpoint = f"{server}/recording"
    processors_endpoint = f"{server}/processors"
    message_endpoint = f"{server}/message"
    
    class EphysModes(Enum):
        idle = "IDLE"
        acquire = "ACQUIRE"
        record = "RECORD"

    @staticmethod
    def set_URL(url):
        EphysHTTP.server = url
        EphysHTTP.status_endpoint = f"{EphysHTTP.server}/status"
        EphysHTTP.recording_endpoint = f"{EphysHTTP.server}/recording"
        EphysHTTP.processors_endpoint = f"{EphysHTTP.server}/processors"
        EphysHTTP.message_endpoint = f"{EphysHTTP.server}/message"

    @staticmethod
    def get_mode() -> requests.Response:
        logging.info(f"request: 'mode' <-- {EphysHTTP.status_endpoint}")
        return requests.get(EphysHTTP.status_endpoint).json()['mode']

    @staticmethod
    def set_mode(mode: EphysModes) -> requests.Response:
        if not isinstance(mode, EphysHTTP.EphysModes):
            raise TypeError(f"Expected mode of type EphysModes but found {type(mode)}")
        mode_msg = {"mode":mode.value}
        logging.info(f"sending: {mode_msg} --> {EphysHTTP.status_endpoint}")
        return requests.put(EphysHTTP.status_endpoint, json.dumps(mode_msg))

    @staticmethod
    def start_ecephys_recording():
        return EphysHTTP.set_mode(EphysHTTP.EphysModes.record)

    @staticmethod
    def stop_ecephys_recording():
        return EphysHTTP.set_mode(EphysHTTP.EphysModes.acquire)

    @staticmethod
    def start_ecephys_acquisition():
        return EphysHTTP.set_mode(EphysHTTP.EphysModes.acquire)

    @staticmethod
    def stop_ecephys_acquisition():
        return EphysHTTP.set_mode(EphysHTTP.EphysModes.idle)

    @staticmethod
    def set_open_ephys_name(path: Optional[str] = None,  prepend_text: Optional[str] = None, append_text: Optional[str] = None):
        
        recording = requests.get(EphysHTTP.recording_endpoint).json()
        
        if path:
            if path == "":
                path = "_" # filename cannot be zero length
            if "." in path:
                m = f"setting open ephys directory name - cannot contain periods: {path}"                
                print(m)
                raise ValueError(m)
            recording['base_text'] = path
            
        if prepend_text:
            recording['prepend_text'] = prepend_text
        if append_text:
            recording['append_text'] = append_text
        return requests.put(EphysHTTP.recording_endpoint, json.dumps(recording))

    @staticmethod
    def clear_open_ephys_name():
        return EphysHTTP.set_open_ephys_name(path="temp", prepend_text="_", append_text="_")

    @staticmethod
    def request_open_ephys_status():
        return EphysHTTP.get_mode()

    @staticmethod
    def reset_open_ephys():
        if EphysHTTP.request_open_ephys_status() == "RECORD":
            EphysHTTP.stop_ecephys_recording()
            time.sleep(.5)
        if EphysHTTP.request_open_ephys_status() == "ACQUIRE":
            EphysHTTP.stop_ecephys_acquisition()
            time.sleep(.5)
        EphysHTTP.clear_open_ephys_name()
        time.sleep(.5)
        EphysHTTP.start_ecephys_acquisition()
        time.sleep(.5)
        EphysHTTP.start_ecephys_recording()
        time.sleep(3)
        EphysHTTP.stop_ecephys_recording()
        time.sleep(.5)
        EphysHTTP.stop_ecephys_acquisition()
        time.sleep(.5)
        
    """  
    @staticmethod
    def set_ref(ext_tip="TIP"):
        # for port in [0, 1, 2]: 
        #     for slot in [0, 1, 2]: 
                
        slot = 2 #! Test
        port = 100 #! Test
        dock = 0 # TODO may be 1 or 2 with firmware upgrade 
        tip_ref_msg = {"text": f"NP REFERENCE {slot} {port} {dock} {ext_tip}"}
        #logging.info(f"sending ...
        print(f"sending: {tip_ref_msg} --> {EphysHTTP.message_endpoint}")
        # return 
        requests.put(EphysHTTP.message_endpoint, json.dumps(tip_ref_msg))
        time.sleep(3)
    """
    
    
# TODO set up everything possible from here to avoid accidentally changed settings ? 
# probe channels
# sampling rate 
# tip ref
# signal chain?
# acq drive letters

"""
if __name__ == "__main__":
    r = requests.get(EphysHTTP.recording_endpoint)
    print((r.json()['current_directory_name'], r.json()['prepend_text'], r.json()['append_text']))
        
    r = EphysHTTP.set_open_ephys_name(path = "mouseID_", prepend_text="sessionID", append_text="_date")
    print((r.json()['current_directory_name'], r.json()['prepend_text'], r.json()['append_text']))
    
    r = EphysHTTP.set_open_ephys_name(path = "mouse", prepend_text="session", append_text="date")
    print((r.json()['current_directory_name'], r.json()['prepend_text'], r.json()['append_text']))
    
    print((r.json()['base_text'])) # fails as of 06/23 https://github.com/open-ephys/plugin-GUI/pull/514
"""

    

    