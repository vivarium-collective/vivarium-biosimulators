import traceback

from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium_biosimulators.processes.biosimulators_process import test_biosimulators_process


SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'


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
        'simulation': 'steady_state',
    },
    {
        'api': 'biosimulators_cbmpy',
        'simulation': 'steady_state',
    },
    {
        'api': 'biosimulators_bionetgen',
        'model_language': ModelLanguage.BNGL.value,
    },
    {
        'api': 'biosimulators_gillespy2',
    },
    {
        'api': 'biosimulators_libsbmlsim',
    },
    {
        'api': 'biosimulators_rbapy',
    },
    {
        'api': 'biosimulators_xpp',
        'model_language': ModelLanguage.XPP.value,
    },
]


def test_all_biosimulators():
    for spec in BIOSIMULATOR_SPECS:
        biosimulator_api = spec['api']
        model_language = spec.get('model_language', ModelLanguage.SBML.value)
        model_source = spec.get('model_source', SBML_MODEL_PATH)
        simulation = spec.get('simulation', 'uniform_time_course')

        print(f'TESTING {biosimulator_api}')
        try:
            test_biosimulators_process(
                biosimulator_api=biosimulator_api,
                model_language=model_language,
                model_source=model_source,
                simulation=simulation,
            )
            print('...PASS!')
        except:
            print('...FAIL!')
            traceback.print_exc()

if __name__ == '__main__':
    test_all_biosimulators()
