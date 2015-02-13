#!/bin/bash

set -e
set -xv

py_version_short=$(python -c "import sys; print(''.join(str(x) for x in sys.version_info[:2]))")
# -> 26 or 27 or 34 or ..

get_name (){
    echo $(python -c 'import json; print json.load(open("'$1'package.json"))["name"]')
}

SHI_DST=test/tmp/shinken

setup_submodule (){
    local dep
    local mname
    local mpath
    for dep in $(cat test/dep_modules.txt); do
        mname=$(basename $dep | sed 's/.git//g')
        mpath="test/tmp/$mname"
        git clone --depth 10 "$dep" "$mpath"
        ( cd $mpath && git status && git log -1)
        rmname=$(get_name "$mpath/")
        ln -s "$PWD/$mpath/module" "$PWD/$SHI_DST/test/modules/$rmname"
        if [ -f "$mpath/requirements.txt" ]
        then
            pip install -r "$mpath/requirements.txt"
        fi
    done
}

name=$(get_name)

pip install pycurl
pip install coveralls

rm -rf test/tmp
mkdir -p test/tmp/

git clone --depth 10 https://github.com/naparuba/shinken.git "$SHI_DST"
( cd "$SHI_DST" && git status && git log -1)

spec_requirement="requirements-${py_version_short}.txt"

(
    cd "$SHI_DST"
    pip install -r test/requirements.txt
    if [ -f "test/${spec_requirement}" ]
    then
        pip install -r "test/${spec_requirement}"
    fi
)

if [ -f test/dep_modules.txt ]
then
    setup_submodule
fi

if [ -f requirements.txt ]
then
    pip install -r requirements.txt
fi
if [ -f "$spec_requirement" ]
then
    pip install --use-mirrors -r "$spec_requirement"
fi

test_requirement="test/requirements.txt"
if [ -f "$test_requirement" ]
then
    pip install --use-mirrors -r "$test_requirement"
fi

cp -r test/etc "$SHI_DST/test/"

ln -s "$PWD/module" "$SHI_DST/test/modules/$name"
