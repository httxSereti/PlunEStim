# # Ramp
# Use new vars max/min/cycle/back_to_min
# max=current set for level
# min=% of max , if 100% -> no ramp
# cycle=duration in sec of for min->max
# back_to_min = bool if decrease after max to min or restart from min
# task with 0,5 cycle for calc new value for each channel

import asyncio
import datetime
import json
import logging
import math
import os
import os.path
import pathlib
import random
import re
import time
import traceback
import uuid
from functools import partial
from threading import Thread
from typing import Optional

import jwt
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import aiohttp
import bluetooth  # type: ignore
import dotenv
import nextcord
import serial.tools.list_ports  # type: ignore


from bleak import BleakClient
from bleak.exc import BleakDeviceNotFoundError
from nextcord import Interaction, SlashOption
from nextcord.ext.commands import Bot as NextcordBot
from nextcord.ext import tasks

from pprint import pprint

from constants import DISCORD_GUILD_IDS

from profiles import ProfileModule

from typings import *
from typings import Permission
from services.chaster import *
from services.notifier import *
from utils import *

from store import Store
from models.User import User

from utils.users.generate_root_access import generate_root_access

from api.rest import users, auth, admin

# load env
dotenv.load_dotenv('config.env')

# DEBUG setting
ENABLE_MK2BT = True  # Disable mk2bt thread
ENABLE_BT_SENSORS = True  # Disable BT sensors thread

# API change
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

# Directory
DIR_BACKUP = pathlib.Path(os.getenv('DIR_BACKUP')) # type: ignore
DIR_PROFILE = pathlib.Path(os.getenv('DIR_PROFILE')) # type: ignore
DIR_TMP = pathlib.Path(os.getenv('DIR_TMP')) # type: ignore

# Chaster API
CHASTER_TOKEN = os.getenv('CHASTER_TOKEN')
CHASTER_URL = os.getenv('CHASTER_URL')
CHASTER_HEADERS = {'accept': 'application/json', 'Authorization': f'Bearer {CHASTER_TOKEN}', 'Content-Type': 'application/json'}

# BT serial configuration for 2B
SERIAL_BAUDRATE = 9600
SERIAL_RETRY = 5
SERIAL_TIMEOUT = 2
SERIAL_KEEPALIVE = 20  # check every x second the connexion (100 ms steps)
BT_UNITS = ("UNIT1", "UNIT2", "UNIT3")

# Bot config
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Default event config
with open('configurations/event_action.json') as json_file:
    EVENT_ACTION = json.load(json_file)

# Limit for estim level for every usage
with open('configurations/usage_limit.json') as json_file:
    USAGE_LIMIT = json.load(json_file)

# hardware units settings
with open('configurations/default_usage.json') as json_file:
    DEFAULT_USAGE = json.load(json_file)

# starting value
with open('configurations/init_settings.json') as json_file:
    DEFAULT_USAGE_SETTING = json.load(json_file)

# Bluetooth sensors type/mac/service_id
with open('configurations/bt_sensors.json') as json_file:
    BT_SENSORS = json.load(json_file)
    
with open('configurations/configuration.json') as json_file:
    CONFIGURATION = json.load(json_file)

# Debug level to discord channel
BOT_LOG_LEVEL = logging.INFO
BOT_MSG_LEVEL = logging.WARNING

# Others REGEX
REGEX_LEVEL_FORMAT = r'(%*[\\+,-]*)([1-9]*\d)$'

# 2B mode description
MODE_2B = ({"id": "pulse", "adj_1": "rate", "adj_2": "feel"},
           {"id": "bounce", "adj_1": "rate", "adj_2": "feel"},
           {"id": "continuous", "adj_1": "feel", "adj_2": ""},
           {"id": "flo", "adj_1": "rate", "adj_2": "feel"},
           {"id": "asplit", "adj_1": "rate", "adj_2": "feel"},
           {"id": "bsplit", "adj_1": "rate", "adj_2": "feel"},
           {"id": "wave", "adj_1": "flow", "adj_2": "steep"},
           {"id": "waterfall", "adj_1": "flow", "adj_2": "steep"},
           {"id": "squeeze", "adj_1": "rate", "adj_2": "feel"},
           {"id": "milk", "adj_1": "rate", "adj_2": "feel"},
           {"id": "throb", "adj_1": "low", "adj_2": "high"},
           {"id": "thrust", "adj_1": "low", "adj_2": "high"},
           {"id": "cycle", "adj_1": "low", "adj_2": "high"},
           {"id": "twist", "adj_1": "low", "adj_2": "high"},
           {"id": "random", "adj_1": "range", "adj_2": "feel"},
           {"id": "step", "adj_1": "steep", "adj_2": "feel"},
           {"id": "training", "adj_1": "steep", "adj_2": "feel"})

# Values for arguments checking about power and timing
CHECK_ARG = {
    'POWER_LEVEL': ('L', 'H', 'D'),
    'POWER_BIAS': ('CHA', 'CHB', 'AVG', 'MAX'),
    'POWER_MAP': ('A', 'B', 'C'),
    'RAMP_SPEED': ('X1', 'X2', 'X3', 'X4'),
    'WRAP_FACTOR': ('X1', 'X2', 'X4', 'X8', 'X16', 'X32')
}

# firmware command , order is important
FW_2B_CMD = {
    'level_h': 'L-H',  # power Low/High
    'level_d': '-Y',  # power dynamic mode
    'power_bias': 'Q',  # power bias Q0=chA,Q1=chB,Q2=avg,Q3=max
    'level_map': 'O',  # power curve O0=Map A/O1=Map B/02= Map C
    'mode': 'M',  # mode see mode description
    'adj_1': 'C',  # waveform set 1
    'adj_2': 'D',  # waveform set 2
    'adj_3': 'R',  # ramp speed RO=x1,R1=x2,R2=x3,R3=x4
    'adj_4': 'W',  # warp factor WO=x1,W1=x2,W2=x4,W3=x8,W4=x16,W5=x32
    'ch_A': 'A',  # chA level
    'ch_B': 'B'  # chB level
}

# fields used for profile
PROFILE_FIELDS = ['ch_A_max', 'ch_B_max',
                  'adj_1_max', 'adj_2_max', 'adj_3', 'adj_4',
                  'mode', 'level_h', 'level_d', 'power_bias', 'level_map',
                  'ch_A_ramp_phase', 'ch_A_ramp_prct',
                  'ch_B_ramp_phase', 'ch_B_ramp_prct',
                  'adj_1_ramp_phase', 'adj_1_ramp_prct',
                  'adj_2_ramp_phase', 'adj_2_ramp_prct',
                  'ramp_time', 'ramp_wave'
                  ]

# Queue statistics
queue_stats = {
    'waiting': 0,
    'constant': 0,
    'running': 0,
    'done': 0
}

# --start---------

# init logging
logger = logging.getLogger()


# filter
def filter_logger(record):
    # if record.module == 'proactor_events':
    #   return False
    return True


# File
logging.basicConfig(level=logging.DEBUG,
                    format='[%(asctime)s] %(threadName)s %(module)s %(message)s',
                    datefmt='%H:%M:%S',
                    filename='log.txt',
                    filemode='w')
# Console
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter('[%(asctime)s] %(threadName)s %(module)s %(message)s'))
console.addFilter(filter_logger)
logger.addHandler(console)
# Discord Log
# debug
logger_nextcord = logging.getLogger('nextcord')
logger_nextcord.setLevel(logging.INFO)
handler_nextcord = logging.FileHandler(filename='nextcord.log', encoding='utf-8', mode='w')
handler_nextcord.setFormatter(logging.Formatter('[%(asctime)s]%(levelname)s:%(name)s: %(message)s'))
logger_nextcord.addHandler(handler_nextcord)

# init Store
store = Store()

#------------------
# fastAPI
#------------------

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

app = FastAPI()

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# init multi threading
threads_settings = {}

# Slash_Command constantes
PROFILE_RANDOM = 'ABCDEFGHIJ'
PROFILE_AVAILABLE = {
    'Cage only': 'A',
    'rotate stimuling pulse': 'B',
    'rotate stimuling continous': 'C',
    'ass fuck': 'D',
    'endless edging': 'E',
    'mix pain/edge': 'F',
    'hard mix pain/edge': 'G',
    'torture': 'H',
    'stressful': 'I',
    'spank': 'J',
    'endless intense edging': 'K',
    'nothing': 'Z',
    'random': 'X'
}
CHOICE_UNIT = ('1', '2', '3', '12', '23', '123')
CHOICE_UNIT_RANDOM = {
    '1': '1',
    '2': '2',
    '3': '3',
    '12': '12',
    '23': '23',
    '123': '123',
    'Random_many_on_12': '12RM',
    'Random_many_on_23': '23RM',
    'Random_many_on_123': '123RM',
    'Random_one_on_12': '12RO',
    'Random_one_on_23': '23RO',
    'Random_one_on_123': '123RO',
}
CHOICE_UNIT_UNIQ = ('1', '2', '3')
CHOICE_CHANNEL = ('A', 'B', 'AB')
CHOICE_CHANNEL_UNIQ = ('A', 'B')
CHOICE_CHANNEL_RANDOM = {
    'A': 'A',
    'B': 'B',
    'AB': 'AB',
    'Random many on AB': 'ABRM',
    'Random one on AB': 'ABRO'
}
CHOICE_LEVEL_ACTION = {
    'absolute': '',
    'add_relative': '+',
    'sub_relative': '-',
    'random_relative': '=',
    'add_pourcent': '%+',
    'sub_pourcent': '%-',
    'random_pourcent': '%='
}
CHOICE_ADV_POWER = {
    'Power Low': 'P0',
    'Power High': 'P1',
    'Power Dynamic': 'P2',
    'Power Bias Ch A': 'B0',
    'Power Bias Ch B': 'B1',
    'Power Bias Ch average': 'B2',
    'Power Bias Ch max': 'B3',
    'Power Map A': 'M0',
    'Power Map B': 'M1',
    'Power Map C': 'M2'
}
CHOICE_ADV_TIMER = {
    'Ramp_speed_x1': 'S0',
    'Ramp_speed_x2': 'S1',
    'Ramp_speed_x3': 'S2',
    'Ramp_speed_x4': 'S3',
    'Wrap_factor_x1': 'W0',
    'Wrap_factor_x2': 'W1',
    'Wrap_factor_x4': 'W2',
    'Wrap_factor_x8': 'W3',
    'Wrap_factor_x16': 'W4',
    'Wrap_factor_x32': 'W5'
}
CHOICE_MODE = []
CHOICE_MODE_SETTING = []
CHOICE_RAMP_TARGET = {'Channel A': 'ch_A', 'Channel B': 'ch_B', 'waveform set1': 'adj_1',
                      'waveform set2': 'adj_2'}
for idx_mode in range(len(MODE_2B)):
    CHOICE_MODE.append(MODE_2B[idx_mode]['id'])
    for idx_setting in ('adj_1', 'adj_2'):
        if MODE_2B[idx_mode][idx_setting] not in CHOICE_MODE_SETTING and MODE_2B[idx_mode][idx_setting] != '':
            CHOICE_MODE_SETTING.append(MODE_2B[idx_mode][idx_setting])
