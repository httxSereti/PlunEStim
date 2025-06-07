import os
import aiohttp

from pprint import pprint

from typings import PilloryVoteDict

from constants import CHASTER_API_URL
from utils import Logger

PLAY_PREVIOUS_PILLORY_EVENT: bool = True

class Chaster():
    """
        Manage all Chaster funcs
    """
    def __init__(self):
        # Requests params
        self.token = os.getenv('CHASTER_TOKEN')
        self.headers = {'accept': 'application/json', 'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        # Chaster attributes
        self.lockId: str = ""
        self.linked: bool = False
        
        # Features/Extensions
        self.currentTaskVoteId: str = ""
        
        # Pillory Feature
        self.pilloryExtensionId: str | None = None
        self.pillories: dict[str, PilloryVoteDict] = {}
        
    async def linkLock(self):
        """ Detect and link Chaster lock and extensions """
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{CHASTER_API_URL}/locks?status=active', headers=self.headers) as response:
                locks = await response.json()
                
                # Check if there is an active lock
                if (len(locks) == 0):
                    Logger.info("[Chaster] There is no active lock.")
                    return
                
                # Select only the first Lock
                lock = locks[0]
                
                # Detect and Setup id
                if not self.lockId:
                    self.lockId = lock['_id']
                    Logger.info(f"[Chaster] Linked an active lock '{lock['title']}', (id='{lock['_id']}')")
                    
                for extension in lock['extensions']:
                    # pprint(extension)
                    
                    if extension['slug'] == "pillory":
                        pilloryExtensionId = extension['_id']
                        if self.pilloryExtensionId != pilloryExtensionId:
                            self.pilloryExtensionId = pilloryExtensionId
                            Logger.info(f"[Chaster] Pillory feature is enabled and linked (id='{pilloryExtensionId}')")
                            
                    if extension['slug'] == "tasks":
                        self.currentTaskVoteId = extension['userData']['currentTaskVote']
                        Logger.info(f"[Chaster] Linked an active vote for a Task (id='{lock['_id']}')")
                        
        await self.fetchPillories()

        self.linked = True
        # TODO: Notify Chaster is successfully linked after fetched all datas
        
    async def fetchPillories(self) -> None:
        """
            Fetch and parse data from Pillory Extension
        """
        
        # Pillory Extension is not enabled/linked
        if self.pilloryExtensionId is None:
            return
        
        # Fetch status of all running pillories
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=f'{CHASTER_API_URL}/locks/{self.lockId}/extensions/{self.pilloryExtensionId}/action',
                headers=self.headers,
                json={"action": "getStatus", "payload": {}}
            ) as answer:
                # Parse JSON as dict
                data = await answer.json()
                
                # If votes are running
                if 'votes' in data:
                    for vote in data['votes']:
                        # Not already tracked, track it.
                        if vote['_id'] not in self.pillories:
                            
                            # TODO: Notify a Pillory has been detected, maybe use 
                            
                            self.pillories[vote['_id']] = {
                                "canVote": vote['canVote'],
                                "createdAt": vote['createdAt'],
                                "nbVotes": 0 if PLAY_PREVIOUS_PILLORY_EVENT else vote['nbVotes'], # If true, will play all votes previously recorded too
                                "reason": vote['reason'],
                                "totalDurationAdded": vote['totalDurationAdded'],
                                "voteEndsAt": vote['voteEndsAt'],
                            }
                            
                        # For events happened between checks, add it into actionQueue
                        for counter in range(self.pillories[vote['_id']]['nbVotes'], vote['nbVotes']):
                            Logger.info(f'[Chaster] New pillory vote! Vote="{vote['_id']}", Counter="{counter + 1}"')
                            
                            # TODO: Play all trigger rules of Events related to pilloryVote or events
                            # await self.add_event_action(
                            #     'pilloryvote',
                            #     'pillory_chaster_' + str(i) + '_' + instance['_id'],
                            #     time.localtime())
                            # self.chaster_pillory_vote_by_id[instance['_id']] = instance['nbVotes']
                            
                        # Synchronise counter with Chaster
                        self.pillories[vote['_id']]['nbVotes'] = vote['nbVotes']
                        