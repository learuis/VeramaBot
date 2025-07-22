import os
import re
import socket
import struct
import sys

from rcon import Console
from rcon.util import remove_formatting_codes
from ftplib import FTP
import sqlite3
from timeout_function_decorator import timeout

from dotenv import load_dotenv

load_dotenv('data/server.env')
RCON_HOST = os.getenv('RCON_HOST')
RCON_PORT = int(os.getenv('RCON_PORT'))
RCON_PASS = str(os.getenv('RCON_PASS'))
FTP_HOST = os.getenv('FTP_HOST')
FTP_PORT = os.getenv('FTP_PORT')
FTP_USER = os.getenv('FTP_USER')
FTP_PASS = os.getenv('FTP_PASS')

def downloadSave():

    ftp = FTP()

    #os.chdir('data')

    ftp.connect(FTP_HOST, int(FTP_PORT))
    ftp.login(FTP_USER, FTP_PASS)
    ftp.cwd(r'ConanSandbox\saved\Logs')
    ftp.encoding = 'latin-1'

    # For text files

    lines = []
    #ftp.retrbinary('RETR ConanSandbox.log', open('data/ConanSandbox.log', 'wb').write)
    ftp.retrlines('RETR ConanSandbox.log', lambda d: lines.append(d + '\n'))
    f = open('data/ConanSandbox.log', 'w')
    #returnFile.close()
    f.writelines(lines)
    returnFile = f
    f.close()

    ftp.close()

    return returnFile

def db_query(commit_query: bool, query: str):

    # print(os.getcwd())
    # print(os.listdir())
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(query)

    if commit_query:
        con.commit()
        result = True
    else:
        result = cur.fetchall()
    con.close()

    if result:
        return result
    else:
        return False

def db_delete_single_record(table: str, key_field: str, record_to_delete: int):
    check_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    check_cur = check_con.cursor()

    # print(f'select * from {table} where {key_field} = {record_to_delete}')
    check_cur.execute(f'select * from {table} where {key_field} = {record_to_delete}')
    check_res = check_cur.fetchone()
    check_con.close()

    if not check_res:
        return False

    del_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    del_cur = del_con.cursor()

    del_cur.execute(f'delete from {table} where {key_field} = {record_to_delete}')
    del_con.commit()

    return check_res

@timeout(7, TimeoutError)
def runRcon(command: str):

    class RconResponse:
        def __init__(self):
            self.output = []
            self.error = 0
        def __bool__(self):
            return self.output != []

    returnValue = RconResponse()
    
    commandOutput = []
    connection_failures = 0
    command_failures = 0

    while connection_failures < 6:
        try:
            # print(f'{RCON_HOST}:{RCON_PORT}')
            console = Console(host=RCON_HOST, port=int(RCON_PORT), password=RCON_PASS)
            break
        except Exception:
            connection_failures += 1

    if connection_failures == 6:
        returnValue.output = ['Authentication failed 5 times in a row.']
        returnValue.error = 1
        return returnValue

    while command_failures < 6:
        try:
            res_body = console.command(command)
            break
        except Exception:
            command_failures += 1
            print(f'RCON Failure #{command_failures}')

    if command_failures == 6:
        returnValue.output = ['Received few bytes exception 5x in a row']
        returnValue.error = 1
        return returnValue

    console.close()

    res_body = remove_formatting_codes(res_body)

    if not res_body.endswith('\n'):
        res_body += '\n'

    res_list = res_body.splitlines()

    for x in res_list:
        commandOutput.append(x)

    returnValue.output = commandOutput
    return returnValue

def count_online_players():
    connected_chars = []

    try:
        rconResponse = runRcon('listplayers')
    except TimeoutError:
        return False

    rconResponse.output.pop(0)

    for x in rconResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)

    return len(connected_chars)

async def async_count_online_players():
    connected_chars = []

    rconResponse = await async_runRcon('listplayers')
    rconResponse.output.pop(0)

    for x in rconResponse.output:
        match = re.findall(r'\s+\d+ | [^|]*', x)
        connected_chars.append(match)

    return len(connected_chars)

def notify_all(style: int, text1: str, text2: str):
    failures = 0
    command_list = []

    while failures < 6:
        try:
            console = Console(host=RCON_HOST, port=int(RCON_PORT), password=RCON_PASS)
            break
        except Exception:
            failures += 1

    if failures == 6:
        print(f'Error connecting via RCON')
        return

    console.close()

    online_players = count_online_players()

    if online_players > 0:
        for rcon_id in range(0, online_players):
            command_list.append(f'con {rcon_id} testfifo {style} {text1} {text2}')
        multi_rcon(command_list)
    else:
        return

    # try:
    #     res_body = console.command(f'con {rcon_id} testfifo {style} {text1} {text2}')
    # except Exception:
    #     print(f'Could not notify player in slot {rcon_id}')
    #     continue

def multi_rcon(commands: list[str]):
    failures = 0

    while failures < 6:
        try:
            console = Console(host=RCON_HOST, port=int(RCON_PORT), password=RCON_PASS)
            break
        except Exception:
            failures += 1

    if failures == 6:
        print(f'Error connecting via RCON')
        return False

    for command in commands:
        try:
            console.command(f'{command}')
            #print(f'{command}')
        except Exception:
            print(f'Could not execute command {command}')
            continue

    console.close()

def rcon_all(command: str):
    failures = 0

    while failures < 6:
        try:
            console = Console(host=RCON_HOST, port=int(RCON_PORT), password=RCON_PASS)
            break
        except Exception:
            failures += 1

    if failures == 6:
        print(f'Error connecting via RCON')
        return

    online_players = count_online_players()

    for rcon_id in range(0, online_players-1):
        try:
            console.command(f'con {rcon_id} {command}')
        except Exception:
            print(f'Could not run command {command} on player in slot {rcon_id}')
            continue

    console.close()

def send_rcon_command(command):
    #written by FreeFun
    def create_packet(request_id, request_type, payload):
        payload = payload.encode('utf-8')
        length = 10 + len(payload)
        return struct.pack('<iii', length, request_id, request_type) + payload + b'\x00\x00'

    def read_response(sock):
        # Read the length of the response
        data = sock.recv(4)
        if len(data) < 4:
            raise ValueError("Failed to receive data")

        length = struct.unpack('<i', data)[0]

        # Read the rest of the response
        data = sock.recv(length)
        if len(data) < length:
            raise ValueError("Failed to receive full data")

        request_id, response_type = struct.unpack('<ii', data[:8])
        response = data[8:].decode('utf-8')
        return request_id, response

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect the socket to the port where the server is listening
        sock.connect((RCON_HOST, RCON_PORT))

        # Send the RCON login request
        login_packet = create_packet(1, 3, RCON_PASS)
        sock.sendall(login_packet)
        request_id, response = read_response(sock)

        if request_id == -1:
            raise ValueError("RCON login failed")

        # Send the RCON command
        command_packet = create_packet(2, 2, command)
        sock.sendall(command_packet)
        _, response = read_response(sock)

        return response

    finally:
        sock.close()
