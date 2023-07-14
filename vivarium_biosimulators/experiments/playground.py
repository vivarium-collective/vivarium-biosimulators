from typing import *
import multiprocessing
import pandas as pd
from vivarium_biosimulators.library.process_logger import ProcessLogger
from vivarium_biosimulators.library.mappings import tellurium_mapping
from vivarium_biosimulators.processes.biosimulator_process import Biosimulator
from biosimulators_utils.sedml.data_model import ModelLanguage
import numpy as np


def get_logger(dirpath: str, filename: str):
    return ProcessLogger(dirpath, filename)


def make_process(model_source: str, config: Dict, logger: ProcessLogger):
    config['model_source'] = model_source
    process = Biosimulator(config)
    logger.add_entry(f'Process created with the following parameters: {process.parameters}')
    return process


SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'
XPP_MODEL_PATH = 'Biosimulators_test_suite/examples/xpp/Wu-Biochem-Pharmacol-2006-pituitary-GH3-cells/GH3_Katp.ode'
RBA_MODEL_PATH = 'Biosimulators_test_suite/examples/rba/Escherichia-coli-K12-WT/model.zip'
BNGL_MODEL_PATH = 'Biosimulators_test_suite/examples/bngl/Dolan-PLoS-Comput-Biol-2015-NHEJ/Dolan2015.bngl'


# Python modules can be found at https://api.biosimulators.org/simulators/
# get example models from https://github.com/biosimulators/Biosimulators_test_suite/tree/dev/examples
BIOSIMULATOR_SPECS = [
    {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': SBML_MODEL_PATH,


        'total_time': 10.,
    },
    {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,

        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    }
]
# PROCESS 0

COBRA_PROCESS_LOG_DIRPATH = '/Users/alex/Desktop/vivarium_logs'
COBRA_PROCESS_LOG_FILENAME = 'vivarium_biosimulators_cobra_process_log.json'
COBRA_PROCESS_MODEL_SOURCE = '/Users/alex/Desktop/uchc_work/repos/vivarium-repos/vivarium-biosimulators/vivarium_biosimulators/models/BIOMD0000000297_url.xml'
COBRA_PROCESS_CONFIG = {
    'biosimulator_api': 'biosimulators_cobrapy',
    'model_language': ModelLanguage.SBML.value,
    'model_source': COBRA_PROCESS_MODEL_SOURCE,
    'emit_ports': ['output'],
    'simulation': 'steady_state',
}
COBRA_PROCESS_LOGGER = get_logger(COBRA_PROCESS_LOG_DIRPATH, COBRA_PROCESS_LOG_FILENAME)


# PROCESS 1
TELLURIUM_PROCESS_LOG_DIRPATH = '/Users/alex/Desktop/vivarium_logs'
TELLURIUM_PROCESS_LOG_FILENAME = 'vivarium_biosimulators_tellurium_process_log.json'
TELLURIUM_PROCESS_MODEL_SOURCE = '/Users/alex/Desktop/uchc_work/repos/vivarium-repos/vivarium-biosimulators/vivarium_biosimulators/models/BIOMD0000000244_url.xml'
TELLURIUM_PROCESS_CONFIG = {
    'biosimulator_api': 'biosimulators_tellurium',
    'model_language': ModelLanguage.SBML.value,
    'model_source': TELLURIUM_PROCESS_MODEL_SOURCE,
    'emit_ports': ['input', 'output'],
    'simulation': 'steady_state',
}
TELLURIUM_PROCESS_LOGGER = get_logger(TELLURIUM_PROCESS_LOG_DIRPATH, TELLURIUM_PROCESS_LOG_FILENAME)


def orchestrate_processes():
    processes = {
        '0_cobrapy': make_process(
            COBRA_PROCESS_MODEL_SOURCE,
            COBRA_PROCESS_CONFIG,
            COBRA_PROCESS_LOGGER
        ),
        '1_tellurium': make_process(
            TELLURIUM_PROCESS_MODEL_SOURCE,
            TELLURIUM_PROCESS_CONFIG,
            TELLURIUM_PROCESS_LOGGER
        ),
    }
    return processes


if __name__ == '__main__':
    processes = orchestrate_processes()
    for proc in processes:
        print(proc)
