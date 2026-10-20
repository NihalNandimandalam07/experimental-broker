#! /bin/bash

mkdir build_temp
cd build_temp
python -m venv venv --copies

venv/bin/python -m pip install -r ../../../../modules/experiment-broker/experiment_code/activities/requirements.txt

if [ "$CHAOS_TOOLKIT_TYPE" == "main" ]; then
  venv/bin/python -m pip install -r ../../../../modules/experiment-broker/experiment_code/activities/requirements-chaostoolkit.txt
else
  cp -r ../../../../modules/chaos-toolkit-lite/chaos_toolkit_lite/chaosaws venv/lib/python3.11/site-packages/
  cp -r ../../../../modules/chaos-toolkit-lite/chaos_toolkit_lite/chaosk8s venv/lib/python3.11/site-packages/
  cp -r ../../../../modules/chaos-toolkit-lite/chaos_toolkit_lite/chaoslib venv/lib/python3.11/site-packages/
  cp -r ../../../../modules/chaos-toolkit-lite/chaos_toolkit_lite/chaostoolkit venv/lib/python3.11/site-packages/
fi

cp -r ../../../../modules/experiment-broker/experiment_code/activities venv/lib/python3.11/site-packages/

cp -r ../../../../modules/experiment-broker-logging venv/lib/python3.11/site-packages/

cd venv/lib/python3.11/site-packages
zip -r ../../../../experiment_broker_lambda  .
cd -

cp ../../../../modules/experiment-broker/experiment_code/lambda/handler.py .
zip -u experiment_broker_lambda handler.py