# Available Target
CHOICE_USAGE = USAGE_LIMIT.keys()
##Available Target + All
CHOICE_USAGE_ALL = list(CHOICE_USAGE)
CHOICE_USAGE_ALL.append('all')
# Available Target + All + Random
CHOICE_USAGE_ALL_RND = list(CHOICE_USAGE)
CHOICE_USAGE_ALL_RND.append('all')
CHOICE_USAGE_ALL_RND.append('rnd')
CHOICE_USAGE_ALL_RND.append('rnd multiple')
# Power level selection
CHOICE_POWER = {'Low': 'L', 'High': 'H'}
class UnitConnect:
    """
 Manage the connexion to the 2B unit with the serial over BT
    """

    def __init__(self, unit_name: str, settings: dict) -> None:
        """
        init all attributes
        Args:
            unit_name: BT name of the 2B module UNITx
            settings: target settings for the 2B
        """
        self.name = unit_name
        self.status = 'not connected'
        self.settings_target = settings
        # settings of the 2B
        self.settings_current = {
            "ch_A": 0,
            "ch_B": 0,
            "adj_1": 50,
            "adj_2": 50,
            "mode": 0,
            "level_h": False,
            "ch_link": False,
        }
        # returned values from the 2B
        self.settings_return = {
            "ch_A": 0,
            "ch_B": 0,
            "adj_1": 50,
            "adj_2": 50,
            "mode": 0,
            "level_h": False,
            "ch_link": False,
            "bat_level": 0
        }
        # serial access for the BT connexion
        self.serial_dev = None
        # start trying to connect the 2B
        self.detect()

    def parse_reply(self, reply_raw: bytes) -> Optional[str]:
        """
        parse the data returned by the 2B, if it's fail the serial connexion is reinitialized
        Args:
            reply_raw: raw data from serial reply of the 2B

        Returns:
            Firmware version off the 2B if successful
        """
        reply = reply_raw.decode().rstrip('\r\n')

        logger.debug('{} 2B reply : {}'.format(self.name, reply))

        if m := re.match(r"^(\d+):(\d+):(\d+):(\d+):(\d+):(\d+):([L,H]):(\d+):(\d+):(\d+):(\d+):(\d+):(2\..+)$", reply):
            self.settings_return["bat_level"] = int(m[1])
            self.settings_return["ch_A"] = int(m[2]) // 2
            self.settings_return["ch_B"] = int(m[3]) // 2
            self.settings_return["adj_1"] = int(m[4]) // 2
            self.settings_return["adj_2"] = int(m[5]) // 2
            self.settings_return["mode"] = int(m[6])
            self.settings_return["level_h"] = (m[7] == 'H')
            self.settings_return["level_d"] = (m[7] == 'D')
            self.settings_return["power_bias"] = int(m[8])
            self.settings_return["level_map"] = int(m[10])
            self.settings_return["adj_4"] = int(m[11])
            self.settings_return["adj_3"] = int(m[12])
            return str(m[13])  # return firmware version
        logger.info('Fail to parse the 2B {} reply {} -> reconnecting'.format(self.name, reply))
        self.detect()
        return None

    def detect(self):
        """
        Detect the BT module of the 2B and initialize the serial port
        Returns: serial port object
        """
        self.settings_target["cnx_ok"] = False
        self.settings_target["sync"] = False
        # close previous open (lost connexion)
        if self.serial_dev:
            if self.serial_dev.isOpen():
                logger.debug('{} close serial port'.format(self.name))
                self.serial_dev.close()
            else:
                logger.debug('{} port already close'.format(self.name))

        # loop for BT serial connexion until succes
        while True:
            logger.debug('{} BTscan for devices'.format(self.name))
            nearby_devices = bluetooth.discover_devices(duration=1, lookup_names=True,
                                                        flush_cache=True, lookup_class=False)
            #
            if len(nearby_devices) == 0:
                time.sleep(5)  # BT desactivate
            # Loop on BT device to find the good one
            for addr, name in nearby_devices:
                if self.name == name:
                    logger.debug('{} detected in {}'.format(self.name, addr))
                    com_ports = list(serial.tools.list_ports.comports())
                    addr = addr.replace(':', '')
                    # Find the associated COM port
                    for com, des, hwenu in com_ports:
                        if addr in hwenu:
                            logger.debug('{} serial port detected {}'.format(self.name, com))
                            for retry in range(1, SERIAL_RETRY):
                                try:
                                    self.serial_dev = serial.Serial(
                                        com,
                                        SERIAL_BAUDRATE,
                                        timeout=SERIAL_TIMEOUT,
                                        bytesize=serial.EIGHTBITS,
                                        parity=serial.PARITY_NONE,
                                        stopbits=serial.STOPBITS_ONE)
                                except serial.SerialException:
                                    logger.debug('{} serial retry open {}'.format(self.name, retry))
                                    time.sleep(0.5)
                                else:
                                    self.serial_dev.write(b"E\n\r")  # reset
                                    firmware_version = self.parse_reply(self.serial_dev.readline())
                                    if firmware_version is not None:
                                        logger.info(f'{self.name} serial access to 2B is OK')
                                        logger.debug(f'{self.name} version={firmware_version}')
                                        self.settings_target["cnx_ok"] = True
                                        return self.serial_dev
                                    logger.info('{} 2B not responding'.format(self.name))
                                    self.serial_dev.close()
                                    logger.debug('{} serial retry open {}'.format(self.name, retry))
                                    time.sleep(0.5)

    def send_cmd(self, cmd: str) -> Optional[str]:
        """
        Send a command to the 2B
        Args:
            cmd: command in 2B format

        Returns:
            2B text reply
        """
        cmd = cmd + "\n\r"  # standard CR for the 2B
        while True:
            try:
                self.serial_dev.write(cmd.encode())
            except serial.SerialException:
                self.detect()
            else:
                return self.parse_reply(self.serial_dev.readline())

    def check_2b_settings(self) -> bool:
        """
        Check if the 2B settings are equal to the targets values and adjusts if needed
        Returns:
            True if settings match the target
        """
        self.serial_dev.write(b"\n\r")
        self.parse_reply(self.serial_dev.readline())
        no_updated = True
        # loop on all 2B settings (the order is important)
        for field in FW_2B_CMD.keys():
            # check if update is needed
            if self.settings_return[field] != self.settings_target[field]:
                logger.debug('{} adjust {} {} -> {}'.format(self.name, field,
                                                            self.settings_return[field], self.settings_target[field]))
                # the update command can be fixed value or an argument
                if len(FW_2B_CMD[field]) == 1:
                    cmd = '{}{}'.format(FW_2B_CMD[field], self.settings_target[field])
                else:
                    cmd = FW_2B_CMD[field].split('-')[int(self.settings_target[field])]
                # if something to do
                if cmd != '':
                    logger.debug('{} cmd {}'.format(self.name, cmd))
                    # check if target and 2B synchronized on the next call
                    self.settings_target["sync"] = False
                    no_updated = False
                    self.send_cmd(cmd)
        # if no change it is synchronized !
        if no_updated:
            self.settings_target["sync"] = True
        return no_updated


def thread_bt_unit(unit: str, settings: dict) -> None:
    """
    Manage on 2B unit, this function must run inside a thread
    Args:
        unit: name of the 2B unit like UNITx
        settings: dict with the target settings for this unit

    Returns:
    """

    while True:
        try:
            # create bt object inside a thread
            bt = UnitConnect(unit, threads_settings[unit])

            cycle = 0  # for the keepalive
            while True:
                # if new values are waiting
                if settings["updated"]:
                    # the 2BT is not in sync if new value wait
                    settings["sync"] = False
                    # reset the updated state
                    settings["updated"] = False
                    # Set the target with the new values
                    for setting in FW_2B_CMD.keys():
                        bt.settings_target[setting] = settings[setting]
                    bt.check_2b_settings()
                    cycle = 0  # reset keepalive
                elif cycle > SERIAL_KEEPALIVE:
                    # check connection state
                    bt.check_2b_settings()
                    cycle = 0
                else:
                    time.sleep(0.1)
                    cycle = cycle + 1
        except Exception as err:
            logger.info(f"Thread error with estim unit {unit} : {err=}, {type(err)=}")
            time.sleep(30)


