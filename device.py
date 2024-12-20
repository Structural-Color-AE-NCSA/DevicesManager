import traceback
from flask import Flask, Response, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort

import time
from .auth import role_required

from flask import jsonify
from .utilities.user_utilities import *
from .utilities.rabbitMQ.cameraFrames import CameraFrames
from .utilities.rabbitMQ.pcpFile import PCPFile
from .utilities.rabbitMQ.printingParams import PrintingParams
from .utilities.grid_plot import *

from flask_paginate import Pagination, get_page_args
from .config import Config
import logging
from time import gmtime
from flask_socketio import SocketIO


logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("device.py")

devicebp = Blueprint('device', __name__, url_prefix=Config.URL_PREFIX+'/device')


pcp_file = PCPFile()
printing_params = PrintingParams()
# app = Flask(__name__)
# socketio = SocketIO(app)
# socketio.run(app, allow_unsafe_werkzeug=True, logger=True, engineio_logger=True, cors_allowed_origins="*")
# camera_frames = CameraFrames(SOCKET_IO)
grid_plot = GridPlot()


def init_socketio(socketio):
    camera_frames = CameraFrames(socketio)

shape_x = 0
shape_y = 0
buf = None
@devicebp.route('/device/init_pcp_file', methods=['POST'])
@role_required("user")
def load_pcp_file():
    """
    load pcp file and initialize the grid
    :return:
    """
    is_abs_printing = False
    file_content = json.loads(request.data).get("data")
    x_start_pos = 0
    y_start_pos = 0

    x_min = 0
    x_max = 0
    y_min = 0
    y_max = 0
    x = 0
    y = 0
    pcp_commands = file_content.split("\r\n")
    for cmd in pcp_commands:
        if len(cmd) <= 0:
            continue
        print(cmd)
        cmd = cmd.replace("\\n", "\n")
        tmp = cmd.split("(")
        command = tmp[0].split(".")
        name = command[0]  # device
        sub = cmd[1 + len(name):]
        op = None  # operation
        params = None  # operation params
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
        if name == "axes":
            if op == "move":
                print("lulzbot.move: " + params)

                x_move_pattern = r"X(-?\d+)"
                match = re.search(x_move_pattern, params)
                if match:
                    x_delta = int(match.group(1))
                    x = x + x_delta
                    x_min = min(x_min, x)
                    x_max = max(x_max, x)

                y_move_pattern = r"Y(-?\d+)"
                match = re.search(y_move_pattern, params)
                if match:
                    y_delta = int(match.group(1))
                    y = y + y_delta
                    y_min = min(y_min, y)
                    y_max = max(y_max, y)
            elif op == "startPoint":
                is_abs_printing = True
                print("lulzbot.startPoint: " + params)
                x_abs_pattern = r"X=(-?\d+)"
                match = re.search(x_abs_pattern, params)
                if match:
                    x_start_pos = int(match.group(1))
                y_abs_pattern = r"Y=(-?\d+)"
                match = re.search(y_abs_pattern, params)
                if match:
                    y_start_pos = int(match.group(1))

    print("pcp shape width: " + str(x_max-x_min))
    print("pcp shape height: " + str(y_max - y_min))
    shape_x = x_max-x_min
    shape_y = y_max - y_min
    buf = grid_plot.init_plot(282, 582, shape_x, shape_y)

    if is_abs_printing:
        cell_id = grid_plot.calculate_cell_id(x_start_pos, y_start_pos)
        grid_plot.set_starting_cell_id(cell_id)
    return Response(buf, mimetype='image/png')

@devicebp.route('/device/send_printing_params', methods=['POST'])
def send_printing_params():
    commands = dict()
    x_relative_pos = request.form.get('x_relative_pos')
    y_relative_pos = request.form.get('y_relative_pos')
    z_relative_pos = request.form.get('z_relative_pos')
    print_speed = request.form.get('single_print_speed')
    pressure = request.form.get('single_pressure')
    bed_temp = request.form.get('single_bed_temp')
    pos = ""
    if x_relative_pos:
        pos = pos + "X" + str(x_relative_pos) + " "
    if y_relative_pos:
        pos = pos + "Y" + str(y_relative_pos) + " "
    if z_relative_pos:
        pos = pos + "Z" + str(z_relative_pos) + " "
    if print_speed:
        pos = pos + "F" + str(print_speed)
    if pos:
        commands['pos'] = "G1 " + pos + "\n"

    if pressure:
        commands['pressure'] = pressure

    if bed_temp:
        commands['bed_temp'] = "M140 S"+bed_temp + "\n"

    printing_params.send_printing_params(commands)

    return jsonify([]), 200

