# Shared private-file checks for trusted local sandbox entrypoints.
private_path() {
    local item="$1" maximum="$2" task_owner task_mode task_size
    test ! -L "$item" || return 1
    if test "$(uname -s)" = Darwin; then
        read -r task_owner task_mode task_size < <(stat -f '%u %Lp %z' "$item")
    else
        read -r task_owner task_mode task_size < <(stat -c '%u %a %s' "$item")
    fi
    [[ "$task_mode" =~ ^[0-7]{3,4}$ && "$task_size" =~ ^[0-9]+$ ]] || return 1
    test "$task_owner" = "$(id -u)" || return 1
    (( (8#$task_mode & 077) == 0 && task_size <= maximum ))
}
