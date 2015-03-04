senlin
======

Senlin is a clustering service for OpenStack cloud. It creates and operates
clusters of homogenous objects exposed by other OpenStack services. The 
goal is to make orchestration of collections of similar objects easier.

Senlin provides ReSTful APIs to users so that they can associate various
policies to a cluster.  Sample policies include placement policy, load
balancing policy, failover policy, scaling policy, ... and so on.

Developers will decide when to contribute it to OpenStack community.

IRC Channel: #senlin

Installation
-----
1. Get senlin code from github
    git clone https://github.com/tengqm/senlin.git
2. Install requirements
    pip install -r requirements.txt
3. Install senlin
    ./install.sh
4. Create keystone service for senlin
    keystone service-create --type clustering --name senlin
5. Create keystone endpoint for senlin
    keystone endpoint-create --region RegionOne --service <service_id> --publicurl 'http://<your_ip>:8778/v1/$(tenant_id)s' --adminurl 'http://<your_ip>:8778/v1/$(tenant_id)s' --internalurl 'http://<your_ip>:8778/v1/$(tenant_id)s'
6. Update configuration file /etc/senlin/senlin.conf according to your system
Note that the item policy_dir should be pointed to a folder which include file policy.json
7. Start senlin engine and api service
    senlin-engine --config-file /etc/senlin/senlin.conf --log-file /tmp/senlin-api.log --debug
    senlin-api --config-file /etc/senlin/senlin.conf --log-file /tmp/senlin-api.log --debug
8. Get senlin client code
    git clone https://github.com/tengqm/python-senlinclient.git
9. Install senlin client
    python setup.py install
10. You are ready to play with senlin right now