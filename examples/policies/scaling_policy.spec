# Sample scaling policy that can be attached to a cluster

# Min number of nodes to keep the cluster operational
min_size: 1

# Max number of nodes to cap resource consumption
max_size: 10

adjustment:
  # Adjustment type, valid values include:
  # EXACT_CAPACITY, CHANGE_IN_CAPACITY, CHANGE_IN_PERCENTAGE
  type: CHANGE_IN_CAPACITY

  # A number that will be interpreted based on the type setting
  value: 1
 
  # When type is set CHNAGE_IN_PERCENTAGE, min_step specifies
  # that the cluster size will be changed by at least the number
  # of nodes specified here
  min_step: 1
