from bson.objectid import ObjectId
from time import mktime
from datetime import datetime, timedelta
from flask import Flask, request, render_template, flash
from flask_bootstrap import Bootstrap
from sys import stdout
from pymongo import ASCENDING, DESCENDING
from models import db, bgp_updates, bgp_peers

app = Flask(__name__)
Bootstrap(app)

def minutes_ago(minutes):

	return datetime.utcnow() - timedelta(minutes=minutes)

@app.route('/')
def dashboard():

	updates = [x for x in bgp_updates.find({'type': { '$nin': ['keepalive', 'state']}}).sort('time', DESCENDING).limit(10)]
	peers = [x for x in bgp_peers.find()]

	return render_template('dashboard.html', updates=updates, peers=peers)

# @app.route('/peer/<peer_id>')
# def peer(peer_id):

# 	peer = bgp_peers.find_one({'_id': peer_id})
# 	state
# 	last_updates


@app.route('/command', methods=['POST'])
def command():

	command = request.form['command']
	stdout.write( command + '\n')
	stdout.flush()

	return command + '\n'

if __name__ == '__main__':
    app.run(debug=True)

