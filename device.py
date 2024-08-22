from datetime import datetime, timedelta
from .utilities import source_utilities, notification

from flask import Flask, render_template, url_for, flash, redirect, Blueprint, request, session, current_app, \
    send_from_directory, abort

from .auth import role_required

from flask import jsonify
from .utilities.user_utilities import *
from .utilities.constants import *
from .utilities.rabbitMQ.receiver import RpcDevicesReceiver
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

@devicebp.route('/device/<id>',  methods=['POST'])
@role_required("user")
def activate(id):
    pass


@devicebp.route('/device/<id>',  methods=['POST'])
@role_required("user")
def deactivate(id):
    pass
