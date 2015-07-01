#!/usr/bin/env python

import json
import os
from sys import stdin, stdout
import time
from datetime import datetime
from pymongo import MongoClient
from tasks import announce_route, withdraw_route

########################################
###### Syslog for Troubleshooting ######
########################################
import syslog

def _prefixed (level, message):
    now = time.strftime('%a, %d %b %Y %H:%M:%S',time.localtime())
    return "%s %-8s %-6d %s" % (now,level,os.getpid(),message)

syslog.openlog("ExaBGP")

########################################
##############  DB Setup ###############
########################################
#This can possibly be imported from models
#I'm not sure yet as it might be good to keep it separate with the ExaBGP process
client = MongoClient()
db = client.exabgp_db
updates = db.bgp_updates
bgp_peers = db.bgp_peers
adv_routes = db.adv_routes
bgp_config = db.bgp_config

def update_state(state):

    # Update ExaBGP state and last_start
    current_config = bgp_config.find_one()
    if state == 'running':
        bgp_config.update(current_config, {'$set': {'state': 'running', 'last_start': datetime.now()}})
    else:
        bgp_config.update(current_config, {'$set': {'state': state, 'last_stop': datetime.now()}})

update_state('running')

def object_formatter(line):
    temp_message = json.loads(line)

    try:
        timestamp = datetime.fromtimestamp(temp_message['time'])
    except Exception as e:
        syslog.syslog(syslog.LOG_ALERT, _prefixed('ERROR', 'Peer: %s, %s' % (temp_message['neighbor']['ip'], e.message)))
        return None

    if temp_message['type'] == 'update':
        
        #Ignore EoR updates
        if temp_message['neighbor']['message'].get("eor", None):
            return None

        try:
            message = {
                'type': 'update',
                'time': timestamp,
                'peer': temp_message['neighbor']['ip'],
            }
            
            # Get rid of IP address keys, use list prefixes instead
            update = {}
            for section, info in temp_message['neighbor']['message']['update'].iteritems():
                if section == 'attribute':
                    update['attribute'] = info

                elif section == 'announce':
                    announce = {}
                    for family, peer in info.iteritems():
                        prefix_list = []
                        for peer_adv in peer.values():
                            for prefix in peer_adv:
                                # Add to peer list of current prefixes
                                bgp_peers.update_one({'ip': message['peer']}, {'$addToSet': {'current_prefixes': prefix}})
                                
                                prefix_list.append(prefix)
                    announce[family] = prefix_list
                    update['announce'] = announce

                elif section == 'withdraw':
                    syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', temp_message))
                    withdraw = {}
                    for family, peer in info.iteritems():
                        prefix_list = []
                        for prefix in peer:
                            # Remove from peer list of current prefixes
                            bgp_peers.update_one({'ip': message['peer']}, {'$pull': {'current_prefixes': prefix}})

                            prefix_list.append(prefix)
                    withdraw[family] = prefix_list
                    update['withdraw'] = withdraw

            message['update'] = update


            return message

        except KeyError:
            syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', line))



    if temp_message['type'] == 'keepalive':
        message = {
            'type': 'keepalive',
            'time': timestamp,
            'peer': temp_message['neighbor']['ip'],
        }

        return message

    if temp_message['type'] == 'state':
        message = {
            'type': 'state',
            'time': timestamp,
            'peer': temp_message['neighbor']['ip'],
            'state': temp_message['neighbor']['state'],
        }

        if message['state'] in ('up'):
            # Check if peer was previously down. If so, re-advertise routes
            peer = bgp_peers.find_one({'ip': message['peer']})
            if peer['state'] != 'up':
                for route in adv_routes.find({'peer': peer['ip']}):
                    # announce_route(peer, route)
                    announcement =  'neighbor %s announce route %s next-hop %s' % (
                        peer['ip'], route['prefix'], route['attributes']['next-hop'])
                    stdout.write( announcement + '\n')
                    stdout.flush()

            # Change state to up from down or connected
            bgp_peers.update_one({'ip': message['peer']}, {'$set': {'state': message['state']}})

            return message
        else:
            bgp_peers.update_one({'ip': message['peer']}, {'$set': {'state': message['state']}})

        try:
            if 'closed by the remote end' in temp_message['neighbor']['reason']:
                message['reason'] = 'Peer closed connection'
            else:
                message['reason'] = temp_message['neighbor']['reason']
        except KeyError:
            syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', temp_message))

        return message

    if temp_message['type'] == 'notification':
        if temp_message['notification'] == 'shutdown':
            for peer in bgp_peers.find():
                # Mark peers as offline
                bgp_peers.update({'ip': peer['ip']}, { '$set': {'state': 'down'}})

                update_state('stopped')

        return None

    else:
        syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', temp_message))
        return None

counter = 0
while True:
    try:
        line = stdin.readline().strip()
        
        # When the parent dies we are seeing continual newlines, so we only access so many before stopping
        if line == "":
            counter += 1
            if counter > 100:
                break
            continue

        counter = 0
        
        message = object_formatter(line)

        if message:
            try:
                updates.insert_one(message)
            except:
                syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', message))

    except KeyboardInterrupt:
        client.close()
    except IOError:
        # most likely a signal during readline
        pass