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

import pytz
import json
import datetime
import requests
import traceback
# import googlemaps
import os
import re
import tempfile
import shutil
from flask import current_app, session, flash
from bson.objectid import ObjectId
from bson.errors import InvalidId
from datetime import datetime, date
from dateutil import tz

from .source_utilities import s3_publish_image
from PIL import Image
import boto3
import os
import glob
from ..config import Config
from .constants import *
from .event_time_conversion import *
from ..db import find_all, find_one, update_one, find_distinct, insert_one, find_one_and_update, delete_events_in_list, \
    text_index_search, group_text_index_search
import logging
from time import gmtime
logging.Formatter.converter = gmtime
logging.basicConfig(level=logging.INFO, datefmt='%Y-%m-%dT%H:%M:%S',
                    format='%(asctime)-15s.%(msecs)03dZ %(levelname)-7s [%(threadName)-10s] : %(name)s - %(message)s')
__logger = logging.getLogger("user_utilities.py")

GOOGLEKEY = Config.GOOGLE_KEY
# gmaps = googlemaps.Client(key=GOOGLEKEY)
gmaps = None


def get_all_user_events(select_status):
    eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                             condition={"sourceId": {"$exists": False},
                                        "eventStatus": {"$in": select_status}})
    events_by_eventId = {}
    for eventId in eventIds:
        events = list(find_all(current_app.config['EVENT_COLLECTION'],
                               filter={"eventId": eventId,
                                       "eventStatus": {"$in": select_status}}))

        if events:
            events_by_eventId[eventId] = events

    return events_by_eventId

    # return find_all(current_app.config['EVENT_COLLECTION'], filter={"sourceId": {"$exists": False},
    #                                                                 "eventStatus": {"$in": select_status}})


def get_all_user_events_count(group_ids, select_status, start=None, end=None):
    today = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    if start and end and 'hide_past' in select_status:
        return len(find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            # "createdByGroupId": {"$in": group_ids},
                                            "eventStatus": {"$in": select_status},
                                            "$and": [{"startDate": {"$gte": start}},
                                                     {"endDate": {"$lte": end}}],
                                            "$or": [{"endDate": {"$gte": today}},
                                                    {"endDate": {"$exists": False}}]}))
    elif start and end:
        return len(find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            # "createdByGroupId": {"$in": group_ids},
                                            "eventStatus": {"$in": select_status},
                                            "$and": [{"startDate": {"$gte": start}},
                                                     {"endDate": {"$lte": end}}]}))
    elif start != '' and end == '':
        return len(find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            # "createdByGroupId": {"$in": group_ids},
                                            "eventStatus": {"$in": select_status},
                                            "startDate": {"$gte": start}}))
    elif end != '' and start == '':
        return len(find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            # "createdByGroupId": {"$in": group_ids},
                                            "eventStatus": {"$in": select_status},
                                            "endDate": {"$lte": end}}))
    elif 'hide_past' in select_status:
        return len(find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            # "createdByGroupId": {"$in": group_ids},
                                            "eventStatus": {"$in": select_status},
                                            "$or": [{"endDate": {"$gte": today}},
                                                    {"endDate": {"$exists": False}}]}))
    return len(find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                             condition={"sourceId": {"$exists": False},
                                        # "createdByGroupId": {"$in": group_ids},
                                        "eventStatus": {"$in": select_status}}))

def get_all_device_status_pagination(skip, limit, response):
    begin = skip
    end = min(len(response), skip + limit)
    device_status_by_deviceID = {}
    for device_status in response[begin:end]:
        device_ID = device_status['_id']
        device = [device_status]
        if device:
            device_status_by_deviceID[device_ID] = device
    return device_status_by_deviceID, len(response)

def get_all_user_events_pagination(group_ids, select_status, skip, limit, startDate=None, endDate=None):
    today = date.today().strftime("%Y-%m-%dT%H:%M:%S")
    if startDate and endDate and 'hide_past' in select_status:
        eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            "eventStatus": {"$in": select_status},
                                            "createdByGroupId": {"$in": group_ids},
                                            "$and": [{"startDate": {"$gte": startDate}},
                                                     {"endDate": {"$lte": endDate}}],
                                            "$or": [{"endDate": {"$gte": today}},
                                                    {"endDate": {"$exists": False}}]},
                                 skip=skip,
                                 limit=limit)
    elif startDate and endDate:
        eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            "eventStatus": {"$in": select_status},
                                            "createdByGroupId": {"$in": group_ids},
                                            "$and": [{"startDate": {"$gte": startDate}},
                                                     {"endDate": {"$lte": endDate}}]},
                                 skip=skip,
                                 limit=limit)
    elif startDate != '' and endDate == '':
        eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            "eventStatus": {"$in": select_status},
                                            "createdByGroupId": {"$in": group_ids},
                                            "startDate": {"$gte": startDate}},
                                 skip=skip,
                                 limit=limit)
    elif endDate != '' and startDate == '':
        eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            "eventStatus": {"$in": select_status},
                                            "createdByGroupId": {"$in": group_ids},
                                            "endDate": {"$lte": endDate}},
                                 skip=skip,
                                 limit=limit)
    elif 'hide_past' in select_status:
        eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            "eventStatus": {"$in": select_status},
                                            "createdByGroupId": {"$in": group_ids},
                                            "$or": [{"endDate": {"$gte": today}},
                                                    {"endDate": {"$exists": False}}]},
                                 skip=skip,
                                 limit=limit)
    else:
        eventIds = find_distinct(current_app.config['EVENT_COLLECTION'], key="eventId",
                                 condition={"sourceId": {"$exists": False},
                                            "createdByGroupId": {"$in": group_ids},
                                            "eventStatus": {"$in": select_status}},

                                 skip=skip,
                                 limit=limit)
    begin = skip
    end = min(len(eventIds), skip + limit)
    events_by_eventId = {}
    for eventId in eventIds[begin:end]:
        if startDate and endDate and 'hide_past' in select_status:
            events = list(find_all(current_app.config['EVENT_COLLECTION'],
                                   filter={"eventId": eventId,
                                           "eventStatus": {"$in": select_status},
                                           "$and": [{"startDate": {"$gte": startDate}},
                                                    {"startDate": {"$lte": endDate}}],
                                           "$or": [{"endDate": {"$gte": today}},
                                                   {"endDate": {"$exists": False}}]}))
        elif startDate and endDate:
            events = list(find_all(current_app.config['EVENT_COLLECTION'],
                                   filter={"eventId": eventId,
                                           "eventStatus": {"$in": select_status},
                                           "$and": [{"startDate": {"$gte": startDate}},
                                                    {"startDate": {"$lte": endDate}}]}))
        elif 'hide_past' in select_status:
            events = list(find_all(current_app.config['EVENT_COLLECTION'],
                                   filter={"eventId": eventId,
                                           "eventStatus": {"$in": select_status},
                                           "$or": [{"endDate": {"$gte": today}},
                                                   {"endDate": {"$exists": False}}]}))
        else:
            events = list(find_all(current_app.config['EVENT_COLLECTION'],
                                   filter={"eventId": eventId,
                                           "eventStatus": {"$in": select_status}}))
        if events:
            events_by_eventId[eventId] = events

    return events_by_eventId


