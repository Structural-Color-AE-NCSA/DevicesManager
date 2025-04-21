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
        campaign_id = json.loads(body.decode('utf-8')).get('campaign_id')
        payload = json.dumps({'cell_id': cell_id, 'campaign_id': campaign_id})
        #campaign_id to get campaign record from db
        # Sending a POST request
        #TODO: store the cell id and color info to db
        #TODO: update frontend
        #TODO: check if campaign is done then update the campaign status to done in db
        #TODO: if campaign is done, then terminiate the live cell color update.

        #TODO: use session token
        # url = Config.INTERNAL_HOST_URL+"devices-manager/device/update_pcp_plot"
        # payload = json.dumps({'cell_id': cell_id})
        # headers = {'Content-Type': 'application/json'}
        # response = requests.post(url, data=payload, headers=headers)
        # if response.status_code == 200:
        #     print("Request was successful!")
        #     # print("Response JSON:", response.json())
        # else:
        #     print(f"Failed with status code: {response.status_code}")

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

    def send_pcp_file(self, campaign_id, commands, cell_id=-1,  number_prints_trigger_prediction = 1, rank_run = 0,
                      accum_h_mu=0.0,
                      bed_temp = None, print_speed = None, pressure = None):
        metadata = dict()
        metadata['campaign_id'] = campaign_id
        metadata['cell_id'] = cell_id
        metadata['type'] = 'pcp_commands'
        metadata['rank_run'] = rank_run
        metadata['accum_h_mu'] = accum_h_mu
        metadata['number_prints_trigger_prediction'] = number_prints_trigger_prediction
        metadata['data'] = commands
        if bed_temp:
            metadata['bed_temp'] = bed_temp
        if print_speed:
            metadata['print_speed'] = print_speed
        if pressure:
            metadata['pressure'] = pressure
        json_string = json.dumps(metadata)
        print("send pcp file:" + json_string)
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