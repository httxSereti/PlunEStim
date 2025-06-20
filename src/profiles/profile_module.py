import os
import pathlib

from utils import Logger

from constants import DIR_USERDATA

class ProfileModule:
    
    def __init__(self) -> None:
        # Initialize
        self.initialized: bool = False
        self.profilePath: pathlib.Path = pathlib.Path(DIR_USERDATA + "/profiles")
        self.profileFiles: list[str] = []
        
    def loadProfiles(self) -> None:
        """ Load all Profiles inside userdata """
        Logger.info("[Profile] Loading Profiles...")
        
        profileFiles: list[str] = []
        
        try: 
            profileFiles = os.listdir(self.profilePath)
        except FileNotFoundError:
            os.makedirs(self.profilePath)
            Logger.info("[Profile] Created Profile directory!")
            
        Logger.info(f"[Profile] Loaded {len(self.profileFiles)} profiles!")
        self.profileFiles = profileFiles
        self.initialized = True