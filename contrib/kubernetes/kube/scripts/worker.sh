#!/bin/sh
HOSTNAME=`hostname`
echo "127.0.0.1 $HOSTNAME" >> /etc/hosts
apt-get update && apt-get install -y docker.io curl apt-transport-https
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
MASTER_IP={{ MASTERIP }}
kubeadm join --token {{ KUBETOKEN }} --skip-preflight-checks --discovery-token-unsafe-skip-ca-verification $MASTER_IP:6443
