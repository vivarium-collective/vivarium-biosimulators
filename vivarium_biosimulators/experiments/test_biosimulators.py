import traceback

from vivarium.core.control import run_library_cli, Control
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulators_process import test_biosimulators_process


SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'
XPP_MODEL_PATH = 'Biosimulators_test_suite/examples/xpp/Wu-Biochem-Pharmacol-2006-pituitary-GH3-cells/GH3_Katp.ode'
RBA_MODEL_PATH = 'Biosimulators_test_suite/examples/rba/Escherichia-coli-K12-WT/model.zip'


# TODO (ERAN): automatically access the ids from BioSimulators
# Python modules can be found at https://api.biosimulators.org/simulators/
# get example models from https://github.com/biosimulators/Biosimulators_test_suite/tree/dev/examples
BIOSIMULATOR_SPECS = [
    {
        'api': 'biosimulators_tellurium',
        'model_source': SBML_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    },
    {
        'api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
    },
    {
        'api': 'biosimulators_cbmpy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
    },
    {
        'api': 'biosimulators_bionetgen',
        'model_source': '',  # add model
        'model_language': ModelLanguage.BNGL.value,
        'simulation': 'uniform_time_course',
    },
    {
        'api': 'biosimulators_gillespy2',
        'model_source': '',  # add model
        'model_language': ModelLanguage.SBML.value,  # Is this correct?
        'simulation': 'uniform_time_course',
    },
    {
        'api': 'biosimulators_libsbmlsim',
        'model_source': '',  # add model
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    },
    {
        'api': 'biosimulators_rbapy',
        'model_source': RBA_MODEL_PATH,
        'model_language': ModelLanguage.RBA.value,
        'simulation': 'uniform_time_course',
    },
    {
        'api': 'biosimulators_xpp',
        'model_source': XPP_MODEL_PATH,
        'model_language': ModelLanguage.XPP.value,
        'simulation': 'uniform_time_course',
    },
]


def test_all_biosimulators(biosimulator_ids=None):
    import warnings; warnings.filterwarnings('ignore')

    for spec in BIOSIMULATOR_SPECS:
        biosimulator_api = spec['api']
        if biosimulator_ids and biosimulator_api not in biosimulator_ids:
            continue

        print(f'TESTING {biosimulator_api}')
        try:
            test_biosimulators_process(
                biosimulator_api=spec['api'],
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

