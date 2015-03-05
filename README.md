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
* Get senlin code from github

```
git clone https://github.com/tengqm/senlin.git
```

* Install requirements

```
pip install -r requirements.txt
```

* Install senlin

```
./install.sh
```

* Create keystone service for senlin

There is a setup-service script under tools folder to do this for you, you should use the script to automate this step and step 5 for you.

```
keystone service-create --type clustering --name senlin
```

* Create keystone endpoint for senlin

There is a setup-service script under tools folder to do this for you, you should use the script to automate step 4 and this step for you.


```
keystone endpoint-create --region RegionOne --service <service_id> --publicurl 'http://<your_ip>:8778/v1/$(tenant_id)s' --adminurl 'http://<your_ip>:8778/v1/$(tenant_id)s' --internalurl 'http://<your_ip>:8778/v1/$(tenant_id)s'
```

* Update configuration file /etc/senlin/senlin.conf according to your system

Note that the item policy_dir should be pointed to a folder which include file policy.json

* Start senlin engine and api service

```
senlin-engine --config-file /etc/senlin/senlin.conf --log-file /tmp/senlin-api.log --debug
senlin-api --config-file /etc/senlin/senlin.conf --log-file /tmp/senlin-api.log --debug
```

* Get senlin client code

```
git clone https://github.com/tengqm/python-senlinclient.git
```

* Install senlin client

```
python setup.py install
```

* You are ready to play with senlin right now