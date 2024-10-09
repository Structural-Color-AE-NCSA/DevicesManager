import traceback
from flask import jsonify
from flask import Flask, Response, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort
from .auth import role_required
from flask_paginate import Pagination, get_page_args

from .config import Config
from .utilities.rabbitMQ.deviceStatus import DeviceStatus
from .utilities.user_utilities import *


devices_listing_bp = Blueprint('devices_listing', __name__, url_prefix=Config.URL_PREFIX+'/devices')
device_status = DeviceStatus()


@devices_listing_bp.route('/activate',  methods=['POST'])
@role_required("user")
def activate():
    device_id = request.form.get('id')
    device_status.activate(int(device_id))
    return jsonify([]), 200


@devices_listing_bp.route('/deactivate',  methods=['POST'])
@role_required("user")
def deactivate():
    device_id = request.form.get('id')
    device_status.deactivate(int(device_id))
    return jsonify([]), 200

@devices_listing_bp.route('/', methods=['GET', 'POST'])
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

    return render_template("events/device_listing.html", posts_dic = posts_dic,
                            select_status=select_status, page=page,
                            per_page=per_page, pagination_links=pagination.links,
                            isUser=True, start=start, end=end, page_config=Config.EVENTS_PER_PAGE,
                            groups=groups,
                            selected_group=session.get('group'))