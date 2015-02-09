# This is a spec for an AWS ELB load-balancer 
AvailabilityZones: []
HealthCheck:
  HealthyThreshold: 5 
  Interval: 60
  Target: 80
  Timeout: 30
  UnhealtyThreshold: 15 
Instances: []
Listeners:
  - InstancePort: 80
    LoadBalancerPort: 80
    Protocol: HTTP
    SSLCertificateId: MyCertificate
    PolicyNames:
      - PolicyA
      - PolicyB
AppCookieStickinessPolicy:
  - What
LBCookieStickienessPolicy:
  - What
SecurityGroups:
  - ssh_group
Subnets:
  - private_sub_net_01
