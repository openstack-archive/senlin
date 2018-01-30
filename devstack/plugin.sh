# senlin.sh - Devstack extras script to install senlin

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "senlin's plugin.sh was called..."
. $DEST/senlin/devstack/lib/senlin
(set -o posix; set)

if is_service_enabled sl-api sl-eng; then
    if [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing senlin"
        install_senlin
        echo_summary "Installing senlinclient"
        install_senlinclient
        if is_service_enabled horizon; then
            echo_summary "Installing senlin dashboard"
            install_senlin_dashboard
        fi
        cleanup_senlin
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring senlin"
        configure_senlin

        if is_service_enabled horizon; then
            echo_summary "Configuring senlin dashboard"
            config_senlin_dashboard
        fi

        if is_service_enabled key; then
            create_senlin_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize senlin
        init_senlin

        # Start the senlin API and senlin taskmgr components
        echo_summary "Starting senlin"
        start_senlin
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_senlin
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_senlin

        if is_service_enabled horizon; then
            cleanup_senlin_dashboard
        fi
    fi
fi

# Restore xtrace
$XTRACE
