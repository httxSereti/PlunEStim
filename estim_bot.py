# 2b boo
# MAIN TODO

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
from functools import partial
from threading import Thread
from typing import Optional

import aiohttp
import bluetooth  # type: ignore
import dotenv
import nextcord
import plotly.graph_objs as go  # type: ignore
import pyttsx3  # type: ignore
import serial.tools.list_ports  # type: ignore
from bleak import BleakClient
from discord_handler import DiscordHandler  # type: ignore
from discord_webhook import DiscordWebhook
from nextcord import Interaction, SlashOption
from nextcord.ext import commands
from nextcord.ext import tasks
from plotly.subplots import make_subplots  # type: ignore

# load env
dotenv.load_dotenv('config_bot.env')

# DEBUG setting
NO_MK2BT = False  # Disable mk2bt thread
NO_BT_SENSORS = True  # Disable BT sensors thread
NO_VOCAL = True

# API change
intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True

# Directory
DIR_BACKUP = pathlib.Path(os.getenv('DIR_BACKUP'))
DIR_PROFILE = pathlib.Path(os.getenv('DIR_PROFILE'))
DIR_TMP = pathlib.Path(os.getenv('DIR_TMP'))

# Chaster API
CHASTER_TOKEN = os.getenv('CHASTER_TOKEN')
CHASTER_URL = os.getenv('CHASTER_URL')
CHASTER_HEADERS = {'accept': 'application/json', 'Authorization': 'Bearer ' + CHASTER_TOKEN,
                   'Content-Type': 'application/json'}

# BT serial configuration for 2B
SERIAL_BAUDRATE = 9600
SERIAL_RETRY = 5
SERIAL_TIMEOUT = 2
SERIAL_KEEPALIVE = 20  # check every x second the connexion (100 ms steps)
BT_UNITS = ("UNIT1", "UNIT2", "UNIT3")

# Bot config
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_BOT_CHANNEL_NAME = os.getenv('DISCORD_BOT_CHANNEL_NAME')
STATUS_IMG_FILE = os.getenv('STATUS_IMG_FILE')
DISCORD_MY_ACCOUNT = os.getenv('DISCORD_MY_ACCOUNT')
DISCORD_TRUSTED_ACCOUNT = os.getenv('DISCORD_TRUSTED_ACCOUNT').split(';')
DISCORD_LOG_WEBHOOKS = os.getenv('DISCORD_LOG_WEBHOOKS')
DISCORD_STATUS_WEBHOOKS = os.getenv('DISCORD_STATUS_WEBHOOKS')
TESTING_GUILD_ID = int(os.getenv('TESTING_GUILD_ID'))

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

# speech synthesis
vocal_queue = []


class VocalLogger(logging.Handler):
    def write(*args):
        for txt in args:
            vocal_queue.append(txt[:60])  # too long with big messages

    def flush(*args):
        return None


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
                    format='%(asctime)s: %(threadName)s %(module)s %(message)s',
                    datefmt='%H:%M:%S',
                    filename='log.txt',
                    filemode='w')
# Console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter('%(asctime)s: %(threadName)s %(module)s %(message)s'))
console.addFilter(filter_logger)
logger.addHandler(console)
# Vocal
vocal_log = logging.StreamHandler(VocalLogger)
vocal_log.setLevel(logging.WARNING)
logger.addHandler(vocal_log)
# Discord Log
discord_log = DiscordHandler(DISCORD_LOG_WEBHOOKS, 'Estim Bot', notify_users=[], emit_as_code_block=False, max_size=200)
discord_log.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
discord_log.setLevel(BOT_LOG_LEVEL)
logger.addHandler(discord_log)
# Discord Bot
discord_msg = DiscordHandler(DISCORD_STATUS_WEBHOOKS, 'Estim Bot', notify_users=[], emit_as_code_block=False,
                             max_size=200)
discord_msg.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%H:%M:%S"))
discord_msg.setLevel(BOT_MSG_LEVEL)
logger.addHandler(discord_msg)
# debug
logger_nextcord = logging.getLogger('nextcord')
logger_nextcord.setLevel(logging.DEBUG)
handler_nextcord = logging.FileHandler(filename='nextcord.log', encoding='utf-8', mode='w')
handler_nextcord.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger_nextcord.addHandler(handler_nextcord)

logger_asyncio = logging.getLogger('asyncio')
logger_asyncio.setLevel(logging.DEBUG)
handler_asyncio = logging.FileHandler(filename='asyncio.log', encoding='utf-8', mode='w')
handler_asyncio.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger_asyncio.addHandler(handler_asyncio)

logger_aiohttp = logging.getLogger('aiohttp.client')
logger_aiohttp.setLevel(logging.DEBUG)
handler_aiohttp = logging.FileHandler(filename='aiohttp.log', encoding='utf-8', mode='w')
handler_aiohttp.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger_asyncio.addHandler(handler_aiohttp)

# init multi threading
sensors_settings = {}
threads_settings = {}
threads = {}

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


