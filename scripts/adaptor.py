#!/usr/bin/env python
import pika
import random
import json
import re
import time

# from scripts import clowder
# from ximea_camera import XimeaCamera
#
# ximean_cam = XimeaCamera()


# printer position string
printer_start_pos = None
printer_end_pos = None
try:
    from polychemprint3.tools.ultimusExtruder import ultimusExtruder
    from polychemprint3.axes.lulzbotTaz6_BP import lulzbotTaz6_BP
    tool = ultimusExtruder()
    tool_passed = tool.activate()
    lulzbot = lulzbotTaz6_BP()
    lulzbot_passed = lulzbot.activate()
    printer_start_pos = lulzbot.move("G28\n")
    printer_end_pos = printer_start_pos
except:
    tool = None
    lulzbot = None
    tool_passed = False
    lulzbot_passed = False
EXCHANGE_NAME = 'devices_manager'
# parameters = pika.URLParameters('amqp://devicesmanager:password@141.142.216.87/%2F')
parameters = pika.URLParameters('amqp://guest:guest@localhost/%2F')
connection = pika.BlockingConnection(parameters)
channel = connection.channel()
channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
deviceIDs = {'lulzbot':0, 'tool':1}
queue_names = []
def listen_device_status():
    queue_name = "device_status_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=queue_name, routing_key='device_status')
    channel.basic_consume(
        queue=queue_name, on_message_callback=on_request, auto_ack=True)
def listen_device_activate_deactivate():
    queue_name = "device_activate_deactivate_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=queue_name, routing_key='device_activate_deactivate')
    channel.basic_consume(
        queue=queue_name, on_message_callback=on_request, auto_ack=True)
def listen_pcp_commands():
    queue_name = "pcp_file_commands_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=queue_name, routing_key='pcp_file')
    channel.basic_consume(
        queue=queue_name, on_message_callback=on_request, auto_ack=True)


def listen_printing_params():
    queue_name = "pcp_file_commands_queue"
    channel.queue_declare(queue=queue_name, durable=True)
    channel.queue_bind(
        exchange=EXCHANGE_NAME, queue=queue_name, routing_key='printer_params')
    channel.basic_consume(
        queue=queue_name, on_message_callback=on_request, auto_ack=True)


def send_printing_params(params):
    print(params)
    data = params.get('data')
    if 'pos' in data:
        lulzbot.move(data.get('pos'))
    if 'pos' in data and 'pressure' in data:
        lulzbot.move("M400\n")
    if 'pressure' in data:
        tool.setValue(int(data.get('pressure')))

    if 'bed_temp' in data:
        lulzbot.move(data.get('bed_temp'))


