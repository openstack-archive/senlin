# load-balancing policy spec using Neutron LBaaS service
# NOTE: properties are combined from LB and Pool
# Each Pool member has its own 'address', 'protocol_port, 'weight',
# and 'admin_state_up' property

#### LB propertie

# Port on which servers are running on the members
protocol_port: 80

#### Pool properties

pool:
  # Pool ID/name, if given can use an existing pool
  # pool: <ID>

  # Protocol used for load balancing
  protocol: HTTP

  # Subnet for the port on which members can be connected
  subnet: private_subnet

  # Valid values include:
  # ROUND_ROBIN, LEAST_CONNECTIONS, SOURCE_IP
  lb_method: ROUND_ROBIN

  # Administrative state of the pool
  admin_state_up: True

# IP address and port of the pool
vip:
  # Subnet of the VIP
  subnet: public_subnet
  # IP adddress of the VIP
  address: 172.24.4.220
  # Max #connections per second allowed for this VIP
  connection_limit: 500
  # TCP port to listen on
  protocol_port: 80
  # Administrative state up
  admin_state_up: True
  # session persistence configuration
  session_persistence:
    # type of session persistence implementation, valid values include:
    # SOURCE_IP, HTTP_COOKIE, APP_COOKIE
    type: SOURCE_IP
    # Name of cookie if type set to APP_COOKIE
    cookie_name: whatever