# TODO get searched posts
def get_searched_user_events(searchDic, select_status):
    searchDic['sourceId'] = {"$exists": False}
    searchDic['eventStatus'] = {"$in": select_status}
    return list(find_all(current_app.config['EVENT_COLLECTION'], filter=searchDic))


def find_user_event(objectId):
    try:
        _id = ObjectId(objectId)
    except InvalidId:
        return {}
    return find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(objectId)})


def update_user_event(objectId, update, delete_field=None):
    try:
        _id = ObjectId(objectId)
    except InvalidId:
        return {}
    updateResult = update_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(objectId)},
                              update={
                                  "$set": update
                              })
    if delete_field:
        updateResult = update_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(objectId)},
                                  update={
                                      "$unset": delete_field
                                  })

    if updateResult.modified_count == 0 and updateResult.matched_count == 0 and updateResult.upserted_id is None:
        __logger.error("Update {} fails in update_user_event".format(objectId))


def find_user_all_object_events(eventId):
    __logger.info(eventId)
    result_events = find_all(current_app.config['EVENT_COLLECTION'], filter={"eventId": eventId})
    if result_events is None:
        return []
    return result_events


def delete_user_event_in_building_block(objectId_list):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + session["id_token"]
    }
    delete_success_list = []
    fail_count = 0
    for _id in objectId_list:
        event = find_one(current_app.config['EVENT_COLLECTION'], condition=_id)
        url = current_app.config['EVENT_BUILDING_BLOCK_URL'] + '/' + str(event.get('platformEventId'))
        try:
            result = requests.delete(url, headers=headers)
            if result.status_code != 202:
                __logger.error("Event {} deletion fails. Response {} {}".format(_id, result.status_code, result.text))
                fail_count += 1
            else:
                delete_success_list.append(_id)
        except requests.exceptions.RequestException as err:
            __logger.error("Unexpected network error when deleting user event {}:".format(_id), err)
            fail_count += 1
    success_count = len(delete_success_list)

    __logger.info("failed deleted in building block: " + str(fail_count))
    __logger.info("successfully deleted in building block: " + str(success_count))
    return delete_success_list


def delete_user_event(eventId):
    # Fetching event status
    event_status = get_user_event_status(eventId)

    # Deleting 'pending' events off of the local db
    if event_status == 'pending':
        local_del_id = ObjectId(eventId)
        local_delete_list = []
        local_delete_list.append(local_del_id)
        local_delete_event_local = delete_events_in_list(current_app.config['EVENT_COLLECTION'], local_delete_list)
        local_delete_count = len(local_delete_event_local)
        if local_delete_count < 1:
            __logger.error("Local event {} deletion failed".format(eventId))
            return
        else:
            __logger.info("Local event {} deletion successful".format(eventId))
            return local_delete_event_local[0]

    # Deleting 'published' events off of the building block and then the local db
    elif event_status == 'approved':
        id = ObjectId(eventId)
        delete_list = []
        delete_list.append(id)
        successfull_delete_list = delete_user_event_in_building_block(delete_list)
        delete_count = len(successfull_delete_list)
        # Since we're only dealing with deleting a singular item at a time
        # if delete_count < 1, the item wasn't successfully deleted off of the events building block
        if delete_count < 1:
            __logger.error("Local and remote event {} deletion failed".format(eventId))
            return
        else:
            # delete from group BB
            event = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(eventId)},
                             projection={'_id': 0, 'eventStatus': 0})
            url = "%sint/group/%s/events/%s" % (
                current_app.config['GROUPS_BUILDING_BLOCK_BASE_URL'], event['createdByGroupId'], event["platformEventId"])
            result = requests.delete(url, headers={"Content-Type": "application/json",
                                                   "INTERNAL-API-KEY": current_app.config['INTERNAL_API_KEY']})
            # if failed then messagebox!
            if result.status_code != 200:
                flash(
                    'An error occurred when registering this event with the selected Group. Please contact an administrator to resolve this issue.')
                __logger.error(result.reason + " fail to delete group building block {} {}".format(result.status_code, result.text))

            delete_event_local = delete_events_in_list(current_app.config['EVENT_COLLECTION'], successfull_delete_list)
            __logger.info("Local and remote event {} deletion successful".format(eventId))
            return delete_event_local[0]


# Find the approval status for one event
def get_user_event_status(objectId):
    event = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(objectId)})
    event_status = event['eventStatus']
    return event_status


def approve_user_event(objectId):
    __logger.info("{} is going to be approved".format(objectId))
    result = find_one_and_update(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(objectId)}, update={
        "$set": {"eventStatus": "approved"}
    })
    if not result:
        __logger.error("Approve event {} fails in approve_event".format(id))


