import threading
import json
import re
import requests
from .connector import DeviceConnector

from ...config import Config

class PCPFile(object):
    def __init__(self):
        queue_name = 'printer_movement_update_queue'
        routing_key = 'printer_movement'
        status_updates = DeviceConnector(queue_name, routing_key, self.on_message)
        status_updates.connect()
        self.start_listen(status_updates)

        queue_name = 'printer_movement_done_queue'
        routing_key = 'printer_movement_done'
        pcp_movement_done = DeviceConnector(queue_name, routing_key, self.pcp_movement_done_process)
        pcp_movement_done.connect()
        self.start_listen(pcp_movement_done)

        self.status_request = DeviceConnector(None, 'pcp_file')
        self.status_request.connect()

    def start_listen(self, target):
        thread = threading.Thread(target=target.consume)
        thread.daemon = True
        thread.start()

    def pcp_movement_done_process(self, ch, method, properties, body):
        cell_id = json.loads(body.decode('utf-8')).get('cell_id')
        payload = json.dumps({'cell_id': cell_id})

        # Sending a POST request
        #TODO: use session token
        url = Config.INTERNAL_HOST_URL+"devices-manager/device/update_pcp_plot"
        payload = json.dumps({'cell_id': cell_id})
        headers = {'Content-Type': 'application/json'}
        response = requests.post(url, data=payload, headers=headers)
        if response.status_code == 200:
            print("Request was successful!")
            # print("Response JSON:", response.json())
        else:
            print(f"Failed with status code: {response.status_code}")

    def on_message(self, ch, method, properties, body):
        # print(f" [x] {method.routing_key}:{body}")
        start = json.loads(body.decode('utf-8')).get('start')
        end = json.loads(body).get('end')
        start_pos = parse_printer_pos(start)
        end_pos = parse_printer_pos(end)

        if start_pos is not None and end_pos is not None:
            # draw it
            pass
        if start_pos:
            print("from " + json.dumps(start_pos))
        if end_pos:
            print("to " + json.dumps(end_pos))

    def send_pcp_file(self, commands, cell_id=-1):
        metadata = dict()
        metadata['cell_id'] = cell_id
        metadata['type'] = 'pcp_commands'
        metadata['data'] = commands
        json_string = json.dumps(metadata)
        self.status_request.send_message('pcp_file', json_string)
        return True



def parse_printer_pos(pos):
    if pos is not None:
        x = None
        y = None
        z = None
        matches = re.findall(r'X:([0-9.]+) Y:([0-9.]+) Z:([0-9.]+)', pos)
        if matches:
            x, y, z = matches[0]
            return {'X': float(x), 'Y': float(y), 'Z': float(z)}
    return None