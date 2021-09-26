import traceback
import numpy as np

from vivarium.core.composition import simulate_process
from vivarium.core.control import Control
from vivarium_biosimulators.processes.biosimulators_process import BiosimulatorsProcess
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
    },
    {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.)
    },
    {
        'biosimulator_api': 'biosimulators_cbmpy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
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
    },
    {
        'biosimulator_api': 'biosimulators_xpp',
        'model_source': XPP_MODEL_PATH,
        'model_language': ModelLanguage.XPP.value,
        'simulation': 'uniform_time_course',
    },
]


def test_biosimulators_process(
        biosimulator_api,
        model_source,
        model_language=ModelLanguage.SBML.value,
        simulation='uniform_time_course',
        initial_state=None,
        input_output_map=None,
        total_time=10.,
):
    """Test BiosimulatorProcess with an API and model

    Load BiosimulatorProcess with a single Biosimulator API and model, and run it
    """
    import warnings; warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': biosimulator_api,
        'model_source': model_source,
        'model_language':  model_language,
        'simulation': simulation,
    }
    process = BiosimulatorsProcess(config)

    # make a topology
    topology = {
        'global_time': ('global_time',),
        'input': ('state',) if not input_output_map else {
            **{'_path': ('state',)},
            **input_output_map,
        },
        'output': ('state',)
    }

    # get initial_state
    initial_state = initial_state or {}
    initial_model_state = {'state': initial_state} or process.initial_state()

    # run the simulation
    sim_settings = {
        'topology': topology,
        'total_time': total_time,
        'initial_state': initial_model_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

    return output


def test_all_biosimulators(biosimulator_ids=None):
    """
    Runs test_biosimulators_process with any number of the available Biosimulator APIs
    """
    import warnings; warnings.filterwarnings('ignore')

    for spec in BIOSIMULATOR_SPECS:
        biosimulator_api = spec['biosimulator_api']
        if biosimulator_ids and biosimulator_api not in biosimulator_ids:
            continue

        print(f'TESTING {biosimulator_api}')
        try:
            test_biosimulators_process(
                biosimulator_api=spec['biosimulator_api'],
                model_language=spec['model_language'],
                model_source=spec['model_source'],
                simulation=spec['simulation'],
            )
            print('...PASS!')
        except:
            print('...FAIL!')
            traceback.print_exc()


test_library = {
    '0': test_all_biosimulators,
}
workflow_library = {
    'all': {
        'experiment': '0'
    },
    'tellurium': {
        'experiment': {
            'experiment_id': '0',
            'biosimulator_ids': 'biosimulators_tellurium'
        },
    },
    'cobra': {
        'experiment': {
            'experiment_id': '0',
            'biosimulator_ids': 'biosimulators_cobrapy'
        },
    }
}

# run methods in workflow_library from the command line with:
# python vivarium_biosimulators/experiments/test_biosimulators.py -w [workflow id]
if __name__ == '__main__':
    Control(
        experiments=test_library,
        workflows=workflow_library,
    )