def publish_user_event(eventId):
    put_status = True
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + session["id_token"]
    }

    try:
        # Put event in object, but exclude ID and status
        event = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(eventId)},
                         projection={'_id': 0, 'eventStatus': 0})
        superEventID = event.get('superEventID')
        if event:
            # Formatting Date and time for json dump
            if event.get('startDate'):
                if isinstance(event.get('startDate'), str):
                    event['startDate'] = datetime.strptime(event.get('startDate'), '%Y-%m-%dT%H:%M:%S')
                elif isinstance(event.get('startDate'), datetime.date):
                    event['startDate'] = event['startDate'].isoformat()
                    event['startDate'] = datetime.datetime.strptime(event['startDate'], "%Y-%m-%dT%H:%M:%S")
                event['startDate'] = event['startDate'].strftime("%Y/%m/%dT%H:%M:%S")
            if event.get('endDate'):
                if isinstance(event.get('endDate'), str):
                    event['endDate'] = datetime.strptime(event.get('endDate'), '%Y-%m-%dT%H:%M:%S')
                elif isinstance(event.get('endDate'), datetime.date):
                    event['endDate'] = event['endDate'].isoformat()
                    event['endDate'] = datetime.datetime.strptime(event['endDate'], "%Y-%m-%dT%H:%M:%S")
                event['endDate'] = event['endDate'].strftime("%Y/%m/%dT%H:%M:%S")
            if event.get('eventId'):
                del event['eventId']
            if event.get('superEventID'):
                del event['superEventID']
            if event.get('timezone'):
                del event['timezone']
            if event.get('subEvents'):
                # Remove unnecessary fields in sub-event array
                for subEvent in event['subEvents']:
                    id = subEvent.get('id', None)
                    isFeatured = subEvent.get('isFeatured', None)
                    track = subEvent.get('track', None)
                    subEvent.clear()
                    if id is not None:
                        subEvent['id'] = id
                    if isFeatured is not None:
                        subEvent['isFeatured'] = isFeatured
                    if track is not None:
                        subEvent['track'] = track
            # event = {k: v for k, v in event.items() if v}
            if 'subcategory' in event.keys() and event['subcategory'] is None:
                event['subcategory'] = ''
            if 'targetAudience' in event.keys() and event['targetAudience'] is None:
                event['targetAudience'] = []
            if 'contacts' in event.keys() and event['contacts'] is None:
                event['contacts'] = []
            if 'tags' in event.keys() and event['tags'] is None:
                event['tags'] = []
            if 'subEvents' in event.keys() and event['subEvents'] is None:
                event['subEvents'] = []
            if 'location' in event.keys() and event['location'] is None:
                event['location'] = dict()
            # Setting up post request
            result = requests.post(current_app.config['EVENT_BUILDING_BLOCK_URL'], headers=headers,
                                   data=json.dumps(event))

            # if event submission fails, print that out and change status back to pending
            if result.status_code != 201:
                __logger.error("Event {} POST submission fails. Response {} {}".format(eventId, result.status_code, result.text))
                failed_event = find_one_and_update(current_app.config['EVENT_COLLECTION'],
                                                   condition={"_id": ObjectId(eventId)}, update={
                        "$set": {"eventStatus": "pending"}
                    })
                __logger.info("Event {} status changed back to pending".format(eventId))
                return False
            # if successful, change status of event to approved.
            else:
                platform_event_id = result.json()['id']
                # post eventid to group building block
                url = "%sint/group/%s/events" % (current_app.config['GROUPS_BUILDING_BLOCK_BASE_URL'], event['createdByGroupId'])
                result = requests.post(url, headers={"Content-Type": "application/json", "INTERNAL-API-KEY": current_app.config['INTERNAL_API_KEY']},
                                       data=json.dumps({"event_id": platform_event_id, "creator":{"email": session['email'], "name": session['name'], "user_id": session['uin']} }))
                if result.status_code != 200:
                    flash('An error occurred when registering this event with the selected Group. Please contact an administrator to resolve this issue.')
                    __logger.error(result.reason + " {} {} Fail to get group building block eventId {} ".format(result.status_code, result.text, platform_event_id))
                    return False

                # else:
                #     flash('successfully post event id to group building block!')

                # Should upload user images
                s3_client = boto3.client('s3')
                imageId = s3_publish_user_image(eventId, platform_event_id, s3_client)
                updates = {"eventStatus": "approved", "platformEventId": platform_event_id}
                # write platform id to db
                update_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(eventId)},
                                          update={"$set": updates})
                # add platformid to its superevent's subevents
                if superEventID is not None:
                    superEvent = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(superEventID)})
                    if 'subEvents' in superEvent and superEvent['subEvents'] is not None:
                        for subEvent in superEvent['subEvents']:
                            if 'eventId' in subEvent and subEvent['eventId'] == eventId:
                                subEvent['id'] = platform_event_id
                                overwriteSubeventsList = list()
                                overwriteSubeventsList.append(subEvent)
                                overwrite_subevents_to_superevent(overwriteSubeventsList, superEventID)
                                break
                if imageId:
                    __logger.info("User image upload successful for event {}".format(eventId))
                    event['imageURL'] = current_app.config['ROKWIRE_IMAGE_LINK_FORMAT'].format(platform_event_id, imageId)
                    updates = {"imageURL": event['imageURL']}
                    updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                                              condition={"_id": ObjectId(eventId)},
                                              update={"$set": updates})
                    put_status = put_user_event(eventId)
                    if not put_status:
                        #TODO: think to notify user failure of upload image url to events building block
                        __logger.error("Event image {} upload fails".format(eventId))
                return True
    except Exception as ex:
        __logger.exception(ex)
        return False


