group exabgpmon { 
	router-id {{ config['router-id'] }}; 
	local-address {{ config['local-address'] }}; 

	capability {
	    route-refresh;
	}

	process logtodb { 
		run {{ config['python-path'] }} {{ config['root-path'] }}/app/logtodb.py; 
		encoder json;
		receive-routes;
		neighbor-changes;

	}

	process http-api { 
		run {{ config['python-path'] }} {{ config['root-path'] }}/app/http_api.py; 
		encoder json;
		receive-routes;
		neighbor-changes;
	} 

	{% for peer in peers %}
	{%- if peer['enabled'] -%}
	neighbor {{ peer['ip']}} { 
		peer-as {{ peer['asn'] }}; 
		local-as {{ peer['asn'] }};
	}
	{% endif %}
	{% endfor %}

}
