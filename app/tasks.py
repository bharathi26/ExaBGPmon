import os
from requests import post
from sys import stdout
from jinja2 import Environment, FileSystemLoader

def build_config_file(config, peers):
	""" This function uses the bgp_config collection to populate the conf.tpl template.
	An ExaBGP file will be created that will launch the logtodb and http-api processes.

	"""
	temp_path = os.path.join(os.path.abspath(os.curdir), 'etc')
	print temp_path
	j2_env = Environment(loader=FileSystemLoader(os.path.join(temp_path)))

	config_file = j2_env.get_template('conf.tpl').render(config=config, peers=peers)

	with open(os.path.join(temp_path, 'conf.ini'), 'w') as ini_file:
		ini_file.write(config_file)

def announce_route(peer, adv_route):
	message =  'neighbor %s announce route %s next-hop %s' % (
		peer['ip'], adv_route['prefix'], adv_route['attributes']['next-hop'])

	r = post('http://localhost:5001', {'command': message})

def withdraw_route(peer, adv_route):
	message =  'neighbor %s withdraw route %s next-hop %s' % (
		peer['ip'], adv_route['prefix'], adv_route['attributes']['next-hop'])
	
	r = post('http://localhost:5001', {'command': message})