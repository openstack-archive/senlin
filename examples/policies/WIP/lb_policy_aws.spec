# Sample load-balancing policy modled after AWS ELB load-balancer 

# TODO(Qiming): Rework this based on ELB spec
AvailabilityZones: []
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