def put_user_event(eventId):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + session["id_token"]
    }
    try:
        # Put event in object, but exclude ID and status
        event = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(eventId)},
                         projection={'_id': 0, 'eventStatus': 0})
        if event:
            # Formatting Date and time for json dump
            if event.get('startDate'):
                if isinstance(event.get('startDate'), str):
                    event['startDate'] = datetime.strptime(event.get('startDate'), '%Y-%m-%dT%H:%M:%S')
                elif isinstance(event.get('startDate'), datetime.date):
                    event['startDate'] = event['startDate'].isoformat()
                    event['startDate'] = datetime.datetime.strptime(event['startDate'], "%Y-%m-%dT%H:%M:%S")
                event['startDate'] = event['startDate'].strftime("%Y/%m/%dT%H:%M:%S")
            if event.get('endDate'):
                if isinstance(event.get('endDate'), str):
                    event['endDate'] = datetime.strptime(event.get('endDate'), '%Y-%m-%dT%H:%M:%S')
                elif isinstance(event.get('endDate'), datetime.date):
                    event['endDate'] = event['endDate'].isoformat()
                    event['endDate'] = datetime.datetime.strptime(event['endDate'], "%Y-%m-%dT%H:%M:%S")
                event['endDate'] = event['endDate'].strftime("%Y/%m/%dT%H:%M:%S")
            if event.get('eventId'):
                del event['eventId']
            if event.get('superEventID'):
                superEventID = event['superEventID']
                del event['superEventID']
            if event.get('timezone'):
                timezone = event['timezone']
                del event['timezone']
            if event.get('subEvents'):
                # Remove unnecessary fields in sub-event array
                for subEvent in event['subEvents']:
                    id = subEvent.get('id', None)
                    isFeatured = subEvent.get('isFeatured', None)
                    track = subEvent.get('track', None)
                    subEvent.clear()
                    if id is not None:
                        subEvent['id'] = id
                    if isFeatured is not None:
                        subEvent['isFeatured'] = isFeatured
                    if track is not None:
                        subEvent['track'] = track

            # Getting rid of all the empty fields for PUT request
            # event = {k: v for k, v in event.items() if v}
            if 'subcategory' in event.keys() and event['subcategory'] is None:
                event['subcategory'] = ''
            if 'targetAudience' in event.keys() and event['targetAudience'] is None:
                event['targetAudience'] = []
            if 'contacts' in event.keys() and event['contacts'] is None:
                event['contacts'] = []
            if 'tags' in event.keys() and event['tags'] is None:
                event['tags'] = []
            if 'subEvents' in event.keys() and event['subEvents'] is None:
                event['subEvents'] = []
            if 'location' in event.keys() and event['location'] is None:
                event['location'] = dict()
            # Generation of URL via platformEventId
            url = current_app.config['EVENT_BUILDING_BLOCK_URL'] + '/' + event.get('platformEventId')
            # Getting rid of platformEventId from PUT request
            platform_event_id = event["platformEventId"]
            if "platformEventId" in event:
                del event["platformEventId"]

            # get previous groupid from events building block
            result = requests.get(url, headers=headers)
            previous_groupid = None
            if result.status_code == 200:
                previous_groupid = result.json().get('createdByGroupId')
            else:
                __logger.error("fail to get groupid {} from events building block. Response {} {}".format(eventId, result.status_code, result.text))
            # PUT request
            result = requests.put(url, headers=headers, data=json.dumps(event))

            # If PUT request fails, print that out and change status back to pending
            if result.status_code != 200:
                __logger.error("Event {} PUT submission fails. Response {} {}".format(eventId, result.status_code, result.text))
                failed_event = find_one_and_update(current_app.config['EVENT_COLLECTION'],
                                                   condition={"_id": ObjectId(eventId)}, update={
                        "$set": {"eventStatus": "pending"}
                    })
                __logger.info("Event {} status changed back to pending".format(eventId))
                return False

            # If PUT request successful, change status to approved
            else:
                updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                                          condition={"_id": ObjectId(eventId)},
                                          update={
                                              "$set": {"eventStatus": "approved"}
                                          })
                if previous_groupid and previous_groupid != event['createdByGroupId'] and platform_event_id:
                    url = "%sint/group/%s/events/%s" % (
                        current_app.config['GROUPS_BUILDING_BLOCK_BASE_URL'], previous_groupid, platform_event_id)
                    result = requests.delete(url, headers={"Content-Type": "application/json",
                                                         "INTERNAL-API-KEY": current_app.config['INTERNAL_API_KEY']})
                    # if failed then messagebox!
                    if result.status_code != 200:
                        flash('An error occurred when registering this event with the selected Group. Please contact an administrator to resolve this issue.')
                        __logger.error("fail to delete user event {}'s group id from group building block. Response {} {}".format(eventId, result.status_code, result.text))
                    else:
                        # post to group bb
                        # post eventid to group building block
                        url = "%sint/group/%s/events" % (
                        current_app.config['GROUPS_BUILDING_BLOCK_BASE_URL'], event['createdByGroupId'])
                        result = requests.post(url, headers={"Content-Type": "application/json",
                                                             "INTERNAL-API-KEY": current_app.config['INTERNAL_API_KEY']},
                                               data=json.dumps({"event_id": platform_event_id,
                                                                "creator": {"email": session['email'],
                                                                            "name": session['name'],
                                                                            "user_id": session['uin']}}))
                        # if failed then messagebox!
                        if result.status_code != 200:
                            flash('An error occurred when registering this event with the selected Group. Please contact an administrator to resolve this issue.')
                            __logger.error("User event {} fail to post to group building block. Response {} {}".format(eventId, result.status_code, result.text))

                        else:
                            __logger.info(
                                'update event: {} groupid from {} to {} successful'.format(platform_event_id, previous_groupid, event['createdByGroupId']))

                return True

    except Exception as ex:
        __logger.exception(ex)
        return False


def disapprove_user_event(objectId):
    __logger.info("{} is going to be disapproved".format(objectId))
    result = find_one_and_update(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(objectId)}, update={
        "$set": {"eventStatus": "pending"}
    })
    if not result:
        __logger.error("Disapprove event {} fails in disapprove_event".format(objectId))


def create_new_user_event(new_user_event):
    update_result = None
    result = insert_one(current_app.config['EVENT_COLLECTION'], new_user_event)
    if result.inserted_id:
        update = dict()
        update['eventStatus'] = 'pending'
        update['eventId'] = str(result.inserted_id)
        # for key in update:
        update_result = update_one(current_app.config['EVENT_COLLECTION'],
                                   condition={"_id": ObjectId(result.inserted_id)},
                                   update={
                                       "$set": update
                                   })
    if update_result is None or update_result.modified_count == 0 and update_result.matched_count == 0 and update_result.upserted_id is None:
        __logger.error("create_new_user_event {} failed")
    return result.inserted_id


