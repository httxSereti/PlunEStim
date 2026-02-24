# ˚.✨⋆ PlunEStim

PlunEStim is a Software running a Discord BOT as Client, managing 1+ EStim units using 2B-Estim Board over BT or Serial.

> [!NOTE] Better readibility
> Documentation is made using [Obsidian](https://obsidian.md/), to have the best reading clone and open this folder as vault.

## ˚.✨⋆ Project goals

From a given project (thanks to the OG author), create the first brick of Plune Project.
A Software that can arouse, calm or train you into being nice c:
EStim is a fun thing, even more fun when you're not the one having controls, being just here, you don't know if you'll have pleasure or pain...
Randomness and Surprise is a real funny thing, having random actions done over you or your devices, giving up controls to random people or a special one.

## ˚.✨⋆ How its work

You can control this software using the Discord Bot, using Slash Commands from discord, check `/guide` to see what you can do.
Increase, Decrease using random, arbitrary value or percentage (~, +5%, -5) intensity of the units with ease, apply different profile, listener rules, programs, mode, ton of settings just waiting to be discovered.
This Software also use multiples `Service Integrations` (like Chaster, X, Sensors) these can be enabled to listen to supported `Events` (by example Noises made, Post liked, Pillory Vote...)
Administrators can setup `Listener Rules` triggered by `Events`, applying one or many `Actions` (Shock, Apply new profile, Increase Level, Change Settings), queueing them to play them one by one or playing them as cumulative at the same time...

## ˚.✨⋆ Hardware Setup

```text
- a lot of wires for estim targets
- 3 x 2B units (2 Ch Estim each) over Bluetooth
- 2 x BT motion sensor (fixed on body) (wip: rework)
- 1 x BT noise sensor (wip: rework)
- A computer to run PlunEStim
```

## ˚.✨⋆ [[Integrated Services]]

3rd party application that work with PlunEStim, listening to events, interacting with them to update data/values.. add times or create more interactions.

```text
- Chaster (Pillory, Time Events, Tasks, Wheel of Fortune)
- X (tba)
- Reddit (tba)
- Fetlife (tba)
```

## ˚.✨⋆ [[Events]]

See events.md.

## ˚.✨⋆ [[Actions]]

Actions are payload (values) send to 1 or more EStim Units, mostly issued by **Events**, stored in queue waiting to be executed except when Action is Cumulative.

## ˚.✨⋆ Sensors

Sensors are used to monitor @Subject actions, monitored actions;

- Noise (Subject do more than {**x**} decibels)
- Motion  (Sensor move or not)
- Position (Sensor is/isn't in the area defined)