

def announce_route(peer, adv_route):
	print 'neighbor %s announce route %s next-hop %s' % (
		peer['ip'], adv_route['prefix'], adv_route['attributes']['next-hop'])

def withdraw_route(peer, adv_route):
	print 'neighbor %s withdraw route %s next-hop %s' % (
		peer['ip'], adv_route['prefix'], adv_route['attributes']['next-hop'])