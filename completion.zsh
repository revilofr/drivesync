#compdef drivesync

_drivesync_ids() {
    drivesync dir list --json 2>/dev/null | python3 -c 'import json,sys
try:
    payload=json.load(sys.stdin)
except Exception:
    payload=[]
for item in payload:
    value=item.get("id")
    if isinstance(value,str):
        print(value)
'
}

_drivesync_remotes() {
    rclone listremotes 2>/dev/null | sed 's/:$//'
}

_drivesync() {
    local -a top_commands dir_actions sync_actions config_actions config_path_actions config_root_actions config_logs_actions config_logs_precision_actions config_logs_max_size_actions auth_actions schedule_actions ids remotes

    top_commands=(
        'dir:Manage synchronized directories'
        'sync:Synchronization commands'
        'config:Configuration path commands'
        'auth:Manage rclone authentication'
        'schedule:Manage scheduled synchronizations'
    )

    dir_actions=(
        'add:Register a local directory'
        'remove:Unregister a local directory'
        'list:List managed directories'
        'show:Show one managed directory'
    )

    sync_actions=(
        'check:Run preflight checks'
        'run:Run synchronization'
        'status:Show synchronization status'
        'logs:Inspect synchronization logs'
    )

    config_actions=(
        'path:Configuration path commands'
        'root:Remote root directory commands'
        'logs:Logging configuration commands'
    )

    config_path_actions=(
        'show:Show resolved config paths'
        'set:Set persistent config dir'
        'reset:Reset to default config dir resolution'
    )

    config_root_actions=(
        'show:Show configured remote root'
        'set:Set remote root directory'
        'reset:Reset remote root directory to default'
    )

    config_logs_actions=(
        'precision:Logging precision commands'
        'max-size:Sync history max size commands'
    )

    config_logs_precision_actions=(
        'show:Show configured logs precision'
        'set:Set logs precision'
    )

    config_logs_max_size_actions=(
        'show:Show configured sync history max size in KB'
        'set:Set sync history max size in KB'
    )

    auth_actions=(
        'setup:Configure rclone remote for DriveSync'
        'status:Check rclone auth state'
    )

    schedule_actions=(
        'set:Create or update one schedule'
        'show:Show one configured schedule'
        'list:List configured schedules'
        'remove:Remove one configured schedule'
        'preview:Preview managed cron block'
        'install:Apply configured schedules to user crontab'
        'uninstall:Remove DriveSync schedules from user crontab'
    )

    if (( CURRENT == 2 )); then
        _describe -t commands 'drivesync command' top_commands
        return
    fi

    case "${words[2]}" in
        dir)
            if (( CURRENT == 3 )); then
                _describe -t dir-actions 'dir action' dir_actions
                return
            fi

            case "${words[3]}" in
                add)
                    if (( CURRENT == 4 )); then
                        _message 'directory id'
                        return
                    fi

                    if (( CURRENT == 5 )); then
                        _path_files -/
                        return
                    fi

                    _arguments \
                        '--remote-dir[Remote subdirectory under configured root]:remote subdirectory:' \
                        '--create[Create local directory if it does not exist]'
                    return
                    ;;
                remove|show)
                    ids=("${(@f)$(_drivesync_ids)}")
                    if (( CURRENT == 4 )); then
                        if (( ${#ids} > 0 )); then
                            compadd -- $ids
                        fi
                        return
                    fi

                    _arguments '--json[Output as JSON]'
                    return
                    ;;
                list)
                    _arguments '--json[Output as JSON]'
                    return
                    ;;
            esac
            ;;

        sync)
            if (( CURRENT == 3 )); then
                _describe -t sync-actions 'sync action' sync_actions
                return
            fi

            case "${words[3]}" in
                check)
                    _arguments '--json[Output as JSON]'
                    return
                    ;;
                run)
                    ids=("${(@f)$(_drivesync_ids)}")
                    if (( CURRENT >= 4 )); then
                        compadd -- --resync --force --json
                        if (( ${#ids} > 0 )); then
                            compadd -- $ids
                        fi
                        return
                    fi
                    ;;
                status)
                    ids=("${(@f)$(_drivesync_ids)}")
                    if (( CURRENT >= 4 )); then
                        compadd -- --json
                        if (( ${#ids} > 0 )); then
                            compadd -- $ids
                        fi
                        return
                    fi
                    ;;
                logs)
                    ids=("${(@f)$(_drivesync_ids)}")
                    if (( CURRENT >= 4 )); then
                        compadd -- --json --path --raw
                        if (( ${#ids} > 0 )); then
                            compadd -- $ids
                        fi
                        return
                    fi
                    ;;
            esac
            ;;

        config)
            if (( CURRENT == 3 )); then
                _describe -t config-actions 'config action' config_actions
                return
            fi

            if [[ "${words[3]}" == "path" ]]; then
                if (( CURRENT == 4 )); then
                    _describe -t config-path-actions 'config path action' config_path_actions
                    return
                fi

                case "${words[4]}" in
                    show|reset)
                        _arguments '--json[Output as JSON]'
                        return
                        ;;
                    set)
                        if (( CURRENT == 5 )); then
                            _path_files -/
                            return
                        fi
                        _arguments '--json[Output as JSON]'
                        return
                        ;;
                esac
            elif [[ "${words[3]}" == "root" ]]; then
                if (( CURRENT == 4 )); then
                    _describe -t config-root-actions 'config root action' config_root_actions
                    return
                fi

                case "${words[4]}" in
                    show|reset)
                        _arguments '--json[Output as JSON]'
                        return
                        ;;
                    set)
                        _arguments '--json[Output as JSON]'
                        return
                        ;;
                esac
            elif [[ "${words[3]}" == "logs" ]]; then
                if (( CURRENT == 4 )); then
                    _describe -t config-logs-actions 'config logs action' config_logs_actions
                    return
                fi

                if [[ "${words[4]}" == "precision" ]]; then
                    if (( CURRENT == 5 )); then
                        _describe -t config-logs-precision-actions 'config logs precision action' config_logs_precision_actions
                        return
                    fi

                    case "${words[5]}" in
                        show)
                            _arguments '--json[Output as JSON]'
                            return
                            ;;
                        set)
                            if (( CURRENT == 6 )); then
                                compadd -- light full
                                return
                            fi
                            _arguments '--json[Output as JSON]'
                            return
                            ;;
                    esac
                elif [[ "${words[4]}" == "max-size" ]]; then
                    if (( CURRENT == 5 )); then
                        _describe -t config-logs-max-size-actions 'config logs max-size action' config_logs_max_size_actions
                        return
                    fi

                    case "${words[5]}" in
                        show)
                            _arguments '--json[Output as JSON]'
                            return
                            ;;
                        set)
                            if (( CURRENT == 6 )); then
                                _message 'size in KB'
                                return
                            fi
                            _arguments '--json[Output as JSON]'
                            return
                            ;;
                    esac
                fi
            fi
            ;;

        auth)
            if (( CURRENT == 3 )); then
                _describe -t auth-actions 'auth action' auth_actions
                return
            fi

            case "${words[3]}" in
                status)
                    _arguments '--json[Output as JSON]'
                    return
                    ;;
                setup)
                    remotes=("${(@f)$(_drivesync_remotes)}")
                    if (( CURRENT == 4 )); then
                        compadd -- --json
                        if (( ${#remotes} > 0 )); then
                            compadd -- $remotes
                        fi
                        return
                    fi
                    _arguments '--json[Output as JSON]'
                    return
                    ;;
            esac
            ;;
        schedule)
            if (( CURRENT == 3 )); then
                _describe -t schedule-actions 'schedule action' schedule_actions
                return
            fi

            case "${words[3]}" in
                set)
                    if (( CURRENT == 4 )); then
                        ids=("${(@f)$(_drivesync_ids)}")
                        if (( ${#ids} > 0 )); then
                            compadd -- $ids
                        fi
                        return
                    fi
                    case "${words[CURRENT-1]}" in
                        --frequency)
                            compadd -- 5minutes hourly daily weekly
                            return
                            ;;
                        --day)
                            compadd -- monday tuesday wednesday thursday friday saturday sunday
                            return
                            ;;
                    esac
                    _arguments \
                        '--frequency[Schedule frequency]:frequency:(5minutes hourly daily weekly)' \
                        '--at[Schedule time in HH:MM]:time:' \
                        '--day[Schedule day for weekly frequency]:day:(monday tuesday wednesday thursday friday saturday sunday)' \
                        '--json[Output as JSON]'
                    return
                    ;;
                show|remove)
                    ids=("${(@f)$(_drivesync_ids)}")
                    if (( CURRENT == 4 )); then
                        if (( ${#ids} > 0 )); then
                            compadd -- $ids
                        fi
                        return
                    fi
                    _arguments '--json[Output as JSON]'
                    return
                    ;;
                list|preview|install|uninstall)
                    _arguments '--json[Output as JSON]'
                    return
                    ;;
            esac
            ;;
    esac
}

compdef _drivesync drivesync
