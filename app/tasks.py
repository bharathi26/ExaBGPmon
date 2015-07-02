import os
from jinja2 import Environment, FileSystemLoader
from requests import post
from sys import stdout
from subprocess import check_output

def build_config_file(config, peers):
	""" This function uses the bgp_config collection to populate the conf.tpl template.
	An ExaBGP file will be created that will launch the logtodb and http-api processes.

	"""
	temp_path = os.path.join(os.path.abspath(os.curdir), 'etc')
	j2_env = Environment(loader=FileSystemLoader(os.path.join(temp_path)))

	config_file = j2_env.get_template('conf.tpl').render(config=config, peers=peers)

	with open(os.path.join(temp_path, 'conf.ini'), 'w') as ini_file:
		ini_file.write(config_file)
	
	print 'Created config file: %s' % os.path.join(temp_path, 'conf.ini')

def announce_route(peer, adv_route):
	message =  'neighbor %s announce route %s next-hop %s' % (
		peer['ip'], adv_route['prefix'], adv_route['attributes']['next-hop'])

	r = post('http://localhost:5001', {'command': message})

def withdraw_route(peer, adv_route):
	message =  'neighbor %s withdraw route %s next-hop %s' % (
		peer['ip'], adv_route['prefix'], adv_route['attributes']['next-hop'])
	
	r = post('http://localhost:5001', {'command': message})

def is_exabgp_running():
	""" This function checks if the exabgp process is running. """

	r = check_output(['supervisorctl', 'status'])

	if 'RUNNING' in r:
		return True
	else:
		return False

def exabpg_process(action):
	""" This function will check that supervisord is running and then start 
	exabgp using the exabgpmon.conf file included with exabgpmon.

	"""
	# Start supervisord (if already running we'll just see a help message
	if action == 'start':
		pass
		# check_output(['supervisord'])

	# Make a subprocess call if it's to start/stop the service
	if action in ('start', 'stop', 'restart'):
		# Start exabgp process and check output
		r = check_output(['supervisorctl', action, 'exabgp'])
		print r
		return r

	# Make a call to HTTP API to reload the ExaBGP config
	if action == 'reload':
		r = post('http://localhost:5001', {'command': 'reload'})
		return r.text

	return 'Not a valid action (stop, stop, restart, reload).'