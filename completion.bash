# Bash completion for drivesync

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

_drivesync_tail_values() {
    compgen -W "1 5 10 20 50 100" -- "$1"
}

_drivesync_remotes() {
    rclone listremotes 2>/dev/null | sed 's/:$//'
}

_drivesync() {
    local cur prev top sub sub2 sub3
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    top="${COMP_WORDS[1]}"
    sub="${COMP_WORDS[2]}"
    sub2="${COMP_WORDS[3]}"
    sub3="${COMP_WORDS[4]}"

    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "dir sync status config auth schedule -h --help" -- "$cur") )
        return 0
    fi

    case "$top" in
        dir)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "add remove list show" -- "$cur") )
                return 0
            fi

            case "$sub" in
                add)
                    if [[ "$prev" == "--remote-dir" ]]; then
                        return 0
                    fi

                    if [[ ${COMP_CWORD} -eq 4 ]]; then
                        COMPREPLY=( $(compgen -d -- "$cur") )
                        return 0
                    fi

                    COMPREPLY=( $(compgen -W "--remote-dir --create" -- "$cur") )
                    ;;
                remove|show)
                    if [[ ${COMP_CWORD} -eq 3 ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids)" -- "$cur") )
                        return 0
                    fi
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
                list)
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
            esac
            ;;
        sync)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "check run status logs" -- "$cur") )
                return 0
            fi

            case "$sub" in
                check)
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
                run)
                    if [[ "$prev" == "--json" || "$prev" == "--resync" || "$prev" == "--force" ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids)" -- "$cur") )
                        return 0
                    fi

                    if [[ ${COMP_CWORD} -eq 3 ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids) --resync --force --json" -- "$cur") )
                        return 0
                    fi

                    COMPREPLY=( $(compgen -W "--resync --force --json" -- "$cur") )
                    ;;
                status)
                    if [[ ${COMP_CWORD} -eq 3 ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids) --json --executor" -- "$cur") )
                        return 0
                    fi
                    COMPREPLY=( $(compgen -W "--json --executor" -- "$cur") )
                    ;;
                logs)
                    if [[ "$prev" == "--tail" ]]; then
                        COMPREPLY=( $(_drivesync_tail_values "$cur") )
                        return 0
                    fi

                    local logs_id_seen=0
                    local logs_follow_seen=0
                    local logs_path_seen=0
                    local logs_json_seen=0
                    local skip_next=0
                    local index
                    for ((index = 3; index < COMP_CWORD; index++)); do
                        if (( skip_next )); then
                            skip_next=0
                            continue
                        fi
                        case "${COMP_WORDS[index]}" in
                            --tail)
                                skip_next=1
                                ;;
                            --path)
                                logs_path_seen=1
                                ;;
                            --follow|-f)
                                logs_follow_seen=1
                                ;;
                            --json)
                                logs_json_seen=1
                                ;;
                            --raw)
                                ;;
                            *)
                                logs_id_seen=1
                                ;;
                        esac
                    done

                    local logs_options="--json --path --raw --tail --follow -f"
                    if (( logs_follow_seen || logs_json_seen )); then
                        logs_options="${logs_options// --follow/}"
                        logs_options="${logs_options// -f/}"
                    fi
                    if (( logs_follow_seen || logs_path_seen )); then
                        logs_options="${logs_options// --path/}"
                    fi
                    if (( logs_follow_seen || logs_json_seen )); then
                        logs_options="${logs_options// --json/}"
                    fi
                    if (( logs_id_seen )); then
                        COMPREPLY=( $(compgen -W "$logs_options" -- "$cur") )
                    else
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids) $logs_options" -- "$cur") )
                    fi
                    ;;
            esac
            ;;
        status)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "$(_drivesync_ids) --json --executor" -- "$cur") )
                return 0
            fi
            COMPREPLY=( $(compgen -W "--json --executor" -- "$cur") )
            ;;
        config)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "path root logs" -- "$cur") )
                return 0
            fi

            if [[ "$sub" == "path" ]]; then
                if [[ ${COMP_CWORD} -eq 3 ]]; then
                    COMPREPLY=( $(compgen -W "show set reset" -- "$cur") )
                    return 0
                fi

                case "$sub2" in
                    show|reset)
                        COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                        ;;
                    set)
                        if [[ ${COMP_CWORD} -eq 4 ]]; then
                            COMPREPLY=( $(compgen -d -- "$cur") )
                            return 0
                        fi
                        COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                        ;;
                esac
            elif [[ "$sub" == "root" ]]; then
                if [[ ${COMP_CWORD} -eq 3 ]]; then
                    COMPREPLY=( $(compgen -W "show set reset" -- "$cur") )
                    return 0
                fi

                case "$sub2" in
                    show|reset)
                        COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                        ;;
                    set)
                        COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                        ;;
                esac
            elif [[ "$sub" == "logs" ]]; then
                if [[ ${COMP_CWORD} -eq 3 ]]; then
                    COMPREPLY=( $(compgen -W "precision max-size" -- "$cur") )
                    return 0
                fi

                if [[ "$sub2" == "precision" ]]; then
                    if [[ ${COMP_CWORD} -eq 4 ]]; then
                        COMPREPLY=( $(compgen -W "show set" -- "$cur") )
                        return 0
                    fi

                    case "$sub3" in
                        show)
                            COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                            ;;
                        set)
                            if [[ ${COMP_CWORD} -eq 5 ]]; then
                                COMPREPLY=( $(compgen -W "light full" -- "$cur") )
                                return 0
                            fi
                            COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                            ;;
                    esac
                elif [[ "$sub2" == "max-size" ]]; then
                    if [[ ${COMP_CWORD} -eq 4 ]]; then
                        COMPREPLY=( $(compgen -W "show set" -- "$cur") )
                        return 0
                    fi

                    case "$sub3" in
                        show)
                            COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                            ;;
                        set)
                            if [[ ${COMP_CWORD} -eq 5 ]]; then
                                return 0
                            fi
                            COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                            ;;
                    esac
                fi
            fi
            ;;
        auth)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "setup status" -- "$cur") )
                return 0
            fi

            case "$sub" in
                status)
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
                setup)
                    if [[ ${COMP_CWORD} -eq 3 ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_remotes) --json" -- "$cur") )
                        return 0
                    fi
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
            esac
            ;;
        schedule)
            if [[ ${COMP_CWORD} -eq 2 ]]; then
                COMPREPLY=( $(compgen -W "set show list remove preview install uninstall" -- "$cur") )
                return 0
            fi

            case "$sub" in
                set)
                    if [[ "$prev" == "--frequency" ]]; then
                        COMPREPLY=( $(compgen -W "5minutes hourly daily weekly" -- "$cur") )
                        return 0
                    fi
                    if [[ "$prev" == "--day" ]]; then
                        COMPREPLY=( $(compgen -W "monday tuesday wednesday thursday friday saturday sunday" -- "$cur") )
                        return 0
                    fi
                    if [[ ${COMP_CWORD} -eq 3 ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids)" -- "$cur") )
                        return 0
                    fi
                    COMPREPLY=( $(compgen -W "--frequency --at --day --json" -- "$cur") )
                    ;;
                show|remove)
                    if [[ ${COMP_CWORD} -eq 3 ]]; then
                        COMPREPLY=( $(compgen -W "$(_drivesync_ids)" -- "$cur") )
                        return 0
                    fi
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
                list|preview|install|uninstall)
                    COMPREPLY=( $(compgen -W "--json" -- "$cur") )
                    ;;
            esac
            ;;
    esac

    return 0
}

complete -F _drivesync drivesync