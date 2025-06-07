# ˚.✨⋆ PlunEStim

PlunEStim is a Software running a Discord BOT as Client, managing 1+ EStim units using 2B-Estim Board over BT or Serial.

> [!NOTE] Better readibility
> Documentation is made using [Obsidian](https://obsidian.md/), to have the best reading use this folder as vault.

## ˚.✨⋆ Introductions

This repository is a personnal project, updates, fix or new features happens when I want to spend some free time into that project. I'll not reply to any ask on how to use it or such, ask but i'll may not reply.

## ˚.✨⋆ Hardware Setup

```
- a lot of wires for estim targets
- 3 x 2B units (2 Ch Estim each) over Bluetooth
- 2 x BT motion sensor (fixed on body) (wip: rework)
- 1 x BT noise sensor (wip: rework)
- A computer to run PlunEStim
```

## ˚.✨⋆ [[Events]]
E

## ˚.✨⋆ [[Actions]]
Actions are payload (values) send to 1 or more EStim Units, mostly issued by **Events**, stored in queue waiting to be executed except when Action is Cumulative.

## ˚.✨⋆ Sensors

Sensors are used to monitor @Subject actions, monitored actions;

- Noise (Subject do more than {**x**} decibels)
- Motion  (Sensor move or not)
- Position (Sensor is/isn't in the area defined)

You can add "Action Rules", whenever the @Subject trigger a monitored action rule, trigger a consequences (apply profile, increase/decrease level of outputs)

