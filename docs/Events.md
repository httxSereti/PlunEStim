## How it works? 

List of supported Events: 
```
chaster_PilloryVote
chaster_VoteAdd
chaster_VoteSub
```

1. At BOT start, Monitors are launched for each Integrations.
2. Monitors watch for changes.
3. Monitor detect change, call trigger_event
4. Check if Events has `TriggerRules`
5. Trigger `TriggerRules`
6. Notify Users
7. Apply Action (Profile, +/-/+% Intensity, Update Settings)
8. Reverse Action when Duration is over
