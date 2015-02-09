# Sample health policy based on node health checking 

detection:
  # Type for health checking, valid values include:
  # NODE_STATUS_POLLING, LB_STATUS_POLLING, VM_EVENT_LISTENING
  type: NODE_STATUS_POLLING

  # Number of seconds between two adjacent checking
  interval: 60

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
