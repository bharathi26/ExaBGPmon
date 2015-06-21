from pymongo import MongoClient

client = MongoClient()
db = client.exabgp_db
bgp_updates = db.bgp_updates
bgp_peers = db.bgp_peers

peer = {  #db.bgp_peers
	'ip': '10.10.1.1',
	'asn': 65000,
	'state': 'up',
	'current_prefixes': ['1.1.1.1/32', '200.200.1.0/24'],
}

