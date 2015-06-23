#!/usr/bin/env python
import os
from app.app import app
from app.models import bgp_updates, adv_routes, bgp_peers, bgp_config
from app.tasks import build_config_file
from flask.ext.script import Manager, Shell, Command
from subprocess import check_output

# app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)

def init_config():

	python_path = check_output(['which', 'python']).strip()

	root_path = os.path.abspath(os.curdir)
	config_path = os.path.join(root_path, 'etc', 'conf.ini')

	config = {
		'local-as': 65000,
		'router-id': '127.0.0.1',
		'local-address': '127.0.0.1',
		'state': 'stopped',
		'last_start': None,
		'last_stop': None,
		'python-path': python_path,
		'root-path': root_path,
		'config-path': config_path
	}

	print config # debug

	bgp_config.remove()
	bgp_config.insert_one(config)

if not bgp_config.find_one():
	print 'No config found, initializing config file.'
	init_config()

class InitConfig(Command):
	"Initializes default config settings"

	def run(self):
		init_config()
manager.add_command("init_config", InitConfig())

def make_shell_context():
	return dict(app=app, bgp_updates=bgp_updates, adv_routes=adv_routes, bgp_peers=bgp_peers, bgp_config=bgp_config)
manager.add_command("shell", Shell(make_context=make_shell_context))

class BuildConfig(Command):
    "Builds config file"

    def run(self):
        build_config_file(bgp_config.find_one(), list(bgp_peers.find()))
manager.add_command("build_config", BuildConfig())

if __name__ == '__main__': 
	manager.run()