@devicebp.route('/device/run_pcp_file', methods=['POST'])
@role_required("user")
def send_pcp_file():
    filename = request.form.get('pcpFileName')
    cell_ids = request.form.get('cell_ids')
    print(f'PCP File Name: {filename}')
    path_to_pcp_file = os.path.join(os.getcwd(), 'pcp', filename)
    file_content = ""
    with open(path_to_pcp_file, 'r') as file:
        file_content = file.read()

    if len(cell_ids) == 0:# relative postions
        pcp_commands = file_content + "Done\n"
        pcp_file.send_pcp_file(pcp_commands, -1)
    else:
        cells = [item.strip() for item in cell_ids.split(',')]
        for cell_id in cells:
            abs_x, abs_y = grid_plot.get_top_left_corner_pos_by_cell_id(int(cell_id))
            X="\"X="+str(abs_x)
            Y = "Y="+str(abs_y)
            Z = "Z=21.4"+"\""
            start_point_pos = "axes.startPoint("+X+" " + Y+" " + Z+")"
            print(start_point_pos)
            pcp_commands = start_point_pos+"\r\n"+file_content + "Done\n"
            pcp_file.send_pcp_file(pcp_commands, int(cell_id))


    # for filename in request.form:
    #     print(f'PCP File Name: {filename}')
    #     path_to_pcp_file = os.path.join(os.getcwd(), 'pcp', filename)
    #     with open(path_to_pcp_file, 'r') as file:
    #         file_content = file.read()
    #     # add end line to notify pcp completion
    #     file_content = file_content + "Done\n"
    #     pcp_file.send_pcp_file(file_content, grid_plot.get_cell_id())
        #fixme, mimic another the 6 runs
        # time.sleep(1)
        # pcp_file.send_pcp_file(file_content, 1+grid_plot.get_cell_id())
        # time.sleep(1)
        # pcp_file.send_pcp_file(file_content, 2+grid_plot.get_cell_id())
        # time.sleep(1)
        # pcp_file.send_pcp_file(file_content, 3+grid_plot.get_cell_id())
        # time.sleep(1)
        # pcp_file.send_pcp_file(file_content, 4+grid_plot.get_cell_id())
        # time.sleep(1)
        # pcp_file.send_pcp_file(file_content, 5+grid_plot.get_cell_id())
        # time.sleep(1)
        # pcp_file.send_pcp_file(file_content, 6+grid_plot.get_cell_id())
    return jsonify([]), 200

@devicebp.route('/pcp_plot')
def pcp_plot():
    buf = grid_plot.load_plot()
    return Response(buf, mimetype='image/png')

@devicebp.route('/update_pcp_plot', methods=['POST'])
# @role_required("user")
def update_pcp_plot():
    # fake x, y
    # x = [random.randint(1, 282)/10 for _ in range(10)]
    # y = [random.randint(1, 582)/10 for _ in range(10)]
    params = json.loads(request.data.decode('unicode_escape'))
    cell_id = params.get('cell_id', None)
    if cell_id < 0:
        return jsonify(["cell id not found, not abs position"]), 500
    try:
        grid_plot.update_plot(cell_id)
        print(f"{cell_id} has been updated")
        return jsonify(["success update cell done"]), 200
    except:
        traceback.print_exc()
        return jsonify(["cell id not found"]), 500


@devicebp.route('/campaign/new',  methods=['GET'])
@role_required("user")
def start_campaign():
    post = None
    if os.path.exists('pcpfig.png'):
        os.remove('pcpfig.png')
    return render_template("events/device.html", post=post, eventTypeMap=eventTypeMap,
                           isUser=True, apiKey=current_app.config['GOOGLE_MAP_VIEW_KEY'],
                           timestamp=datetime.now().timestamp(),
                           timezones=Config.TIMEZONES,
                           extensions=",".join("." + extension for extension in Config.ALLOWED_PCP_FILE_EXTENSIONS),
                           # groupName=groupName
                            )
