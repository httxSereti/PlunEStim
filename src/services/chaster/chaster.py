import os
import time
import aiohttp

import nextcord
from datetime import datetime

from pprint import pprint

from typings import PilloryVoteDict

from constants import CHASTER_API_URL, PILLORY_PLAY_PREVIOUS_EVENTS
from utils import Logger

from .utils import EmbedChasterPilloryStarted, EmbedChasterPilloryVote

class Chaster():
    """
        Manage all Chaster related things
        Supported extensions;
            - Pillory
    """
    
    def __init__(self, bot):
        self.bot = bot
        
        # Requests params
        self.token = os.getenv('CHASTER_TOKEN')
        self.headers = {'accept': 'application/json', 'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        # Chaster attributes
        self.lockId: str = ""
        self.linked: bool = False
        
        # Task Extension
        self.currentTaskVoteId: str = ""
        
        # Pillory Extension
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
                            Logger.info(f"[Chaster] Pillory Extension is enabled and linked (id='{pilloryExtensionId}')")
                            
                    if extension['slug'] == "tasks":
                        self.currentTaskVoteId = extension['userData']['currentTaskVote']
                        Logger.info(f"[Chaster] Linked an active vote for a Task (id='{lock['_id']}')")
                    
        # Links Extensions    
        await self.fetchPillories()

        self.linked = True
        # TODO: Notify Chaster is successfully linked after fetched all datas
        
    async def fetchPillories(self) -> None:
        """ Fetch and parse data from Pillory Extension """
        
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
                    # TODO: Check for diff between data and app, to create PilloryStoppedEvent
                    
                    # Explore runnning votes
                    for vote in data['votes']:
                        # Not already tracked, track it.
                        if vote['_id'] not in self.pillories:
                            # Add a StatusEmbed for this vote
                            messageId: nextcord.Message = await self.bot.statusChannel.send(
                                embed=EmbedChasterPilloryStarted(
                                    reason=vote['reason'],
                                    nbVotes=vote['nbVotes'],
                                    startedAt=vote['createdAt'],
                                    endAt=vote['voteEndsAt'],
                                )
                            )
                            
                            # Store the new vote
                            self.pillories[vote['_id']] = {
                                "canVote": vote['canVote'],
                                "createdAt": vote['createdAt'],
                                "nbVotes": 0 if PILLORY_PLAY_PREVIOUS_EVENTS else vote['nbVotes'], # If true, will play all votes previously recorded too
                                "reason": vote['reason'],
                                "totalDurationAdded": vote['totalDurationAdded'],
                                "voteEndsAt": vote['voteEndsAt'],
                                "messageId": messageId.id
                            }
                            
                        newVotes: int = vote['nbVotes'] - self.pillories[vote['_id']]['nbVotes']
                        
                        # Notify only if votes has been updated
                        if newVotes > 0:
                            Logger.info('[Chaster] Received {} pillory vote(s)! Pillory reason: "{}"'.format(
                                newVotes,
                                vote['reason']
                            ))
                            
                            await self.bot.logChannel.send(
                                embed=EmbedChasterPilloryVote(
                                    reason=vote['reason'],
                                    nbVotes=newVotes,
                                    nbTotalVotes=vote['nbVotes'],
                                    endAt=vote['voteEndsAt'],
                                )
                            )

                        # For events happened between checks, add it into actionQueue
                        for counter in range(self.pillories[vote['_id']]['nbVotes'], vote['nbVotes']):
                            # TODO: use trigger rules over events (one event can have many actions)
                            # Trigger event 
                            await self.bot.add_event_action(
                                'pilloryvote',
                                'pillory-' + vote['_id'] + '-' + str(counter),
                                time.localtime()
                            )
                            
                        # Synchronise Chaster counter with app
                        self.pillories[vote['_id']]['nbVotes'] = vote['nbVotes']
                        # TODO: Edit PilloryEmbed to update nbVotes