class Bot2b3(NextcordBot):
    @staticmethod
    async def check_unit(ctx, unit_arg: str) -> str:
        """
        Check unit argument and decode random options
        Args:
            ctx: discord context
            unit_arg: argument for unit with or without random option
        Returns:
            unit valid list or empty string if invalid syntax
        """
        unit_arg = unit_arg.upper()
        if m := re.match(r'^([1-3]+)RO$', unit_arg):
            return m.group(1)[random.randint(0, (len(m.group(1)) - 1))]
        if m := re.match(r'^([1-3]+)RM$', unit_arg):
            new_val = ''
            for unit in m.group(1):
                if random.randint(0, 1) == 1:
                    new_val = new_val + unit
            if new_val == '':  # if nothing is get in the multi random
                new_val = m.group(1)[random.randint(0, (len(m.group(1)) - 1))]
            return new_val
        if re.match('^[1-3]+$', unit_arg):
            return unit_arg
        if ctx:
            await ctx.response.send_message('invalid units argument')
        return ''

    @staticmethod
    def calc_new_val(newval: str, unit: str, val: str) -> int:
        """
        Decode level value
        Args:
            newval: new value
            unit: 2B unit id
            val: field to change

        Returns:
            the new value
        """
        if match := re.match(REGEX_LEVEL_FORMAT, newval):
            if match.group(1) == '+':
                new_val = min(threads_settings[unit][val] + int(match.group(2)), 99)
            elif match.group(1) == '-':
                new_val = max(threads_settings[unit][val] - int(match.group(2)), 0)
            elif match.group(1) == '%+':
                new_val = min(
                    threads_settings[unit][val] + math.ceil(threads_settings[unit][val] * int(match.group(2)) / 100),
                    99)
            elif match.group(1) == '%-':
                new_val = min(
                    threads_settings[unit][val] - math.ceil(threads_settings[unit][val] * int(match.group(2)) / 100),
                    99)
            else:
                new_val = int(match.group(2))
            return new_val
        return threads_settings[unit][val]

    @staticmethod
    async def check_mode(ctx, mode: str) -> Optional[int]:
        """
        Return the id of the mode
        Args:
            ctx: discord context
            mode: mode name
        Returns:
            id of the mode, None if not exist
        """
        mode = mode.lower()
        for mode_id in range(len(MODE_2B)):
            if MODE_2B[mode_id]['id'] == mode.lower():
                return mode_id
        if ctx:
            await ctx.response.send_message('invalid mode argument')
        return None

    @staticmethod
    async def check_ch(ctx, ch_arg: str) -> str:
        """
        Check unit argument and decode random options
        Args:
            ctx: discord context
            ch_arg: channels list with RO at the end if the random concerne only one unit and RM if many channels
        Returns:
            channel list, empty string if invalid syntax
        """
        ch_arg = ch_arg.upper()
        if m := re.match(r'^([A,B]+)RO$', ch_arg):
            return m.group(1)[random.randint(0, (len(m.group(1)) - 1))]
        if m := re.match(r'^([A,B]+)RM$', ch_arg):
            new_val = ''
            for ch in m.group(1):
                if random.randint(0, 1) == 1:
                    new_val = new_val + ch
            if new_val == '':  # if nothing is get in the multi random
                new_val = m.group(1)[random.randint(0, (len(m.group(1)) - 1))]
            return new_val
        if re.match('^[A,B]+$', ch_arg):
            return ch_arg
        if ctx:
            await ctx.response.send_message('invalid channel argument')
        return ''

    @staticmethod
    async def check_duration(ctx, dur_arg: str) -> int:
        """
        Check duration argument and decode random options
        Args:
            ctx: discord context
            dur_arg: duration number, for randomized val the syntax is min>max

        Returns: duration number, -1 if invalid syntaxe

        """
        if m := re.match(r'^(\d+)>(\d+)$', dur_arg):
            return random.randint(int(m.group(1)), int(m.group(2)))
        if m := re.match(r'^(\d+)$', dur_arg):
            return int(m.group(1))
        if ctx:
            await ctx.response.send_message('invalid duration argument')
        return -1

    @staticmethod
    async def check_sensor_level(ctx, level_arg: int) -> int:
        """
        Check sensor level arg
        Args:
            ctx: discord context
            level_arg: level of the threshold

        Returns: level, -1 if invalid

        """
        if 2 < level_arg < 51:
            return level_arg
        if ctx:
            await ctx.response.send_message('invalid level argument')
        return -1

    @staticmethod
    async def check_sensor_duration(ctx, duration_arg: int) -> int:
        """
        Check duration level arg
        Args:
            ctx: discord context
            duration_arg: level of the threshold

        Returns: duration, -1 if invalid

        """
        if 0 < duration_arg < 301:
            return duration_arg
        if ctx:
            await ctx.response.send_message('invalid duration argument')
        return -1

    @staticmethod
    async def check_level(ctx, lvl_arg: str) -> str:
        """
        Check level argument and decode random options
        Args:
            ctx: discord context
            lvl_arg: level number, relative/absolue and/or random options are documented in help

        Returns: level number with all prefix , '' if invalid syntaxe
        """
        # random absolute value
        prefix = ''
        # relative value ?
        if m := re.match(r'^%(.*)', lvl_arg):
            prefix = '%'
            lvl_arg = m.group(1)
        # random sign ? -> replace by relative value
        if m := re.match(r'^=(.*)', lvl_arg):
            lvl_arg = '-+'[random.randint(0, 1)] + m.group(1)
        # relative value
        if m := re.match(r'^([+,-])(.*)$', lvl_arg):
            prefix = prefix + m.group(1)
            lvl_arg = m.group(2)
        # random range
        if m := re.match(r'^(\d+)>(\d+)$', lvl_arg):
            return prefix + str(random.randint(int(m.group(1)), int(m.group(2))))
        # fixed value
        if m := re.match(r'^(\d+)$', lvl_arg):
            return prefix + m.group(1)
        if ctx:
            await ctx.response.send_message('invalid level argument')
        return ''

    #
    # refactoré avant
    #

    def __init__(
        self,
    ):
        super().__init__(
            command_prefix="/", 
            description='ESTIM Remote management',
            help_command=None,
            intents=intents,
            rollout_all_guilds=True,
            default_guild_ids=DISCORD_GUILD_IDS
        )
        
        self.initialized: bool = False
        
        # Initialize Environment Vars
        self.subjectId: int = CONFIGURATION['subjectDiscordId']
        self.administrators: list[int] = [self.subjectId, CONFIGURATION['trustedDiscordId']]
        
        # @TextChannel
        self.cmdsChannel: nextcord.abc.GuildChannel | None = None
        self.logChannel: nextcord.abc.GuildChannel | None = None
        self.statusChannel: nextcord.abc.GuildChannel | None = None
        
        self.chaster: Chaster = Chaster(self)
        self.notifier: Notifier = Notifier(self)
        
        # Queue        
        self.queueRunning = True  # Queue status.
        self.action_queue = []  # async actions for estim config
        self.back_action_queue = []  # async back actions for estim config
        
        # Queue V2
        self.queueActions: list[ActionDict] = []
        # pprint(self.queueActions)
        
        # self.queueActions.append({
        #     "type": "PROFILE",
        #     "issuer": "user:Sereti",
        #     "duration": 15
        # })
        
        # pprint(self.queueActions)
        
        
        self.previous_2B_sync = False  # previous global 2B sync
        
        self.chaster_lockid = None  # id of the current chaster lock
        self.chaster_taskid = None  # id of the task extension
        self.chaster_task_pool = 0  # number of poll
        self.chaster_taskvote = {}  # vote list for task
        self.chaster_history_event_parsed = []  # wof/vote list for duration already parsed
        self.chaster_pilloryid = None  # id of the pillory extension
        self.chaster_pillory_vote_by_id = {}
        
        @self.slash_command(name='backup', description='Backup bot config')
        async def bot_backup(
            interaction: Interaction,
            filename: str = SlashOption(name='name', description='backup_name', required=True)
        ):
            backup_data = {
                'EVENT_ACTION': EVENT_ACTION,
                'threads_settings': threads_settings,
                'sensors_settings': store.get_all_sensors_settings(),
                'USAGE_LIMIT': USAGE_LIMIT
            }
            filename = filename + '.json'
            bck_file = open(DIR_BACKUP / filename, 'w')
            json.dump(backup_data, bck_file, indent=4)
            bck_file.close()
            await interaction.response.send_message("backup done")

        @self.slash_command(name='restore', description='Restore bot config')
        async def bot_recover(
            interaction: Interaction,
            filename: str = SlashOption(
                name='name',
                description='backup_name',
                required=True
            )
        ) -> None:
            filename = filename + '.json'
            bck_file = open(DIR_BACKUP / filename, 'r')
            backup_data = json.load(bck_file)
            bck_file.close()
            # actions
            for action in backup_data['EVENT_ACTION']:
                EVENT_ACTION[action] = backup_data['EVENT_ACTION'][action]
            # 2B
            for bck_bt_name in backup_data['threads_settings']:
                threads_settings[bck_bt_name]['sync'] = False
                for field in backup_data['threads_settings'][bck_bt_name]:
                    if field == "updated":
                        threads_settings[bck_bt_name][field] = True
                    else:
                        threads_settings[bck_bt_name][field] = backup_data['threads_settings'][bck_bt_name][field]

            # restore Sensors
            for sensor_name in backup_data['sensors_settings'].keys():
                
                # fetch current sensor configuration
                current_sensor_config = store.get_sensor_setting(sensor_name)
                
                # no sensor, so init it
                if current_sensor_config is None:
                    current_sensor_config = {}
                
                # explore fields
                for field in backup_data['sensors_settings'][sensor_name].keys():
                    # restore only these
                    if re.search(r"(_alarm_level|_delay_on|_delay_off)", field):
                        current_sensor_config[field] = backup_data['sensors_settings'][sensor_name][field]
                
                # Save
                store.set_sensor_setting(sensor_name, current_sensor_config)
                            
            # limit
            for usage in backup_data['USAGE_LIMIT']:
                USAGE_LIMIT[usage] = backup_data['USAGE_LIMIT'][usage]
            await interaction.response.send_message("Recover done")

        # noinspection PickleLoad
        @self.slash_command(name='profile', description='Manage profile')
        async def manage_profile(interaction: Interaction,
                                 action_arg: str = SlashOption(name="action",
                                                               description="what we do on profile",
                                                               required=True,
                                                               choices=['save', 'apply', 'info']
                                                               ),
                                 name_arg: str = SlashOption(name="name",
                                                             description="name of the profile",
                                                             required=True,
                                                             choices=PROFILE_AVAILABLE
                                                             ),
                                 lvl_prct_arg: int = SlashOption(name="lvl_prct",
                                                                 description="Prct of the definied level when apply",
                                                                 required=False,
                                                                 default=100,
                                                                 min_value=10,
                                                                 max_value=300
                                                                 )) -> None:
            name_arg = name_arg.upper() + '.json'
            if action_arg == 'save':
                bck_file = open(DIR_PROFILE / name_arg, 'w')
                backup_data = {'threads_settings': threads_settings}
                # Clean some values
                for unit in BT_UNITS:
                    threads_settings[unit]['ch_A'] = 0
                    threads_settings[unit]['ch_B'] = 0
                    threads_settings[unit]['ramp_progress'] = 0
                json.dump(backup_data, bck_file, indent=4)
                bck_file.close()
                await interaction.response.send_message("profile {} created".format(name_arg))
            else:
                bck_file = open(DIR_PROFILE / name_arg, 'r')
                backup_data = json.load(bck_file)
                bck_settings = backup_data['threads_settings']
                bck_file.close()
                if action_arg == 'apply':
                    # Estim settings
                    for bck_bt_name in bck_settings:
                        threads_settings[bck_bt_name]['sync'] = False
                        threads_settings[bck_bt_name]['updated'] = True
                        for field in bck_settings[bck_bt_name]:
                            if field in PROFILE_FIELDS:
                                if field in ('ch_A_max', 'ch_B_max'):
                                    threads_settings[bck_bt_name][field] = int(bck_settings[bck_bt_name][field] * lvl_prct_arg / 100)
                                elif field in ('ch_A', 'ch_B', 'ramp_progress'):
                                    threads_settings[bck_bt_name][field] = 0  # Ramp will update the level
                                else:
                                    threads_settings[bck_bt_name][field] = bck_settings[bck_bt_name][field]
                    # end
                    await interaction.response.send_message("profile {} applied".format(name_arg))
                else:
                    txt = ['---- Profile {} settings ---'.format(name_arg)]
                    for unit_name in bck_settings:
                        # power info
                        if threads_settings[unit_name]['level_d']:
                            level_txt = CHECK_ARG['POWER_BIAS'][threads_settings[unit_name]['power_bias']]
                        elif threads_settings[unit_name]['level_h']:
                            level_txt = 'H'
                        else:
                            level_txt = 'L'
                        level_txt = level_txt + chr(threads_settings[unit_name]['level_map'] + ord('a'))
                        # data for the unit
                        txt.append('{} chA {}: lvl {} Ramp {}% {}° '.format(
                            unit_name,
                            threads_settings[unit_name]['ch_A_use'],
                            threads_settings[unit_name]['ch_A_max'],
                            threads_settings[unit_name]['ch_A_ramp_prct'],
                            threads_settings[unit_name]['ch_A_ramp_phase']))
                        txt.append('{} chB {}: lvl {} Ramp {}% {}° '.format(
                            unit_name,
                            threads_settings[unit_name]['ch_B_use'],
                            threads_settings[unit_name]['ch_B_max'],
                            threads_settings[unit_name]['ch_B_ramp_prct'],
                            threads_settings[unit_name]['ch_B_ramp_phase']))
                        txt.append('{} {}: lvl {} Ramp {}% {}° '.format(
                            unit_name,
                            MODE_2B[threads_settings[unit_name]['mode']]['adj_1'],
                            threads_settings[unit_name]['adj_1_max'],
                            threads_settings[unit_name]['adj_1_ramp_prct'],
                            threads_settings[unit_name]['adj_1_ramp_phase']))
                        txt.append('{} {}: lvl {} Ramp {}% {}° '.format(
                            unit_name,
                            MODE_2B[threads_settings[unit_name]['mode']]['adj_2'],
                            threads_settings[unit_name]['adj_2_max'],
                            threads_settings[unit_name]['adj_2_ramp_prct'],
                            threads_settings[unit_name]['adj_2_ramp_phase']))
                        txt.append('{} mode:{} ramp time:{} wave:{} Power:{} hardware ramp:{} wrap:{}'.format(
                            unit_name,
                            MODE_2B[threads_settings[unit_name]['mode']]['id'],
                            threads_settings[unit_name]['ramp_time'],
                            threads_settings[unit_name]['ramp_wave'],
                            level_txt,
                            (CHECK_ARG['RAMP_SPEED'][threads_settings[unit_name]['adj_3']]),
                            (CHECK_ARG['WRAP_FACTOR'][threads_settings[unit_name]['adj_4']])
                        ))
                        # end
                    await interaction.response.send_message("\n".join(txt))

        @self.slash_command(name='event_multi',
                            description='Associate event with level multiplier change')
        async def bot_event_multi(interaction: Interaction,
                                  event_arg: str = SlashOption(
                                      name="event",
                                      description="event name",
                                      choices=EVENT_ACTION.keys(),
                                      required=True
                                  ),
                                  usage_arg: str = SlashOption(
                                      name="target",
                                      description="Estim output",
                                      choices=CHOICE_USAGE_ALL,
                                      required=True
                                  ),
                                  prct_arg: int = SlashOption(
                                      name="prct",
                                      description="percentage add or sub to the multiplier",
                                      required=True,
                                      min_value=-20,
                                      default=5,
                                      max_value=20
                                  ),
                                  rnd_arg: int = SlashOption(
                                      name="random",
                                      description="randomize between 0 and prct value",
                                      choices={'Yes': True, 'No': False},
                                      required=True,
                                  )
                                  ) -> None:
            if await check_permission(interaction, 'administrator'):
                # Event exist ?
                if event_arg not in EVENT_ACTION:
                    await interaction.response.send_message('invalid event')
                    return None

                # add event
                EVENT_ACTION[event_arg] = {
                    "type": 'multi',
                    "target": usage_arg,
                    "prct": prct_arg,
                    "rnd": rnd_arg
                }
            await interaction.response.send_message('event {} modified'.format(event_arg))
            return None

        @self.slash_command(name='event_level',
                            description='Associate event with Estim config change')
        async def bot_event_level(interaction: Interaction,
                                  event_arg: str = SlashOption(
                                      name="event",
                                      description="event name",
                                      choices=EVENT_ACTION.keys(),
                                      required=True
                                  ),
                                  unit_arg: str = SlashOption(
                                      name="unit",
                                      description="units impacted",
                                      choices=CHOICE_UNIT_RANDOM,
                                      required=True
                                  ),
                                  dest_arg: str = SlashOption(
                                      name="channels",
                                      description="channels impacted",
                                      choices=CHOICE_CHANNEL_RANDOM,
                                      required=True
                                  ),
                                  level_op: str = SlashOption(
                                      name="operation",
                                      description="how the level is changing",
                                      choices=CHOICE_LEVEL_ACTION,
                                      required=True
                                  ),
                                  level_arg_min: int = SlashOption(
                                      name="level_start",
                                      description="level or min level range",
                                      required=True,
                                  ),
                                  duration_arg_min: int = SlashOption(
                                      name="duration_start",
                                      description="duration or min duration range(sec),0=permanent",
                                      required=True,
                                  ),
                                  wait_arg: int = SlashOption(name="queuing",
                                                              description="put the action in queue",
                                                              required=True,
                                                              choices={'Yes': 1, 'No': 0}
                                                              ),
                                  level_arg_max: int = SlashOption(
                                      name="level_max",
                                      description="max level range",
                                      required=False,
                                  ),
                                  duration_arg_max: int = SlashOption(
                                      name="duration_max",
                                      description="max duration range (sec)",
                                      required=False,
                                  )
                                  ) -> None:
            if await check_permission(interaction, 'administrator'):
                # Event exist ?
                if event_arg not in EVENT_ACTION:
                    await interaction.response.send_message('invalid event')
                    return None
                # Unit valid ?
                if await self.check_unit(interaction, unit_arg) == '':
                    return None
                # Channel valid ?
                if await self.check_ch(interaction, dest_arg) == '':
                    return None
                level_arg = level_op + str(level_arg_min)
                if level_arg_max:
                    level_arg = level_arg + '>' + str(level_arg_max)
                level_arg = await self.check_level(interaction, level_arg)
                if not level_arg:
                    return None
                # Duration valid ?
                duration_arg = str(duration_arg_min)
                if duration_arg_max:
                    duration_arg = duration_arg + '>' + str(duration_arg_max)
                if await self.check_duration(interaction, duration_arg) < 0:
                    return None
                # add
                EVENT_ACTION[event_arg] = {
                    "type": 'lvl',
                    "unit": unit_arg,
                    "dest": dest_arg,
                    "level": level_arg,
                    "duration": duration_arg,
                    "wait": bool(wait_arg)
                }
            await interaction.response.send_message('event {} modified'.format(event_arg))
            return None

        @self.slash_command(name='event_duration',
                            description='Associate event with session duration increasing')
        async def bot_event_duration(interaction: Interaction,
                                     event_arg: str = SlashOption(
                                         name="event",
                                         description="event name",
                                         choices=EVENT_ACTION.keys(),
                                         required=True
                                     ),
                                     duration_arg: int = SlashOption(
                                         name="duration",
                                         description="number of minute added to the max duration",
                                         required=True,
                                         min_value=1,
                                         max_value=60
                                     ),
                                     add_arg: int = SlashOption(name="add_current",
                                                                description="add time also in resting time",
                                                                required=True,
                                                                choices={'Yes': 0, 'No': 1}
                                                                )

                                     ) -> None:
            if await check_permission(interaction, 'administrator'):
                # Event exist ?
                if event_arg not in EVENT_ACTION:
                    await interaction.response.send_message('invalid event')
                    return None
                # add
                EVENT_ACTION[event_arg] = {
                    "type": 'add',
                    "duration": duration_arg,
                    "only_max": bool(add_arg)
                }
            await interaction.response.send_message('event {} modified'.format(event_arg))
            return None

        @self.slash_command(name='event_profile',
                            description='Associate event with Estim profile')
        async def bot_event_profile(interaction: Interaction,
                                    event_arg: str = SlashOption(
                                        name="event",
                                        description="event name",
                                        choices=EVENT_ACTION.keys(),
                                        required=True
                                    ),
                                    profile_arg: str = SlashOption(
                                        name="profile",
                                        description="profile name",
                                        required=True
                                    ),
                                    level_arg: int = SlashOption(
                                        name="level_prct",
                                        description="percentage for level 100=original settings ",
                                        required=True,
                                        min_value=10,
                                        max_value=400
                                    ),
                                    duration_arg_min: int = SlashOption(
                                        name="duration_start",
                                        description="duration or min duration range(sec),0=permanent",
                                        required=True,
                                    ),
                                    wait_arg: int = SlashOption(name="queuing",
                                                                description="put the action in queue",
                                                                required=True,
                                                                choices={'Yes': 1, 'No': 0}
                                                                ),
                                    duration_arg_max: int = SlashOption(
                                        name="duration_max",
                                        description="max duration range (sec)",
                                        required=False,
                                    )
                                    ) -> None:
            if await check_permission(interaction, 'administrator'):
                # Event exist ?
                if event_arg not in EVENT_ACTION:
                    await interaction.response.send_message('invalid event')
                    return None
                # profile valid ?
                if not os.path.exists(DIR_PROFILE / (profile_arg.upper() + '.json')):
                    await interaction.response.send_message('profile not exist')
                    return None
                # Duration valid ?
                duration_arg = str(duration_arg_min)
                if duration_arg_max:
                    duration_arg = duration_arg + '>' + str(duration_arg_max)
                if await self.check_duration(interaction, duration_arg) < 0:
                    return None
                # add
                EVENT_ACTION[event_arg] = {
                    "type": 'pro',
                    "profile": profile_arg.upper(),
                    "level": level_arg,
                    "duration": duration_arg,
                    "wait": bool(wait_arg)
                }
            await interaction.response.send_message('event {} modified'.format(event_arg))
            return None

        @self.slash_command(name='mode',
                            description='Change Estim mode')
        async def bot_mode(interaction: Interaction,
                           unit_arg: str = SlashOption(name="unit",
                                                       description="Estim unit impacted with the new mode",
                                                       required=True,
                                                       choices=CHOICE_UNIT,
                                                       ),
                           mode_arg: str = SlashOption(name="mode",
                                                       description="New mode for the selected units",
                                                       required=True,
                                                       choices=CHOICE_MODE,
                                                       )) -> None:
            if await check_permission(interaction, 'administrator'):
                mode_id = await self.check_mode(interaction, mode_arg)
                if mode_id:
                    for unit in await self.check_unit(interaction, unit_arg):
                        unit = 'UNIT' + str(unit)
                        threads_settings[unit]['updated'] = True
                        threads_settings[unit]['mode'] = mode_id
                        if MODE_2B[mode_id]['adj_2'] == '':  # reset to adj_1 for modes without adj_2
                            threads_settings[unit]['adj_2'] = threads_settings[unit]['adj_1']
                    await interaction.response.send_message(
                        'new mode for unit {} is {}'.format(unit_arg, mode_arg))
            return None

        @self.slash_command(name='usage',
                            description='Change channel usage')
        async def bot_usage(interaction: Interaction,
                            unit_arg: str = SlashOption(name="unit",
                                                        description="Estim unit impacted with the new usage",
                                                        required=True,
                                                        choices=CHOICE_UNIT_UNIQ,
                                                        ),
                            ch_arg: str = SlashOption(name="channel",
                                                      description="Estim channel impacted with the new usage",
                                                      required=True,
                                                      choices=CHOICE_CHANNEL_UNIQ,
                                                      ),
                            usage_arg: str = SlashOption(name="usage",
                                                         description="Usage of the channel",
                                                         required=True,
                                                         choices=CHOICE_USAGE,
                                                         )) -> None:
            if await check_permission(interaction, 'administrator'):
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    for ch in await self.check_ch(interaction, ch_arg):
                        ch = 'ch_' + ch + '_use'
                        threads_settings[unit][ch] = usage_arg
                        threads_settings[unit]['updated'] = True
                await interaction.response.send_message(
                    'new usage for unit {} ch {} is {}'.format(unit_arg, ch_arg, usage_arg))
            return None

        #
        # ---------Refactoring
        #
        @self.slash_command(name='multi',
                            description='manuel multiplier change')
        async def bot_multi(interaction: Interaction,
                            usage_arg: str = SlashOption(
                                name="usage",
                                description="Estim ouput usage",
                                choices=CHOICE_USAGE_ALL,
                                required=True
                            ),
                            prct_arg: int = SlashOption(
                                name="prct",
                                description="new percentage for the multiplier",
                                required=True,
                                min_value=-50,
                                default=100,
                                max_value=200
                            ),
                            ):
            if await check_permission(interaction, 'administrator'):
                for unit in BT_UNITS:
                    for ch in ['A', 'B']:
                        # find channel with this usage
                        if threads_settings[unit][
                            f'ch_{ch}_use'] == usage_arg.lower() or usage_arg.lower() == 'all':
                            ch_name = f'ch_{ch}_multiplier'
                            threads_settings[unit]['updated'] = True
                            threads_settings[unit][ch_name] = prct_arg
                await interaction.response.send_message('Multiplier updated')
                return None

        # ----- Quick change

        # --- Quick Level ------
        @self.slash_command(name='add',
                            description='quick increase level')
        async def bot_add(interaction: Interaction,
                          usage_arg: str = SlashOption(
                              name="usage",
                              description="Estim ouput usage",
                              choices=CHOICE_USAGE_ALL,
                              required=True
                          )):
            if await check_permission(interaction, 'administrator'):
                txt = []
                level_arg = '%+5'
                for unit in BT_UNITS:
                    for ch in ['A', 'B']:
                        # find channel with this usage
                        if threads_settings[unit][f'ch_{ch}_use'] == usage_arg.lower() or usage_arg.lower() == 'all':
                            ch_name = f'ch_{ch}_max'
                            level_arg = await self.check_level(interaction, level_arg)
                            if level_arg:
                                new_val = self.calc_new_val(level_arg, unit, ch_name)
                                txt.append(">>new level for unit {} ch {} ({}) change from {} to {}".format(
                                    unit, ch, threads_settings[unit][f'ch_{ch}_use'], threads_settings[unit][ch_name],
                                    new_val))
                                threads_settings[unit]['updated'] = True
                                threads_settings[unit][ch_name] = new_val
                if len(txt) == 0:
                    await interaction.response.send_message('There are no channel with this usage')
                else:
                    await interaction.response.send_message("\n".join(txt))
                return None

        @self.slash_command(name='sub',
                            description='quick decrease level')
        async def bot_sub(interaction: Interaction,
                          usage_arg: str = SlashOption(
                              name="usage",
                              description="Estim ouput usage",
                              choices=CHOICE_USAGE_ALL,
                              required=True
                          )):
            txt = []
            level_arg = '%-5'
            for unit in BT_UNITS:
                for ch in ['A', 'B']:
                    # find channel with this usage
                    if threads_settings[unit][f'ch_{ch}_use'] == usage_arg.lower() or usage_arg.lower() == 'all':
                        ch_name = f'ch_{ch}_max'
                        level_arg = await self.check_level(interaction, level_arg)
                        if level_arg:
                            new_val = self.calc_new_val(level_arg, unit, ch_name)
                            txt.append(">>new level for unit {} ch {} ({}) change from {} to {}".format(
                                unit, ch, threads_settings[unit][f'ch_{ch}_use'], threads_settings[unit][ch_name],
                                new_val))
                            threads_settings[unit]['updated'] = True
                            threads_settings[unit][ch_name] = new_val
            if len(txt) == 0:
                await interaction.response.send_message('There are no channel with this usage')
            else:
                await interaction.response.send_message("\n".join(txt))
            return None

        # ----- LEVEL SETTINGS -----
        @self.slash_command(name='level')
        async def bot_level(interaction: nextcord.Interaction):
            pass

        @bot_level.subcommand(description='Advanced Estim level change')
        async def advanced(interaction: Interaction,
                           unit_arg: str = SlashOption(
                               name="unit",
                               description="units impacted",
                               choices=CHOICE_UNIT_RANDOM,
                               required=True
                           ),
                           dest_arg: str = SlashOption(
                               name="channels",
                               description="channels impacted",
                               choices=CHOICE_CHANNEL_RANDOM,
                               required=True
                           ),
                           level_op: str = SlashOption(
                               name="operation",
                               description="how the level is changing",
                               choices=CHOICE_LEVEL_ACTION,
                               required=True
                           ),
                           level_arg_min: int = SlashOption(
                               name="level_start",
                               description="min or fixed level",
                               required=True,
                           ),
                           level_arg_max: int = SlashOption(
                               name="level_max",
                               description="max level",
                               required=False,
                           )
                           ) -> None:
            if await check_permission(interaction, 'administrator'):
                level_arg = level_op + str(level_arg_min)
                if level_arg_max:
                    level_arg = level_arg + '>' + str(level_arg_max)
                txt = []
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    for ch in await self.check_ch(interaction, dest_arg):
                        ch_name = f'ch_{ch}_max'
                        level_arg_ch = await self.check_level(interaction, level_arg)
                        if level_arg:
                            new_val = self.calc_new_val(level_arg_ch, unit, ch_name)
                            txt.append(">>new level for unit {} ch {} ({}) change from {} to {}".format(
                                unit, ch, threads_settings[unit][f'ch_{ch}_use'], threads_settings[unit][ch_name],
                                new_val))
                            threads_settings[unit]['updated'] = True
                            threads_settings[unit][ch_name] = new_val
                await interaction.response.send_message("\n".join(txt))
            return None

        @bot_level.subcommand(description='Estim level change by use')
        async def usage(interaction: Interaction,
                        usage_arg: str = SlashOption(
                            name="usage",
                            description="Estim ouput usage",
                            choices=CHOICE_USAGE,
                            required=True
                        ),
                        level_op: str = SlashOption(
                            name="operation",
                            description="how the level is changing",
                            choices=CHOICE_LEVEL_ACTION,
                            required=True
                        ),
                        level_arg_min: int = SlashOption(
                            name="level_start",
                            description="min or fixed level",
                            required=True,
                        ),
                        level_arg_max: int = SlashOption(
                            name="level_max",
                            description="max level",
                            required=False,
                        )
                        ) -> None:
            # only commands for increase level are permitted all the time
            if level_op == '+' or level_op == '%+' or await check_permission(interaction, 'administrator'):
                level_arg = level_op + str(level_arg_min)
                # when range of level is used
                if level_arg_max:
                    level_arg = level_arg + '>' + str(level_arg_max)
                txt = []
                for unit in BT_UNITS:
                    for ch in ['A', 'B']:
                        # find channel with this usage
                        if threads_settings[unit][f'ch_{ch}_use'] == usage_arg.lower():
                            ch_name = f'ch_{ch}_max'
                            level_arg = await self.check_level(interaction, level_arg)
                            if level_arg:
                                new_val = self.calc_new_val(level_arg, unit, ch_name)
                                txt.append(">>new level for unit {} ch {} ({}) change from {} to {}".format(
                                    unit, ch, threads_settings[unit][f'ch_{ch}_use'], threads_settings[unit][ch_name],
                                    new_val))
                                threads_settings[unit]['updated'] = True
                                threads_settings[unit][ch_name] = new_val
                if len(txt) == 0:
                    await interaction.response.send_message('There are no channel with this usage')
                else:
                    await interaction.response.send_message("\n".join(txt))
            return None

        # ----- UNIT SETTINGS -----
        @self.slash_command(name='unit')
        async def bot_unit_set(interaction: nextcord.Interaction):
            pass

        @bot_unit_set.subcommand(description='Multiple power level changing')
        async def power(interaction: Interaction,
                        unit_arg: str = SlashOption(
                            name="unit",
                            description="Estim unit impacted with the new power setting",
                            required=True,
                            choices=CHOICE_UNIT,
                        ),
                        unit_setting: str = SlashOption(
                            name="setting",
                            description="New power setting for the selected units",
                            required=True,
                            choices=CHOICE_ADV_POWER.keys(),
                        )) -> None:
            if await check_permission(interaction, 'administrator'):
                new_setting_type = CHOICE_ADV_POWER[unit_setting][0]
                new_setting_val = int(CHOICE_ADV_POWER[unit_setting][1])
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    threads_settings[unit]['updated'] = True
                    # Power level
                    if new_setting_type == 'P':
                        if new_setting_val > 1:
                            threads_settings[unit]['level_d'] = True
                        else:
                            threads_settings[unit]['level_h'] = bool(new_setting_val)
                            threads_settings[unit]['level_d'] = False
                    # Power Map
                    elif new_setting_type == 'M':
                        threads_settings[unit]['level_map'] = new_setting_val
                    # Power Bias
                    elif new_setting_type == 'B':
                        threads_settings[unit]['power_bias'] = new_setting_val
                await interaction.response.send_message(
                    'new power setting for unit {} is {}'.format(unit_arg, unit_setting))
            return None

        @bot_unit_set.subcommand(description='Change advanced timer setting')
        async def timer(interaction: Interaction,
                        unit_arg: str = SlashOption(name="unit",
                                                    description="Estim unit impacted with the new setting",
                                                    required=True,
                                                    choices=CHOICE_UNIT,
                                                    ),
                        unit_setting: str = SlashOption(name="setting",
                                                        description="New timer setting for the selected units",
                                                        required=True,
                                                        choices=CHOICE_ADV_TIMER.keys(),
                                                        )) -> None:

            if await check_permission(interaction, 'administrator'):
                new_setting_type = CHOICE_ADV_TIMER[unit_setting][0]
                new_setting_val = int(CHOICE_ADV_TIMER[unit_setting][1])
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    threads_settings[unit]['updated'] = True
                    # Power level
                    if new_setting_type == 'S':
                        threads_settings[unit]['adj_3'] = new_setting_val
                    elif new_setting_type == 'W':
                        threads_settings[unit]['adj_4'] = new_setting_val
                await interaction.response.send_message('new timer setting for unit {} is {}'
                                                        .format(unit_arg, unit_setting))
            return None

        @bot_unit_set.subcommand(description='Estim mode settings (change waveform)')
        async def mode(interaction: Interaction,
                       unit_arg: str = SlashOption(name="unit",
                                                   description="Estim unit impacted with the new setting",
                                                   required=True,
                                                   choices=CHOICE_UNIT_UNIQ,
                                                   ),
                       setting_arg: str = SlashOption(
                           name="setting",
                           description="setting impacted",
                           choices=CHOICE_MODE_SETTING,
                           required=True
                       ),
                       level_op: str = SlashOption(
                           name="operation",
                           description="how the value is changing",
                           choices=CHOICE_LEVEL_ACTION,
                           required=True
                       ),
                       level_arg_min: int = SlashOption(
                           name="level_start",
                           description="min range or fixed val",
                           required=True,
                       ),
                       level_arg_max: int = SlashOption(
                           name="level_max",
                           description="max range",
                           required=False,
                       )
                       ) -> None:

            if await check_permission(interaction, 'administrator'):
                level_arg = level_op + str(level_arg_min)
                if level_arg_max:
                    level_arg = level_arg + '>' + str(level_arg_max)
                txt = []
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    # check if setting is valid
                    adj_set = ''
                    for adj in ('adj_1', 'adj_2'):
                        if MODE_2B[threads_settings[unit]['mode']][adj] == setting_arg:
                            adj_set = adj
                    if adj_set == '':
                        mode = MODE_2B[threads_settings[unit]['mode']]['id']
                        await interaction.response.send_message(
                            'Invalid setting {} for mode {}'.format(setting_arg.lower(), mode))
                        return None
                    new_val = self.calc_new_val(level_arg, unit, adj_set)
                    txt.append(">>new setting for unit {} {} change from {} to {}".format(
                        unit, setting_arg, threads_settings[unit][adj_set + '_max'], new_val))
                    threads_settings[unit]['updated'] = True
                    threads_settings[unit][adj_set + '_max'] = new_val
                    # reset to adj_1 for modes without adj_2
                    if MODE_2B[threads_settings[unit]['mode']]['adj_2'] == '':
                        threads_settings[unit]['adj_2_max'] = threads_settings[unit]['adj_1_max']
                await interaction.response.send_message("\n".join(txt))
            return None

        # ----- EVENT MANAGEMENT ----
        @self.slash_command(name='events')
        async def bot_events(interaction: nextcord.Interaction):
            pass

        @bot_events.subcommand(
            description='List all events action'
        )
        async def list(interaction: Interaction) -> None:
            await interaction.response.send_message(embed=EmbedEventList(EVENT_ACTION))

        # ----- EMERGENCY STOP ----------
        @self.slash_command(
            name='stop',
            description='Emergency stop'
        )
        async def bot_stop(interaction: Interaction) -> None:
            if interaction.user:
                if interaction.user.id == self.subjectId or await check_permission(interaction, 'administrator'):
                    self.queueRunning = False
                    for unit in BT_UNITS:
                        for ch in ('ch_A', 'ch_B'):
                            threads_settings[unit]['updated'] = True
                            threads_settings[unit][ch] = 0
                            threads_settings[unit][ch + '_max'] = 0
                    await interaction.response.send_message('stop all channels')
            return None

        # ----- RAMP COMMANDS ------
        @self.slash_command(name='ramp', )
        async def bot_ramp(interaction: nextcord.Interaction):
            pass

        @bot_ramp.subcommand(description='Software ramp level')
        async def level(interaction: Interaction,
                        unit_arg: str = SlashOption(name="unit",
                                                    description="Estim unit impacted with the new setting",
                                                    required=True,
                                                    choices=CHOICE_UNIT_UNIQ,
                                                    ),
                        target_arg: str = SlashOption(
                            name="target",
                            description="channel or waveform settings impacted",
                            choices=CHOICE_RAMP_TARGET,
                            required=True
                        ),
                        ramp_prct_arg: int = SlashOption(
                            name="prct",
                            description="prct of max for the min value, 100=ramp disable",
                            required=True,
                            min_value=0,
                            max_value=100,
                        ),
                        phase_arg: int = SlashOption(
                            name="phase",
                            description="Phase of the ramp",
                            required=False,
                            default=0,
                            min_value=0,
                            max_value=179
                        )
                        ) -> None:

            if await check_permission(interaction, 'administrator'):
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    # check if setting is valid
                    if ramp_prct_arg < 100:
                        threads_settings[unit][target_arg + '_ramp_phase'] = phase_arg
                        threads_settings[unit][target_arg + '_ramp_prct'] = ramp_prct_arg
                await interaction.response.send_message("Software ramp adjusted")
            return None

        @bot_ramp.subcommand(description='Software ramp settings')
        async def settings(interaction: Interaction,
                           unit_arg: str = SlashOption(name="unit",
                                                       description="Estim unit impacted with the new setting",
                                                       required=True,
                                                       choices=CHOICE_UNIT,
                                                       ),
                           enable_arg: str = SlashOption(
                               name="enable",
                               description="activate the software ramp",
                               choices={'ON': '1', 'OFF': '0'},
                               required=True
                           ),
                           wave_arg: str = SlashOption(
                               name="wave",
                               description="wave mode or just ramp",
                               choices={'ON': '1', 'OFF': '0'},
                               default='0',
                               required=False
                           ),
                           duration_arg: int = SlashOption(
                               name="duration",
                               description="duration of the ramp cycle in seconde",
                               required=False,
                               default=120,
                               min_value=10,
                               max_value=600
                           )
                           ) -> None:

            if await check_permission(interaction, 'administrator'):
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    if bool(int(enable_arg)):
                        threads_settings[unit]['ramp_time'] = duration_arg
                    else:
                        threads_settings[unit]['ramp_time'] = 0
                    threads_settings[unit]['ramp_progress'] = 0
                    threads_settings[unit]['updated'] = True
                    threads_settings[unit]['ramp_wave'] = bool(int(wave_arg))
                await interaction.response.send_message('Software ramp settings updated')
            return None

    # ------------- Event management ------------------
    async def trigger_event(
        self, 
        event_type: TriggerableEvent,
        **kwargs,
    ) -> None:
        """
            WIP
            Handle triggered Events, will check for `TriggerRules` and call them and send `Notifications`
        """
        # TODO: trigger event func
        Logger.info(f"[Events] Events received, [type={event_type}]")
        
        # dispatch notification through discord
        await self.notifier.triggerEvent(event_type, eventData=kwargs["eventData"])
        
        # debug
        if kwargs and "eventData" in kwargs:
            pprint(kwargs['eventData'])

    # add action into queue
    async def add_event_action(self, type_action: str, origin_action: str, event_time) -> None:
        
        Logger.info(f"Action received! {type_action}")
        # action parsed in the event
        
        await store.websocket.broadcast({
            "type": "event-trigger",
            "payload": {
                "type_action": type_action,
                "origin_action": origin_action,
                "event_time": event_time,
            }
        })
            

        m = re.search('^wof_([A-Z])([A-Z,a-z])([A-Z,a-z])$', type_action)
        if m:
            Logger.info("New event type {} added in queue ".format(type_action))
            Logger.info("New custom task event")
            profile = m.group(1).upper()
            level_coef = 100
            if m.group(2).isupper():
                level_coef = 100 + (ord(m.group(2)) - 65) * 5  # add 5% peer steep
            else:
                level_coef = 100 - (ord(m.group(2)) - 97) * 2  # sub 2% peer steep
            duration = 0
            if m.group(3).isupper():
                duration = (ord(m.group(3)) - 64) * 10  # add 10 sec peer steep
            else:
                duration = random.randint(10, (ord(m.group(3)) - 96) * 10)  # add 10 sec peer steep

            self.action_queue.append({
                'origine': origin_action,
                'type': 'pro',
                'profile': profile,
                'level': level_coef,
                'duration': duration,
                'wait': True,
                'display': type_action + ' ' + time.strftime('%H:%M:%S', event_time),
                'counter': -1
            })

        # find action associated to the event
        elif EVENT_ACTION[type_action]:
            Logger.info("New event type {} added in queue : {}".format(type_action, EVENT_ACTION[type_action]))
            # Level change -> queue
            if EVENT_ACTION[type_action]['type'] == 'lvl':
                Logger.warning("New level event")
                self.action_queue.append({
                    'origine': origin_action,
                    'type': 'lvl',
                    'unit': EVENT_ACTION[type_action]['unit'],
                    'dest': EVENT_ACTION[type_action]['dest'],
                    'level': await self.check_level(self, EVENT_ACTION[type_action]['level']),
                    'duration': await self.check_duration(self, EVENT_ACTION[type_action]['duration']),
                    'wait': EVENT_ACTION[type_action]['wait'],
                    'display': type_action + ' ' + time.strftime('%H:%M:%S', event_time),
                    'counter': -1
                })
            # Apply profile -> queue
            elif EVENT_ACTION[type_action]['type'] == 'pro':
                Logger.warning("New profile event")
                self.action_queue.append({
                    'origine': origin_action,
                    'type': 'pro',
                    'profile': EVENT_ACTION[type_action]['profile'],
                    'level': EVENT_ACTION[type_action]['level'],
                    'duration': await self.check_duration(self, EVENT_ACTION[type_action]['duration']),
                    'wait': EVENT_ACTION[type_action]['wait'],
                    'display': type_action + ' ' + time.strftime('%H:%M:%S', event_time),
                    'counter': -1
                })
            # Multi change
            elif EVENT_ACTION[type_action]['type'] == 'multi':
                Logger.warning("New multiplier event")
                for unit in BT_UNITS:
                    for ch in ['A', 'B']:
                        # find channel with this usage
                        if threads_settings[unit][f'ch_{ch}_use'] == EVENT_ACTION[type_action]['target'].lower() or EVENT_ACTION[type_action]['target'].lower() == 'all':
                            ch_name = f'ch_{ch}_multiplier'
                            add_vall = 0
                            if EVENT_ACTION[type_action]['rnd']:
                                if EVENT_ACTION[type_action]['prct'] > 0:
                                    add_vall = random.randint(0, EVENT_ACTION[type_action]['prct'])
                                else:
                                    add_vall = random.randint(EVENT_ACTION[type_action]['prct'], 0)
                            else:
                                add_vall = EVENT_ACTION[type_action]['prct']
                            threads_settings[unit][ch_name] += add_vall
                            threads_settings[unit]['updated'] = True
            # Add max time / Add time
            elif EVENT_ACTION[type_action]['type'] == 'add':
                Logger.warning("New duration event")
                duration = int(EVENT_ACTION[type_action]['duration']) * 60
                # Chaster
                if self.chaster_lockid:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f'{CHASTER_URL}/locks/{self.chaster_lockid}',
                                               headers=CHASTER_HEADERS) as current_lock:
                            json_data = await current_lock.json()
                            max_time = datetime.datetime.strptime(json_data['maxDate'], '%Y-%m-%dT%H:%M:%S.%fZ')
                            if json_data['maxLimitDate']:  # case of no max
                                max_time = datetime.datetime.strptime(json_data['maxLimitDate'],
                                                                      '%Y-%m-%dT%H:%M:%S.%fZ')
                            max_time = max_time + datetime.timedelta(seconds=duration)
                            async with session.post(f'{CHASTER_URL}/locks/{self.chaster_lockid}/max-limit-date',
                                                    json={'maxLimitDate': max_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                                                          'disableMaxLimitDate': False},
                                                    headers=CHASTER_HEADERS) as update_dur:
                                logger.debug(update_dur.text())
                            if not EVENT_ACTION[type_action]['only_max']:
                                async with session.post(f'{CHASTER_URL}/locks/{self.chaster_lockid}/update-time',
                                                        json={'duration': duration},
                                                        headers=CHASTER_HEADERS) as update_dur:
                                    logger.debug(update_dur.text())
        else:
            Logger.info("[Actions] New event type {} unknow".format(type_action))

    async def reverse_action(self, action: dict) -> None:
        """
        Reverse change from a previous action
        Args:
            action: Dict with action to reverse

        Returns:None

        """

        if action['type'] == 'lvl':
            unit = action['unit']
            var = action['dest']
            new_val = threads_settings[unit][var] + action['level_diff']
            new_val = max(0, min(100, new_val))  # to avoid special case (or bug) ...
            Logger.info(f'return to initial value for unit {unit} var {var} is {new_val}')
            threads_settings[unit]['updated'] = True
            threads_settings[unit][var] = new_val
            
            Logger.info(f"[Action] Successfully back to initial Levels.")
            
        elif action['type'] == 'pro':
            file_bck = open(DIR_TMP / action['bck_file'], 'r')
            backup_data = json.load(file_bck)
            bck_settings = backup_data['threads_settings']
            file_bck.close()
            os.remove(DIR_TMP / action['bck_file'])
            # apply old profile
            for bck_bt_name in bck_settings:
                threads_settings[bck_bt_name]['sync'] = False
                threads_settings[bck_bt_name]['updated'] = True
                for field in bck_settings[bck_bt_name]:
                    if field in PROFILE_FIELDS:
                        threads_settings[bck_bt_name][field] = bck_settings[bck_bt_name][field]
                        
            Logger.info(f"[Action] Successfully back to initial Profile.")

    async def apply_action(self, action: dict) -> None:
        """
        Apply action from Event
        Args:
            action: Dict with action to do

        Returns: None

        """
        # pprint(action)
        # pprint(threads_settings)
        Logger.info("{} action start\n".format(action['origine']))
        # Level update
        if action['type'] == 'lvl':
            for unit in await self.check_unit(None, action['unit']):
                unit = 'UNIT' + str(unit)
                # level adjust
                for ch in await self.check_ch(None, action['dest'].upper()):
                    ch_name = f'ch_{ch}_max'
                    old_val = threads_settings[unit][ch_name]
                    new_val = self.calc_new_val(action['level'], unit, ch_name)
                    threads_settings[unit]['updated'] = True
                    threads_settings[unit][ch_name] = new_val
                    self.back_action_queue.append({
                        'type': action['type'],
                        'unit': unit,
                        'dest': ch_name,
                        'level_diff': old_val - new_val,
                        'origine': action['origine']
                    })
                    Logger.info("[Action] level for {} {} -> {}".format(threads_settings[unit][f'ch_{ch}_use'], old_val, new_val))
                    
                    await store.websocket.broadcast({
                        "type": "level-update",
                        "payload": {
                            "electrode_name": threads_settings[unit][f'ch_{ch}_use'],
                            "type": action['type'],
                            "unit": unit,
                            "channel": ch_name,
                            "level_old": old_val,
                            "level_new": new_val,
                        }
                    })
                    
        # profile update
        elif action['type'] == 'pro':
            if action['profile'] == 'X':
                action['profile'] = random.choice(PROFILE_RANDOM)
            filename = action['profile'] + '.json'
            if not os.path.isfile(DIR_PROFILE / filename):
                Logger.info("Profile file {} missing".format(DIR_PROFILE / filename))
            else:
                # backup current profile
                file_bck = open(DIR_TMP / action['origine'], 'w')
                backup_data = {'threads_settings': threads_settings}
                json.dump(backup_data, file_bck, indent=4)
                file_bck.close()
                self.back_action_queue.append({
                    'type': action['type'],
                    'bck_file': action['origine'],
                    'origine': action['origine']
                })
                # load new profile
                file_profile = open(DIR_PROFILE / filename, 'r')
                backup_data = json.load(file_profile)
                bck_settings = backup_data['threads_settings']
                file_profile.close()
                # apply new profile
                for bck_bt_name in bck_settings:
                    threads_settings[bck_bt_name]['sync'] = False
                    threads_settings[bck_bt_name]['updated'] = True
                    threads_settings[bck_bt_name]['ramp_progress'] = 0
                    for field in bck_settings[bck_bt_name]:
                        if field in PROFILE_FIELDS:
                            if field in ['ch_A_max', 'ch_B_max']:
                                new_val = round(int(bck_settings[bck_bt_name][field]) \
                                                * int(action['level']) / 100)
                                threads_settings[bck_bt_name][field] = min(100, max(0, new_val))
                            else:
                                threads_settings[bck_bt_name][field] = bck_settings[bck_bt_name][field]

    # BT sensors polling for new alarm
    async def bt_sensor_alarm(self):
        """
        Check alarm about position and moving for the BT sensors and apply actions if needed
        Args:

        Returns:
            None

        """
        # loop by sensor
        for sensor_name in sorted(store.get_all_sensors_settings().keys()):
            current_sensor_settings = store.get_sensor_setting(sensor_name)
            
            # loop by value from the sensor
            for field in sorted(current_sensor_settings.keys()):
                # find the name of the sensor from the config
                if m := re.match(r"^(\w+)_alarm_number$", field):
                    value = m[1]
                    # check if the alarm counter have changed
                    if current_sensor_settings[value + '_alarm_number'] != current_sensor_settings[value + '_alarm_number_action']:
                        current_sensor_settings[value + '_alarm_number_action'] = current_sensor_settings[value + '_alarm_number']
                        store.update_sensor_field(sensor_name, value + "_alarm_number_action", current_sensor_settings[value + '_alarm_number'])
                        
                        # if alarm is active, add event in queue
                        if EVENT_ACTION[value] and current_sensor_settings['alarm_enable']:
                            Logger.warning(f'[Sensor] Alarm! "{sensor_name}" Sensor fired!')
                            await self.add_event_action(value, sensor_name + ' BT sensor ' + value + str(current_sensor_settings[value + '_alarm_number_action']), time.localtime())

    # for exception in tasks bt_sensor_alarm
    @tasks.loop(seconds=1)
    async def rerun_bt_sensor_alarm(self):
        try:
            await self.bt_sensor_alarm()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception bt_sensor_alarm")
            logger.debug(traceback.print_exc())

    # Chaster detect active lock et task/pillory pooling
    async def set_chaster(self) -> None:
        """
        Enable current chaster session for detect event
        Args:

        Returns: None
        """
        # get active lock from API
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{CHASTER_URL}/locks?status=active', headers=CHASTER_HEADERS) as data_current_lock:
                json_feed = await data_current_lock.json()
                if len(json_feed) > 0:
                    # get the first active lock
                    if not self.chaster_lockid:
                        logger.warning('Chaster active lock detected lockid : {}'.format(json_feed[0]['_id']))
                    self.chaster_lockid = json_feed[0]['_id']
                    # check which extensions are actives
                    for idx in range(len(json_feed[0]['extensions'])):
                        # Tasks detection
                        if json_feed[0]['extensions'][idx]['displayName'] == 'Tasks':
                            taskid = json_feed[0]['extensions'][idx]['userData']['currentTaskVote']
                            if taskid:
                                if self.chaster_taskid != taskid:
                                    self.chaster_taskvote = {}  # New poll, reset previous results
                                    logger.warning('Chaster tasks voting detected taskid : {}'.format(taskid))
                                    self.chaster_taskid = taskid
                                self.chaster_task_pool = self.chaster_task_pool + 1  # used for uniq id for action
                        # Pilory detection
                        if json_feed[0]['extensions'][idx]['displayName'] == 'Pillory':
                            pilloryid = json_feed[0]['extensions'][idx]['_id']
                            if pilloryid:
                                if self.chaster_pilloryid != pilloryid:
                                    logger.warning('Chaster pillory detected pilloryid : {}'.format(pilloryid))
                                    self.chaster_pilloryid = pilloryid

    # for exception in tasks set_chaster
    @tasks.loop(seconds=60)
    async def rerun_set_chaster(self):
        try:
            await self.set_chaster()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception set_chaster")
            logger.debug(traceback.print_exc())

    async def chaster_history(self) -> None:
        """
        Parse Chaster history for event detecting
        Args:

        Returns: None
        """
        # if no active lock
        if not self.chaster_lockid:
            return
        # get votes info from API history
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f'{CHASTER_URL}/locks/{self.chaster_lockid}/history',
                    json={"limit": 30},
                    headers=CHASTER_HEADERS) as data_current_history:
                json_history = await data_current_history.json()
                for chaster_event in json_history['results']:       
                    # check if event is new
                    if chaster_event['_id'] not in self.chaster_history_event_parsed:
                        self.chaster_history_event_parsed.append(chaster_event['_id'])
                        # parse voting
                        if chaster_event['type'] == 'link_time_changed':
                            if 'duration' not in chaster_event['payload']:
                                logger.warning('new chaster vote without duration')
                                await self.add_event_action('vote', 'vote' + chaster_event['_id'], time.localtime())
                            elif chaster_event['payload']['duration'] > 0:
                                logger.warning('new chaster vote add')
                                await self.add_event_action('vote', 'vote' + chaster_event['_id'], time.localtime())
                            else:
                                logger.warning('new chaster vote sub')
                                await self.add_event_action('vote_sub', 'vote' + chaster_event['_id'], time.localtime())
                        # parse wheel of fortune
                        elif chaster_event['type'] == 'wheel_of_fortune_turned' and chaster_event['payload']['segment']['type'] == 'text':
                            # Looking for keyword
                            
                            m = re.search('^(\\d|[A-Z][A-Z,a-z][A-Z,a-z]):', chaster_event['payload']['segment']['text'])
                            if m:
                                print('new chaster wheel of fortune action:' + m.group(1))
                                await self.add_event_action('wof_' + m.group(1), 'wof' + chaster_event['_id'],
                                                            time.localtime())
                            else:
                                logger.warning(
                                    'unknow wheel of fortune test:' + chaster_event['payload']['segment']['text'])

    # for exception in tasks chaster_history
    @tasks.loop(seconds=30)
    async def rerun_chaster_history(self):
        try:
            await self.chaster_history()
            await self.chaster.monitorHistory()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception chaster_history")
            logger.debug(traceback.print_exc())

    # Chaster parse task pooling
    async def chaster_task(self) -> None:
        """
        Parse Chaster task extention for detecting new vote
        Args:

        Returns: None
        """
        # if no task extention
        if not self.chaster_taskid:
            return
        elif self.chaster_taskid not in self.chaster_taskvote:
            self.chaster_taskvote[self.chaster_taskid] = {}

        # get tasks info from API
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    f'{CHASTER_URL}/extensions/tasks/votes/{self.chaster_taskid}',
                    headers=CHASTER_HEADERS) as data_current_vote:
                json_feed = await data_current_vote.json()
                # parse voting task stats
                for idx in range(len(json_feed['choices'])):
                    # looking for keyword
                    m = re.search('^(\\d|[A-Z][A-Z,a-z][A-Z,a-z]):', json_feed['choices'][idx]['task'])
                    if m:
                        type_action = 'wof_' + m.group(1)
                        nb_votes = int(json_feed['choices'][idx]['nbVotes'])
                        # new entry
                        if type_action not in self.chaster_taskvote[self.chaster_taskid]:
                            self.chaster_taskvote[self.chaster_taskid][type_action] = 0
                        # check if there are some new votes
                        for i in range(self.chaster_taskvote[self.chaster_taskid][type_action], nb_votes):
                            logger.warning(f'new chaster vote task {type_action}')
                            # add event to queue
                            await self.add_event_action(
                                type_action,
                                type_action + '_chaster_' + str(i) + '_' + str(self.chaster_task_pool),
                                time.localtime())
                        self.chaster_taskvote[self.chaster_taskid][type_action] = nb_votes

    # for exception in tasks chaster_task
    @tasks.loop(seconds=30)
    async def rerun_chaster_task(self):
        try:
            await self.chaster_task()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception chaster_task")
            logger.debug(traceback.print_exc())

    # for exception in tasks chaster_pillory
    @tasks.loop(seconds=30)
    async def rerun_chaster_pillory(self):
        try:
            await self.chaster.fetchPillories()
        except asyncio.CancelledError:
            raise
        except Exception:
            Logger.error(f"[Chaster-Threads] Task exception chaster_pillory")
            logger.debug(traceback.print_exc())

    # Event action queueing
    async def event_queue_mgmt(self):
        """
        Check queue for all actions form vent
        Returns:

        """
        # purge finished actions (except for duration=0 of permanent action)
        tmp_array = []
        queue_nb_run = 0
        queue_nb_wait = 0
        # Browse all the queue for see if something need to do
        for idx in range(len(self.action_queue)):
            # if duration=0 => permanent action so no need to return on old values and no
            if self.action_queue[idx]['counter'] > 0 and self.action_queue[idx]['duration'] == 0:
                queue_stats['constant'] = queue_stats['constant'] + 1
                continue
            # for action with fixed duration, check if it is finished
            if self.action_queue[idx]['counter'] < self.action_queue[idx]['duration']:
                # not finished, the action is keep in queue
                tmp_array.append(self.action_queue[idx])
                # statistics
                if self.action_queue[idx]['counter'] == -1:
                    queue_nb_wait = queue_nb_wait + 1
                else:
                    queue_nb_run = queue_nb_run + 1
            else:
                # Action Finished
                logger.warning(
                    "{} action stop after {} sec".format(self.action_queue[idx]['display'],
                                                         self.action_queue[idx]['duration']))
                queue_stats['done'] = queue_stats['done'] + 1
                # Make a reverse action for returned to the original settings
                for action in self.back_action_queue:
                    if self.action_queue[idx]['origine'] == action['origine']:
                        await self.reverse_action(action)
        # Update global stats
        queue_stats['running'] = queue_nb_run
        queue_stats['waiting'] = queue_nb_wait

        # Stop here if Queue in pause
        if not self.queueRunning:
            return

        self.action_queue = tmp_array
        # find if some actions are already active and increase the counter
        something_active = 0
        for idx in range(len(self.action_queue)):
            if self.action_queue[idx]['counter'] > 0:
                something_active = something_active + 1
                self.action_queue[idx]['counter'] = self.action_queue[idx]['counter'] + 1

        # look if no-cumulative action can be start if nothing already running
        if something_active == 0:
            for idx in range(len(self.action_queue)):
                # start the new event
                if self.action_queue[idx]['wait'] and self.action_queue[idx]['counter'] == -1:
                    self.action_queue[idx]['counter'] = 1
                    await self.apply_action(self.action_queue[idx])
                    break  # Only one action in progress in no cumulative mode

        # look if cumulative action can be start
        for idx in range(len(self.action_queue)):
            if not self.action_queue[idx]['wait'] and self.action_queue[idx]['counter'] == -1:
                self.action_queue[idx]['counter'] = 1
                await self.apply_action(self.action_queue[idx])

    # for exception in tasks event_queue_mgmt
    @tasks.loop(seconds=1)
    async def rerun_event_queue_mgmt(self):
        try:
            await self.event_queue_mgmt()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception event_queue_mgmt")
            logger.debug(traceback.print_exc())

    # update boot status
    async def update_status(self):
        """
        Update the status in bot status
        Returns:

        """
        # text status for the bot
        msg = "Cnx: "
        bot_status = nextcord.Status.online
        for unit in BT_UNITS:
            if threads_settings[unit]['cnx_ok']:
                msg += unit
            else:
                bot_status = nextcord.Status.do_not_disturb
        await self.change_presence(status=bot_status,
                                   activity=nextcord.Activity(type=nextcord.ActivityType.listening, state='',
                                                              name=msg))

    # for exception in tasks update_status
    @tasks.loop(seconds=30)
    async def rerun_update_status(self):
        try:
            await self.update_status()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception update_status")
            logger.debug(traceback.print_exc())

    # @Bot is Ready
    async def on_ready(self):
        # Find and save usefull channels
        self.logChannel = self.get_channel(CONFIGURATION['logsChannelId']) # type: ignore
        self.statusChannel = self.get_channel(CONFIGURATION['statusChannelId']) # type: ignore
        # print(f"chaster={self.chaster.linked}")
        # print(f"profile={self.profile.profileFiles}")
        
        # create root and redirect host to it
        magicLink: str = generate_root_access()
        await self.get_user(CONFIGURATION['subjectDiscordId']).send(content=f"Magic Link: {magicLink}")
        
        await self.chaster.linkLock()
        
        # Start all tasks
        self.rerun_update_status.start()  # bot console
        self.rerun_event_queue_mgmt.start()  # queue management
        self.rerun_bt_sensor_alarm.start()  # Bluetooth sensors
        
        self.rerun_set_chaster.start()  # Detect Chaster lock
        self.rerun_chaster_history.start()  # Chaster votes
        self.rerun_chaster_task.start()  # Chaster tasks
        self.rerun_chaster_pillory.start()  # Chaster Pillory
        return True

    # cmd arg errors
    async def on_command_error(self, context, exception):
        logger.error(str(exception))

