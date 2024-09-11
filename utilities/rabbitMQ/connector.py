#!/usr/bin/env python
import threading
import traceback

import pika
from pika.exceptions import ConnectionClosed, ChannelClosed, ChannelWrongStateError
import re
import json
from ...config import Config


class DeviceConnector(object):
    EXCHANGE_NAME = 'devices_manager'

    PCP_FILE_ROUTING_KEY = 'pcp_file'
    DEVICE_ACTIVATE_DEACTIVATE_ROUTING_KEY = 'device_activate_deactivate'

    PRINTER_MOVEMENT_ROUTING_KEY = 'printer_movement'
    PRINTER_MOVEMENT_UPDATE_QUEUENAME = 'printer_movement_update_queue'

    device_status_response = None
    connection = None
    channel = None
    printer_pre_pos = None
    printer_cur_pos = None

    def __init__(self, queue_name, routing_key, on_message=None):
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.on_message = on_message

    def connect(self):
        parameters = pika.URLParameters(Config.RABBITMQ_URI)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=1)
        if self.queue_name is not None:
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.queue_bind(
                exchange=self.EXCHANGE_NAME, queue=self.queue_name, routing_key=self.routing_key)
        self.channel.exchange_declare(exchange=self.EXCHANGE_NAME, exchange_type='direct', durable=True)

    def consume(self):
        self.channel.basic_consume(
            queue=self.queue_name, on_message_callback=self.on_message, auto_ack=True)
        # This will block and listen for messages
        self.channel.start_consuming()

    def send_message(self, routing_key, message):
        try:
            self.channel.basic_publish(
                exchange=self.EXCHANGE_NAME, routing_key=routing_key, body=message)
        except (ConnectionClosed, ChannelClosed, ChannelWrongStateError) as error:
            traceback.print_exc()
