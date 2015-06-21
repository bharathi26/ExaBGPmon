#!/usr/bin/env python

import os
import sys
import json
from datetime import datetime
import time
from pymongo import MongoClient

#### Syslog
import syslog

def _prefixed (level, message):
	now = time.strftime('%a, %d %b %Y %H:%M:%S',time.localtime())
	return "%s %-8s %-6d %s" % (now,level,os.getpid(),message)

syslog.openlog("ExaBGP")



client = MongoClient()
db = client.exabgp_db
updates = db.bgp_updates
bgp_peers = db.bgp_peers

# When the parent dies we are seeing continual newlines, so we only access so many before stopping
counter = 0

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
			# syslog.syslog(syslog.LOG_ALERT, _prefixed('INFO', 'Peer: %s, Update EoR' % temp_message['neighbor']['ip']))
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
			                    prefix_list.append(prefix)
			        announce[family] = prefix_list
			        update['announce'] = announce
			    elif section == 'withdraw':
			        withdraw = {}
			        for family, peer in info.iteritems():
			            prefix_list = []
			            for prefix, value in peer.iteritems():
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

		bgp_peers.update_one({'ip': message['peer']}, {'$set': {'state': message['state']}})

		if message['state'] in ('up', 'connected'):
			return message

		try:
			if 'closed by the remote end' in temp_message['neighbor']['reason']:
				message['reason'] = 'Peer closed connection'
			else:
				message['reason'] = temp_message['neighbor']['reason']
		except KeyError:
			syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', temp_message))

		return message

	else:
		return None

while True:
	try:
		line = sys.stdin.readline().strip()
		if line == "":
			counter += 1
			if counter > 100:
				break
			continue

		counter = 0
		
		message = object_formatter(line)

		if message:
			syslog.syslog(syslog.LOG_ALERT, _prefixed('INFO', message))
			try:
				updates.insert_one(message)
			except:
				syslog.syslog(syslog.LOG_ALERT, _prefixed('DEBUG', message))
		# else:
		# 	syslog.syslog(syslog.LOG_ALERT, _prefixed('WARNING', line))

	except KeyboardInterrupt:
		pass
	except IOError:
		# most likely a signal during readline
		pass

client.close()

# updates.find_one({'type':'state' })
# updates.find_one({'neighbor.address.peer':'172.16.2.20'})
# updates.find_one({'neighbor.address.peer':'172.16.2.10'})

# List all updates (can filter too)
# [x for x in updates.find()]
# updates.find_one({'type':'update' })

# Timestamp to datetime
# test = updates.find_one({'type':'update' })
# datetime.datetime.fromtimestamp(test['time'])


#https://groups.google.com/forum/#!msg/exabgp-users/OKUwwxEmBgI/2dsXGEwVNqkJ
# mkdir logs
# touch logs/exabgp.log
# chmod 755 logs/
# sudo chown root:nogroup logs