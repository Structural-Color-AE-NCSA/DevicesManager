import traceback
from flask import Flask, Response, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort

import time

from utilities.messenger import Messenger, gen_fake_message
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

campaigns_bp = Blueprint('campaign', __name__, url_prefix=Config.URL_PREFIX + '/')


@campaigns_bp.route('/campaign/all', methods=['GET'])
@role_required("user")
def get_all_campaigns():
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

    response = find_all(current_app.config['CAMPAIGNS_COLLECTION'])
    if page <= 0 or offset >= len(response):
        offset = 0
        page = 1

    posts_dic, total = get_all_device_status_pagination(offset, per_page, response)
    total_devices_count = total
    pagination = Pagination(page=page, per_page=per_page, total=total, css_framework='bootstrap4')

    return render_template("campaigns/existing-campaigns.html", posts_dic = posts_dic,
                           select_status=select_status, page=page,
                           per_page=per_page, pagination_links=pagination.links,
                           isUser=True, start=start, end=end, page_config=Config.EVENTS_PER_PAGE,
                           groups=groups,
                           selected_group=session.get('group'))

@campaigns_bp.route('/campaign/<id>', methods=['GET'])
@role_required("user")
def campaign(id):
    campaign = find_one(current_app.config['CAMPAIGNS_COLLECTION'], condition={'_id': ObjectId(id)})
    pcp_file_contents = None
    if 'filepath' in campaign:
        with open(campaign['filepath'], 'r') as file:
            # Read the entire contents of the file
            pcp_file_contents = file.read()
    return render_template("campaigns/campaign.html", post=campaign, pcp_file_contents = pcp_file_contents,
                           isUser=True
                           )


@campaigns_bp.route('/campaign/<campaign_id>/update_cell_color', methods=['POST'])
# @role_required("user")
def update_cell_color(campaign_id):
    data = json.loads(request.data)
    cell_id = data.get('cell_id')
    cell_color = data.get('cell_color')
    update_cell = {"cell_id": cell_id, "cell_color": cell_color}
    campaign = find_one(current_app.config['CAMPAIGNS_COLLECTION'], condition={'_id': ObjectId(campaign_id)})
    cells = campaign.get('cells')
    if cells is None:
        cells = list()
    existing_cell = False
    for cell in cells:
        if cell.get('cell_id') == update_cell.get('cell_id'):
            cell['cell_color'] = update_cell.get('cell_color')
            existing_cell = True
    if not existing_cell:
        cells.append(update_cell)
    # save to db
    result = find_one_and_update(current_app.config['CAMPAIGNS_COLLECTION'], condition={"_id": ObjectId(campaign_id)},
                                 update={
                                     "$set": {"cells": cells}
                                 })

    # update front grid cells
    messenger = Messenger(campaign_id)
    messenger.send_message(json.dumps(update_cell))
    response = "success update cell " + str(cell_id) + " color done"
    return jsonify([response]), 200