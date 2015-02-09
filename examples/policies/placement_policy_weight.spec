# Spanning AZs with weights
availability_zones:
  strategy:
    # Valid values include:
    # ROUND_ROBIN, WEIGHTED, SOURCE
    type: WEIGHTED
    options:
      - zone: AZ1
        weight: 100
      - zone: AZ2
        weight: 50

# Spanning regions with weights
regions:
  strategy:
    # Valid values include:
    # ROUND_ROBIN, WEIGHTED, SOURCE
    type: WEIGHTED
    options:
      - region: RegionOne
        weight: 100
      - region: RegionTwo
        weight: 100
