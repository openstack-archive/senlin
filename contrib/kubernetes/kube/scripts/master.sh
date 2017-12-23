#!/bin/sh
HOSTNAME=`hostname`
echo "127.0.0.1 $HOSTNAME" >> /etc/hosts
apt-get update && apt-get install -y docker.io curl apt-transport-https
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
echo "deb http://apt.kubernetes.io/ kubernetes-xenial main" > /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
PODNETWORKCIDR=10.244.0.0/16
kubeadm init --token {{ KUBETOKEN }} --skip-preflight-checks --pod-network-cidr=$PODNETWORKCIDR --apiserver-cert-extra-sans={{ MASTER_FLOATINGIP}} --token-ttl 0
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config
mkdir -p root/.kube
cp -i /etc/kubernetes/admin.conf root/.kube/config
chown root:root root/.kube/config
cp -i /etc/kubernetes/admin.conf /opt/admin.kubeconf
echo "# Setup network pod"
kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/v0.9.0/Documentation/kube-flannel.yml
echo "# Install kubernetes dashboard"
kubectl create -f https://raw.githubusercontent.com/kubernetes/dashboard/master/src/deploy/recommended/kubernetes-dashboard.yaml
echo "# Install heapster"
kubectl create -f https://raw.githubusercontent.com/kubernetes/heapster/master/deploy/kube-config/influxdb/grafana.yaml
kubectl create -f https://raw.githubusercontent.com/kubernetes/heapster/master/deploy/kube-config/influxdb/heapster.yaml
kubectl create -f https://raw.githubusercontent.com/kubernetes/heapster/master/deploy/kube-config/influxdb/influxdb.yaml
kubectl create -f https://raw.githubusercontent.com/kubernetes/heapster/master/deploy/kube-config/rbac/heapster-rbac.yaml
echo "# Download monitor script"
curl -o /opt/monitor.sh https://raw.githubusercontent.com/lynic/templates/master/k8s/monitor.sh
chmod a+x /opt/monitor.sh
echo "*/1 * * * * root bash /opt/monitor.sh 2>&1 >> /var/log/kube-minitor.log" > /etc/cron.d/kube-monitor
systemctl restart cron
echo "# Get status"
kubectl get nodes