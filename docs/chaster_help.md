# Estim bot README

this text try to explain how to use it

## hardware

- a lot of wires for estim targets
- 3 x 2B units (2 Ch Estim each) with BT
- 2 x BT motion sensor (fixed on body)
- 1 x BT noise sensor
- A laptop for hosting the Discord/Chaster Bot

## Usage

The bot can be managed with Discord on a dedicated server, but it is not necessary it can be used
with the initial settings
The bot use the existing lock on chaster for trigger some events and is also possible to do it with some
slash commands on discord (there are a lot of commands)

Every 5 seconds a picture with all the settings about Estim / sensors / event queue is updated on a discord channel

it is possible to disable the wearer access on bot or grant access to a new discord account (it not use discord
permission)

## Events associations

Several events can be associated with estim config change :

### Community votes

all votes generate an event in real time who is added to the event queue

- Pillory votes
- share links vote with different settings for add or sub vote
- task votes, each choice can be associate with a specific event

### Wheel of fortune

With text part inside the wheel of fortune it is possible to associate event

### Sensors

Some sensors linked with the bot can be used for trigger some events,
it is possible to set the sensibility / time before trigger / time before rearm the sensor

- 2 motions sensors with 2 type events : move and position (if you move slowly for position changing)
- noise sensors, the event is triger when noise level exceed an level

## Free settings on Wof and task votings

With the last version it is possible to directly configure the action into the text on the task voting or in the wof.
The syntax is xyz: free text after

### x: is the profile configuration for the estim , the possible values are :

- A -> Only ramp of pulse with variable length on cage - dick press felling
- B -> Ramp of pulse on all targets but with units dephased - rotate stimuling
- C -> Ramp of twist mode on all targets but with units dephased - rotate stimuling
- D -> Only ramp of deep pulse with variable length on plug + cheek - feel like ass fuck
- E -> long ramp with increasing level on all targets - endless edging
- F -> long ramp with high increment on all targets - mix pain/edge
- G -> long ramp of wave pulse on all targets - mix pain/edge
- H -> long ramp with high increment on balls/nipples - only pain
- I -> Random pulse on all targets - stressful
- J -> Strong deep pulse on cheek only - spank felling
- Z -> do nothing ( can be used as pause )

### y: is the adjusting level of the profile

- 100% is even significant !
- A or a give 100% of the initial value.
- Upper case increase level B=105%, C=110%, D=115%, ...
- Lower case decrease level, b=98% , c=96%, d=94%

### z: is the duration in second

- if the letter is in lower case the value in randomized between 0 and the target.
- A=10s B=20s C=30s ...

for example for 1min of only anal plug at 110% the syntax is :
DCF: nice fucking during one minute