def send_pcp_commands(message):
    # if tool is None or lulzbot is None:
    #     return False
    cell_id = message['cell_id']
    pcp_commands = message['data'].splitlines()
    for cmd in pcp_commands:
        if len(cmd) <= 0:
            continue
        print(cmd)
        cmd = cmd.replace("\\n", "\n")
        if cmd == "Done":
            lulzbot.move("M400\n")
            time.sleep(5)
            print(f"Cell #{cell_id} PCP running is done")
            send_message('printer_movement_done', json.dumps({'cell_id': cell_id}))
            # ximea camera frame
            filename = ximean_cam.take_frame()
            # send to clowder
            clowder.upload_a_file_to_dataset(filename)
            # TODO: assume do cleanup after every pcp file print
            clean_nozzle()
            break
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
                if tool and lulzbot:
                    lulzbot.setPosMode(params)
            elif op == "move":
                print("lulzbot.move: " + params)
                if tool and lulzbot:
                    lulzbot.move(params)
                    # get current position of printer for this move
                    cur_pos = lulzbot.move("M114\n")
                    status = dict()
                    status["pos"] = cur_pos
                    send_message('printer_movement', json.dumps(status))
            elif op == "startPoint":
                match = re.search(r'X=([-]?[0-9.]+)', params)
                abs_x = None
                if match:
                    abs_x =  float(match.group(1))
                abs_y = None
                match = re.search(r'Y=([-]?[0-9.]+)', params)
                if match:
                    abs_y =  float(match.group(1))
                abs_z = None
                match = re.search(r'Z=([-]?[0-9.]+)', params)
                if match:
                    abs_z =  float(match.group(1))
                abs_position_move_printer(abs_x, abs_y, abs_z)
        elif name == "tool":
            if op == "setValue":
                if tool and lulzbot:
                    tool.setValue(params)
            elif op == "engage":
                if tool and lulzbot:
                    tool.engage()
            elif op == "disengage":
                if tool and lulzbot:
                    tool.disengage()
    return True
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
    status = None
    message = json.loads(body)
    type = message['type']
    print("process: " + type)
    if type == 'device_status':
        status = json.dumps(get_devices_status())
        send_message('device_status_update', status)
    elif type == 'pcp_commands':
        send_pcp_commands(message)
        status = "OK"
    elif type == 'printing_params':
        send_printing_params(message)
        status = "OK"
    elif type == 'activate':
        if message['data'] == 'tool':
            if tool is not None:
                status = tool.activate()
        elif message['data'] == 'lulzbot':
            if lulzbot is not None:
                status =lulzbot.activate()
                #TODO: update printer_start_pos?
        # TODO: update device status
        # send_message('device_status_update', status)
    elif type == 'deactivate':
        if message['data'] == 'tool':
            if tool is not None:
                status = tool.deactivate()
        elif message['data'] == 'lulzbot':
            if lulzbot is not None:
                status = lulzbot.deactivate()
                # TODO: update printer_start_pos, set to None?
        # TODO: update device status
        # send_message('device_status_update', status)
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
def abs_position_move_printer(x_pos = None, y_pos = None, z_pos = None):
    """
    abs pos of home X:-22 Y:287 Z:290
    delta_x =
    """
    lulzbot.setPosMode("relative")
    cur_pos = lulzbot.move("M114\n")
    # cur_pos = 'X:0.00 Y:127.00 Z:145.00 E:0.00 Count X: 0 Y:10160 Z:116000'
    cur_x_pos = ""
    cur_y_pos = ""
    # get X
    match = re.search(r'X:([-]?[0-9.]+)', cur_pos)
    is_x_delta = False
    if match:
        is_x_delta = True
        cur_x_pos = float(match.group(1))
    is_y_delta = False
    match = re.search(r'Y:([-]?[0-9.]+)', cur_pos)
    if match:
        is_y_delta = True
        cur_y_pos = float(match.group(1))
    is_z_delta = False
    match = re.search(r'Z:([-]?[0-9.]+)', cur_pos)
    if match:
        is_z_delta = True
        cur_z_pos = float(match.group(1))
    #"G1 X\n"
    if x_pos:
        if is_x_delta:
            delta_x = x_pos- cur_x_pos
            cmd = "G1"
            cmd = cmd + " F2000 X%s\n" % str(delta_x)
            lulzbot.move(cmd)
    if y_pos:
        if is_y_delta:
            delta_y = y_pos - cur_y_pos
            cmd = "G1"
            cmd = cmd + " F2000 Y%s\n" % str(delta_y)
            lulzbot.move(cmd)
    if z_pos:
        if is_z_delta:
            delta_z = z_pos - cur_z_pos
            cmd = "G1"
            cmd = cmd + " F2000 Z%s\n" % str(delta_z)
            lulzbot.move(cmd)
def clean_nozzle():
    abs_position_move_printer(z_pos=290)
    abs_position_move_printer(x_pos=-22, y_pos=20)
    abs_position_move_printer(z_pos=40)
    lulzbot.move("M400\n")
    time.sleep(5)
    abs_position_move_printer(z_pos=290)
    print("nozzle has been cleaned")
# mimic the print and then clean nozzle and then print anther shape
# abs_position_move_printer(100, 200, 200)
# clean_nozzle()
# abs_position_move_printer(150, 50, 100)
channel.basic_qos(prefetch_count=1)
status = json.dumps(get_devices_status())
send_message('device_status_update', status)
# home_pos = dict()
# home_pos['start'] = 'X:0.00 Y:127.00 Z:145.00 E:0.00 Count X: 0 Y:10160 Z:116000'
# send_message('printer_movement', json.dumps(home_pos))
listen_device_status()
listen_pcp_commands()
listen_printing_params()
listen_device_activate_deactivate()
print(" [x] Adaptor starting")
channel.start_consuming()