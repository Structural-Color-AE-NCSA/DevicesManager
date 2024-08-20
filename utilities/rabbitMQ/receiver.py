#!/usr/bin/env python
import pika
import uuid
import json
from ...config import Config


class RpcDevicesReceiver(object):

    def __init__(self):
        parameters = pika.URLParameters(Config.RABBITMQ_URI)
        self.connection = pika.BlockingConnection(parameters)

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)
        
        self.channel.exchange_declare(exchange='device_commands', exchange_type='direct')

        self.response = None
        self.corr_id = None

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = json.loads(body)

    def get_device_status(self):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        metadata = dict()
        metadata['type'] = 'device_status'
        json_string = json.dumps(metadata)
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json_string)
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response
    def send_pcp_file(self, commands):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        metadata = dict()
        metadata['type'] = 'pcp_commands'
        metadata['data'] = commands
        json_string = json.dumps(metadata)
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_queue',
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.corr_id,
            ),
            body=json_string)
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response
    def add_command(self, device_id, command):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        body = json.dumps(command)
        print('waiting response at:', self.device_callback_queue[device_id])
        self.channel.basic_publish(
            exchange='device_commands',
            routing_key=device_id,
            properties=pika.BasicProperties(
                reply_to=self.device_callback_queue[device_id],
                correlation_id=self.corr_id,
            ),
            body=body)
        while self.response is None:
            self.connection.process_data_events(time_limit=None)
        return self.response

if __name__ == "__main__":
    statusRpc = RpcDevicesReceiver()

    print(" [x] Requesting 3d printer status")
    response = statusRpc.call()
    print(f" [.] Got response:")
    for r in response:
        print(r)
        # {'_id': 0, 'title': 'device_0', 'isConnected': False}
        # {'_id': 1, 'title': 'device_1', 'isConnected': True}
        # {'_id': 2, 'title': 'device_2', 'isConnected': False}
        # {'_id': 3, 'title': 'device_3', 'isConnected': True}
        # {'_id': 4, 'title': 'device_4', 'isConnected': False}
    print(" [x] Sending a 3d printer command")
    command = {'command_id': str(uuid.uuid4()), 'command': 'test_command', 'device_id': 'device_0'}
    response_command = statusRpc.add_command('device_0', command)
    print(f" [.] Got response:")
    print(response_command)
    
