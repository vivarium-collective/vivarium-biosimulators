import os
from typing import List
import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage

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
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
        'total_time': 10.,
    },
    {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    },
    {
        'biosimulator_api': 'biosimulators_cbmpy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    },
    {
        'biosimulator_api': 'biosimulators_bionetgen',
        'model_source': BNGL_MODEL_PATH,
        'model_language': ModelLanguage.BNGL.value,
        'simulation': 'uniform_time_course',
    },
    {
        'biosimulator_api': 'biosimulators_gillespy2',
        'model_source': SBML_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    },
    {
        'biosimulator_api': 'biosimulators_libsbmlsim',
        'model_source': SBML_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    },
    {
        'biosimulator_api': 'biosimulators_rbapy',
        'model_source': RBA_MODEL_PATH,
        'model_language': ModelLanguage.RBA.value,
        'simulation': 'steady_state',
        'algorithm': {
            'kisao_id': 'KISAO_0000669',
        }
    },
    {
        'biosimulator_api': 'biosimulators_xpp',
        'model_source': XPP_MODEL_PATH,
        'model_language': ModelLanguage.XPP.value,
        'simulation': 'uniform_time_course',
    },
]


def GET_ALL_MODEL_FILES(root: str = 'vivarium_biosimulators/models') -> List[str]:
    '''
    Returns all filepaths in dedicated repo model directory.\n
    Args:\n
    :param:`root(`str`)`: base path of dedicated models directory. Defaults to 'vivarium_biosimulators/models'.
    '''
    return [os.path.join(root, p) for p in os.listdir(root)]
