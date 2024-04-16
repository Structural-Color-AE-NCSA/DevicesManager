#!/usr/bin/env python
import pika
import random
import json

class RpcDevicesAdaptor(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost'))

        self.channel = self.connection.channel()

        self.channel.queue_declare(queue='rpc_queue')
        self.channel.exchange_declare(exchange='device_commands', exchange_type='direct')

        self.deviceIDs = {'device_0':0, 'device_1':1, 'device_2':2, 'device_3':3, 'device_4':4, 
            'device_5':5, 'device_6':6, 'device_7':7, 'device_8':8, 'device_9':9}
        self.queue_names = []
        for deviceTitle in self.deviceIDs.keys():
            result = self.channel.queue_declare(queue='')
            queue_name = result.method.queue
            self.queue_names.append(queue_name)
            self.channel.queue_bind(
                exchange='device_commands', queue=queue_name, routing_key=deviceTitle)

    def get_channel(self):
        return self.channel
    
    def get_queue_names(self):
        return self.queue_names
    
    def generate_status(self):
        return random.choice([True, False])

    def generate_command_status(self):
        return random.choice(['Executing', 'Finished', 'Queued'])

    def getDevicesStatus(self):
        # {'_id': 0, 'title': 'device_0', 'isConnected': True}
        devicesStatusList = []
        
        for deviceTitle, deviceId in self.deviceIDs.items():
            status = self.generate_status()
            devicesStatusList.append({'_id': deviceId, 'title': deviceTitle, 'isConnected': status})
        return devicesStatusList

    def on_request(self, ch, method, props, body):
        print(f" [.] incomming message: {body}")
        # response = fib(n)
        status = json.dumps(self.getDevicesStatus())

        ch.basic_publish(exchange='',
                        routing_key=props.reply_to,
                        properties=pika.BasicProperties(correlation_id = \
                                                            props.correlation_id),
                        body=status)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def on_command_request(self, ch, method, props, body):
        json_body = json.loads(body)
        print(f" [.] incomming command: {json_body}")
        # {'command_id': str(uuid.uuid4()), 'command': 'testCommand', 'device_id': 'id_1'}
        device_id = json_body['device_id']
        command_id = json_body['command_id']
        
        device_command = json_body['command']
        device_command_list = device_command.split('_')
        if device_command_list[0] == 'testCommand':
            # Do nothing
            print('testing add device command, do nothing')
        elif device_command_list[0] == 'moveTo':
            # command = moveTo_x_y_z
            x_coord = float(device_command_list[1])
            y_coord = float(device_command_list[2])
            z_coord = float(device_command_list[3])
            print(f"moving device to (x, y, z): ({x_coord}, {y_coord}, {z_coord})")
        else:
            print(f"we don't support this command yet, direct default case, command = {device_command}")
        
        device_status = self.generate_command_status()
        status = json.dumps({
            'command_id': command_id, 'device_status': device_status, 'device_id': device_id
        })
        
        ch.basic_publish(exchange='',
                        routing_key=props.reply_to,
                        properties=pika.BasicProperties(correlation_id = \
                                                            props.correlation_id),
                        body=status)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        print('sent response to:', props.reply_to)

if __name__ == "__main__":
    rpc_device_adaptor = RpcDevicesAdaptor()
    
    rpc_device_adaptor_channel = rpc_device_adaptor.get_channel()
    rpc_device_adaptor_channel.basic_qos(prefetch_count=1)
    rpc_device_adaptor_channel.basic_consume(queue='rpc_queue', on_message_callback=rpc_device_adaptor.on_request)
    for queue_n in rpc_device_adaptor.get_queue_names():
        rpc_device_adaptor_channel.basic_consume(queue=queue_n, on_message_callback=rpc_device_adaptor.on_command_request)

    print(" [x] Awaiting RPC requests")
    rpc_device_adaptor_channel.start_consuming()