def sensor_check_val(sensor_name: str, measure: str, val: int) -> None:
    """
    Check if the sensor can fire an alarm
    Args:
        sensor: Name of the sensor
        measure: What the sensor check
        val: sensor value

    Returns:

    """
    # fetch current settings
    current_sensor_settings = store.get_sensor_setting(sensor_name)
    
    # max value at 50 (why?)
    if sensor_name == "sound":
        new_current_value = min(round(val), 90)
    else:
        new_current_value = min(round(val), 50)

    # no check if offline
    if not current_sensor_settings['sensor_online']:
        return
    
    fields_to_update = {
        'current_' + measure: new_current_value
    }
    
    new_counter = current_sensor_settings[measure + '_alarm_counter']

    # value is superior to alarm level
    if val > current_sensor_settings[measure + '_alarm_level'] or current_sensor_settings[measure + '_alarm_counter'] < 0:
        current_sensor_settings[measure + '_alarm_counter'] = current_sensor_settings[measure + '_alarm_counter'] + 1

        new_counter = new_counter + 1
        fields_to_update[measure + '_alarm_counter'] = new_counter
        
    # consecutive detect and activate delay_off
    if new_counter >= current_sensor_settings[measure + '_delay_on']:
        # alarm
        fields_to_update[measure + '_alarm_number'] = current_sensor_settings[measure + '_alarm_number'] + 1
        # add delay before the next alarm
        fields_to_update[measure + '_alarm_counter'] = -current_sensor_settings[measure + '_delay_off']

    store.update_sensor_fields(sensor_name, fields_to_update)


