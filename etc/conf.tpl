group exabgpmon { 
	router-id {{ config['router-id'] }}; 
	local-as {{ config['local-as'] }}; 
	local-address {{ config['local-address'] }}; 

	process syslog { 
		run {{ config['python-path'] }} {{ config['root-path'] }}/app/logtodb.py; 

		encoder json;
		receive {
			parsed;
			update;
			neighbor-changes;
		}

	} 

	{% for peer in peers %}
	neighbor {{ peer['ip']}} { 
		peer-as {{ peer['asn'] }}; 
	}
	{% endfor %}

}
