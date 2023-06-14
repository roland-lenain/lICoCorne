#!/usr/bin/env bash
set -euo pipefail
unalias -a
current_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

#######################################
# Functions
#######################################

function download_merlin() {
    local tar_file=$1
    shift
    local extract_dir=$1
    shift
    if [ -f "${tar_file}" ]; then
        rm -f ${tar_file}
    fi
    wget http://merlin.polymtl.ca/downloads/version5_v5.1.tgz -O ${tar_file}
    tar -xzf ${tar_file} --strip-components=1 -C ${extract_dir}
}

function create_venv() {
    local venv_dir="$(realpath venv-licocorne)"

    if [ -d "${venv_dir}" ]; then
        read -rep "Erase old environment ? (yes/no) " -i "yes" answer
        if [[ "${answer}" != "no" ]]; then
            rm -rf ${venv_dir}
        else
            return 0
        fi
    fi
    python3 -m venv ${venv_dir}

    cat >>${venv_dir}/bin/activate <<EOF

# Support for HDF5
export HDF5_INC="${HDF5_INC}" # HDF5 include directory
export HDF5_API="${HDF5_API}" # HDF5 C API
# export LD_LIBRARY_PATH="\${HDF5_API}"
# Support for MEDCOUPLING
# Support for Python3 API
export FORTRANPATH="/usr/lib/" # contains libgfortran.so
EOF
    . ${venv_dir}/bin/activate
}


function install() {
    local merlin_dir="${prereq_dir}/merlin"

    if [[ ! -v VIRTUAL_ENV ]]; then
        echo "'VIRTUAL_ENV' is not defined."
        exit 1
    fi

    pip install --upgrade pip setuptools "numpy<2" "pybind11-stubgen"

    # Install Python API
    if [ -d "${merlin_dir}" ]; then
        read -rep "Reload prerequisities ? (yes/no) " -i "no" answer
        if [[ "${answer}" == "yes" ]]; then
            rm -rf ${merlin_dir}
            download_merlin ${prereq_dir}/merlin.tgz ${merlin_dir}
        fi
    else
        mkdir ${merlin_dir}
        download_merlin ${prereq_dir}/merlin.tgz ${merlin_dir}
    fi

    echo "======================================> make donjon"
    (cd ${merlin_dir}/PyGan/ && make donjon)

    local PyGan_PYTHONPATH="${merlin_dir}/PyGan/lib/Linux_x86_64/python"
    if [ ! -d "${PyGan_PYTHONPATH}" ]; then
        echo "'${PyGan_PYTHONPATH}' not found."
        exit 1
    fi
    echo "${PyGan_PYTHONPATH}" > ${VIRTUAL_ENV}/lib/python${python_version}/site-packages/PyGan.pth

    python3 -m pybind11_stubgen lcm -o ${VIRTUAL_ENV}/lib/python${python_version}/site-packages/
    python3 -m pybind11_stubgen lifo -o ${VIRTUAL_ENV}/lib/python${python_version}/site-packages/
    python3 -m pybind11_stubgen cle2000 -o ${VIRTUAL_ENV}/lib/python${python_version}/site-packages/

    echo "======================================> pip install -e"
    pip install -e "${current_script_dir}"
}

function test_install () {
    echo "======================================> pip install -e test"
    pip install -e "${current_script_dir}[test]"
    # pytest src # unit tests
    pytest tests # integration tests
}


####################################################################################################
# Execution
####################################################################################################

readonly current_script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# root directory
readonly project_root_dir="${current_script_dir}"
# current directory
readonly current_dir="${PWD}"
# config directoy
readonly config_dir="${current_script_dir}/config"
# prerequisities directoy
readonly prereq_dir="${current_script_dir}/extern"

. ${config_dir}/bash_utils.sh

python_version=$(python3 -c 'import sys; print(".".join(map(str,sys.version_info[0:2])))')
if [[ ! -v hdf5_root ]]; then
    if [[ "${os_id}" = "ubuntu" ]] && [[ "${os_version}" = "22"* ]] ; then
        HDF5_INC="/usr/include/hdf5/serial/" # HDF5 include directory
        HDF5_API="/usr/lib/x86_64-linux-gnu/hdf5/serial/" # HDF5 C API
    else
        error "Error: unknown platform ${os_id} ${os_version}" 1
    fi
else
    HDF5_INC="${hdf5_root}/include" # HDF5 include directory
    HDF5_API="${hdf5_root}/lib" # HDF5 C API
fi

if (( $# > 0 )); then
    echo "${BASH_SOURCE[0]}: $(basename ${BASH_SOURCE[0]})

    The following commands/variable can be overloaded:
        'python3' command is used to create a virtual environment,
        # 'hdf5_root' variable is HDF5 root directory,
        "
    exit 0
fi

create_venv

install

test_install

echo -e "$(tput setaf 2)Installation success!\nTo activate the environment, source :\n. ${VIRTUAL_ENV}/bin/activate $(tput sgr0)"
