# load-balancing policy spec using Neutron LBaaS service

#### Pool properties
pool:
  # Protocol used for load balancing
  protocol: HTTP

  # Port on which servers are running on the members
  protocol_port: 80

  # Name or ID of subnet for the port on which members can be connected.
  subnet: private-subnet

  # Valid values include:
  # ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP
  lb_method: ROUND_ROBIN

  # Administrative state of the pool
  admin_state_up: True

  # session persistence configuration
  session_persistence:
    # type of session persistence implementation, valid values include:
    # SOURCE_IP, HTTP_COOKIE, APP_COOKIE
    type: SOURCE_IP
    # Name of cookie if type set to APP_COOKIE
    cookie_name: whatever

#### Virtual IP properties
vip:
  # Name or ID of Subnet on which VIP address will be allocated
  subnet: private-subnet

  # IP adddress of the VIP
  # address: <ADDRESS>

  # Max #connections per second allowed for this VIP
  connection_limit: 500

  # Protocol used for VIP
  protocol: HTTP

  # TCP port to listen on
  protocol_port: 80

  # Administrative state up
  admin_state_up: True