class Bot2b3(commands.Bot):
    """ Bot for control SDRConsole
    """
    channelIdTxt: nextcord.TextChannel.id

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

    def __init__(self):
        #
        # Bot heritage
        super().__init__(command_prefix="/", description='ESTIM Remote management',
                         help_command=None,
                         intents=intents,
                         rollout_all_guilds=True,
                         default_guild_ids=[TESTING_GUILD_ID]
                         )
        self.bot_channel = None  # channel dedicated to the bot
        self.bot_last_mess = None  # for removing the previous graph
        self.account_w = DISCORD_MY_ACCOUNT  # default wearer account
        self.account_h = [DISCORD_MY_ACCOUNT] + DISCORD_TRUSTED_ACCOUNT  # default holder account
        self.action_queue = []  # async actions for estim config
        self.back_action_queue = []  # async back actions for estim config
        self.update_graph_status = 0  # update the image of all units status
        self.BOT_HELP_CMD = {'help': ''}  # help structure
        self.previous_2B_sync = False  # previous global 2B sync
        self.queuing_pause = False  # stop the management of new action
        self.chaster_lockid = None  # id of the current chaster lock
        self.chaster_taskid = None  # id of the task extension
        self.chaster_task_pool = 0  # number of poll
        self.chaster_taskvote = {}  # vote list for task
        self.chaster_history_event_parsed = []  # wof/vote list for duration already parsed
        self.chaster_pilloryid = None  # id of the pillory extension
        self.chaster_pillory_pool = 0  # number of poll
        self.chaster_pillory_vote_by_id = {}

        async def check_permission(ctx: Interaction, wearer: bool, holder: bool) -> bool:
            """
            check if the author can do the action
            Args:
                ctx: discord context
                wearer: the wearer can do the action
                holder: the holder can do the action

            Returns: true if authorized

            """
            if wearer and str(ctx.user) in self.account_w:
                return True
            if holder and str(ctx.user) in self.account_h:
                return True
            await ctx.response.send_message(f'Your account {str(ctx.user)}is not granted for this command')
            return False

        @self.slash_command(name='backup', description='Backup bot config')
        async def bot_backup(interaction: Interaction,
                             filename: str = SlashOption(name='name', description='backup_name',
                                                         required=True)) -> None:
            backup_data = {
                'EVENT_ACTION': EVENT_ACTION,
                'threads_settings': threads_settings,
                'sensors_settings': sensors_settings,
                'USAGE_LIMIT': USAGE_LIMIT
            }
            filename = filename + '.json'
            bck_file = open(DIR_BACKUP / filename, 'w')
            json.dump(backup_data, bck_file, indent=4)
            bck_file.close()
            await interaction.response.send_message("backup done")

        @self.slash_command(name='restore', description='Restore bot config')
        async def bot_recover(interaction: Interaction,
                              filename: str = SlashOption(name='name', description='backup_name',
                                                          required=True)) -> None:
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
            # sensor
            for sensor in backup_data['sensors_settings'].keys():
                for field in backup_data['sensors_settings'][sensor].keys():
                    if re.search(r"(_alarm_level|_delay_on|_delay_off)", field):
                        sensors_settings[sensor][field] = backup_data['sensors_settings'][sensor][field]
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
                                    threads_settings[bck_bt_name][field] = int(
                                        bck_settings[bck_bt_name][field] * lvl_prct_arg / 100)
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

        @self.slash_command(name='status',
                            description='show bot pic status in the current channel')
        async def bot_status(interaction: Interaction) -> None:
            await interaction.response.send_message('status:')
            await interaction.channel.send(files=[nextcord.File(STATUS_IMG_FILE)])
            return None

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
            if await check_permission(interaction, False, True):
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
            if await check_permission(interaction, False, True):
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
            if await check_permission(interaction, False, True):
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
            if await check_permission(interaction, False, True):
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

        @self.slash_command(name='queuing',
                            description='Event queuing management')
        async def bot_queuing(interaction: Interaction, action: str = SlashOption(
            name="action",
            description="action about event queue",
            required=True,
            choices=['resume', 'pause', 'list', 'purge']
        )) -> None:
            if action == 'list':
                list_action = ['-- waiting events --']
                nb = 0
                for idx in range(len(self.action_queue)):
                    if self.action_queue[idx]['counter'] == -1:
                        nb = nb + 1
                        list_action.append(self.action_queue[idx]['origine'])
                list_action.append("  {} event waiting in queue".format(nb))
                await interaction.response.send_message("\n".join(list_action))
                return None

            # need more permission for others commands
            if await check_permission(interaction, False, True):
                if action == 'purge':
                    for idx in range(len(self.action_queue)):
                        if self.action_queue[idx]['counter'] == -1:
                            self.action_queue[idx]['counter'] = self.action_queue[idx]['duration']
                    await interaction.response.send_message('queue management purged')
                elif action == 'pause':
                    if self.queuing_pause:
                        await interaction.response.send_message('queuing is already paused')
                    else:
                        await interaction.response.send_message('pause event queue management')
                        self.queuing_pause = True
                elif action == 'resume':
                    if self.queuing_pause:
                        await interaction.response.send_message('resume queue management')
                        self.queuing_pause = False
                    else:
                        await interaction.response.send_message('queue management is already active')
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
            if await check_permission(interaction, False, True):
                mode_id = await self.check_mode(interaction, mode_arg)
                if mode_id:
                    for unit in await self.check_unit(interaction, unit_arg):
                        unit = 'UNIT' + str(unit)
                        threads_settings[unit]['updated'] = True
                        threads_settings[unit]['mode'] = mode_id
                        if MODE_2B[mode_id]['adj_2'] == '':  # reset to adj_1 for modes without adj_2
                            threads_settings[unit]['adj_2'] = threads_settings[unit]['adj_1']
                    self.update_graph_status = 0
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
            if await check_permission(interaction, True, False):
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
            if await check_permission(interaction, False, True):
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
            if await check_permission(interaction, False, True):
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
                    self.update_graph_status = 0
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
                self.update_graph_status = 0
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
            if await check_permission(interaction, False, True):
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
                self.update_graph_status = 0
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
            if level_op == '+' or level_op == '%+' or await check_permission(interaction, False, True):
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
                    self.update_graph_status = 0
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
            if await check_permission(interaction, False, True):
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
                self.update_graph_status = 0
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

            if await check_permission(interaction, False, True):
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
                self.update_graph_status = 0
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

            if await check_permission(interaction, False, True):
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
                self.update_graph_status = 0
                await interaction.response.send_message("\n".join(txt))
            return None

        # ----- EVENT MANAGEMENT ----
        @self.slash_command(name='events')
        async def bot_events(interaction: nextcord.Interaction):
            pass

        @bot_events.subcommand(description='List all events action')
        async def list(interaction: Interaction) -> None:
            reply_event = '------ actions for events -----------'
            for action in EVENT_ACTION:
                if EVENT_ACTION[action]:
                    if EVENT_ACTION[action]['type'] == 'lvl':
                        reply_event = "{}\n event {} => unit:{} channel:{} level:{} duration:{} wait other event:{}". \
                            format(reply_event, action, EVENT_ACTION[action]['unit'],
                                   EVENT_ACTION[action]['dest'],
                                   EVENT_ACTION[action]['level'],
                                   EVENT_ACTION[action]['duration'],
                                   EVENT_ACTION[action]['wait']
                                   )
                    elif EVENT_ACTION[action]['type'] == 'pro':
                        reply_event = "{}\n event {} => profile:{} level:{}% duration:{} wait other event:{}". \
                            format(reply_event, action, EVENT_ACTION[action]['profile'],
                                   EVENT_ACTION[action]['level'],
                                   EVENT_ACTION[action]['duration'],
                                   EVENT_ACTION[action]['wait']
                                   )
                    elif EVENT_ACTION[action]['type'] == 'add':
                        reply_event = "{}\n event {} => add duration:{} min only max:{}". \
                            format(reply_event, action, EVENT_ACTION[action]['duration'],
                                   EVENT_ACTION[action]['only_max']
                                   )
                    elif EVENT_ACTION[action]['type'] == 'multi':
                        reply_event = "{}\n event {} => change multiplier: {} % on {} random={}". \
                            format(reply_event, action,
                                   EVENT_ACTION[action]['prct'], EVENT_ACTION[action]['target']
                                   , EVENT_ACTION[action]['rnd']
                                   )
            await interaction.response.send_message(reply_event)

        # ----- SENSORS --------
        @self.slash_command(name='sensors', )
        async def bot_sensors(interaction: nextcord.Interaction):
            pass

        @bot_sensors.subcommand(description='Display sensors configuration')
        async def display(interaction: Interaction) -> None:
            config_txt = [" --- Sensors configuration ---"]
            for sensor in sorted(sensors_settings.keys()):
                config_txt.append(" --- {}  alarm enable:{}".format(sensor, sensors_settings[sensor]["alarm_enable"]))
                for field in sorted(sensors_settings[sensor].keys()):
                    if ma := re.match(r"^(\w+)_alarm_level$", field):
                        value = ma[1]
                        config_txt.append("{} threshold:{} start delay:{} restart delay:{}".format(
                            value,
                            sensors_settings[sensor][value + '_alarm_level'],
                            sensors_settings[sensor][value + '_delay_on'],
                            sensors_settings[sensor][value + '_delay_off']))
            await interaction.response.send_message("\n".join(config_txt))
            return None

        @bot_sensors.subcommand(description='Activate sensor alarm')
        async def alarm(interaction: Interaction,
                        arg_sensor: str = SlashOption(name="sensor",
                                                      description="type of sensor measurement",
                                                      required=True,
                                                      choices=['motion1',
                                                               'motion2',
                                                               'sound']),
                        arg_enable: int = SlashOption(name="status",
                                                      description="Activate sensor alarm",
                                                      choices={'enable': 1, 'disable': 0},
                                                      required=True),
                        arg_delay: int = SlashOption(name="delay",
                                                     description="Delay before doing the change",
                                                     default=0,
                                                     min_value=0,
                                                     max_value=60,
                                                     required=False)
                        ) -> None:
            if await check_permission(interaction, False, True):
                if arg_delay > 0:
                    await interaction.response.send_message(
                        'Sensor {} alarm wil be set in {} sec'.format(arg_sensor, arg_delay))
                    await asyncio.sleep(arg_delay)
                else:
                    await interaction.response.send_message('Sensor {} alarm is set'.format(arg_sensor))
                sensors_settings[arg_sensor]['alarm_enable'] = bool(arg_enable)
            return None

        @bot_sensors.subcommand(description='Adjust sensors configuration')
        async def set(interaction: Interaction,
                      arg_mode: str = SlashOption(name="setting",
                                                  description="setting choice",
                                                  required=True,
                                                  choices={'level': 'level', 'on': 'on', 'off': 'off'},
                                                  ),
                      arg_type: str = SlashOption(name="type",
                                                  description="sensor measurement",
                                                  required=True,
                                                  choices={'position1': 'motion1,position',
                                                           'position2': 'motion2,position',
                                                           'move1': 'motion1,move',
                                                           'move2': 'motion2,move',
                                                           'sound': 'sound,sound'}),
                      arg_level: int = SlashOption(name="value",
                                                   description="trigger level",
                                                   min_value=1, max_value=50,
                                                   required=True)
                      ) -> None:
            if await check_permission(interaction, False, True):
                sensor = arg_type.split(',')
                if arg_mode == 'level':
                    if await self.check_sensor_level(interaction, arg_level) > 0:
                        sensors_settings[sensor[0]][sensor[1] + '_alarm_level'] = arg_level
                        await interaction.response.send_message('New level is set')
                elif await self.check_sensor_duration(interaction, arg_level) > 0:
                    sensors_settings[sensor[0]][sensor[1] + '_delay_' + arg_mode] = arg_level
                    await interaction.response.send_message('New duration is set')
            return None

        # ----- EMERGENCY STOP ----------
        @self.slash_command(name='stop',
                            description='Emergency stop')
        async def bot_stop(interaction: Interaction) -> None:
            if await check_permission(interaction, False, True):
                self.queuing_pause = True
                for unit in BT_UNITS:
                    for ch in ('ch_A', 'ch_B'):
                        threads_settings[unit]['updated'] = True
                        threads_settings[unit][ch] = 0
                        threads_settings[unit][ch + '_max'] = 0
                await interaction.response.send_message('stop all channels')
                self.update_graph_status = 0
            return None

        # ----- SECURITY COMMANDS ------
        @self.slash_command(name='security', )
        async def bot_security(interaction: nextcord.Interaction):
            pass

        @bot_security.subcommand(description='Remove most bot access for the wearer')
        async def lock(interaction: Interaction) -> None:
            if await check_permission(interaction, False, True):
                if self.account_w in self.account_h:
                    self.account_h.remove(self.account_w)
                    await interaction.response.send_message('Remove change permissions to the wearer')
                else:
                    await interaction.response.send_message('The permissions for the wearer are already removed')

        @bot_security.subcommand(description='Reverse the lock command')
        async def unlock(interaction: Interaction) -> None:
            if await check_permission(interaction, False, True):
                if self.account_w not in self.account_h:
                    self.account_h.append(self.account_w)
                    await interaction.response.send_message('Add change permissions to the wearer')
                else:
                    await interaction.response.send_message('The change permissions is already active for the wearer')

        @bot_security.subcommand(description='list holder account')
        async def list(interaction: Interaction) -> None:
            await interaction.response.send_message('the holder list is : {}'.format(','.join(self.account_h)))
            return None

        @bot_security.subcommand(description='add a discord account to holder list')
        async def holder(interaction: Interaction,
                         type_action: str = SlashOption(
                             name="type_action",
                             description="Manage holder list",
                             choices=["add", "remove"],
                             required=True
                         ),
                         account: str = SlashOption(name='account', description='Discord account',
                                                    required=True)) -> None:
            if await check_permission(interaction, True, True):
                if type_action == 'add' and account not in self.account_w and account not in self.account_h:
                    self.account_h.append(account)
                if type_action == 'remove' and account not in self.account_w and account in self.account_h:
                    self.account_h.remove(account)
                await interaction.response.send_message('the holder list is now : {}'.format(','.join(self.account_h)))
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

            if await check_permission(interaction, False, True):
                for unit in await self.check_unit(interaction, unit_arg):
                    unit = 'UNIT' + str(unit)
                    # check if setting is valid
                    if ramp_prct_arg < 100:
                        threads_settings[unit][target_arg + '_ramp_phase'] = phase_arg
                        threads_settings[unit][target_arg + '_ramp_prct'] = ramp_prct_arg
                self.update_graph_status = 0
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

            if await check_permission(interaction, False, True):
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

    # add action into queue
    async def add_event_action(self, type_action: str, origin_action: str, event_time) -> None:
        # action parsed in the event
        m = re.search('^wof_([A-Z])([A-Z,a-z])([A-Z,a-z])$', type_action)
        if m:
            logger.info("New event type {} added in queue ".format(type_action))
            logger.warning("New custom task event")
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
                'counter': -1})

        # find action associated to the event
        elif EVENT_ACTION[type_action]:
            logger.info(
                "New event type {} added in queue : {}".format(type_action, EVENT_ACTION[type_action]))
            # Level change -> queue
            if EVENT_ACTION[type_action]['type'] == 'lvl':
                logger.warning("New level event")
                self.action_queue.append({
                    'origine': origin_action,
                    'type': 'lvl',
                    'unit': EVENT_ACTION[type_action]['unit'],
                    'dest': EVENT_ACTION[type_action]['dest'],
                    'level': await self.check_level(self, EVENT_ACTION[type_action]['level']),
                    'duration': await self.check_duration(self, EVENT_ACTION[type_action]['duration']),
                    'wait': EVENT_ACTION[type_action]['wait'],
                    'display': type_action + ' ' + time.strftime('%H:%M:%S', event_time),
                    'counter': -1})
            # Apply profile -> queue
            elif EVENT_ACTION[type_action]['type'] == 'pro':
                logger.warning("New profile event")
                self.action_queue.append({
                    'origine': origin_action,
                    'type': 'pro',
                    'profile': EVENT_ACTION[type_action]['profile'],
                    'level': EVENT_ACTION[type_action]['level'],
                    'duration': await self.check_duration(self, EVENT_ACTION[type_action]['duration']),
                    'wait': EVENT_ACTION[type_action]['wait'],
                    'display': type_action + ' ' + time.strftime('%H:%M:%S', event_time),
                    'counter': -1})
            # Multi change
            elif EVENT_ACTION[type_action]['type'] == 'multi':
                logger.warning("New multiplier event")
                for unit in BT_UNITS:
                    for ch in ['A', 'B']:
                        # find channel with this usage
                        if threads_settings[unit][f'ch_{ch}_use'] == EVENT_ACTION[type_action]['target'].lower() or \
                                EVENT_ACTION[type_action]['target'].lower() == 'all':
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
                logger.warning("New duration event")
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
            logger.info("New event type {} unknow".format(type_action))

    def reverse_action(self, action: dict) -> None:
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
            logger.info(f'return to initial value for unit {unit} var {var} is {new_val}')
            threads_settings[unit]['updated'] = True
            threads_settings[unit][var] = new_val
        elif action['type'] == 'pro':
            logger.info(f'return to initial profile')
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

    async def apply_action(self, action: dict) -> None:
        """
        Apply action from Event
        Args:
            action: Dict with action to do

        Returns: None

        """
        logger.info("{} action start".format(action['origine']))
        txt = ["{} action start".format(action['origine'])]
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
                    txt.append(">> level for {} {}-->{}".format(threads_settings[unit][f'ch_{ch}_use'],
                                                                old_val, new_val))
            self.update_graph_status = 0
        # profile update
        elif action['type'] == 'pro':
            if action['profile'] == 'X':
                action['profile'] = random.choice(PROFILE_RANDOM)
            filename = action['profile'] + '.json'
            if not os.path.isfile(DIR_PROFILE / filename):
                logger.warning("Profile file {} missing".format(DIR_PROFILE / filename))
            else:
                # backup current profile
                txt.append(">> backup current profile")
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

        logger.info("\n".join(txt))
        self.update_graph_status = 0

    # BT sensors polling for new alarm
    async def bt_sensor_alarm(self):
        """
        Check alarm about position and moving for the BT sensors and apply actions if needed
        Args:

        Returns:
            None

        """
        # loop by sensor
        for sensor in sorted(sensors_settings.keys()):
            # loop by value from the sensor
            for field in sorted(sensors_settings[sensor].keys()):
                # find the name of the sensor from the config
                if m := re.match(r"^(\w+)_alarm_number$", field):
                    value = m[1]
                    # check if the alarm counter have changed
                    if sensors_settings[sensor][value + '_alarm_number'] != \
                            sensors_settings[sensor][value + '_alarm_number_action']:
                        sensors_settings[sensor][value + '_alarm_number_action'] = \
                            sensors_settings[sensor][value + '_alarm_number']
                        # if alarm is active, add event in queue
                        if EVENT_ACTION[value] and sensors_settings[sensor]['alarm_enable']:
                            logger.warning('alarm sensor ' + sensor)
                            await self.add_event_action(value, sensor + ' BT sensor ' + value + str(
                                sensors_settings[sensor][value + '_alarm_number_action']), time.localtime())

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
            async with session.get(f'{CHASTER_URL}/locks?status=active',
                                   headers=CHASTER_HEADERS) as data_current_lock:
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
                        elif chaster_event['type'] == 'wheel_of_fortune_turned' and chaster_event['payload']['segment'][
                            'type'] == 'text':
                            # Looking for keyword
                            m = re.search('^(\\d|[A-Z][A-Z,a-z][A-Z,a-z]):',
                                          chaster_event['payload']['segment']['text'])
                            if m:
                                logger.warning('new chaster wheel of fortune action:' + m.group(1))
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

    # Chaster parse pillory pooling
    async def chaster_pillory(self) -> None:
        """
        Parse Chaster task extention for detecting new vote
        Args:

        Returns: None
        """
        # if no active pillory extention
        if not self.chaster_pilloryid:
            return
        # get pillory info from API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    f'{CHASTER_URL}/locks/{self.chaster_lockid}/extensions/{self.chaster_pilloryid}/action',
                    json={"action": "getStatus", "payload": {}}, headers=CHASTER_HEADERS) as data_current_vote:
                json_feed = await data_current_vote.json()
                if 'votes' in json_feed:
                    for instance in json_feed['votes']:
                        if instance['_id'] not in self.chaster_pillory_vote_by_id:
                            self.chaster_pillory_vote_by_id[instance['_id']] = 0
                        # check for new votes
                        for i in range(self.chaster_pillory_vote_by_id[instance['_id']], instance['nbVotes']):
                            logger.warning('chaster new pillory vote')
                            # add event to queue
                            await self.add_event_action(
                                'pilloryvote',
                                'pillory_chaster_' + str(i) + '_' + instance['_id'],
                                time.localtime())
                            self.chaster_pillory_vote_by_id[instance['_id']] = instance['nbVotes']

    # for exception in tasks chaster_pillory
    @tasks.loop(seconds=30)
    async def rerun_chaster_pillory(self):
        try:
            await self.chaster_pillory()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning(f"Task exception chaster_pillory")
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
                        self.reverse_action(action)
        # Update global stats
        queue_stats['running'] = queue_nb_run
        queue_stats['waiting'] = queue_nb_wait

        # if pause is enable stop here
        if self.queuing_pause:
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

    # when bot is ready
    async def on_ready(self):
        # Find discord channel for status
        for channel in bot.get_all_channels():
            if str(channel.type) == 'text' and DISCORD_BOT_CHANNEL_NAME in channel.name:
                self.channelIdTxt = channel.id
                self.bot_channel = self.get_channel(self.channelIdTxt)
                break
        else:
            return False
        logger.warning('Discord online')
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


