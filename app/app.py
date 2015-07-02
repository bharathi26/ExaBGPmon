from bson.objectid import ObjectId
from time import mktime
from datetime import datetime, timedelta
from flask import Flask, request, render_template, flash, redirect, url_for, jsonify
from flask_bootstrap import Bootstrap
from sys import stdout
from pymongo import ASCENDING, DESCENDING
from config import Config
from models import db, bgp_updates, bgp_peers, adv_routes, bgp_config
from forms import AdvertiseRoute, ConfigForm
from tasks import announce_route, withdraw_route, exabpg_process, is_exabgp_running

app = Flask(__name__)
app.config.from_object(Config)
Bootstrap(app)

def datetimeformat(value, format='%c'):
    return value.strftime(format)
app.jinja_env.filters['datetimeformat'] = datetimeformat

def minutes_ago(minutes):

    return datetime.utcnow() - timedelta(minutes=minutes)

@app.route('/')
def dashboard():

    updates = [x for x in bgp_updates.find({'type': { '$nin': ['keepalive']}}).sort('time', DESCENDING).limit(10)]
    peers = list(bgp_peers.find())

    return render_template('dashboard.html', updates=updates, peers=peers)

@app.route('/peer/<peer_id>', methods=['GET', 'POST'])
def peer(peer_id):

    form = AdvertiseRoute()
    peer = bgp_peers.find_one({'_id': ObjectId(peer_id)})

    if form.validate_on_submit():
        # Check if route is already advertised to this peer
        if adv_routes.find_one({'peer': peer['ip'], 'prefix': form.prefix.data, 'next-hop': form.next_hop.data}):
            flash('%s is already being advertised to %s with a next-hop of %s.' % (
                form.prefix.data, peer.ip, form.next_hop.data), 'warning')

        # Create the advertised route object
        adv_route = {
            'prefix': form.prefix.data,
            'peer': peer['ip'],
            'attributes': {
                'origin': form.origin.data,
                'local-preference': form.local_pref.data,
                'med': form.med.data,
                'next-hop': form.next_hop.data
            }
        }

        adv_routes.insert_one(adv_route)
        announce_route(peer, adv_route)
        flash('%s has been announced to %s' % (adv_route['prefix'], peer['ip']), 'success')

        return redirect(url_for('peer', peer_id=peer_id))
    
    else:
        advertised_routes = adv_routes.find({'peer': peer['ip']})

        return render_template('peer_info.html', peer=peer, form=form, advertised_routes=advertised_routes)

@app.route('/peer/<peer_id>/withdraw/<adv_route_id>')
def delete_adv_route(peer_id, adv_route_id):

    peer = bgp_peers.find_one({'_id': ObjectId(peer_id)})
    adv_route = adv_routes.find_one({'_id': ObjectId(adv_route_id)})

    withdraw_route(peer, adv_route)
    adv_routes.remove({'_id': ObjectId(adv_route_id)}, 1)

    flash('%s has been withdrawn from %s.' % (adv_route['prefix'], peer['ip']), 'success')
    return redirect(url_for('peer', peer_id=peer_id))

@app.route('/config', methods=['GET', 'POST'])
def config():

    config_form = ConfigForm()
    
    if config_form.validate_on_submit():
        
        bgp_config.update(bgp_config.find_one(), 
            {'$set': {
                'local-as': int(config_form.asn.data),
                'router-id': config_form.router_id.data,
                'local-address': config_form.local_ip.data
            }
        })

        flash('Config successfully updated.', 'success')
        return redirect(url_for('config', _anchor='exabgp'))

    else:

        peers = list(bgp_peers.find())
        config = bgp_config.find_one()

        config_form.asn.data = config['local-as']
        config_form.router_id.data = config['router-id']
        config_form.local_ip.data = config['local-address']
        return render_template('config.html', peers=peers, config=config, config_form=config_form)

@app.route('/config/exabgp/<action>')
def config_action(action):

    result = exabpg_process(action)

    # Update ExaBGP state and last_start
    current_config = bgp_config.find_one()
    if action == 'stop':
        bgp_config.update(current_config, {'$set': {'state': 'stopped', 'last_stop': datetime.now()}})
    elif action == 'restart':
        bgp_config.update(current_config, {'$set': {'state': 'running', 'last_start': datetime.now(), 'last_stop': datetime.now()}})
    elif action == 'start':
        bgp_config.update(current_config, {'$set': {'state': 'running', 'last_start': datetime.now()}})

    return jsonify(result=result), 200

@app.route('/config/exabgp/status')
def exabgp_status():

    current_config = bgp_config.find_one()

    # Update database
    if is_exabgp_running():
        bgp_config.update(current_config, {'$set': {'state': 'running'}})
    else:
        bgp_config.update(current_config, {'$set': {'state': 'stopped'}})

    return jsonify(state=current_config['state'],
        last_start=current_config['last_start'],
        last_stop=current_config['last_stop'])

if __name__ == '__main__':
    app.run(debug=True)