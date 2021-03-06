from flask import Blueprint, jsonify, request, g
from backend.api.models import *
from backend.server import db
from backend.api.decorators import check_private_room
from flask_cors import CORS

server_blueprint = Blueprint('server', __name__)
CORS(server_blueprint)

@server_blueprint.route('/')
def index():
    return jsonify({'working': True})


@server_blueprint.route('/tables/create_new', methods=['POST'])
def create_table():
    """
        creates a new user group

        INPUT:
            takes json post request in format of
                {
                    'roomName': roomName,
                    'private': True or False,
                    'password': password if private
                }
        OUTPUT:
            {
                'status': 'success' or 'error'
                'url': encoded url (to be used for accessing)
            }

        NOTE:
            name of room must be greater than 4 chars (4 is arbitary)
    """

    data = request.get_json()
    # check if data is valid
    if not data['roomName'] or len(data['roomName']) < 4:
        return jsonify({'status': 'error', 'message': 'invalid room name'}), 400
    # check if room exists done on database

    new_room = Room(data['roomName'])
    db.session.add(new_room)
    db.session.commit()

    if data['private']:
        new_room.private = True
        new_room.password = data['password']
        db.session.commit()

    response = {'status': 'success', 'url': new_room.encoded_room_name}
    return jsonify(response)

@server_blueprint.route('/tables/fetch', methods=['POST'])
@check_private_room
def getTable():
    """
        Gets based on encoded_room_name and returns table info

        INPUT: (checked for validity by check_private_room decorator)
            request.json = {
                'requestedRoom': Encoded room name,
                'password': None (if not a private room) otherwise password
            }
            passes on requested room via global context variable from decorator

        OUTPUT:
            json response {
                'status':
                'message':
                'roomInfo':{
                    'roomName':
                    'date_created':
                    'private':
                    'items': [
                        {
                            'name':
                            'description':
                            'who_owns':
                            'who_has_current':
                            'how_long_can_borrow':
                            'due_back':
                            'date_posted':
                            'history': [{
                                id:
                                who_borrowed:
                                date_borrowed:
                                due_back:
                                returned:
                                date_returned:
                                notes:
                            }...]
                        },
                    ...]
                }
            }
    """

    requested_room = g.room

    return jsonify({
        'status': 'success',
        'message': 'here is the info you requested',
        'roomInfo': requested_room.get_items()
    })

@server_blueprint.route('/tables/modify/delete-item')
@check_private_room
def delete_record():
    """
        Deletes record (not hooked up at the moment)

        INPUT:
            json in request
            {
                requestedRoom:
                password:
                action: {
                    type: delete,
                    target: item or room or borrowHistory
                    targetId: targetid
                }
            }
    """
    requested_room = g.room
    data = request.get_json()
    pass

@server_blueprint.route('/tables/modify/update', methods=['POST'])
@check_private_room
def update_record():
    """
        Updates an already existing item, room, or borrowHistory

        INPUT: request with json
            {
                requestedRoom:
                password:
                action: {
                    type: update,
                    target: item or room or borrowHistory
                    targetId: targetid
                    dataToUpdate: {column: newVal, column2: newVal...}
                }
            }
        OUTPUT:
            {
                'status': success or error
                'message': reason for error or success
            }
    """
    requested_room = g.room
    data = request.get_json()

    info = data.get('action')
    if not info:
        return jsonify({
            'status': 'error',
            'message': 'no action supplied'
        }), 400

    if info['type'] != 'update':
        return jsonify({
            'status': 'error',
            'message': 'invalid action type for endpoint'
        }), 400
    target_dict = {
        'item': Item,
        'room': Room,
        'borrowHistory': BorrowHistory
    }
    try:
        target_id = int(info['targetId'])
        target = target_dict[info['target']]
    except KeyError:
        return jsonify({
            'status': 'error',
            'message': 'unknown key'
        }), 400
    try:
        check = db.session.query(target).filter(target.id == target_id).update(
                {getattr(target, k): v for k,v in info['dataToUpdate'].items()})
    except AttributeError:
        return jsonify({
            'status': 'error',
            'message': 'invalid columns for this update'
        }), 400

    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': 'data modified successfully',
        'dbresponse': check
    })

@server_blueprint.route('/tables/modify/create', methods=['POST'])
@check_private_room
def create_item():
    """
        creates a new item

        INPUT:
            request with json
            {
                requestedRoom:
                password:
                action: {
                    type: create,
                    target: item,
                    name:
                    who_owns:
                    optional_fields: {
                        description:
                        who_has_current:
                        how_long_can_borrow:
                        due_back:
                    }
                }
            }
        OUTPUT:
            {
                'status': success or error
                'message': reason for success or error
            }
    """

    room = g.room
    data = request.get_json()
    info = data.get('action')
    response = {
        'status': 'error',
        'message': 'Something went wrong'
    }

    if info is None or info.get('type') != 'create':
        response['message'] = 'Wrong request data'
        return jsonify(response), 400
    if len(info.get('name')) < 2 or info.get('who_owns') is None:
        response['message'] = 'name of new item is too short or data is wrong'
        return jsonify(response), 400

    new_item = Item(room, info.get('name'), info.get('who_owns'))
    db.session.add(new_item)
    db.session.commit()


    if (info.get('optional_fields') is not None
        and len(info['optional_fields']) > 0):

        check = db.session.query(Item).filter(Item.id == new_item.id).update(
                {getattr(Item, k): v for k,v in info['optional_fields'].items()})

        db.session.commit()
    else:
        check = 1


    if check == 1:
        response['status'] = 'success'
        response['message'] = f'Item added to {room.room_name}'
        return jsonify(response)
    else:
        response['message'] = 'error adding item to database'
        return jsonify(response), 400

@server_blueprint.route('/test/check-decorator')
@check_private_room
def testDecorator():
    """
        Function to test check_private_room decorator
    """
    requested_room = g.room
    return jsonify({
        'status': 'success',
        'message': 'greetings from testDecorator function',
        'requestedRoomName': requested_room.room_name
    })
