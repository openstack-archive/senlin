This is the directory to hold Rally plugins for Senlin. So we don't need to
merge them into Rally's repository to support Senlin test. Specifying
additional plugin paths with the `--plugin-paths` argument, or with the
`RALLY_PLUGIN_PATHS` environment variable when invoking rally cmd will make
the plugin to be autoloaded by Rally. An alternative is copying file under
this directory to `~/.rally/plugins` or `/opt/rally/plugins`.

More information about Rally plugins can be found here:
- https://rally.readthedocs.org/en/latest/plugins.html
