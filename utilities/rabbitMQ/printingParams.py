import threading
import json
import re
import requests
from .connector import DeviceConnector

from ...config import Config


class PrintingParams(object):
    def __init__(self):
        self.status_request = DeviceConnector(None, 'printer_params')
        self.status_request.connect()

    def send_printing_params(self, commands):
        metadata = dict()
        metadata['type'] = 'printing_params'
        metadata['data'] = commands
        json_string = json.dumps(metadata)
        self.status_request.send_message('printer_params', json_string)
        return True