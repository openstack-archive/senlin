# Sample health policy using AWS-style load-balancer

# The HealthCheck map should be attached to the load-balancer
# TODO(Qiming): Check out how the attachement can be done
HealthCheck:
  HealthyThreshold: 5 
  Interval: 60
  Target: 80
  Timeout: 30
  UnhealtyThreshold: 15 
