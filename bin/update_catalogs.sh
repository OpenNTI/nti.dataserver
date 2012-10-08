#!/bin/bash

python setup.py extract_messages
python setup.py update_catalog -l en
python setup.py compile_catalog -l en
