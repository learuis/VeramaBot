import re
import os
import requests
from rcon import Console
from rcon.util import remove_formatting_codes
from ftplib import FTP

from dotenv import load_dotenv

load_dotenv('data/bandofoutcasts.env')
RCON_HOST = os.getenv('RCON_HOST')
RCON_PORT = os.getenv('RCON_PORT')
RCON_PASS = os.getenv('RCON_PASS')
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

def runRcon(command: str):

    class RconResponse:
        def __init__(self):
            self.output = []
            self.error = 0

    returnValue = RconResponse()
    
    commandOutput = []
    failures = 0
    
    while failures < 6:
        try:
            console = Console(host=RCON_HOST, port=int(RCON_PORT), password=RCON_PASS)
            break
        except Exception:
            failures += 1

    if failures == 6:
        returnValue.output = ['Authentication failed 5 times in a row.']
        returnValue.error = 1
        return returnValue
    
    #add error handling here
    res_body = console.command(command).body
    console.close()

    res_body = remove_formatting_codes(res_body)

    if not res_body.endswith('\n'):
        res_body += '\n'

    res_list = res_body.splitlines()
    
    for x in res_list:
        if command == 'listplayers':
            x = re.sub(r'\s', '', x)
            x = re.sub(r'\|', ',', x)
            commandOutput.append(x.split(','))
        else:
            commandOutput.append(x)

    returnValue.output = commandOutput
    return returnValue

    #return commandOutput