def sensor_notification(sensor_name, _, data: bytearray) -> None:
    """
    Function call for every BT notify
    Args:
        sensor:sensor name
        _:BT client
        data: notification data

    Returns:

    """
    
    current_sensor_settings = store.get_sensor_setting(sensor_name)
    
    if sensor_name == 'sound':
        level = int.from_bytes(data[0:1], byteorder='big', signed=False)
        sensor_check_val(sensor_name, 'sound', level)
    else:
        # X/Y/Z position (not sure about the unit)
        x_angle = int.from_bytes(data[0:2], byteorder='big', signed=True)
        y_angle = int.from_bytes(data[2:4], byteorder='big', signed=True)
        z_angle = int.from_bytes(data[4:6], byteorder='big', signed=True)
        # X/Y/Z acceleration
        x_acc = int.from_bytes(data[6:8], byteorder='big', signed=True)
        y_acc = int.from_bytes(data[8:10], byteorder='big', signed=True)
        z_acc = int.from_bytes(data[10:12], byteorder='big', signed=True)

        # Calc something proportional to movement
        move = round((abs(x_acc) + abs(y_acc) + abs(z_acc)) / 30)

        # Calc something proportional to the position change
        pos = (abs(x_angle) + abs(y_angle) + abs(z_angle)) / 100
        
        # new position
        new_position_ref: int = pos
        
        if current_sensor_settings['position_ref'] == -1:
            new_position_ref = pos
        else:
            new_position_ref = (current_sensor_settings['position_ref'] * 100 + pos) / 101  # Add 1% of the new position
        
        # update sensor    
        store.update_sensor_field(sensor_name, "position_ref", new_position_ref)
        
        pos = abs(pos - new_position_ref)

        # check values
        sensor_check_val(sensor_name, 'position', pos)
        sensor_check_val(sensor_name, 'move', move)


