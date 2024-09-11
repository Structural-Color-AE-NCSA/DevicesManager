#!/usr/bin/env python
import threading
import pika
from pika.exceptions import ConnectionClosed, ChannelClosed, ChannelWrongStateError
import re
import json
from config import Config


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

class DeviceComm(object):
    EXCHANGE_NAME = 'devices_manager'

    DEVICE_STATUS_ROUTING_KEY = 'device_status'
    DEVICE_STATUS_UPDATE_ROUTING_KEY = 'device_status_update'
    DEVICE_STATUS_UPDATE_QUEUENAME = 'devices_status_update_queue'
    PCP_FILE_ROUTING_KEY = 'pcp_file'
    DEVICE_ACTIVATE_DEACTIVATE_ROUTING_KEY = 'device_activate_deactivate'

    PRINTER_MOVEMENT_ROUTING_KEY = 'printer_movement'
    PRINTER_MOVEMENT_UPDATE_QUEUENAME = 'printer_movement_update_queue'

    parameters = None
    queue_name = None
    routing_key = None

    device_status_response = None
    connection = None
    channel = None
    printer_pre_pos = None
    printer_cur_pos = None

    def __init__(self):
        self.parameters = pika.URLParameters(Config.RABBITMQ_URI)
        self.connection = pika.BlockingConnection(self.parameters)

    def listen(self):
        self.make_connection()
        self.channel.exchange_declare(exchange=self.EXCHANGE_NAME, exchange_type='direct', durable=True)
        self._listen_device_status_update()
        # self._listen_printer_movement()
        print("Rabbitmq client running")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
        self.connection.close()


    def make_connection(self):
        self.channel = self.connection.channel()

    def _listen_printer_movement(self):
        queue_name = self.PRINTER_MOVEMENT_UPDATE_QUEUENAME
        routing_key = self.PRINTER_MOVEMENT_ROUTING_KEY
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(
            exchange=self.EXCHANGE_NAME, queue=queue_name, routing_key=routing_key)
        self.channel.basic_consume(
            queue=queue_name, on_message_callback=self.on_printer_movement_response, auto_ack=True)

    def _listen_device_status_update(self):
        queue_name = self.DEVICE_STATUS_UPDATE_QUEUENAME
        routing_key = self.DEVICE_STATUS_UPDATE_ROUTING_KEY
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(
            exchange=self.EXCHANGE_NAME, queue=queue_name, routing_key=routing_key)
        self.channel.basic_consume(
            queue=queue_name, on_message_callback=self.on_device_status_response, auto_ack=True)

    def send_message(self, routing_key, message):
        try:
            self.channel.basic_publish(
                exchange=self.EXCHANGE_NAME, routing_key=routing_key, body=message)
        except (ConnectionClosed, ChannelClosed, ChannelWrongStateError) as error:
            print(error)
            self.make_connection()
            self.resend_message(routing_key, message)
    def resend_message(self, routing_key, message):
        self.send_message(routing_key, message)

    def on_device_status_response(self, ch, method, properties, body):
        self.device_status_response = json.loads(body)
        # print(json.loads(body))

    def on_printer_movement_response(self, ch, method, properties, body):
        # print(f" [x] {method.routing_key}:{body}")
        start = json.loads(body).get('start')
        end = start = json.loads(body).get('end')
        start_pos = parse_printer_pos(start)
        end_pos = parse_printer_pos(end)

        if start_pos is not None and end_pos is not None:
            # draw it
            pass
        if start_pos:
            print(start_pos)
        if end_pos:
            print(end_pos)

    def get_device_status(self):
        self.device_status_response = None
        metadata = dict()
        metadata['type'] = 'device_status'
        json_string = json.dumps(metadata)
        self.send_message(self.DEVICE_STATUS_ROUTING_KEY, json_string)

        while self.device_status_response is None:
            self.connection.process_data_events(time_limit=10)
        if self.device_status_response is None:
            self.device_status_response = dict()
        return self.device_status_response

    def send_pcp_file(self, commands):
        metadata = dict()
        metadata['type'] = 'pcp_commands'
        metadata['data'] = commands
        json_string = json.dumps(metadata)
        self.send_message(self.PCP_FILE_ROUTING_KEY, json_string)
        return True

    def activate(self, id):
        metadata = dict()
        metadata['type'] = 'activate'
        metadata['data'] = self.get_device_title(id)
        json_string = json.dumps(metadata)
        self.send_message(self.DEVICE_ACTIVATE_DEACTIVATE_ROUTING_KEY, json_string)
        return True


    def deactivate(self, id):
        metadata = dict()
        metadata['type'] = 'deactivate'
        metadata['data'] = self.get_device_title(id)
        json_string = json.dumps(metadata)
        self.send_message(self.DEVICE_ACTIVATE_DEACTIVATE_ROUTING_KEY, json_string)
        return True

    def get_device_title(self, device_id):
        for device in self.device_status_response:
            if device.get('_id') == device_id:
                return device.get('title')

