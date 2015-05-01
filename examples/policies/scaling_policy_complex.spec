# Sample scaling policy that can be attached to a cluster

constraints:
  # Min number of nodes to keep the cluster operational
  min_size: 1

  # Max number of nodes to cap resource consumption
  max_size: 10

policies:
  - condition:
      # name of meter for testing
      meter: cpu_util
      # comparison operator, valid values include 'lt', 'gt', 'eq'
      op: gt
      # Threshold for testing
      threshold: 50
      # Length of each evaluation period in seconds
      period: 60
      # Number of evaluations to perform
      evaluations: 1
    adjustment:
      # Adjustment type, valid values include:
      # EXACT_CAPACITY, CHANGE_IN_CAPACITY, CHANGE_IN_PERCENTAGE
      type: CHANGE_IN_CAPACITY

      # A number that will be interpreted based on the type setting
      number: 1

      # When type is set CHNAGE_IN_PERCENTAGE, min_step specifies
      # that the cluster size will be changed by at least the number
      # of nodes specified here
      min_step: 1

  - condition:
      # name of meter for testing
      meter: cpu_util
      # comparison operator, valid values include 'lt', 'gt', 'eq'
      op: lt
      # Threshold for testing
      threshold: 15
      # Length of each evaluation period in seconds
      period: 60
      # Number of evaluations to perform
      evaluations: 1
    adjustment:
       # Adjustment type, valid values include:
      # EXACT_CAPACITY, CHANGE_IN_CAPACITY, CHANGE_IN_PERCENTAGE
      type: CHANGE_IN_CAPACITY

      # A number that will be interpreted based on the type setting
      number: 1

      # When type is set CHNAGE_IN_PERCENTAGE, min_step specifies
      # that the cluster size will be changed by at least the number
      # of nodes specified here
      min_step: 1
