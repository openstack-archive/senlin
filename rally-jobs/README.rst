This directory contains rally jobs to be run by OpenStack CI.

Structure:
* senlin-senlin.yaml describes rally tasks that will be run in rally-gate.
* plugins - directory containing rally plugins for senlin. These plugins
  will be loaded by rally-gate automatically when job is run at gate
  side. User can also manually copy those plugins to `~/.rally/plugins`
  or `/opt/rally/plugins` to make them work if test is done locally.

Please find more information about rally plugins at the following link:
 - https://rally.readthedocs.org/en/latest/plugins.html
