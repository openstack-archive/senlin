TODO:
- Forbid deleting master cluster before deleting node cluster.
- Limit to no more than 1 node in master cluster.
- Drain node before deleting worker node.
- More validation before cluster creation.
- More exception catcher in code.

Done:

- Add ability to do actions on cluster creation/deletion.
- Add more network interfaces in drivers.
- Add kubernetes master profile, use kubeadm to setup one master node.
- Add kubernetes node profile, auto retrieve kubernetes data from master cluster.