def build_status_pic():
    """
    build the pic with all gauges about units settings
    Returns:

    """

    def unit_status_color(unit_name):
        color = "green"
        if not threads_settings[unit_name]['sync']:
            color = "yellow"
        if not threads_settings[unit_name]['cnx_ok']:
            color = "red"
        return color

    def delta_display_type(unit_name, ch):
        if threads_settings[unit_name][ch + '_ramp_prct'] < 100:
            return "gauge+number+delta"
        else:
            return "gauge+number"

    def sensor_color(sensor):
        color = "red"
        if sensors_settings[sensor]['sensor_online']:
            if sensors_settings[sensor]['alarm_enable']:
                color = "green"
            else:
                color = "gray"
        return color

    def delta_info(unit_name, ch):
        delta_dict = {}
        delta_dict['reference'] = int(
            threads_settings[unit_name][ch] + threads_settings[unit_name][ch + '_max'] *
            threads_settings[unit_name][ch + '_ramp_prct'] / 100
        )
        if threads_settings[unit_name][ch + '_ramp_prct'] < 100:
            delta_dict['decreasing'] = {'color': 'green'}
        return delta_dict

    def unit_level_txt(unit_name):
        if threads_settings[unit_name]['level_d']:
            level_txt = CHECK_ARG['POWER_BIAS'][threads_settings[unit_name]['power_bias']]
        elif threads_settings[unit_name]['level_h']:
            level_txt = 'H'
        else:
            level_txt = 'L'
        level_txt = level_txt + chr(threads_settings[unit_name]['level_map'] + ord('a'))
        return level_txt

    indicators = []  # array of all graphs
    for unit_name in BT_UNITS:
        # --- Unit info
        indicators.append(go.Indicator(
            mode="number",
            value=int(unit_name[-1]),
            title={"text": "{mode}".format(mode=MODE_2B[threads_settings[unit_name]['mode']]['id']),
                   "font": {"size": 10}},
            number={'suffix': unit_level_txt(unit_name), "font": {"color": unit_status_color(unit_name)}})
        )
        # -- Channel Info
        for ch in ('ch_A', 'ch_B'):
            # Level
            usage = threads_settings[unit_name][ch + '_use']
            indicators.append(go.Indicator(
                mode=delta_display_type(unit_name, ch),
                value=threads_settings[unit_name][ch],
                title={'text': ch[-1] + ':' + threads_settings[unit_name][ch + '_use'], "font": {"size": 11}},
                delta=delta_info(unit_name, ch),
                gauge={
                    'axis': {'range': [0, 100], 'visible': False},
                    'bar': {'color': 'black'},
                    'steps': [
                        {'range': [0, USAGE_LIMIT[usage]['start']],
                         'color': "lightgray"},
                        {'range': [USAGE_LIMIT[usage]['start'],
                                   USAGE_LIMIT[usage]['warn']], 'color': "lightgreen"},
                        {'range': [USAGE_LIMIT[usage]['warn'],
                                   USAGE_LIMIT[usage]['max']], 'color': "yellow"},
                        {'range': [USAGE_LIMIT[usage]['max'], 100], 'color': "red"}],
                    'threshold': {
                        'line': {'color': "black", 'width': 2},
                        'thickness': 0.55,
                        'value': threads_settings[unit_name][ch + '_max']}
                }
            ))
        # -- Adjuts info
        for ch in ('adj_1', 'adj_2'):
            indicators.append(
                go.Indicator(mode=delta_display_type(unit_name, ch), value=threads_settings[unit_name][ch],
                             title={'text': MODE_2B[threads_settings[unit_name]['mode']][ch],
                                    "font": {"size": 11}},
                             delta=delta_info(unit_name, ch),
                             gauge={
                                 'axis': {'range': [0, 100], 'visible': False},
                                 'bar': {'color': 'black'},
                                 'steps': [
                                     {'range': [0, 100], 'color': "lightgray"}
                                 ],
                                 'threshold': {
                                     'line': {'color': "black", 'width': 2},
                                     'thickness': 0.75,
                                     'value': threads_settings[unit_name][ch + '_max']}
                             }))
        # -- multiplier Info
        for ch in ('ch_A', 'ch_B'):
            # Multiplier
            # -- 2B Ramp speed
            indicators.append(go.Indicator(
                mode="number",
                value=int(threads_settings[unit_name][ch + '_multiplier']),
                title={"text": "multi<br>" + ch, "font": {"size": 9}},
                number={'suffix': "%", "font": {"size": 10}}
            )
            )
        # --- Ramp duration
        if threads_settings[unit_name]['ramp_time'] == 0:
            ramp_mode = 'disable'
        else:
            if threads_settings[unit_name]['ramp_wave']:
                ramp_mode = 'Wave'
            else:
                ramp_mode = 'Ramp'
        indicators.append(go.Indicator(
            mode="number",
            value=threads_settings[unit_name]['ramp_time'],
            title={"text": "cycle<br>{}".format(ramp_mode),
                   "font": {"size": 10}},
            number={'suffix': 's', "font": {"size": 9}})
        )
        # -- 2B Ramp speed
        indicators.append(go.Indicator(
            mode="number",
            value=int((CHECK_ARG['RAMP_SPEED'][threads_settings[unit_name]['adj_3']])[1:]),
            title={"text": "2B ramp<br>speed", "font": {"size": 9}},
            number={'prefix': "x", "font": {"size": 14}}
        )
        )
        # -- Wrap time factor
        indicators.append(go.Indicator(
            mode="number",
            value=int((CHECK_ARG['WRAP_FACTOR'][threads_settings[unit_name]['adj_4']])[1:]),
            title={"text": "wrap<br>timer", "font": {"size": 9}},
            number={'prefix': "x", "font": {"size": 14}}
        )
        )

    # Empty
    indicators.append(None)
    # Motion sensors value
    for sensor in ('motion1', 'motion2'):
        for ch in ('position', 'move'):
            indicators.append(go.Indicator(
                mode="gauge+number",
                value=sensors_settings[sensor]['current_' + ch],
                title={'text': ch + sensor[-1], "font": {"size": 11, "color": sensor_color(sensor)}},
                gauge={  #
                    'axis': {'range': [0, 50], 'visible': False},
                    'bar': {'color': 'black'},
                    'steps': [
                        {'range': [0, sensors_settings[sensor][ch + '_alarm_level']], 'color': "lightgray"},
                        {'range': [sensors_settings[sensor][ch + '_alarm_level'], 50], 'color': "red"}]
                }
            ))

    # sound sensors
    indicators.append(go.Indicator(
        mode="gauge+number",
        value=sensors_settings['sound']['current_sound'],
        title={'text': 'sound', "font": {"size": 11, "color": sensor_color('sound')}},
        gauge={  #
            'axis': {'range': [0, 50], 'visible': False},
            'bar': {'color': 'black'},
            'steps': [
                {'range': [0, sensors_settings['sound']['sound_alarm_level']], 'color': "lightgray"},
                {'range': [sensors_settings['sound']['sound_alarm_level'], 50], 'color': "red"}]
        }))

    # Empty
    indicators.append(None)
    # queue done
    indicators.append(go.Indicator(
        mode="number",
        value=queue_stats['done'],
        title={"text": "done", "font": {"size": 9}},
        number={"font": {"size": 14}}))
    # queue size
    indicators.append(go.Indicator(
        mode="number",
        value=queue_stats['waiting'],
        title={"text": "queued", "font": {"size": 9}},
        number={"font": {"size": 14}}))
    # running size
    indicators.append(go.Indicator(
        mode="number",
        value=queue_stats['running'],
        title={"text": "run", "font": {"size": 9}},
        number={"font": {"size": 14}}))

    # ---build pic
    fig = make_subplots(
        rows=4,
        cols=10,
        column_widths=[0.10, 0.2, 0.2, 0.2, 0.2, 0.08, 0.08, 0.08, 0.08, 0.08],
        specs=[
            [{'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'}],
            [{'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'}],
            [{'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'}],
            [None, {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator'}, {'type': 'indicator'},
             {'type': 'indicator', "colspan": 2}, None,
             {'type': 'indicator'}, {'type': 'indicator'}, {'type': 'indicator'}]]
    )
    for x in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
        for y in (1, 2, 3, 4):
            if indicators[(y - 1) * 10 + x - 1]:
                fig.add_trace(indicators[(y - 1) * 10 + x - 1], row=y, col=x)
    fig['layout'].update(width=500,
                         height=300,
                         showlegend=False,
                         margin=dict(l=5, r=5, t=10, b=5),
                         )
    fig.write_image(STATUS_IMG_FILE)


def thread_push_status_pic():
    """
    Update the status in bot status and publish graph with all settings
    Returns:

    """
    logger.info(f"Start status pic thread")
    update_graph_status = 10
    last_id = None
    while True:
        try:
            time.sleep(0.5)
            if update_graph_status < 1:
                # new pic status
                build_status_pic()
                # remove previous
                if last_id:
                    webhook = DiscordWebhook(url=DISCORD_STATUS_WEBHOOKS, rate_limit_retry=True, username="bot status",
                                             id=last_id)
                    webhook.delete()
                # upload
                webhook = DiscordWebhook(url=DISCORD_STATUS_WEBHOOKS, rate_limit_retry=True, username="bot status")
                with open(STATUS_IMG_FILE, "rb") as f:
                    webhook.add_file(file=f.read(), filename=f'status.jpg')
                webhook.execute()
                last_id = webhook.id
                update_graph_status = 20  # minimal refresh
            else:
                update_graph_status = update_graph_status - 1
        except Exception as err:
            logger.info(f"Thread error in push_status_pic {err=}, {type(err)=}")
            time.sleep(30)


def sensor_check_val(sensor: str, measure: str, val: int) -> None:
    """
    Check if the sensor can fire an alarm
    Args:
        sensor: Name of the sensor
        measure: What the sensor check
        val: sensor value

    Returns:

    """

    # max value at 50
    sensors_settings[sensor]['current_' + measure] = min(round(val), 50)

    # no check if offline
    if not sensors_settings[sensor]['sensor_online']:
        return

    # trigger something or if in recovery
    if val > sensors_settings[sensor][measure + '_alarm_level'] or \
            sensors_settings[sensor][measure + '_alarm_counter'] < 0:
        sensors_settings[sensor][measure + '_alarm_counter'] = sensors_settings[sensor][
                                                                   measure + '_alarm_counter'] + 1

    # consecutive detect and activate delay_off
    if sensors_settings[sensor][measure + '_alarm_counter'] >= sensors_settings[sensor][measure + '_delay_on']:
        # alarm
        sensors_settings[sensor][measure + '_alarm_number'] = sensors_settings[sensor][
                                                                  measure + '_alarm_number'] + 1
        # add delay before the next alarm
        sensors_settings[sensor][measure + '_alarm_counter'] = -sensors_settings[sensor][measure + '_delay_off']


def sensor_notification(sensor, _, data: bytearray) -> None:
    """
    Function call for every BT notify
    Args:
        sensor:sensor name
        _:BT client
        data: notification data

    Returns:

    """
    if sensor == 'sound':
        level = int.from_bytes(data[0:1], byteorder='big', signed=False)
        sensor_check_val(sensor, 'sound', level)
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
        if sensors_settings[sensor]['position_ref'] == -1:
            sensors_settings[sensor]['position_ref'] = pos
        else:
            sensors_settings[sensor]['position_ref'] = \
                (sensors_settings[sensor]['position_ref'] * 100 + pos) / 101  # Add 1% of the new position
        pos = abs(pos - sensors_settings[sensor]['position_ref'])

        # check values
        sensor_check_val(sensor, 'position', pos)
        sensor_check_val(sensor, 'move', move)


async def sensor_bt(sensor: str, address: str, char_uuid: str) -> None:
    """
    Start connexion with the BT ensors and activate notification
    Args:
        sensor: Name of the sensors
        address: BT addr of the module
        char_uuid: BT uuid for the sensor
    Returns:

    """
    sensors_settings[sensor]['sensor_online'] = False
    disconnected_event = asyncio.Event()
    logger.info(f"{sensor} init")

    def disconnected_callback(bt_client):
        logger.info(f"{sensor} sensor is disconnected")
        sensors_settings[sensor]['sensor_online'] = False
        if sensor == 'sound':
            sensor_check_val(sensor, 'sound', 0)
        else:
            sensor_check_val(sensor, 'move', 0)
            sensor_check_val(sensor, 'position', 0)
        disconnected_event.set()

    async with BleakClient(address, disconnected_callback=disconnected_callback) as client:
        logger.info(f"{sensor} sensor is connected")
        sensors_settings[sensor]['sensor_online'] = True
        await client.start_notify(char_uuid, partial(sensor_notification, sensor))
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
    logger.info(f"Start sensor {sensor} thread")
    while True:
        try:
            # thread isolation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # run
            loop.run_until_complete(sensor_bt(sensor, addr, service))
            loop.close()
        except Exception as err:
            logger.info(f"Thread error in start_sensors_bt {sensor}: {err=}, {type(err)=}")
            time.sleep(30)


# Software ramp
def thread_update_ramp():
    RAMP_STEP = 2
    logger.info(f"Start software ramp thread")
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
            logger.info(f"Thread error in update_ramp {err=}, {type(err)=}")
            time.sleep(30)


def sensors_init():
    logger.info(f"Init sensors settings")
    # motion sensors init
    sensors_settings['motion1'] = {
        "position_ref": -1.0,  # position reference
        "position_alarm_level": 45,  # threshold for position alarm action
        "position_delay_on": 1,  # nb consecutive value for starting an action
        "position_delay_off": 5,  # nb consecutive value before starting an action again
        "move_alarm_level": 12,  # threshold for moving alarm action
        "move_delay_on": 1,  # nb consecutive value for starting an action
        "move_delay_off": 5,  # nb consecutive value before starting an action again
        "sensor_online": False,  # true if the sensors is online
        "position_alarm_counter": 0,  # Num of consecutive position alarm
        "move_alarm_counter": 0,  # Num of consecutive move alarm
        "position_alarm_number": 0,  # Number of the last alarm
        "move_alarm_number": 0,  # Number of the last alarm
        "position_alarm_number_action": 0,  # Number of the last alarm who had generated an action
        "move_alarm_number_action": 0,  # Number of the last alarm who had generated an action
        "current_position": 0,  # Current position value
        "current_move": 0,  # Current move value
        "alarm_enable": False  # alarm activation
    }
    sensors_settings['motion2'] = sensors_settings['motion1'].copy()

    # sound sensor init
    sensors_settings['sound'] = {
        "sound_alarm_level": 45,  # threshold for position alarm action
        "sound_delay_on": 5,  # nb consecutive value for starting an action
        "sound_delay_off": 10,  # nb consecutive value before starting an action again
        "sensor_online": False,  # true if the sensors is online
        "sound_alarm_counter": 0,  # Num of consecutive sound alarm
        "sound_alarm_number": 0,  # Number of the last alarm
        "sound_alarm_number_action": 0,  # Number of the last alarm who had generated an action
        "current_sound": 0,  # Current sound value
        "alarm_enable": False  # alarm activation

    }


def mk2b_init():
    # Init 2B threads settings
    logger.info(f"Init 2B initials settings")
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


# Vocal loop
def thread_vocal_text():
    logger.info(f"Start vocal thread")
    while True:
        try:
            time.sleep(1)
            while len(vocal_queue) > 0:

                # check if vocal synthesis is active
                if not NO_VOCAL and len(vocal_queue) < 5:  # skip too many message
                    engine = pyttsx3.init()
                    engine_init = pyttsx3.init()
                    engine.setProperty('voice',
                                       'HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_EN-GB_HAZEL_11.0')
                    engine.setProperty('rate', 220)
                    engine.say(vocal_queue.pop(0))
                    engine.runAndWait()
                else:
                    vocal_queue.pop(0)
        except Exception as err:
            time.sleep(30)


if __name__ == '__main__':

    # init thread for BT sensors
    sensors_init()
    motion_sensors_thread = dict()
    if not NO_BT_SENSORS:
        for name, addr, service in BT_SENSORS:
            threads[name] = Thread(target=thread_sensors_bt, args=(name, addr, service))

    # init threads for each mk2b unit
    mk2b_init()
    if not NO_MK2BT:
        for bt_name in BT_UNITS:
            threads[bt_name] = Thread(target=thread_bt_unit, args=(bt_name, threads_settings[bt_name]))

    # init threads for software ramp
    threads['ramp'] = Thread(target=thread_update_ramp)

    # init vocal log
    threads['vocal'] = Thread(target=thread_vocal_text)

    # status pic
    threads['status_pic'] = Thread(target=thread_push_status_pic)

    # start all thread
    for tr in threads.keys():
        logger.warning(f"start thread {tr}")
        threads[tr].daemon = True
        threads[tr].start()

    # start Discord Bot
    while True:
        try:
            logger.warning('start Discord bot')
            time.sleep(10)
            bot = Bot2b3()
            bot.run(DISCORD_TOKEN)
        except Exception as err:
            logger.error(f'restarting Discord bot after major error {err}')
            time.sleep(10)
            continue
