import os
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
    ftp.retrlines('RETR ConanSandbox.log', lambda d: lines.append(d + '\n'))
    f = open('data/ConanSandbox.log', 'w')
    f.writelines(lines)
    returnFile = f
    f.close()

    ftp.close()

    return returnFile

def db_query(query: str):
    con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    cur = con.cursor()
    cur.execute(query)
    result = cur.fetchall()
    con.close()

    if result:
        return result
    else:
        return False

def db_delete_single_record(table: str, key_field: str, record_to_delete: int):
    check_con = sqlite3.connect(f'data/VeramaBot.db'.encode('utf-8'))
    check_cur = check_con.cursor()

    print(f'select * from {table} where {key_field} = {record_to_delete}')
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

# async def runRcon3():
#     print(f'inside runRcon3')
#     print(f'{RCON_HOST}:{RCON_PORT} {RCON_PASS}')
#     rcon = AsyncRCON(f'{RCON_HOST}:{RCON_PORT}', f'{RCON_PASS}')
#     try:
#         print(f'trying')
#         await rcon.open_connection()
#     except AuthenticationException:
#         print('Login failed: Unauthorized.')
#         return
#
#     print(f'sending command')
#     res = await rcon.command(f'listplayers')
#     if not res:
#         print(f'nothing from server')
#     print(res)
#
#     rcon.close()
#
#     return res

@timeout(7, TimeoutError)
def runRcon(command: str):

    class RconResponse:
        def __init__(self):
            self.output = []
            self.error = 0

    returnValue = RconResponse()
    
    commandOutput = []
    connection_failures = 0
    command_failures = 0

    while connection_failures < 6:
        try:
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
            #print(f'trying rcon command {command}')
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

def notify_all(style: int, text1: str, text2: str):
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

    for rcon_id in range(0, 39):
        try:
            res_body = console.command(f'con {rcon_id} testfifo {style} {text1} {text2}')
        except Exception:
            print(f'Could not notify player in slot {rcon_id}')
            continue

    console.close()

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
            print(f'{command}')
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

    for rcon_id in range(0, 39):
        try:
            console.command(f'con {rcon_id} {command}')
        except Exception:
            print(f'Could not run command {command} on player in slot {rcon_id}')
            continue

    console.close()
