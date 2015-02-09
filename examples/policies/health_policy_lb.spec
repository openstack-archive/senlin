# Sample health policy based on monitoring using LBaaS service

detection:
  # Type for health checking, valid values include:
  # NODE_STATUS_POLLING, LB_STATUS_POLLING, VM_EVENT_LISTENING
  type: LB_STATUS_POLLING

  # Number of seconds between two adjacent checking
  interval: 60

  # Detailed specification for the checking type
  options:

    # Min time in seconds between regular connection of the member
    deplay: 5

    # Max time in seconds for a monitor to wait for a connection to
    # establish before it times out
    timeout: 10

    # Predefined health monitor types, valid values include one of:
    # PING, TCP, HTTP, HTTPS
    type: HTTP 

    # Number of permissible connection failures before chaning the
    # node status to INACTIVE
    max_retries: 3

    # Administrative state of the monitor
    admin_state_up: True

    # HTTP method used for requests by the monitor of type HTTP
    http_method: GET

    # List of HTTP status codes expected in response from the member
    # to declare it healthy
    expected_codes: 200

    # HTTP path used in HTTP request by monitor for health testing
    url_path: /health_status

recovery:
  # List of actions that can be retried on a failed node
  actions:
    - reboot
    - rebuild
    - migrate
    - evacuate
    - recreate

  # List of services that are to be fenced
  fencing:
    - compute
    - storage
    - network
