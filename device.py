import traceback
from datetime import datetime, timedelta
from .utilities import source_utilities, notification
import re
from flask import Flask, Response, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort

import time
from .auth import role_required

from flask import jsonify
from .utilities.user_utilities import *
from .utilities.constants import *
from .utilities.rabbitMQ.client import DeviceComm
from .utilities.rabbitMQ.deviceStatus import DeviceStatus
from .utilities.rabbitMQ.pcpFile import PCPFile

from .utilities.grid_plot import *

from flask_paginate import Pagination, get_page_args
from .config import Config
from werkzeug.utils import secure_filename
from glob import glob
from os import remove, path, getcwd, makedirs
import random
import logging
from time import gmtime

logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("device.py")

devicebp = Blueprint('device', __name__, url_prefix=Config.URL_PREFIX+'/device')

device_status = DeviceStatus()
pcp_file = PCPFile()

grid_plot = GridPlot()

@devicebp.route('/activate',  methods=['POST'])
@role_required("user")
def activate():
    deviceID = request.form.get('id')
    device_status.activate(int(deviceID))
    return jsonify([]), 200


@devicebp.route('/deactivate',  methods=['POST'])
@role_required("user")
def deactivate():
    deviceID = request.form.get('id')
    device_status.deactivate(int(deviceID))
    return jsonify([]), 200


@devicebp.route('/', methods=['GET', 'POST'])
@role_required("user")
def devices():
    if 'from' in session:
        start = session['from']
        end = session['to']
    else:
        start = ""
        end = ""
    groups = ["test"]
    # groups, _ = get_admin_groups()

    if 'select_status' in session:
        select_status = session['select_status']
    else:
        select_status = ['connected']
        session['select_status'] = select_status
    try:
        page, per_page, offset = get_page_args(page_parameter='page', per_page_parameter='per_page')
    except ValueError:
        page = 1

    if 'per_page' in session:
        per_page = session['per_page']
    else:
        per_page = Config.PER_PAGE
        session['per_page'] = per_page
    offset = (page - 1) * per_page

    response = device_status.get_device_status()
    if page <= 0 or offset >= len(response):
        offset = 0
        page = 1

    posts_dic, total = get_all_device_status_pagination(offset, per_page, response)
    total_devices_count = total
    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')

    return render_template("events/user-events.html", posts_dic = posts_dic,
                            select_status=select_status, page=page,
                            per_page=per_page, pagination_links=pagination.links,
                            isUser=True, start=start, end=end, page_config=Config.EVENTS_PER_PAGE,
                            groups=groups,
                            selected_group=session.get('group'))
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


@devicebp.route('/device/run_pcp_file', methods=['POST'])
@role_required("user")
def send_pcp_file():
    for filename in request.form:
        print(f'PCP File Name: {filename}')
        path_to_pcp_file = os.path.join(os.getcwd(), 'pcp', filename)
        with open(path_to_pcp_file, 'r') as file:
            file_content = file.read()
        # add end line to notify pcp completion
        file_content = file_content + "Done\n"
        pcp_file.send_pcp_file(file_content, grid_plot.get_cell_id())
        #fixme, mimic another the 6 runs
        time.sleep(1)
        pcp_file.send_pcp_file(file_content, 1+grid_plot.get_cell_id())
        time.sleep(1)
        pcp_file.send_pcp_file(file_content, 2+grid_plot.get_cell_id())
        time.sleep(1)
        pcp_file.send_pcp_file(file_content, 3+grid_plot.get_cell_id())
        time.sleep(1)
        pcp_file.send_pcp_file(file_content, 4+grid_plot.get_cell_id())
        time.sleep(1)
        pcp_file.send_pcp_file(file_content, 5+grid_plot.get_cell_id())
        time.sleep(1)
        pcp_file.send_pcp_file(file_content, 6+grid_plot.get_cell_id())
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
        return jsonify(["success update cell done"]), 200
    except:
        traceback.print_exc()
        return jsonify(["cell id not found"]), 500