def populate_event_from_form(post_form, email):
    new_event = dict()
    super_event = False
    all_day_event = False
    for item in post_form:
        if item_not_list(item):
            if item == 'isSuperEvent' and post_form.get(item) == 'on':
                new_event['isSuperEvent'] = True
                super_event = True
            elif item == 'allDay' and post_form.get(item) == 'on':
                new_event['allDay'] = True
                all_day_event = True
            elif item == 'isVirtual' and post_form.get(item) == 'on':
                new_event['isVirtual'] = True
            elif item == 'isInPerson' and post_form.get(item) == 'on':
                new_event['isInPerson'] = True
            else:
                new_event[item] = post_form.get(item)
    if not super_event:
        new_event['isSuperEvent'] = False
    if not all_day_event:
        new_event['allDay'] = False

    new_event['contacts'] = get_contact_list(post_form)

    if new_event['isSuperEvent'] == True:
        new_event['subEvents'] = get_subevent_list(post_form)
    else:
        new_event['subEvents'] = None

    new_event['tags'] = get_tags(post_form)

    new_event['targetAudience'] = get_target_audience(post_form)

    if all_day_event:
        start_date = post_form.get('startDate')
    else:
        start_date = post_form.get('startDate') + 'T' + post_form.get('startTime')
    if 'timezone' in post_form:
        new_event['startDate'] = time_zone_to_utc(post_form.get('timezone'), start_date, 'startDate', all_day_event)
    else:
        new_event['startDate'] = get_datetime_in_utc(post_form.get('location'), start_date, 'startDate', all_day_event)

    end_date = post_form.get('endDate')
    if not all_day_event and end_date != '':
        end_date = post_form.get('endDate') + 'T' + post_form.get('endTime')

    if end_date != '':
        if 'timezone' in post_form:
            new_event['endDate'] = time_zone_to_utc(post_form.get('timezone'), end_date, 'endDate', all_day_event)
        else:
            new_event['endDate'] = get_datetime_in_utc(post_form.get('location'), end_date, 'endDate', all_day_event)

    location = post_form.get('location')
    if location != '':
        new_event['location'] = get_location_details(location, False)
    else:
        new_event['location'] = None
    new_event['virtualEventUrl'] = post_form.get('virtualEventUrl')

    new_event['createdBy'] = email

    return new_event


def get_location_details(location_description, is_virtual_event):
    location_obj = dict()
    if is_virtual_event:
        location_obj['description'] = location_description
        return location_obj

    for excluded_location in Config.EXCLUDED_LOCATION:
        if excluded_location.lower() in location_description.lower():
            location_obj['description'] = location_description
            return location_obj
    google_geocoding_api_key = current_app.config['GOOGLE_KEY']
    try:
        google_maps_client = googlemaps.Client(key=google_geocoding_api_key)
        geocoding_response = google_maps_client.geocode(address=location_description + ',Urbana',
                                                        components={'administrative_area': 'Urbana', 'country': "US"})
        if len(geocoding_response) > 0:
            lat = geocoding_response[0]['geometry']['location']['lat']
            lng = geocoding_response[0]['geometry']['location']['lng']
            location_obj = {
                'latitude': lat,
                'longitude': lng,
                'description': location_description
            }
        else:
            location_obj['description'] = location_description
    except ValueError as e:
        __logger.error("Error in connecting to Google Geocoding API: {}".format(e))
        location_obj['description'] = location_description
    except googlemaps.exceptions.ApiError as e:
        __logger.error("API Key Error: {}".format(e))
        location_obj['description'] = location_description

    return location_obj


def get_datetime_in_utc(location, str_local_date, date_field, is_all_day_event):
    __logger.info("str_local_date", str_local_date)
    if is_all_day_event:
        datetime_obj = datetime.strptime(str_local_date, "%Y-%m-%d")
        # Set time to match the
        if date_field == "startDate":
            datetime_obj = datetime_obj.replace(hour=00, minute=00)
        elif date_field == "endDate":
            datetime_obj = datetime_obj.replace(hour=23, minute=59)
    else:
        try:
            datetime_obj = datetime.strptime(str_local_date, "%Y-%m-%dT%H:%M")
        except ValueError:
            datetime_obj = datetime.strptime(str_local_date, "%Y-%m-%dT%H:%M:%S")
    if location:
        latitude = None
        longitude = None
        if location in predefined_locations:
            latitude = predefined_locations[location].latitude
            longitude = predefined_locations[location].longitude
        else:
            try:
                GeoResponse = gmaps.geocode(address=location + ',Urbana',
                                            components={'administrative_area': 'Urbana', 'country': "US"})
                if len(GeoResponse) != 0:
                    latitude = GeoResponse[0]['geometry']['location']['lat']
                    longitude = GeoResponse[0]['geometry']['location']['lng']
            except googlemaps.exceptions.ApiError as e:
                __logger.error("API Key Error: {}".format(e))
        return utctime(datetime_obj, latitude, longitude)
    local_tz = pytz.timezone("US/Central")
    datetime_with_tz = local_tz.localize(datetime_obj, is_dst=None)  # No daylight saving time
    datetime_obj = datetime_with_tz.astimezone(pytz.UTC)
    return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")