async def sensor_bt(sensor_name: str, address: str, char_uuid: str) -> None:
    """
    Start connexion with the BT ensors and activate notification
    Args:
        sensor: Name of the sensors
        address: BT addr of the module
        char_uuid: BT uuid for the sensor
    Returns:
        None
    """
    
    current_sensor_settings = store.get_sensor_setting(sensor_name)
    current_sensor_settings['sensor_online'] = False
    
    disconnected_event = asyncio.Event()
    Logger.info(f"[Sensors] Searching sensor '{sensor_name}'...")

    def disconnected_callback(bt_client):
        Logger.info(f"[Sensors] {sensor_name} sensor is disconnected")
        current_sensor_settings['sensor_online'] = False
        
        if sensor_name == 'sound':
            sensor_check_val(sensor_name, 'sound', 0)
        else:
            sensor_check_val(sensor_name, 'move', 0)
            sensor_check_val(sensor_name, 'position', 0)
            
        # get current loop and queue ws update
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            store.websocket.broadcast({
                "type": "sensors:update",
                "payload": {
                    "id": sensor_name,
                    "changes": {
                        "sensor_online": False
                    }
                },
            }),
            loop
        )
            
        disconnected_event.set()    

    async with BleakClient(address, disconnected_callback=disconnected_callback) as client:
        Logger.info(f"[Sensors] {sensor_name} sensor is connected")
        current_sensor_settings['sensor_online'] = True
        
        # get current loop and queue ws update
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            store.websocket.broadcast({
                "type": "sensors:update",
                "payload": {
                    "id": sensor_name,
                    "changes": {
                        "sensor_online": True
                    }
                },
            }),
            loop
        )
        
        await client.start_notify(char_uuid, partial(sensor_notification, sensor_name))
        await disconnected_event.wait()


