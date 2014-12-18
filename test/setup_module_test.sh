#!/bin/bash

py_version_short=$(python -c "import sys; print(''.join(str(x) for x in sys.version_info[:2]))")
# -> 26 or 27 or 34 or ..

get_name (){
    echo $(python -c 'import json; print json.load(open("'$1'package.json"))["name"]')
}

setup_submodule (){
    for dep in $(cat test/dep_modules.txt); do
        mname=$(basename $dep | sed 's/.git//g')
        git clone $dep ~/$mname
        rmname=$(get_name ~/$mname/)
        cp -r  ~/$mname/module ~/shinken/modules/$rmname
        [ -f ~/$mname/requirements.txt ] && pip install -r ~/$mname/requirements.txt
    done
}

name=$(get_name)

pip install pycurl
pip install coveralls
git clone https://github.com/naparuba/shinken.git ~/shinken
[ -f ~/shinken/test/requirements.txt ] && pip install -r ~/shinken/test/requirements.txt
[ -f test/dep_modules.txt ] && setup_submodule
[ -f requirements.txt ] && pip install -r requirements.txt
spec_requirement="requirements-${py_version_short}.txt"
[ -f "$spec_requirement" ] && pip install --use-mirrors -r "$spec_requirement"
test_requirement="test/requirements.txt"
[ -f "$test_requirement" ] && pip install --use-mirrors -r "$test_requirement"
rm ~/shinken/test/test_*.py
cp test/*.py ~/shinken/test/
[ -d test/etc ] && cp -r test/etc ~/shinken/test/
cp -r module ~/shinken/modules/$name
ln -sf ~/shinken/modules ~/shinken/test/modules
#cd ~/shinken


