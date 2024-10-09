#  Copyright 2020 Board of Trustees of the University of Illinois.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import os
import atexit
import logging
from time import gmtime

from flask import Flask, current_app, redirect, url_for, Blueprint, session, render_template
from git import Repo

from .config import Config
from .db import init_db

from .auth import check_login
from .auth import bp as auth_bp
from .event import bp as event_bp
from .home import bp as home_bp
from .user_events import userbp as user_bp
from .device import devicebp as device_bp
from .devices_listing import devices_listing_bp as devices_listing_bp


from flask_cors import CORS
from flask_socketio import SocketIO


logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("__init__.py")

socketio = SocketIO()


@socketio.on('connect')
def test_connect():
    print("socketio connect!")


@socketio.on('test')
def test_connect():
    print("socketio received message test from javascript!")


def create_app(config_class=Config):
    if Config is not None and Config.URL_PREFIX is not None:
        prefix = Config.URL_PREFIX
        staticpath = prefix+'/static'
    else:
        prefix = None
        staticpath = '/static'
    app = Flask(__name__, static_url_path=staticpath)
    CORS(app)
    app.config.from_object(Config)

    __logger.info("Devices Manager starts.")
    init_db(app)
    try:
        os.mkdir(app.config['WEBTOOL_IMAGE_MOUNT_POINT'])
    except OSError:
        pass

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(device_bp)
    app.register_blueprint(devices_listing_bp)

    socketio.init_app(app)
    device.init_socketio(socketio)
    socketio.run(app, allow_unsafe_werkzeug=True, logger=True, engineio_logger=True, cors_allowed_origins="*",
                 host='0.0.0.0')

    @app.route('/')
    @check_login
    def index():
        return redirect(url_for('home.home'))

    @app.context_processor
    def utility_processor():
        def get_version():
            repo = Repo(os.path.dirname(os.path.realpath(__file__)))
            if len(repo.tags) > 0:
                return repo.tags[-1]
            return 0

        return dict(get_version=get_version)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('errors/500.html'), 500

    return app
