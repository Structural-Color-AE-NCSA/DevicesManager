#!/usr/bin/env python
import pika
import random
import json
import re


try:
    from polychemprint3.tools.ultimusExtruder import ultimusExtruder
    from polychemprint3.axes.lulzbotTaz6_BP import lulzbotTaz6_BP
    tool = ultimusExtruder()
    tool_passed = tool.activate()
    lulzbot = lulzbotTaz6_BP()
    lulzbot_passed = lulzbot.activate()
    lulzbot.move("G28\n")
except:
    tool = None
    lulzbot = None
    tool_passed = False
    lulzbot_passed = False

EXCHANGE_NAME = 'devices_manager'
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)

deviceIDs = {'lulzbot':0, 'tool':1}
queue_names = []
# for deviceTitle in deviceIDs.keys():
#     result = channel.queue_declare(queue='')
#     queue_name = result.method.queue
#     queue_names.append(queue_name)
#     channel.queue_bind(
#         exchange='device_commands', queue=queue_name, routing_key=deviceTitle)


def listen_device_status():
    queue_name = "device_status_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=queue_name, routing_key='device_status')
    channel.basic_consume(
        queue=queue_name, on_message_callback=on_request, auto_ack=True)


def listen_pcp_commands():
    queue_name = "pcp_file_commands_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=queue_name, routing_key='pcp_file')
    channel.basic_consume(
        queue=queue_name, on_message_callback=on_request, auto_ack=True)


def send_pcp_commands(message):
    pcp_commands = message['data'].splitlines()
    for cmd in pcp_commands:
        if len(cmd) <= 0:
            continue
        print(cmd)
        cmd = cmd.replace("\\n", "\n")
        tmp = cmd.split("(")
        command = tmp[0].split(".")
        name = command[0] # device
        sub = cmd[1+len(name):]
        op = None       # operation
        params = None      # operation params
        pattern = r'^(.*?)\('
        match = re.search(pattern, sub)
        if match:
            op = match.group(1)
        pattern = r'"([^"]*)"'
        match = re.search(pattern, sub)
        if match:
            params = match.group(1)
        else:
            pattern = r'\((.*?)\)'
            match = re.search(pattern, sub)
            if match:
                params = match.group(1)
        if name.startswith("axes"):
            print('axes')
        elif name.startswith("tool"):
            print('tool')
        if name == "axes":
            if op == "setPosMode":
                lulzbot.setPosMode(params)
            elif op == "move":
                print("lulzbot.move: " + params)
                lulzbot.move(params)
        elif name == "tool":
            if op == "setValue":
                tool.setValue(params)
            elif op == "engage":
                tool.engage()
            elif op == "disengage":
                tool.disengage()


def generate_command_status():
    return random.choice(['Executing', 'Finished', 'Queued'])


def get_devices_status():
    devicesStatusList = []
    for deviceTitle, deviceId in deviceIDs.items():
        status = False
        if deviceTitle == 'tool':
            status = tool_passed
        elif deviceTitle == 'lulzbot':
            status = lulzbot_passed
        devicesStatusList.append({'_id': deviceId, 'title': deviceTitle, 'isConnected': status})
    return devicesStatusList


def on_request(ch, method, props, body):
    message = json.loads(body)
    type = message['type']
    if type == 'device_status':
        status = json.dumps(get_devices_status())
        send_message('device_status_update', status)
    elif type == 'pcp_commands':
        send_pcp_commands(message)
        status = "OK"


def send_message(routing_key, message):
    channel.basic_publish(
        exchange=EXCHANGE_NAME, routing_key=routing_key, body=message)


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
listen_device_status()
listen_pcp_commands()

print(" [x] Adaptor starting")

channel.start_consuming()