def thread_sensors_bt(sensor: str, addr: str, service: str) -> None:
    """
    Loop forever for collect motion sensor data
        Args:
        sensor: Name of the sensors
        address: BT addr of the module
        char_uuid: BT uuid for the MPU6050 sensor
    Returns:

    """
    Logger.info(f"[Sensors] Start Sensor '{sensor}' thread")
    while True:
        try:
            # thread isolation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # run
            loop.run_until_complete(sensor_bt(sensor, addr, service))
            loop.close()
        except BleakDeviceNotFoundError:
            time.sleep(30)
        except Exception as err:
            logger.info(f"Thread error in start_sensors_bt {sensor}: {err=}, {type(err)=}")
            time.sleep(30)


# Software ramp
def thread_update_ramp():
    RAMP_STEP = 2
    Logger.info(f"Start software ramp thread")
    while True:
        try:
            time.sleep(RAMP_STEP)
            for unit in BT_UNITS:
                # determine percentage
                prct_progress = 0
                # ramp disable
                if threads_settings[unit]['ramp_time'] == 0:
                    prct_progress = 100
                # ramp enable
                else:
                    # check if ramp is over
                    if threads_settings[unit]['ramp_progress'] > threads_settings[unit]['ramp_time']:
                        threads_settings[unit]['ramp_progress'] = 0
                        prct_progress = 0
                    else:
                        # in wave mode we do up and down in the same cycle so 2 times faster
                        if threads_settings[unit]['ramp_wave']:
                            # wave decreasing
                            if threads_settings[unit]['ramp_progress'] > threads_settings[unit]['ramp_time'] / 2:
                                prct_progress = 200 - int(
                                    threads_settings[unit]['ramp_progress'] / threads_settings[unit]['ramp_time'] * 200)
                            # wave increasing
                            else:
                                prct_progress = int(
                                    threads_settings[unit]['ramp_progress'] / threads_settings[unit]['ramp_time'] * 200)
                        else:
                            prct_progress = int(
                                threads_settings[unit]['ramp_progress'] / threads_settings[unit]['ramp_time'] * 100)
                # calc ramp for each value
                update_need = False
                for field in ('ch_A', 'ch_B', 'adj_1', 'adj_2'):
                    # ramp active ?
                    if threads_settings[unit][field + '_ramp_prct'] < 100 and threads_settings[unit]['ramp_time'] > 0:
                        # add phase to progress
                        prct = prct_progress + threads_settings[unit][field + '_ramp_phase'] / 180 * 100
                        if prct > 100:
                            prct = 200 - prct
                        # ramp
                        delta = threads_settings[unit][field + '_max'] * (
                                100 - threads_settings[unit][field + '_ramp_prct']) / 100
                        new_val = threads_settings[unit][field + '_max'] - int(delta * (100 - prct) / 100)
                    else:
                        # no ramp
                        new_val = threads_settings[unit][field + '_max']
                    # add multiplier for level
                    if field in ('ch_A', 'ch_B'):
                        new_val = int(new_val * threads_settings[unit][field + '_multiplier'] / 100)
                    # check if update needed
                    if threads_settings[unit][field] != new_val:
                        threads_settings[unit][field] = new_val
                        update_need = True

                # update the console
                if update_need:
                    threads_settings[unit]['sync'] = False
                    threads_settings[unit]['updated'] = True
                # ramp progress
                threads_settings[unit]['ramp_progress'] = threads_settings[unit]['ramp_progress'] + RAMP_STEP
        except Exception as err:
            Logger.info(f"Thread error in update_ramp {err=}, {type(err)=}")
            time.sleep(30)
    
