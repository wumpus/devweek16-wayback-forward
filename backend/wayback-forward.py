#!/usr/bin/env python3

import os
import sys
import urllib.parse
import urllib.request
from operator import itemgetter
from internetarchive import get_item
import json
from bottle import route, request, response, run, static_file, redirect

reloader=True

def pick_collection(collections):
    for c in collections:
        if c.startswith('alexacrawls'):
            return c
        if c.startswith('survey'):
            return c
        if c.startswith('wide'):
            return c
        if c.startswith('shallow'):
            return c
        if c.startswith('sept11web'):
            return c
        if c.startswith('newscrawl'):
            return c
        if c.startswith('commoncrawl'):
            return c
        if c == 'wikipediaoutlinks':
            return c
        if c.startswith('webbase'):
            return c
        if c.startswith('awayfromkeyboard'):
            return c
        if c.startswith('NO404'):
            return c
        if c.startswith('archiveitpartners'):
            return c
        if c.startswith('archiveitdigitalcollection'):
            return c
        if c.startswith('archiveteam'):
            return c
        if c.startswith('liveweb'):
            return c
        if c.startswith('aroundtheworld'):
            return c

        # these are here to keep things silent
        if c.startswith('nsdlweb'):
            return None
        if c.startswith('customcrawlservices'):
            return None
        if c.startswith('accelovation'):
            return None
        if c.startswith('crawl_UNK'):
            return None

    print('returning none for', collections)
    return None

cdx_secret = ''
cdx_server = ''


# =========== Bottle stuff ======================

# Only open stuff if we are really going to serve queries
if os.environ.get('BOTTLE_CHILD') or not reloader:
    with open(os.path.expanduser('~/.cdx_secret'), 'r') as f:
        for line in f:
              cdx_secret = line.rstrip()
              break
              # Cookie:cdx_auth_token=cdx_secret

    with open(os.path.expanduser('~/.cdx_server'), 'r') as f:
        for line in f:
              cdx_server = line.rstrip()
              break

    cdx_server = os.environ.get('CDXSERVER', cdx_server) # let user override


@route('/')
def front_page():
    return static_file('index.html', root='../Frontend')

@route('/d3.v3.min.js')
def front_page():
    return static_file('d3.v3.min.js', root='../Frontend')

@route('/xmlreader.js')
def front_page():
    return static_file('xmlreader.js', root='../Frontend')

@route('/css/<filename>')
def server_static(filename):
    return static_file(filename, root='../Frontend/css')

@route('/src/<filename>')
def server_static(filename):
    return static_file(filename, root='../Frontend/src')

@route('/robots.txt')
def robots():
    return static_file('robots.txt', root='./static')

@route('/getinfo')
def getinfo():
    url = request.query.url # this is url-decoded already

    endpoint = 'http://' + cdx_server + '/web/timemap/cdx'
    endpoint += '?' + urllib.parse.urlencode({ 'url': url })

    req = urllib.request.Request(endpoint)
    req.add_header('Cookie', 'cdx_auth_token='+cdx_secret)

    with urllib.request.urlopen(req) as response:
        lines = response.read().decode('utf-8').splitlines()

    table = []

    for line in lines:
        fields = line.split(' ')
        date = fields[1]
        code = fields[4]
        sha1 = fields[5]
        item, filename = fields[10].split('/', maxsplit=1)

        row = { 'date': date, 'code': code, 'sha1': sha1, 'item': item }
        table.append(row)

    table = sorted(table, key=itemgetter('date'))

    item_to_collection = {}
    with open(os.path.expanduser('~/.item_to_collection'), 'r') as f:
        for line in f:
            [i, c] = line.rstrip().split(sep=' ', maxsplit=1)
            item_to_collection[i] = c

    i2c_changed = 0
    for row in table:
        if row['item'] not in item_to_collection:
            resp = get_item(row['item'])
            collections = resp.metadata.get('collection', [])
            collection = pick_collection(collections)
            if not collection:
                collection  = 'unknown'
            item_to_collection[row['item']] = collection
            i2c_changed = 1
        row['why'] = item_to_collection[row['item']]

    if i2c_changed:
        with open(os.path.expanduser('~/.item_to_collection.new'), 'w') as f:
            for k in item_to_collection:
                f.write(k + ' ' + item_to_collection[k] + '\n')

        os.rename(os.path.expanduser('~/.item_to_collection.new'), os.path.expanduser('~/.item_to_collection'))

    last_sha1 = ''
    for row in table:
        print('code is', row['code'])
        if row['code'] == '404':
            change = '404'
        elif row['code'].startswith('3'):
            change = 'redir'
        elif row['sha1'] != last_sha1:
            change = 'minor'
        else:
            change = 'none'
        row['change'] = change
        last_sha1 = row['sha1']

    captures = []
    for row in table:
        outrow = {}
        for k in ['date', 'why', 'change']:
            outrow[k] = row[k]
        captures.append(outrow)

    return { 'captures': captures }

run(host='0.0.0.0', port=8081, reloader=reloader)
