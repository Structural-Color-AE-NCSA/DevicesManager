import threading
import json
import re
from .connector import DeviceConnector


class PCPFile(object):
    def __init__(self):
        queue_name = 'printer_movement_update_queue'
        routing_key = 'printer_movement'
        status_updates = DeviceConnector(queue_name, routing_key, self.on_message)
        status_updates.connect()
        device_status_thread = threading.Thread(target=status_updates.consume)
        device_status_thread.daemon = True
        device_status_thread.start()

        self.status_request = DeviceConnector(None, 'pcp_file')
        self.status_request.connect()

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

    def send_pcp_file(self, commands):
        metadata = dict()
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