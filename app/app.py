from bson.objectid import ObjectId
from time import mktime
from datetime import datetime, timedelta
from flask import Flask, request, render_template, flash, redirect, url_for, jsonify
from flask_bootstrap import Bootstrap
from sys import stdout
from pymongo import ASCENDING, DESCENDING
from config import Config
from models import db, bgp_updates, bgp_peers, adv_routes, bgp_config
from forms import AdvertiseRoute, ConfigForm, BGPPeer
from tasks import announce_route, withdraw_route, exabpg_process, is_exabgp_running, send_exabgp_command, build_config_file
from requests import ConnectionError

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

    prefixes_out = adv_routes.distinct('prefix')
    prefixes_out_count = len(prefixes_out)
    prefixes_in = bgp_peers.distinct('current_prefixes')
    prefixes_in_count = len(prefixes_in)

    peers = list(bgp_peers.find())

    overview_counts = {
        'prefixes_out': prefixes_out,
        'prefixes_out_count': prefixes_out_count,
        'prefixes_out_count': prefixes_out_count,
        'prefixes_in' : prefixes_in,
        'prefixes_in_count': prefixes_in_count,
    }

    return render_template('dashboard.html', overview_counts=overview_counts, peers=peers)

@app.route('/peer/<peer_id>', methods=['GET', 'POST'])
def peer(peer_id):

    route_form = AdvertiseRoute()
    peer_form = BGPPeer()

    peer = bgp_peers.find_one({'_id': ObjectId(peer_id)})

    if route_form.validate_on_submit():
        # Check if route is already advertised to this peer
        if adv_routes.find_one({'peer': peer['ip'], 'prefix': route_form.prefix.data, 'next-hop': route_form.next_hop.data}):
            flash('%s is already being advertised to %s with a next-hop of %s.' % (
                route_form.prefix.data, peer.ip, route_form.next_hop.data), 'warning')

        # Create the advertised route object
        adv_route = {
            'prefix': route_form.prefix.data,
            'peer': peer['ip'],
            'attributes': {
                'origin': route_form.origin.data,
                'local-preference': route_form.local_pref.data,
                'med': route_form.med.data,
                'next-hop': route_form.next_hop.data
            }
        }

        adv_routes.insert_one(adv_route)
        
        try:
            announce_route(peer, adv_route)
        except ConnectionError:
            #Exabgp isn't running, but route will be advertised when it starts
            flash('%s queued to be announced to %s' % (adv_route['prefix'], peer['ip']), 'success')
        else:
            flash('%s has been announced to %s' % (adv_route['prefix'], peer['ip']), 'success')

        return redirect(url_for('peer', peer_id=peer_id))
    
    if peer_form.validate_on_submit():

        bgp_peers.update(peer, {'$set': {'asn': peer_form.asn.data}})

        # If there's a change in Peer's enabled state, edit exabgp config
        if peer['enabled'] != peer_form.enabled.data:
            print 'enabled changed from %s to %s' % (peer['enabled'], peer_form.enabled.data)
            bgp_peers.update(peer, {'$set': {'enabled': peer_form.enabled.data}})
            # Rebuild config file and reload ExaBGP config
            build_config_file(bgp_config.find_one(), list(bgp_peers.find()))
            try:
                # Tear down neighbor connection
                if not peer_form.enabled.data:
                    send_exabgp_command('neighbor %s teardown 4' % peer['ip'])
                    bgp_peers.update_one({'ip': peer['ip']}, {'$set': {'state': 'down', 'current_prefixes': []}})
                exabpg_process('reload')
            except ConnectionError:
                # Ignore because ExaBGP will re-read config when it starts
                pass


        flash('Changes saved', 'success')
        return redirect(url_for('peer', peer_id=peer_id))
    
    else:
        advertised_routes = adv_routes.find({'peer': peer['ip']})

        peer_form.ip_address.data = peer['ip']
        peer_form.asn.data = peer['asn']
        try:
            peer_form.enabled.data = peer['enabled']
        except KeyError:
            peer_form.enabled.data = False

        return render_template('peer_info.html', peer=peer, route_form=route_form, peer_form=peer_form, advertised_routes=advertised_routes)

@app.route('/peer/<peer_id>/withdraw/<adv_route_id>')
def delete_adv_route(peer_id, adv_route_id):

    peer = bgp_peers.find_one({'_id': ObjectId(peer_id)})
    adv_route = adv_routes.find_one({'_id': ObjectId(adv_route_id)})

    try:
        withdraw_route(peer, adv_route)
    except ConnectionError:
        #Exabgp isn't running, but route won't be advertised when it starts
        flash('%s is queued to be withdrawn from %s.' % (adv_route['prefix'], peer['ip']), 'success')
    else:
        flash('%s has been withdrawn from %s.' % (adv_route['prefix'], peer['ip']), 'success')

    adv_routes.remove({'_id': ObjectId(adv_route_id)}, 1)

    return redirect(url_for('peer', peer_id=peer_id))

@app.route('/config/', methods=['GET', 'POST'])
def config():

    config_form = ConfigForm()
    peer_form = BGPPeer()
    
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

    if peer_form.validate_on_submit():
            
        try:
            # Create the new peer
            new_peer = {
                'ip': peer_form.ip_address.data,
                'asn': int(peer_form.asn.data),
                'state': 'down',
                'enabled': peer_form.enabled.data
            }

            bgp_peers.insert_one(new_peer)
        except:
            flash('Error adding peer %s.' % peer_form.ip_address.data, 'warning')
        else:
            flash('Peer %s added' % peer_form.ip_address.data, 'success')

        return redirect(url_for('config', _anchor='peers'))

    else:

        peers = list(bgp_peers.find())
        config = bgp_config.find_one()

        config_form.asn.data = config['local-as']
        config_form.router_id.data = config['router-id']
        config_form.local_ip.data = config['local-address']

        return render_template('config.html', peers=peers, config=config, config_form=config_form, peer_form=peer_form)

@app.route('/config/delete_peer/<peer_id>')
def delete_peer(peer_id):

    peer = bgp_peers.find_one({'_id': ObjectId(peer_id)})

    try:
        bgp_peers.remove(peer)
    except:
        flash('Error deleting peer %s' % peer['ip'], 'warning')
    else:
        flash('Peer %s deleted' % peer['ip'], 'success')
    
    return redirect(url_for('config', _anchor='peers'))

@app.route('/config/logs')
def logs():

    try:
        limit = int(request.args.get('limit'))
    except TypeError:
        limit = 250

    exclude = request.args.get('exclude').split(',')
    if not exclude:
        exclude = []

    peer = request.args.get('peer')
    if not peer:
        updates = list(bgp_updates.find({'type': {'$nin': exclude}}, {'_id': False}).sort('time', DESCENDING).limit(limit))
    else:
        updates = list(bgp_updates.find({'type': {'$nin': exclude}, 'peer': {'$eq': peer}}, {'_id': False}).sort('time', DESCENDING).limit(limit))

    return render_template('logs.html', updates=updates)

@app.route('/config/exabgp/<action>')
def config_action(action):

    current_config = bgp_config.find_one()
    peers = list(bgp_peers.find())

    #Rebuild config file before reload action
    if action == 'reload':
        build_config_file(current_config, peers)

    # Send action control to ExaBGP
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