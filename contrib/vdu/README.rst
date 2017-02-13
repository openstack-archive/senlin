# VDU Profile for NFV

## Install
```bash
pip install --editable .
```

## Usage
```bash
source openrc demo demo
senlin profile-create vdu-profile -s examples/vdu.yaml
senlin cluster-create vdu-cluster -p vdu-profile -M config='{"word": "world"}' -c 1
```
