#!/usr/bin/env python
import pika
import uuid
import json
from ...config import Config


class RpcDevicesReceiver(object):
    EXCHANGE_NAME = 'devices_manager'

    DEVICE_STATUS_ROUTING_KEY = 'device_status'
    DEVICE_STATUS_UPDATE_ROUTING_KEY = 'device_status_update'
    DEVICE_STATUS_UPDATE_QUEUENAME = 'devices_status_update_queue'
    PCP_FILE_ROUTING_KEY = 'pcp_file'

    PCP_FILE_MOVEMENT_QUEUENAME = 'pcp_file_movement_queue'
    PCP_FILE_MOVEMENT_ROUTING_KEY = 'pcp_file_movement'
    device_status_response = None

    def __init__(self):
        parameters = pika.URLParameters(Config.RABBITMQ_URI)
        self.connection = pika.BlockingConnection(parameters)

        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=self.EXCHANGE_NAME, exchange_type='direct', durable=True)
        self._listen_device_status_update()
        self._listen_pcp_movement()

    def _listen_device_status_update(self):
        self.channel.queue_declare(queue=self.DEVICE_STATUS_UPDATE_QUEUENAME, durable=True)
        self.channel.queue_bind(
            exchange=self.EXCHANGE_NAME, queue=self.DEVICE_STATUS_UPDATE_QUEUENAME, routing_key=self.DEVICE_STATUS_UPDATE_ROUTING_KEY)
        self.channel.basic_consume(
            queue=self.DEVICE_STATUS_UPDATE_QUEUENAME, on_message_callback=self.on_device_status_response, auto_ack=True)

    def _listen_pcp_movement(self):
        self.channel.queue_declare(queue=self.PCP_FILE_MOVEMENT_QUEUENAME, durable=True)
        self.channel.queue_bind(
            exchange=self.EXCHANGE_NAME, queue=self.PCP_FILE_MOVEMENT_QUEUENAME, routing_key=self.PCP_FILE_MOVEMENT_ROUTING_KEY)
        self.channel.basic_consume(
            queue=self.PCP_FILE_MOVEMENT_QUEUENAME, on_message_callback=self.on_pcp_movement_response, auto_ack=True)

    def send_message(self, routing_key, message):
        self.channel.basic_publish(
            exchange=self.EXCHANGE_NAME, routing_key=routing_key, body=message)

    def on_device_status_response(self, ch, method, properties, body):
        self.device_status_response = json.loads(body)

    def on_pcp_movement_response(self, ch, method, properties, body):
        pass

    def get_device_status(self):
        metadata = dict()
        metadata['type'] = 'device_status'
        json_string = json.dumps(metadata)
        self.send_message(self.DEVICE_STATUS_ROUTING_KEY, json_string)

        while self.device_status_response is None:
            self.connection.process_data_events(time_limit=10)
        return self.device_status_response

    def send_pcp_file(self, commands):
        metadata = dict()
        metadata['type'] = 'pcp_commands'
        metadata['data'] = commands
        json_string = json.dumps(metadata)
        self.send_message(self.PCP_FILE_ROUTING_KEY, json_string)
        return True


    
