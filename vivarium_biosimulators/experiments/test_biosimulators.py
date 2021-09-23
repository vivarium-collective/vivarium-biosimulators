import traceback

from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium_biosimulators.processes.biosimulators_process import test_biosimulators_process


SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'
XPP_MODEL_PATH = '../Biosimulators_test_suite/examples/xpp/Wu-Biochem-Pharmacol-2006-pituitary-GH3-cells/GH3_Katp.ode'
RBA_MODEL_PATH = '../Biosimulators_test_suite/examples/rba/Escherichia-coli-K12-WT/model.zip'


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


def test_all_biosimulators():
    import warnings; warnings.filterwarnings('ignore')

    for spec in BIOSIMULATOR_SPECS:
        biosimulator_api = spec['api']
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

if __name__ == '__main__':
    test_all_biosimulators()
