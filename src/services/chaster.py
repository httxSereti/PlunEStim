import os
import aiohttp

from pprint import pprint

from constants import CHASTER_API_URL
from utils import Logger

class Chaster():
    
    def __init__(self):
        self.token = os.getenv('CHASTER_TOKEN')
        self.headers = {'accept': 'application/json', 'Authorization': 'Bearer ' + self.token , 'Content-Type': 'application/json'}
        self.lockId: str = ""
        
        self.linked: bool = False
        
        self.pilloryId: str = ""
        self.currentTaskVoteId: str = ""
        
        self.pillorys: set(dict) = []
        
    async def linkLock(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{CHASTER_API_URL}/locks?status=active', headers=self.headers) as response:
                locks = await response.json()
                
                if (len(locks) == 0):
                    Logger.info("[Chaster] There is no active lock.")
                    return
                
                # Select only the first Lock
                lock = locks[0]
                
                # Detect and Setup id
                if not self.lockId:
                    self.lockId = lock['_id']
                    Logger.info(f"[Chaster] Detected an active lock '{lock['title']}', (id='{lock['_id']}')")
                    
                for extension in lock['extensions']:
                    # pprint(extension)
                    
                    if extension['slug'] == "pillory":
                        pilloryId = extension['_id']
                        if self.pilloryId != pilloryId:
                            self.pilloryId = pilloryId
                            Logger.info(f"[Chaster] Detected an active pillory (id='{lock['_id']}')")
                            
                        
                    if extension['slug'] == "tasks":
                        self.currentTaskVoteId = extension['userData']['currentTaskVote']
                        Logger.info(f"[Chaster] Detected an active vote for a Task (id='{lock['_id']}')")
                        
                        
                    
                
        self.linked = True
