import functools
from bson.objectid import ObjectId
import ldap
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, abort
)
from oic import rndstr
from oic.oic import Client
from oic.oic.message import RegistrationResponse, AuthorizationResponse, ClaimsRequest, Claims
from oic.utils.authn.client import CLIENT_AUTHN_METHOD
from oic.utils.http_util import Redirect
from werkzeug.security import check_password_hash

from .utilities.user_utilities import get_admin_groups
from .config import Config
from .db import find_one

bp = Blueprint('auth', __name__, url_prefix=Config.URL_PREFIX + '/auth')
# Create OIDC client
client = Client(client_authn_method=CLIENT_AUTHN_METHOD)
# Get authentication provider details by hitting the issuer URL.
provider_info = client.provider_config(Config.ISSUER_URL)
# Store registration details
info = {"client_id": Config.CLIENT_ID, "client_secret": Config.CLIENT_SECRET, "redirect_uris": Config.REDIRECT_URIS}
client_reg = RegistrationResponse(**info)
# client.store_registration_info(client_reg)

def check_login(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        access = session.get("access")
        if access is not None:
            if Config.ROLE.get(access) is not None:
                return redirect(Config.ROLE.get(access)[1])
        return view(**kwargs)

    return wrapped_view


def role_required(role):
    def decorator(view):
        @functools.wraps(view)
        def decorated_function(**kwargs):
            access = session.get("access")
            if access is None:
                session['login'] = False
                session['entry'] = request.blueprint
                return redirect(url_for("auth.login"))
            else:
                return view(**kwargs)
                if role == 'user':
                    userevent_id = kwargs.get('id')
                    if 'user_info' in session:
                        if 'uiucedu_is_member_of' in session.get('user_info'):
                            # check the AD group access
                            if 'urn:mace:uiuc.edu:urbana:authman:app-rokwire-service-policy-rokwire groups access' in session.get('user_info').get('uiucedu_is_member_of'):
                                admin_groups, _ = get_admin_groups()
                                # check the login user must have at least one admin group access.
                                if len(admin_groups) > 0:
                                    if userevent_id is None:
                                        return view(**kwargs)
                                    else:
                                        event = find_one(current_app.config['EVENT_COLLECTION'],
                                                         condition={"_id": ObjectId(userevent_id)},
                                                         projection={'createdByGroupId': 1})
                                        if 'createdByGroupId' in event:
                                            admin_groups, status_code = get_admin_groups()
                                            if status_code == 200:
                                                for admin_group in admin_groups:
                                                    if event.get('createdByGroupId') == admin_group.get('id'):
                                                        return view(**kwargs)
                                else:
                                    return redirect(url_for("home.home",
                                                     error="You don't belong to any of the user groups."))
                    return redirect(url_for("auth.login"))
                else:
                    if Config.ROLE.get(access) is not None:
                        if Config.ROLE.get(access)[0] <= Config.ROLE.get(role)[0] and access != role:
                            return redirect(Config.ROLE.get(access)[1])
                    else:
                        return redirect(url_for("auth.login"))
                return view(**kwargs)

        return decorated_function

    return decorator


def login_db(username, password, error):
    user = find_one(current_app.config['ACCOUNTS_COLLECTION'], condition={"username": username})
    if not user:
        error = 'Incorrect username.'
    elif not check_password_hash(user['password'], password):
        error = 'Incorrect password.'
    else:
        session["access"] = "user"
        session['user_id'] = username
        session['admin'] = username
        session["name"] = username
        # if error is None:
        #     session.clear()
        #     session['user_id'] = str(user['_id'])
        return redirect(url_for('management.home', title='Campaigns'))
    flash('❌ Invalid username or password!', 'error')
    abort(500, description="Invalid username or password!")
    return redirect(url_for('home.home'))


def login_ldap(username, password, error):
    ldap_hostname = current_app.config['LDAP_HOSTNAME']
    ldap_client = ldap.initialize(ldap_hostname)
    ldap_client.set_option(ldap.OPT_REFERRALS, 0)
    user_dn = "uid=%s,%s,%s" % (username, current_app.config['LDAP_USER_DN'], current_app.config['LDAP_BASE_DN'])
    group_dn = "%s,%s" % (current_app.config['LDAP_GROUP_DN'], current_app.config['LDAP_BASE_DN'])
    try:
        ldap_client.protocol_version = ldap.VERSION3
        ldap_client.simple_bind_s(user_dn, password)
    except Exception as ex:
        error = ex

    try:

        search_scope = ldap.SCOPE_SUBTREE
        search_filter = "(&(objectClass=%s)(memberOf=cn=%s,%s)(uid=%s))" % (current_app.config['LDAP_OBJECTCLASS'],
                                                                            current_app.config['LDAP_GROUP'],
                                                                            group_dn, username)
        ldap_result = ldap_client.search_s(current_app.config['LDAP_BASE_DN'], search_scope, search_filter)
        if 0 == len(ldap_result):
            error = "cannot find in this group"

    except Exception as ex:
        error = ex

    ldap_client.unbind_s()
    user = dict()
    admins = current_app.config['ADMINS']
    user['admin'] = False
    if username in admins:
        user['admin'] = True
    user['id'] = username
    if error is None:
        session.clear()
        session['user_id'] = user['id']
        session['admin'] = user['admin']
        return True

    flash(error)
    return False


@bp.route('/login', methods=['GET', 'POST'])
# @check_login
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
    # if Config.LOGIN_MODE == "shibboleth":
    #     return login_shi()
        session["state"] = rndstr()
        session["nonce"] = rndstr()
        return login_db(username, password, None)
    return render_template('login.html')


@bp.before_app_request
def load_logged_in_user_info():
    if session.get("access") is None:
        g.user = None
    else:
        g.user = {"access": session["access"], "username": session["name"]}


@bp.route('/logout')
@role_required('either')
def logout():
    session.clear()
    return redirect(url_for('home.home'))


def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not g.user:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view
