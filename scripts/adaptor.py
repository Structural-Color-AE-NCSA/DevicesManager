#!/usr/bin/env python
import pika
import random
import json

connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))

channel = connection.channel()

channel.queue_declare(queue='rpc_queue')
channel.exchange_declare(exchange='device_commands', exchange_type='direct')

deviceIDs = {'device_0':0, 'device_1':1, 'device_2':2, 'device_3':3, 'device_4':4}
queue_names = []
for deviceTitle in deviceIDs.keys():
    result = channel.queue_declare(queue='')
    queue_name = result.method.queue
    queue_names.append(queue_name)
    channel.queue_bind(
        exchange='device_commands', queue=queue_name, routing_key=deviceTitle)

def generate_status():
    return random.choice([True, False])

def generate_command_status():
    return random.choice(['Executing', 'Finished', 'Queued'])

def getDevicesStatus():
    # {'_id': 0, 'title': 'device_0', 'isConnected': True}
    deviceID = {'device_0':0, 'device_1':1, 'device_2':2, 'device_3':3, 'device_4':4, 
    'device_5':5, 'device_6':6, 'device_7':7, 'device_8':8, 'device_9':9}
    devicesStatusList = []
    
    for deviceTitle, deviceId in deviceID.items():
        status = generate_status()
        devicesStatusList.append({'_id': deviceId, 'title': deviceTitle, 'isConnected': status})
    return devicesStatusList

def on_request(ch, method, props, body):
    print(f" [.] incomming message: {body}")
    # response = fib(n)
    status = json.dumps(getDevicesStatus())

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=status)
    ch.basic_ack(delivery_tag=method.delivery_tag)

def on_command_request(ch, method, props, body):
    json_body = json.loads(body)
    print(f" [.] incomming command: {json_body}")
    # {'command_id': str(uuid.uuid4()), 'command': 'test_command', 'device_id': 'id_1'}
    device_id = json_body['device_id']
    command_id = json_body['command_id']
    device_status = generate_command_status()
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

channel.basic_qos(prefetch_count=1)
channel.basic_consume(queue='rpc_queue', on_message_callback=on_request)
for queue_n in queue_names:
    channel.basic_consume(queue=queue_n, on_message_callback=on_command_request)

print(" [x] Awaiting RPC requests")
channel.start_consuming()
