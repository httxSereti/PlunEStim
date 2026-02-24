import os
import time
import aiohttp
import re

import nextcord
from datetime import datetime

from pprint import pprint

from typings import PilloryVoteDict, TriggerableEvent

from constants import CHASTER_API_URL, PILLORY_PLAY_PREVIOUS_EVENTS
from utils import Logger

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
        
        # History
        self.eventsHistory: list[str] = []
        
    async def linkLock(self):
        """ 
            Detect and link Chaster lock and extensions 
        """
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
                    Logger.info(f"[Chaster] Lock '{lock['title']}' is now Linked (id='{lock['_id']}')")
                    
                # Links Extensions
                for extension in lock['extensions']:
                    # pprint(extension)
                    
                    if extension['slug'] == "pillory":
                        pilloryExtensionId = extension['_id']
                        if self.pilloryExtensionId != pilloryExtensionId:
                            self.pilloryExtensionId = pilloryExtensionId
                            Logger.info(f"[Chaster] Linked Pillory Extension (id='{pilloryExtensionId}')")
                            
                    if extension['slug'] == "tasks":
                        self.currentTaskVoteId = extension['userData']['currentTaskVote']
                        Logger.info(f"[Chaster] Linked Tasks Extension (id='{lock['_id']}')")
                        
                    if extension['slug'] == "wheel-of-fortune":
                        # self.currentTaskVoteId = extension['userData']['currentTaskVote']
                        Logger.info(f"[Chaster] Linked WOF Extension (id='{lock['_id']}')")
                    
        # Links Extensions    
        await self.fetchPillories()

        self.linked = True
        # TODO: Notify Chaster is successfully linked after fetched all datas
        
    async def fetchPillories(self) -> None:
        """ 
            Fetch and parse data from Pillory Extension 
        """
        
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
                        pilloryId = vote['_id']
                                              
                        # Not already tracked, track it.
                        if pilloryId not in self.pillories:
                            # Trigger Event
                            await self.bot.trigger_event(
                                event_type=TriggerableEvent.CHASTER_PILLORY_STARTED,
                                eventData={
                                    "pilloryId": pilloryId,
                                    "reason": vote["reason"],
                                    "nbVotes": vote["nbVotes"],
                                    "startedAt": vote["createdAt"], 
                                    "endAt": vote["voteEndsAt"]
                                }
                            )
                            
                            # Store the new vote
                            self.pillories[pilloryId] = {
                                "canVote": vote['canVote'],
                                "createdAt": vote['createdAt'],
                                "nbVotes": 0 if PILLORY_PLAY_PREVIOUS_EVENTS else vote['nbVotes'], # If true, will play all votes previously recorded too
                                "reason": vote['reason'],
                                "totalDurationAdded": vote['totalDurationAdded'],
                                "voteEndsAt": vote['voteEndsAt'],
                            }

                        # For new votes happened between checks, trigger event vote pillory
                        for counter in range(self.pillories[pilloryId]['nbVotes'], vote['nbVotes']):
                            # V2 
                            await self.bot.trigger_event(
                                event_type=TriggerableEvent.CHASTER_PILLORY_VOTE,
                                eventData={
                                    "pilloryId": pilloryId,
                                    "reason": vote["reason"],
                                    "nbVotes": 1,
                                    "nbTotalVotes": vote["nbVotes"],
                                    "startedAt": vote["createdAt"], 
                                    "endAt": vote["voteEndsAt"],
                                    "time": time.localtime()
                                }
                            )
                            
                            # Trigger event 
                            await self.bot.add_event_action(
                                'chaster_pillory_vote',
                                'pillory-' + pilloryId + '-' + str(counter),
                                time.localtime()
                            )
                            
                        # Synchronise Chaster counter with app
                        self.pillories[pilloryId]['nbVotes'] = vote['nbVotes']
                        
    async def monitorHistory(self) -> None:
        """
            Monitor parse and apply Chaster history for Events
            TODO: use webhooks from Chaster instead of polling 
        """
          
        if not self.lockId:
            return
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{CHASTER_API_URL}/locks/{self.lockId}/history',
                json={"limit": 30},
                headers=self.headers
            ) as response:
                # Parse into JSON history
                history = await response.json()
                # pprint(history)
                
                for event in history['results']:
                    eventId = event['_id']

                    # Check if event is in History
                    if eventId not in self.eventsHistory:
                        self.eventsHistory.append(eventId)
                        
                        if event['type'] == "wheel_of_fortune_turned" and event['payload']['segment']['type'] == "text":
                            textPayload = event['payload']['segment']['text']
                            
                            matcher = re.search('^(\\d|[A-Z][A-Z,a-z][A-Z,a-z]):', textPayload)
                            
                            if matcher:
                                payload = matcher.group(1)
                                Logger.info(f"[Chaster] Detected dynamic WOF Action (payload='{matcher.group(1)}')")
                                
                                eventData = {
                                    "author": event['role'],
                                    "wofText": textPayload,
                                    "wofAction": payload,
                                    "triggeredAt": event['createdAt']
                                }
                                
                                # Dispatch action
                                await self.bot.trigger_event(
                                    event_type=TriggerableEvent.CHASTER_WOF_TURNED,
                                    eventData=eventData
                                )
                            else:
                                Logger.info(f"[Chaster] Unrecognized Dynamic WOF Action (payload='{textPayload}')")
                            
                        # Time Changes (keyholder, user or extension trigger that event)
                        if event['type'] == "time_changed":
                            voteType: TriggerableEvent = TriggerableEvent.CHASTER_TIME_ADD if event['payload']['duration'] > 0 else TriggerableEvent.CHASTER_TIME_SUB
                            
                            Logger.info(f"[Chaster] {event["role"]} changed time (duration='{event['payload']['duration']}', type='{voteType}')")
                            
                            eventData = {
                                "author": event['role'],
                                "duration": event['payload']['duration'],
                                "triggeredAt": event['createdAt']
                            }
                            
                            await self.bot.trigger_event(
                                event_type=voteType,
                                eventData=eventData
                            )
                            
                            # pprint(eventData)
                            
                        # Time changes using Shared Link extension
                        if event['type'] == "link_time_changed":
                            voteType: TriggerableEvent = TriggerableEvent.CHASTER_VOTE_ADD if event['payload']['duration'] > 0 else TriggerableEvent.CHASTER_VOTE_SUB
                            author: str = event["user"]["username"] if "user" in event else "Someone"
                            
                            Logger.info(f"[Chaster] {author} updated time (duration='{event['payload']['duration']}', type='{voteType}')")
                                                        
                            eventData = {
                                "author": author,
                                "duration": event['payload']['duration'],
                                "triggeredAt": event['createdAt']
                            }
                            
                            await self.bot.trigger_event(
                                event_type=voteType,
                                eventData=eventData
                            )
                            
                            # pprint(event)
                            
                        # pprint(event['type'])