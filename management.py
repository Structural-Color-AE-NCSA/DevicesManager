import json
import datetime

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, current_app, session, Request, jsonify, send_from_directory
)
from werkzeug.exceptions import abort

from .auth import role_required

from .scheduler import scheduler_add_job
from .utilities.source_utilities import *
from .utilities.sourceEvents import start
from .utilities.constants import eventTypeMap, eventTypeValues
from flask_paginate import Pagination, get_page_args

from datetime import datetime, timedelta
from .config import Config
import logging
from time import gmtime


bp = Blueprint('management', __name__, url_prefix=Config.URL_PREFIX+'/management')
logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("event.py")

@bp.route('/<title>', methods=['GET'])
# @role_required("source")
def home(title):
    allsources = current_app.config['SIDEBAR_MENU']
    calendars = current_app.config['SIDEBAR_MENU'][title][1]
    return render_template('management.html',
                            allsources=allsources, sourceId=0,
                            title=title, calendars=calendars, total=0,
                            eventTypeValues=eventTypeValues, isUser=False)


@bp.route('/accounts', methods=('GET', 'POST'))
@role_required("source")
def accounts():
    if request.method == 'POST':
        #add update calendars
        existing_users = get_all_user_accounts()
        update_accounts_status(request.form, existing_users)
    users_in_db = get_all_user_accounts()
    user_ids = users_in_db.keys()
    calendar_source = list()
    status = dict()
    accounts = list()
    for user_id in user_ids:
        calendar_source.append({user_id: users_in_db.get(user_id).get('username')})
        status[user_id] = users_in_db.get(user_id).get('status')
        accounts.append(users_in_db.get(user_id))
    INT2SRC = {
        '0': ('Users', calendar_source)
    }
    calendar_prefix=current_app.config['WEBTOOL_CALENDAR_LINK_PREFIX']
    return render_template('accounts/setting.html',
                            isUser=False,
                            sources=INT2SRC,
                            allstatus=status,
                            accounts = accounts,
                            url_prefix=calendar_prefix, schedule_time=get_download_schedule_time())


@bp.route('/accounts/delete', methods=(['POST']))
@role_required("source")
def account_delete():
    username = json.loads(request.data.decode("utf-8")).get('username')
    delete_account(username)
    return jsonify(["success"]), 200


@bp.route('/settings', methods=('GET', 'POST'))
@role_required("source")
def settings():
    if request.method == 'POST':
        #add update calendars
        allstatus = get_all_calendar_status()
        update_calendars_status(request.form, allstatus)
    calendar_in_db = get_all_calendar_status()
    calendar_ids = calendar_in_db.keys()
    calendar_source = list()
    calendar_status = dict()
    for calendar_id in calendar_ids:
        calendar_source.append({calendar_id: calendar_in_db.get(calendar_id).get('calendarName')})
        calendar_status[calendar_id] = calendar_in_db.get(calendar_id).get('status')
    INT2SRC = {
        '0': ('WebTools', calendar_source),
        '1': ('EMS', []),
    }
    calendar_prefix=current_app.config['WEBTOOL_CALENDAR_LINK_PREFIX']
    return render_template('events/setting.html',
                            isUser=False,
                            sources=INT2SRC,
                            allstatus=calendar_status,
                            url_prefix=calendar_prefix, schedule_time=get_download_schedule_time())


@bp.route('/add-new-account', methods=['POST'])
@role_required("source")
def add_new_account():
    __logger.info(request.form)
    # new calendars
    username = request.form.get('data[username]')
    password = request.form.get('data[password]')
    email = request.form.get('data[email]')
    firstname = request.form.get('data[firstname]')
    lastname = request.form.get('data[firstname]')
    is_admin = request.form.get('data[is_admin]')
    is_active = request.form.get('data[is_active]')
    if (is_admin == 'on'):
        is_admin = True
    else:
        is_admin = False
    if (is_active == 'on'):
        is_active = True
    else:
        is_active = False

    if username == '':
        __logger.error("should have both ID and Name!")
        return "invalid", 200
    new_account_doc = {"username" : username, "password": password, "email": email,
                       "firstname": firstname, "lastname": lastname,
                       "is_admin": is_admin, "is_active": is_active}
    insert_result = insert_one(current_app.config['ACCOUNTS_COLLECTION'], document = new_account_doc)
    # insert error condition check
    if insert_result.inserted_id is None:
        __logger.error("Insert new account " + username +" failed")
        return redirect('event.setting')
        return "fail", 400
    else:
        __logger.info(current_app.config['INT2CAL'])
        __logger.info("successfully inserted new account "+ username)
        return "success", 200



#### utility functions
def get_all_user_accounts():
    users = find_all(current_app.config['ACCOUNTS_COLLECTION'], filter={})
    result = {}
    for user in users:
        result[user.get('username')] = user
    return result


def update_accounts_status(update, existing):
    for user_id in existing.keys():
        if user_id in update: # approve
            approve_calendar_db(user_id)
        else: # disapprove
            disapprove_calendar_db(user_id)

def delete_account(username):
    users = find_all(current_app.config['ACCOUNTS_COLLECTION'], filter={"username": username})
    if users:
        return delete_events_in_list(current_app.config['ACCOUNTS_COLLECTION'], [user.get('_id') for user in users])
    return None