def mk2b_init():
    # Init 2B threads settings
    for init_bt_name in BT_UNITS:
        threads_settings[init_bt_name] = {
            # Channel A
            "ch_A": 0,  # ch_A target level for the 2B
            "ch_A_max": 0,  # ch_A set max value
            "ch_A_ramp_phase": 0,  # ramp phase
            "ch_A_ramp_prct": 100,  # ramp % of max for ch A
            "ch_A_multiplier": 100,  # percentage of level multiplier
            # Channel B
            "ch_B": 0,  # ch_B target level for the 2B
            "ch_B_max": 0,  # ch_B set max value
            "ch_B_ramp_phase": 0,  # ramp phase
            "ch_B_ramp_prct": 100,  # ramp % of max for ch B
            "ch_B_multiplier": 100,  # percentage of level multiplier
            # Soft ramp
            "ramp_time": 120,  # ramp duration
            "ramp_wave": False,  # ramp decrease after max also reset to min
            "ramp_progress": 0,  # progress in ramp cycle
            # Channels usage
            "ch_A_use": DEFAULT_USAGE[init_bt_name]['A'],  # ch_A usage
            "ch_B_use": DEFAULT_USAGE[init_bt_name]['B'],  # ch_B usage
            # waveform setting 1
            "adj_1": DEFAULT_USAGE_SETTING[init_bt_name]['adj_1'],  # 2B adj 1 target setting
            "adj_1_max": DEFAULT_USAGE_SETTING[init_bt_name]['adj_1'],  # 2B adj 1 set max value
            "adj_1_ramp_phase": 0,  # ramp phase
            "adj_1_ramp_prct": 100,  # ramp % of max for adj_1
            # waveform setting 2
            "adj_2": DEFAULT_USAGE_SETTING[init_bt_name]['adj_2'],  # 2B adj 2 target setting
            "adj_2_max": DEFAULT_USAGE_SETTING[init_bt_name]['adj_2'],  # 2B adj 2 set max value
            "adj_2_ramp_phase": 0,  # ramp phase
            "adj_2_ramp_prct": 100,  # ramp % of max for adj_2
            # 2B timer adjusts
            "adj_3": DEFAULT_USAGE_SETTING[init_bt_name]['adj_3'],  # ramp speed
            "adj_4": DEFAULT_USAGE_SETTING[init_bt_name]['adj_4'],  # wrap factor
            # power config
            "ch_link": False,  # link between ch A and B (not used)
            "level_d": False,  # Dynamic power mode
            "level_h": DEFAULT_USAGE_SETTING[init_bt_name]['level_h'],  # L/H c
            "level_map": 0,  # power map used
            "power_bias": 0,  # power bias usage
            # mode
            "mode": DEFAULT_USAGE_SETTING[init_bt_name]['mode'],  # mode
            # status
            "cnx_ok": False,  # 2B connexion status
            "sync": False,  # 2B settings are synchronized
            "updated": False  # values are changed
        }
        
    Logger.success(f"[UNITS] Initialized 2B initials settings for {len(BT_UNITS)} Units.")
    
bot = Bot2b3()

# REST API
def start_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
@app.get("/")
async def api_home():
    return {
        "version": "1.0.0",
        "app": "Plune"
    }
    
@app.get("/sensors")
async def sensors():
    return store.get_all_sensors_settings()

@app.get("/units")
async def units():    
    return threads_settings
    # return threads_settings

@app.get("/update")
async def upd():
    # await bot.add_event_action(
    #     'chaster_pillory_vote',
    #     'pillory_chaster' + '_' + "lucie",
    #     time.localtime()
    # )
    await store.websocket.broadcast({
        "type": "sensor-notification",
        "payload": ['sensor 1 updated']
    })
    
    return {"success": "OK"}

# WebSocket API
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user_id = None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        # role = payload.get("role")
        
        # connect User to WebSocket
        await store.websocket.connect(user_id, websocket)
           
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "payload": {
                "message": "WebSocket connected successfully",
                "userId": user_id
            }
        })
        
        await websocket.send_json({
            "type": "sensors:init",
            "payload": store.get_all_sensors_settings()
        })
        
        # Heartbeat and Message handling
        while True:
            try:
                # Wait for messages from client with timeout
                text = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60
                )
                
                message = json.loads(text)
                if message.get("type") != "ping": 
                    print(f"📨 Received: {json.dumps(message, indent=2)}")
                
                msg_id = message.get("id")
                msg_type = message.get("type")
                msg_payload = message.get("payload")

                if msg_type == "ping":
                    """
                        reply to ping for keepalive
                    """
                    await websocket.send_json({"type": "pong"})
                    continue
                elif msg_type == "core:stop":
                    """
                        Emergency shutdown all units and queue
                    """
                    if store.check_permission(user_id, Permission.WRITE_UNITS):
                        bot.queueRunning = False
                        for unit in BT_UNITS:
                            for ch in ('ch_A', 'ch_B'):
                                threads_settings[unit]['updated'] = True
                                threads_settings[unit][ch] = 0
                                threads_settings[unit][ch + '_max'] = 0
                                
                        await websocket.send_json({
                            "type": "command",
                            "payload": {"status": "ok"},
                            "id": msg_id
                        })
                    else:
                        await websocket.send_json({
                            "type": "command",
                            "payload": {"status": "error", "message": "Missing permission: WRITE_UNITS"},
                            "id": msg_id
                        })
                elif msg_type == "sensors:update":
                    """
                        Update one or more Sensors
                    """
                    if store.check_permission(user_id, Permission.WRITE_SENSORS):
                        # loop over sensors then fields
                        for sensorName, value in msg_payload.items():
                            store.update_sensor_fields(sensorName, value)

                        # reply with ok
                        await websocket.send_json({
                            "type": "command",
                            "payload": {"status": "ok"},
                            "id": msg_id
                        })
                    else:
                        await websocket.send_json({
                            "type": "command",
                            "payload": {"status": "error", "message": "Missing permission: WRITE_SENSORS"},
                            "id": msg_id
                        })
                # Handle client messages (e.g., commands)
                elif msg_type == "get:notifications":
                    print(f"🔔 Get notifications - ID: {msg_id}")
                    
                    # Récupérer les notifications
                    notifications = [
                        {"id": 1, "message": "Test notification 1"},
                        {"id": 2, "message": "Test notification 2"}
                    ]
                    
                    # IMPORTANT : Renvoyer avec l'ID
                    response = {
                        "type": "get:notifications",
                        "payload": notifications,
                        "id": msg_id  # ← CRUCIAL
                    }
                    
                    print(f"📤 Sending: {json.dumps(response)}")
                    await websocket.send_json(response)
                else:
                    """
                        Message not supported
                    """
                    print(f"⚠️ Unknown message type: {msg_type}")
                    # if data.get("type") == "command":
                    #     pprint(data)
                    #     # command = DeviceCommand(**data.get("data"))
                    #     # await device_store.websocket.send_command(command)
                
            except asyncio.TimeoutError:
                print("💓 Sending heartbeat ping")
                await websocket.send_json({"type": "ping"})
                continue 

    except jwt.PyJWTError as e:
        print(f"❌ JWT error: {e}")
        await websocket.close(code=4001, reason="Invalid token")
        
    except WebSocketDisconnect:
        print(f"🔴 Client disconnected: {user_id}")
        
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if user_id:
            store.websocket.disconnect(user_id)
# bot

if __name__ == '__main__':
    
    Logger.info("Starting PlunEStim 1.0.0")
    
    threads = {}
    
    # Profiles Module
    profile = ProfileModule()
    profile.loadProfiles()
    
    # init thread for BT sensors
    if ENABLE_BT_SENSORS:
        for name, addr, service in BT_SENSORS:
            threads[name] = Thread(target=thread_sensors_bt, args=(name, addr, service))

    mk2b_init()
    # init threads for each mk2b unit
    if ENABLE_MK2BT:
        for bt_name in BT_UNITS:
            threads[bt_name] = Thread(target=thread_bt_unit, args=(bt_name, threads_settings[bt_name]))
            
    # init threads for software ramp
    threads['ramp'] = Thread(target=thread_update_ramp)

    # api
    threads['api'] = Thread(target=start_api)

    # start all thread
    for tr in threads.keys():
        Logger.warning(f"[Main] Starting thread '{tr}'!")
        threads[tr].daemon = True
        threads[tr].start()

    # start Discord Bot
    while True:
        try:
            Logger.info("[Discord] Loading Discord cogs...")
            
            # Try to load all the cogs
            for cog in get_cogs():
                try:
                    bot.load_extension(cog)
                    Logger.success(f"[Cogs] Successfully loaded '{cog}'!")
                    # Logger.info("Loaded " + cog)
                except Exception as e:
                    Logger.error(e)
                    print(e)
            
            Logger.info("[Discord] Starting Discord Bot...")
            bot.run(DISCORD_TOKEN)
            
        except Exception as err:
            Logger.error(f'Restarting Discord bot after major error {err}')
            time.sleep(1000)
            continue
