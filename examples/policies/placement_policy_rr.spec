# Sample placement policy doing round-robin

# Spanning AZs with weights
availability_zones:
  strategy:
    # Valid values include:
    # ROUND_ROBIN, WEIGHTED, SOURCE
    type: ROUND_ROBIN
    options:
      zones:
        - AZ1
        - AZ2

# Spanning regions with weights
regions:
  strategy:
    # Valid values include:
    # ROUND_ROBIN, WEIGHTED, SOURCE
    type: ROUND_ROBIN 
    options:
      regions:
        - RegionOne
        - RegionTwo
