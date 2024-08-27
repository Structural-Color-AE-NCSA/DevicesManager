from datetime import datetime, timedelta
from .utilities import source_utilities, notification

from flask import Flask, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort

from .auth import role_required

from flask import jsonify
from .utilities.user_utilities import *
from .utilities.constants import *
from .utilities.rabbitMQ.client import DeviceComm
from .utilities.rabbitMQ.deviceStatus import DeviceStatus
from .utilities.rabbitMQ.pcpFile import PCPFile
from flask_paginate import Pagination, get_page_args
from .config import Config
from werkzeug.utils import secure_filename
from glob import glob
from os import remove, path, getcwd, makedirs
import logging
from time import gmtime

logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("device.py")

devicebp = Blueprint('device', __name__, url_prefix=Config.URL_PREFIX+'/device')

device_status = DeviceStatus()
pcp_file = PCPFile()
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

@devicebp.route('/device/run_pcp_file', methods=['POST'])
@role_required("user")
def send_pcp_file():
    for filename in request.form:
        print(f'PCP File Name: {filename}')
        path_to_pcp_file = os.path.join(os.getcwd(), 'pcp', filename)
        with open(path_to_pcp_file, 'r') as file:
            file_content = file.read()
        pcp_file.send_pcp_file(file_content)
    return jsonify([]), 200