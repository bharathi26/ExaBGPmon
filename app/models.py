from pymongo import MongoClient

client = MongoClient()
db = client.exabgp_db
bgp_updates = db.bgp_updates
adv_routes = db.adv_routes
bgp_peers = db.bgp_peers

peer = {  #db.bgp_peers
	'ip': '10.10.1.1',
	'asn': 65000,
	'state': 'up',
	'current_prefixes': ['1.1.1.1/32', '200.200.1.0/24'],
}

adv_route = {
	'peer': '10.10.1.1',
	'prefix': '200.200.0.0/24',
	'attributes': {
		'local-preference': 100,
		'med': 200,
		'origin': '?',
		'next-hop': '2.2.2.2'
	}
}