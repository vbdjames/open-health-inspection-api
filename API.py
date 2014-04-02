import mongolab
import json
import re
from bson.objectid import ObjectId
from flask import Flask, Response, url_for, request, current_app
from functools import wraps


app = Flask(__name__)


try:
    db = mongolab.connect()
except ValueError:
    print "Could not connect to database"


def support_jsonp(f):
    """Wraps JSONified output for JSONP"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        callback = request.args.get('callback', False)
        if callback:
            content = str(callback) + '(' + str(f(*args, **kwargs)) + ')'
            return current_app.response_class(content, mimetype='application/json')
        else:
            return Response(f(*args, **kwargs), mimetype='application/json')
    return decorated_function


@app.route('/')
@support_jsonp
def api_root():
    links = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            links.append(rule.rule)
    return json.dumps(links)


@app.route('/vendors')
@support_jsonp
def api_vendors():
    data = db.va.find({}, {'name': 1,
                           'address': 1,
                           'geo.coordinates': 1})
    if data.count() == 0:
        resp = json.dumps({'status': '204', 'message': 'no results returned'})
    else:
        vendor_list = {}
        for item in data:
            url = url_for('api_vendor', vendorid=str(item['_id']))
            vendor_list[str(item['_id'])] = {'url': url,
                                             'name': item['name'],
                                             'address': item['address'],
                                             'coordinates': {
                                                 'latitude': item['geo']['coordinates'][0],
                                                 'longitude': item['geo']['coordinates'][1]}}
        resp = json.dumps(vendor_list)
    return resp


@app.route('/vendors/textsearch/<searchstring>')
@support_jsonp
def api_vendor_text_search(searchstring):
    regex = re.compile(re.escape(searchstring), re.IGNORECASE)
    data = db.va.find({'$or':
                            [{'name': regex},
                             {'address': regex},
                             {'city': regex}]},
                      {'name': 1,
                       'address': 1,
                       'geo.coordinates': 1})
    if data.count() == 0:
        resp = json.dumps({'status': '204', 'message': 'no results returned'})
    else:
        vendor_list = {}
        for item in data:
            url = url_for('api_vendor', vendorid=item['_id'])
            vendor_list[str(item['_id'])] = {'url': url,
                                             'name': item['name'],
                                             'address': item['address'],
                                             'coordinates': {
                                                 'latitude': item['geo']['coordinates'][0],
                                                 'longitude': item['geo']['coordinates'][1]}}
        resp = json.dumps(vendor_list)
    return resp


@app.route('/vendors/geosearch/<lng>/<lat>/<dist>')
@support_jsonp
def api_vendor_geo_search(lng, lat, dist):
    data = db.va.find({'geo':
                           {'$near':
                                {'$geometry':
                                     {'type': "Point",
                                      'coordinates': [ float(lng), float(lat)]},
                                 '$maxDistance': int(dist)}}},
                      {'name': 1,
                       'address': 1,
                       'geo.coordinates': 1})
    if data.count() == 0:
        resp = json.dumps({'status': '204', 'message': 'no results returned'})
    else:
        vendors = {}
        for item in data:
            url = url_for('api_vendor', vendorid=str(item['_id']))
            vendors[str(item['_id'])] = {'url': url,
                                         'name': item['name'],
                                         'address': item['address'],
                                         'coordinates': {
                                                 'latitude': item['geo']['coordinates'][0],
                                                 'longitude': item['geo']['coordinates'][1]}}
        resp = json.dumps(vendors)
    return resp


@app.route('/vendor/<vendorid>')
@support_jsonp
def api_vendor(vendorid):
    data = db.va.find({'_id': ObjectId(vendorid)}, {'name': 1,
                                                    'address': 1,
                                                    'inspections.0': {'$slice': 1},
                                                    'geo.coordinates': 1}).sort('inspection.date')
    if data.count() == 1:
        item = data[0]
        inspection = item['inspections'][0]
        vendor = {str(item['_id']): {'name': item['name'],
                                     'address': item['address'],
                                     'last_inspection_date': inspection['date'],
                                     'violations': inspection["violations"],
                                     'coordinates': {
                                                 'latitude': item['geo']['coordinates'][0],
                                                 'longitude': item['geo']['coordinates'][1]}}}
        resp = json.dumps(vendor)
    elif data.count() > 1:
        resp = json.dumps({'status': '300'})
    else:
        resp = json.dumps({'status': '204'})
    return resp


@app.route('/inspections/<vendorid>')
@support_jsonp
def api_inspections(vendorid):
    data = db.va.find({'_id': ObjectId(vendorid)}, {'name': 1, 'address': 1,
                                                    'last_inspection_date': 1,
                                                    'inspections': 1,
                                                    'geo.coordinates': 1})
    if data.count() == 1:
        vendor = {str(data[0]["_id"]): {'name': data[0]['name'],
                                        'address': data[0]['address'],
                                        'last_inspection_date': data[0]['last_inspection_date'],
                                        'inspections': data[0]['inspections'],
                                        'coordinates': {
                                                 'latitude': data[0]['geo']['coordinates'][0],
                                                 'longitude': data[0]['geo']['coordinates'][1]}}}
        resp = json.dumps(vendor)
    elif data.count() > 1:
        resp = json.dumps({'status': '300'})
    else:
        resp = json.dumps({'status': '204'})
    return resp


if __name__ == '__main__':
    app.run()