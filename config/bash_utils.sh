# Sharable utils

# Function to raise error if level > 0
# usage: error "message" err_level
function error(){
    if [[ ${2:-0} -gt 0 ]]; then
        echo -e "\033[1;31mError from $0: $1 \033[0m"
        exit $2;
    fi
}

# Function to raise warning if level > 0
# usage: warning "message" wrn_level
function warning(){
    if [[ ${2:-0} -gt 0 ]]; then
        echo -e "\033[1;33mWarning from $0: $1 \033[0m"
    fi
}

# Function to print message in green
function message(){
    echo -e "\033[1;32m$1 \033[0m"
}

# Function to find networt (function unset at the end of this script)
# usage: network="$(_network)"
function _network(){
    if hostname -A | grep orcus > /dev/null 2>&1; then
        echo "orcus"
    elif [ -d "/home/catA" ]||[ -d "/home/catB" ]; then
        echo "oberon"
    elif [ -d "/soft/der/C3PO/mphys/" ]; then
        echo "der"
    else
        echo "unknown"
    fi
}

# Name of the os
readonly os_id=$(source /etc/os-release && echo "$ID")
# Version of the os
readonly os_version=$(source /etc/os-release && echo "$VERSION_ID")
# CEA network name
readonly install_network="$(_network)"

unset _network

pushd(){
    command pushd "$@" > /dev/null
}

popd(){
    command popd "$@" > /dev/null
}
