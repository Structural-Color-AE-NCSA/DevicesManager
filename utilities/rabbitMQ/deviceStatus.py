import threading
import json
from .connector import DeviceConnector


class DeviceStatus(object):
    """
    listen the device status update from remote adaptor
    send request to get device status
    """
    DEVICE_STATUS_ROUTING_KEY = 'device_status'
    device_status_response = None

    def __init__(self):
        # device status update
        queue_name = 'devices_status_update_queue'
        routing_key = 'device_status_update'
        status_updates = DeviceConnector(queue_name, routing_key, self.on_message)
        status_updates.connect()
        device_status_thread = threading.Thread(target=status_updates.consume)
        device_status_thread.daemon = True
        device_status_thread.start()

        self.status_request = DeviceConnector(None, self.DEVICE_STATUS_ROUTING_KEY)
        self.status_request.connect()

        self.onff = DeviceConnector(None, 'device_activate_deactivate')
        self.onff.connect()


    def on_message(self, ch, method, properties, body):
        self.device_status_response = json.loads(body)

    def get_device_status(self):
        self.device_status_response = None
        metadata = dict()
        metadata['type'] = 'device_status'
        json_string = json.dumps(metadata)
        self.status_request.send_message(self.DEVICE_STATUS_ROUTING_KEY, json_string)

        while self.device_status_response is None:
            self.status_request.connection.process_data_events(time_limit=1)
        if self.device_status_response is None:
            self.device_status_response = dict()
        return self.device_status_response

    def activate(self, id):
        metadata = dict()
        metadata['type'] = 'activate'
        metadata['data'] = self.get_device_title(id)
        json_string = json.dumps(metadata)
        self.onff.send_message('device_activate_deactivate', json_string)
        return True

    def deactivate(self, id):
        metadata = dict()
        metadata['type'] = 'deactivate'
        metadata['data'] = self.get_device_title(id)
        json_string = json.dumps(metadata)
        self.onff.send_message('device_activate_deactivate', json_string)
        return True

    def get_device_title(self, device_id):
        for device in self.device_status_response:
            if device.get('_id') == device_id:
                return device.get('title')