def get_datetime_in_local(location, str_utc_date, is_all_day_event):
    timezone = pytz.UTC
    localzone = tz.tzlocal()
    if location and location.get('latitude') and location.get('longitude'):
        latitude = location.get('latitude')
        longitude = location.get('longitude')
        timezone_str = get_timezone_by_geolocation(latitude, longitude)
        localzone = tz.gettz(timezone_str)

    datetime_obj = datetime.strptime(str_utc_date[0:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone).astimezone(
        localzone)

    if is_all_day_event:
        return datetime_obj.strftime("%Y-%m-%d")
    else:
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")


def time_zone_to_utc(time_zone, str_date, date_field, is_all_day_event):
    if is_all_day_event:
        datetime_obj = datetime.strptime(str_date, "%Y-%m-%d")
        if date_field == "startDate":
            datetime_obj = datetime_obj.replace(hour=00, minute=00)
        elif date_field == "endDate":
            datetime_obj = datetime_obj.replace(hour=23, minute=59)
    else:
        try:
            datetime_obj = datetime.strptime(str_date, "%Y-%m-%dT%H:%M")
        except ValueError:
            datetime_obj = datetime.strptime(str_date, "%Y-%m-%dT%H:%M:%S")
    local_tz = pytz.timezone(time_zone)
    datetime_obj = local_tz.localize(datetime_obj, is_dst=None).astimezone(pytz.UTC)
    return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")


def utc_to_time_zone(time_zone, str_date, is_all_day_event):
    datetime_obj = datetime.strptime(str_date, "%Y-%m-%dT%H:%M:%S")
    local_tz = pytz.timezone(time_zone)
    datetime_obj = pytz.UTC.localize(datetime_obj, is_dst=None).astimezone(local_tz)
    if is_all_day_event:
        return datetime_obj.strftime("%Y-%m-%d")
    else:
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")


def get_contact_list(post_form):
    contacts_arrays = []
    has_contacts_in_request = False
    for item in post_form:
        # when contact input field is not empty
        if item == 'firstName' or item == 'lastName' or item == 'email' or item == 'phone' or item == 'organization':
            contact_list = post_form.getlist(item)
            if len(contact_list) != 0:
                # delete first group of empty string
                contact_list = contact_list[1:]
                contacts_arrays += [contact_list]
        # new_event[item] = post_form.get(item)

    if contacts_arrays:
        num_of_contacts = len(contacts_arrays[0])
        contacts_dic = []
        for i in range(num_of_contacts):
            a_contact = {}
            firstName = contacts_arrays[0][i]
            lastName = contacts_arrays[1][i]
            email = contacts_arrays[2][i]
            phone = contacts_arrays[3][i]
            orginazation = contacts_arrays[4][i]
            if firstName != "":
                a_contact['firstName'] = firstName
            if lastName != "":
                a_contact['lastName'] = lastName
            if email != "":
                a_contact['email'] = email
            if phone != "":
                a_contact['phone'] = phone
            if orginazation != "":
                a_contact['organization'] = orginazation
            if a_contact != {}:
                contacts_dic.append(a_contact)
        if contacts_dic != []:
            has_contacts_in_request = True
            return contacts_dic
        # return ""


# helper function to get subevent
def get_subevent_list(post_form):
    subevent_arrays = []
    for item in post_form:
        if item == 'name' or item == 'id' or item == 'track' or item == 'isFeatured' or item == 'status' or item == 'eventId':
            sub_list = post_form.getlist(item)
            if len(sub_list) != 0:
                sub_list = sub_list[1:]
                subevent_arrays += [sub_list]
    if subevent_arrays:
        num_of_sub = len(subevent_arrays[0])
        subevent_dict = []
        for i in range(num_of_sub):
            a_subevent = {}
            sub_name = subevent_arrays[0][i]
            sub_id = subevent_arrays[1][i]
            sub_eventid = subevent_arrays[2][i]
            sub_status = subevent_arrays[3][i]
            sub_track = subevent_arrays[4][i]
            sub_feature = subevent_arrays[5][i]
            if sub_name != "":
                a_subevent['name'] = sub_name
            if sub_id != "":
                a_subevent['id'] = sub_id
            if sub_eventid != "":
                a_subevent['eventId'] = sub_eventid
            if sub_status != "":
                a_subevent['status'] = sub_status
            if sub_track != "":
                a_subevent['track'] = sub_track
            if sub_feature != "":
                if sub_feature == 'Featured':
                    a_subevent['isFeatured'] = True
                else:
                    a_subevent['isFeatured'] = False
            if a_subevent != {}:
                subevent_dict.append(a_subevent)
        if subevent_dict != []:
            return subevent_dict
        else:
            return None
    else:
        return None


def get_tags(post_form):
    tag_arrays = []
    for item in post_form:
        if item == 'tags':
            tag_arrays = post_form.getlist(item)
    if tag_arrays:
        num_of_tag = len(tag_arrays)
        tag_dict = []
        for i in range(num_of_tag):
            a_tag = {}
            tag_name = tag_arrays[i]
            if tag_name != "":
                a_tag = tag_name
            if a_tag != {}:
                tag_dict.append(a_tag)
        if tag_dict != []:
            return tag_dict


def get_target_audience(post_form):
    target_audience_arrays = []
    for item in post_form:
        if item == 'targetAudience':
            target_audience_arrays = post_form.getlist(item)
    if target_audience_arrays:
        num_of_target_audience = len(target_audience_arrays)
        target_audience_dict = []
        for i in range(num_of_target_audience):
            a_target_audience = {}
            target_audience_group = target_audience_arrays[i]
            if target_audience_group != "":
                a_target_audience = target_audience_group
            if a_target_audience != {}:
                target_audience_dict.append(a_target_audience)
        if target_audience_dict != []:
            return target_audience_dict


def item_not_list(item):
    if item not in ['firstName', 'lastName', 'email', 'phone', 'organization', "id", 'track', 'isFeatured', 'tags',
                    'targetAudience', 'startDate', 'endDate', 'location']:
        return True
    else:
        return False

def group_subevents_search(search_string, admin_group_ids):
    results = list()
    list_queries = list()
    try:
        queries_returned = group_text_index_search(current_app.config['EVENT_COLLECTION'], search_string, admin_group_ids)
        list_queries = list(queries_returned)
        for query in list_queries:
            if ('isSuperEvent' in query and True == query['isSuperEvent']) or 'superEventID' in query:
                continue
            query['label'] = query.pop('title')
            if 'platformEventId' in query:
                query['value'] = query.pop('platformEventId')
            if '_id' in query:
                query['eventId'] = str(query.pop('_id'))
            query['status'] = query.pop('eventStatus')
            results.append(query)
    except:
        traceback.print_exc()
    return results

# Uses the implemented text index search to search the queries and modify the search results to JSON
def beta_search(search_string):
    results = list()
    try:
        queries_returned = text_index_search(current_app.config['EVENT_COLLECTION'], search_string)
        list_queries = list(queries_returned)
        for query in list_queries:
            if 'platformEventId' in query:
                query['label'] = query.pop('title')
                query['value'] = query.pop('platformEventId')
                results.append(query)
    except:
        traceback.print_exc()
    return results


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS


def clickable_utility(platformEventId):
    try:
        record = find_one(current_app.config['EVENT_COLLECTION'], condition={"platformEventId": platformEventId})
        if record:
            return record['eventId']
        else:
            __logger.error("Record with platformEventId:{} does not exist".format(platformEventId))

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Record with platformEventId:{} does not exist".format(platformEventId))
        return False


# S3 Utilities

# Initialization of global client
client = boto3.client('s3')


def s3_image_delete(localId, eventId, imageId):
    try:
        record = find_one(current_app.config['IMAGE_COLLECTION'], condition={"eventId": localId})
        if record:
            fileobj = '{}/{}/{}.jpg'.format(current_app.config['AWS_IMAGE_FOLDER_PREFIX'], eventId, imageId)
            client.delete_object(Bucket=current_app.config['BUCKET'], Key=fileobj)
            __logger.info('Image: {} for event {} deletion off of s3 successful'.format(imageId, localId))
            return True
        else:
            __logger.error('Event: {} does not exist'.format(localId))
            return False

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Image: {} for event: {} deletion failed".format(imageId, localId))
        return False


def convert_bytes(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            # return f'{num:.1f} {x}'
            # Alternative return statement works with Python 3.5 and above
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def size_check(eventID):
    try:
        image_path = '{}/{}.png'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], eventId)

        if os.path.isfile(image_path):
            file_information = os.stat(image_path)
            return file_information.st_size
        else:
            __logger.error('Image associated with event: {} does not exist'.format(eventID))

    except Exception as ex:
        __logger.exception(ex)
        __logger.error('Unknown Error occurred')
        return False


