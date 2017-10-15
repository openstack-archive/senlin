kubernetes Profile
==================

Installation
------------

::

  pip install --editable .


Usage
-----

Prepare a profile for master nodes
..................................

Copy the example profile file `kubemaster.yaml` from examples/kubemaster.yaml,
modify related parameters based on your openstack environment.
For now, only official ubuntu 16.04 cloud image is supported.

::

  openstack cluster profile create --spec-file kubemaster.yaml profile-master

Create a cluster for master nodes
.................................

For now, please create exactly one node in this cluster. This profile doesn't
support multiple master nodes as high-availability mode install.

::

  openstack cluster create --min-size 1 --desired-capacity 1 --max-size 1 --profile profile-master cm


Prepare a profile for worker nodes
..................................

Copy the example profile file `kubenode.yaml`, modify related parameters,
change master-cluster to the senlin cluster you just created.

::

  openstack cluster profile create --spec-file kubenode.yaml profile-node


Create a cluster for worker nodes
.................................

::

  openstack cluster create --desired-capacity 2 --profile profile-node cn



Operate kubernetes
------------------

About kubeconfig
................

The config file for `kubectl` is located in the `/root/.kube/config` directory
on the master nodes. Copy this file out and place it at `$HOME/.kube/config`.
Change the IP to master node's floating IP in it. Run `kubectl get nodes` and
see if it works.

Dashboard
.........

Prepare following file to skip dashboard authentication::

  $ cat ./dashboard-admin.yaml
  apiVersion: rbac.authorization.k8s.io/v1beta1
  kind: ClusterRoleBinding
  metadata:
    name: kubernetes-dashboard
    labels:
      k8s-app: kubernetes-dashboard
  roleRef:
    apiGroup: rbac.authorization.k8s.io
    kind: ClusterRole
    name: cluster-admin
  subjects:
  - kind: ServiceAccount
    name: kubernetes-dashboard
    namespace: kube-system

Apply this config::

  kubectl apply -f ./dashboard-admin.yaml

Start a proxy using `kubectl`::

  kubectl proxy

Open dashboard on browser at
`http://localhost:8001/api/v1/namespaces/kube-system/services/https:kubernetes-dashboard:/proxy/`,
skip login process.
