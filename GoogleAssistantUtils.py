from config import ASSISTANT_URL, ASSISTANT_USER
from config import CAST_URL, MUSIC_URL, CAST_DEVICE
import requests

def playMusic():
    body = {
        "device": CAST_DEVICE, # IP address or name
        "source": MUSIC_URL, # URL to media
        "type": "remote" # Not needed for remote files
    }

    x = requests.post(CAST_URL, json = body)

def command(cmd):
    body = {"user": ASSISTANT_USER,"command": cmd}

    x = requests.post(ASSISTANT_URL, json = body)

def broadcast(msg):
    body = {"user": ASSISTANT_USER,"command": msg, "broadcast": True}

    x = requests.post(ASSISTANT_URL, json = body)