def s3_image_upload(localId, eventId, imageId):
    image_location = ''
    success = False
    try:
        for extension in Config.ALLOWED_IMAGE_EXTENSIONS:
            if os.path.isfile('{}/{}.{}'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], localId, extension)):
                image_location = '{}/{}.{}'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], localId, extension)
                break
        if image_location == '':
            raise FileNotFoundError("Image for event {} not found".format(localId))
        # convert to jpg and save it
        with Image.open(image_location) as im:
            im.convert('RGB').save('{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], localId),
                                   quality=95)
        client.upload_file(
            '{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], localId),
            current_app.config['BUCKET'],
            '{}/{}/{}.jpg'.format(current_app.config['AWS_IMAGE_FOLDER_PREFIX'], eventId, imageId),
            ExtraArgs={
                'ACL': 'bucket-owner-full-control'
            }
        )
        success = True

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Upload image: {} for event {} failed".format(imageId, localId))
        success = False
    finally:
        if os.path.exists(image_location):
            os.remove(image_location)

        if os.path.exists('{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], localId)):
            os.remove('{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], localId))

        return success


def s3_image_download(localId, eventId, imageId):
    try:
        record = find_one(current_app.config['IMAGE_COLLECTION'], condition={"eventId": localId})
        if record:
            fileobj = '{}/{}/{}.jpg'.format(current_app.config['AWS_IMAGE_FOLDER_PREFIX'], eventId, imageId)
            tmpfolder = 'temp'
            if not os.path.isdir(tmpfolder):
                os.mkdir(tmpfolder)
            tmpfile = os.path.join(tmpfolder, localId + ".jpg")
            with open(tmpfile, 'wb') as f:
                client.download_fileobj(current_app.config['BUCKET'], fileobj, f)
                __logger.info('Image: {} for event {} download off of s3 successful'.format(imageId, eventId))
                return True

        else:
            __logger.error('Event: {} does not exist'.format(localId))
            return False

    except Exception as ex:
        __logger.exception(ex)
        deletefile(tmpfile)
        __logger.error("Image: {} for event: {} download failed".format(imageId, eventId))
        return False


def deletefile(tmpfile):
    try:
        if os.path.exists(tmpfile):
            os.remove(tmpfile)

    except Exception as ex:
        pass


def s3_delete_reupload(localId, eventId, imageId):
    try:
        record = find_one(current_app.config['IMAGE_COLLECTION'], condition={"eventId": localId})
        if record:
            s3_image_delete(localId, eventId, imageId)
            s3_image_upload(localId, eventId, imageId)
            return True
        else:
            __logger.error('Event: {} does not exist'.format(localId))
            return False

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Image: {} for event: {} reupload edit failed".format(imageId, eventId))
        return False


def imagedId_from_eventId(eventId):
    try:
        record = find_one(current_app.config['IMAGE_COLLECTION'], condition={"eventId": eventId})
        if record:
            return record['eventId']
        else:
            __logger.error('Event: {} does not have associated image'.format(eventId))
            return False

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("imageId retrieval for event: {} failed".format(eventId))
        return False


def update_super_event_by_platform_id(sub_event_id, super_event_id):
    try:
        sub_event_id = find_one(current_app.config['EVENT_COLLECTION'],
                                condition={"platformEventId": sub_event_id})['_id']
        if super_event_id == "":
            updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                                      condition={'_id': ObjectId(sub_event_id)},
                                      update={"$unset": {'superEventID': 1}}, upsert=True)
        else:
            updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                                      condition={'_id': ObjectId(sub_event_id)},
                                      update={"$set": {'superEventID': super_event_id}}, upsert=True)

        if updateResult.modified_count == 0 and updateResult.matched_count == 0 and updateResult.upserted_id is None:
            __logger.error("Failed to mark {} as {}'s super event".format(super_event_id, sub_event_id))
            return False
        else:
            return True

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Failed to mark {} as {}'s super event".format(super_event_id, sub_event_id))
        return False

def update_super_event_by_local_id(sub_eventid, super_event_id):
    sub_event_id = None
    try:
        sub_event_id = find_one(current_app.config['EVENT_COLLECTION'],
                                condition={"_id": ObjectId(sub_eventid)})['_id']
        if super_event_id == "":
            updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                                      condition={'_id': ObjectId(sub_event_id)},
                                      update={"$unset": {'superEventID': 1}}, upsert=True)
        else:
            updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                                      condition={'_id': ObjectId(sub_event_id)},
                                      update={"$set": {'superEventID': super_event_id}}, upsert=True)
        if updateResult.modified_count == 0 and updateResult.matched_count == 0 and updateResult.upserted_id is None:
            __logger.error("Failed to mark {} as {}'s super event".format(super_event_id, sub_event_id))
            return False
        else:
            return True
    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Failed to mark {} as {}'s super event".format(super_event_id, sub_event_id))
        return False

