#!/usr/bin/env python

from bottle import request, response, Bottle, run
from lib import redis_helper
from uuid import uuid4
import time
import json
import settings

app = Bottle()


def raise_error(error_code, msg):
    response.status = error_code
    return json.dumps({'message': msg})


@app.post('/job')
def create_job():
    uuid = str(uuid4())
    timestamp = str(time.mktime(time.gmtime()))
    response.content_type = 'application/json'

    try:
        payload = json.load(request.body)
    except:
        return raise_error(400, 'Invalid JSON payload.')

    ip = payload.get('ip')
    role = payload.get('role').lower()
    username = payload.get('username')
    password = payload.get('password')
    extra_vars = payload.get('extra_vars', {})
    only_tags = payload.get('only_tags', 'all')

    if not (ip and role and username and password):
        return raise_error(400, 'Missing one of the required arguments.')

    if role not in (settings.MODULES + settings.PLAYBOOKS):
        return raise_error(400, 'Invalid role.')

    # Weave role handler
    if role == 'weave':
        if not extra_vars:
            return raise_error(400, 'extra_vars are required when using the role weave.')

        extra_vars['is_master'] = extra_vars.get('is_master', False)
        extra_vars['is_slave'] = extra_vars.get('is_slave', False)

        # Must be either master or slave
        if not (extra_vars['is_master'] or extra_vars['is_slave']):
            return raise_error(400, 'Must be either master or slave when using role weave.')

        # A passphrase must always be supplied.
        if not extra_vars.get('passphrase'):
            return raise_error(400, 'A passphrase is always required when using role weave.')

        # If the role is a slave, the master IP and passphrase is required.
        if extra_vars['is_slave'] and not extra_vars.get('master_ip'):
            return raise_error(400, 'master_ip is required when setting up a weave slave node.')

    # NodeBB role handler
    if role == 'nodebb':
        if not extra_vars:
            return raise_error(400, 'extra_vars are required when using the role nodebb.')

        # A secret must always be supplied.
        if not extra_vars.get('secret'):
            return raise_error(400, 'A secret is always required when using role nodebb.')

        extra_vars['is_master'] = extra_vars.get('is_master', False)

    if only_tags:
        only_tags = only_tags.split(',')

    redis_helper.create_status(uuid, role, ip)
    task = redis_helper.add_to_queue({
        'created_at': timestamp,
        'last_update': None,
        'role': role,
        'ip': ip,
        'username': username,
        'password': password,
        'uuid': uuid,
        'attempts': 0,
        'extra_vars': extra_vars,
        'only_tags': only_tags,
    })

    if task:
        response.status = 201
        return uuid
    else:
        return raise_error(500, 'Unable to process request.')


@app.route('/job/<uuid>')
def get_job_status(uuid):
    response.content_type = 'application/json'
    if uuid:
        job_query = redis_helper.get_status(uuid)
        if job_query:
            return job_query
        else:
            return raise_error(404, 'Job not found.')
    else:
        print 'No job specified.'
        return raise_error(400, 'No job specified.')


@app.delete('/job/<uuid>')
def abort_job(uuid):
    response.content_type = 'application/json'
    if uuid:
        abort_task = redis_helper.update_status(
            uuid=uuid,
            status='Aborted'
        )
        if abort_task:
            response.status = 204
        else:
            return raise_error(500, 'Unable to delete task.')
    else:
        print 'No job specified.'
        return raise_error(400, 'No job specified.')


@app.route('/roles')
def get_roles():
    response.content_type = 'application/json'
    return json.dumps(settings.SINGLE_HOST_PLAYBOOKS)


@app.route('/redis_status')
def get_redis_status():
    response.content_type = 'application/json'
    return redis_helper.get_redis_status()


@app.route('/')
def root():
    return 'Nothing to see here. Carry on.\n'

run(app, host='0.0.0.0', port=8080, server='gunicorn', workers=4, reload=True)