def s3_publish_user_image(id, eventId, client):
    image_location = ''
    try:
        record = find_one(current_app.config['IMAGE_COLLECTION'], condition={"eventId": id})
        for extension in Config.ALLOWED_IMAGE_EXTENSIONS:
            if os.path.isfile('{}/{}.{}'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], id, extension)):
                image_location = '{}/{}.{}'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], id, extension)
                break
        if image_location == '':
            raise FileNotFoundError("Image for event {} not found".format(id))
        # convert to jpg and save it
        with Image.open(image_location) as im:
            im.convert('RGB').save('{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], id),
                                    quality=95)


        # if there is no record before, insert it to get the id
        if not record:
            insertResult = insert_one(current_app.config['IMAGE_COLLECTION'], document={
                'eventId': id
            })
            if insertResult.inserted_id:
                imageId = str(insertResult.inserted_id)
            else:
                return None
        else:
            imageId = str(record['_id'])


        client.upload_file(
            '{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], id),
            current_app.config['BUCKET'],
            '{}/{}/{}.jpg'.format(current_app.config['AWS_IMAGE_FOLDER_PREFIX'], eventId, imageId),
            ExtraArgs={
                'ACL': 'bucket-owner-full-control'
            }
        )

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Upload image for event {} failed".format(id))
        return None

    finally:
        if os.path.exists(image_location):
            os.remove(image_location)

        if os.path.exists('{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], id)):
            os.remove('{}/{}.jpg'.format(current_app.config['WEBTOOL_IMAGE_MOUNT_POINT'], id))

    return imageId

# Get only groups  user is an admin of
def get_admin_groups():
    # Retrieve UIN form session
    uin = session["uin"]
    #  Build request
    url = "%sint/user/%s/groups" % (current_app.config['GROUPS_BUILDING_BLOCK_BASE_URL'], uin)
    headers = {"Content-Type": "application/json", "INTERNAL-API-KEY": current_app.config['INTERNAL_API_KEY']}
    req = requests.get(url, headers=headers)
    group_info = list()
    # Parse Results
    if req.status_code == 200:
        req_data = req.json()
        for item in req_data:
            if item["membership_status"] == "admin":
                group_info.append(item)
    # Return list of groups for specified UIN
    return group_info, req.status_code


# Get group ids for groups user is an admin of
def get_admin_group_ids():
    return ["test"]
    group_info, status_code = get_admin_groups()
    if (status_code == 200):
        group_ids = list()
        for group in group_info:
            group_ids.append(group["id"])
        return group_ids
    else:
        __logger.error("Groups not retrievable")
        return []

# update part of the existing subevents in the given super event with the overwrite_subevent_list
def overwrite_subevents_to_superevent(overwrite_subevent_list, super_eventid):
    try:
        record = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)})
        if record:
            subEvents = record['subEvents']
            if subEvents:
                for overwrite_subevent in overwrite_subevent_list:
                    for i in range(len(subEvents)):
                        subevent = subEvents[i]
                        # published event
                        if 'id' in subevent and 'id' in  overwrite_subevent and subevent['id'] == overwrite_subevent['id']:
                            subEvents[i] = overwrite_subevent
                        # pending event
                        elif 'eventId' in subevent and 'eventId' in  overwrite_subevent and subevent['eventId'] == overwrite_subevent['eventId']:
                            subEvents[i] = overwrite_subevent
            result = find_one_and_update(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)},
                                         update={
                                             "$set": {"subEvents": subEvents}
                                         })
        else:
            __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))
        return False

def store_pending_subevents_to_superevent(pending_subevents_list, super_eventid):
    try:
        record = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)})
        if record:
            published_subevent_list = list()
            subEvnts = record['subEvents']
            if subEvnts:
                for subevent in subEvnts:
                    if 'id' in subevent: # published
                        published_subevent_list.append(subevent)
            subevents_list = published_subevent_list + pending_subevents_list
            result = find_one_and_update(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)},
                                         update={
                                             "$set": {"subEvents": subevents_list}
                                         })
        else:
            __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))
        return False

def remove_subevent_from_superevent_by_event_id(subevent_id, super_eventid):
    try:
        record = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)})
        if record:
            subEvnts = record['subEvents']
            if subEvnts:
                for subevent in subEvnts:
                    if 'eventId' in subevent and subevent['eventId'] == subevent_id:
                        # remove it
                        subEvnts.remove(subevent)
                        result = find_one_and_update(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)},
                                                     update={
                                                         "$set": {"subEvents": subEvnts}
                                                     })
                        break
        else:
            __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))
        return False

def remove_subevent_from_superevent_by_paltformid(subevent_platform_id, super_eventid):
    try:
        record = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)})
        if record:
            subEvnts = record['subEvents']
            if subEvnts:
                for subevent in subEvnts:
                    if 'id' in subevent and subevent['id'] == subevent_platform_id:
                        # remove it
                        subEvnts.remove(subevent)
                        result = find_one_and_update(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(super_eventid)},
                                                     update={
                                                         "$set": {"subEvents": subEvnts}
                                                     })
                        break
        else:
            __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))

    except Exception as ex:
        __logger.exception(ex)
        __logger.error("Record with platformEventId:{} does not exist".format(super_eventid))
        return False

def publish_pending_subevents(superEventID):
    subEvents = find_one(current_app.config['EVENT_COLLECTION'], condition={"_id": ObjectId(superEventID)})['subEvents']
    if subEvents == None:
        return
    for subEvent in subEvents:
        if subEvent.get('status') == 'pending' and 'eventId' in subEvent:
            try:
                image = False
                if len(glob.glob(os.path.join(Config.WEBTOOL_IMAGE_MOUNT_POINT, subEvent['eventId'] + '*'))) > 0:
                    image = True
                success = publish_user_event(subEvent['eventId'])
                if success and image:
                    updateResult = update_one(current_app.config['IMAGE_COLLECTION'],
                                              condition={'eventId': subEvent['eventId']},
                                              update={"$set": {'status': 'new',
                                                               'eventId': subEvent['eventId']}}, upsert=True)
                    if updateResult.modified_count == 0 and updateResult.matched_count == 0 and updateResult.upserted_id is None:
                        __logger.error(
                            "Failed to mark image record as new of event: {} upon event publishing".format(
                                subEvent['eventId']))
                    approve_user_event(subEvent['eventId'])
                if success:
                    subEvent['id'] = find_one(current_app.config['EVENT_COLLECTION'],
                                              condition={"_id": ObjectId(subEvent['eventId'])})['platformEventId']
                    subEvent['status'] = 'approved'
            except Exception as ex:
                __logger.exception(ex)
    updateResult = update_one(current_app.config['EVENT_COLLECTION'],
                              condition={"_id": ObjectId(superEventID)},
                              update={
                                  "$set": {"subEvents": subEvents}
                              })
    if updateResult.modified_count == 0 and updateResult.matched_count == 0 and updateResult.upserted_id is None:
        __logger.error(
            "Failed to update sub events list for {}".format(
                superEventID))
    return subEvents

def deduplicate_sub_events(subEvents):
    uniqueEventIdOfSubEvents = set()
    uniqueIdOfSubEvents = set()
    deduplicatedSubEvents = list()
    for subEvent in subEvents:
        if 'id' in subEvent:
            if subEvent['id'] not in uniqueIdOfSubEvents:
                deduplicatedSubEvents.append(subEvent)
                uniqueIdOfSubEvents.add(subEvent['id'])
        elif 'eventId' in subEvent:
            if subEvent['eventId'] not in uniqueEventIdOfSubEvents:
                deduplicatedSubEvents.append(subEvent)
                uniqueEventIdOfSubEvents.add(subEvent['eventId'])
    return deduplicatedSubEvents
