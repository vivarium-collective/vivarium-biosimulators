import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composition import simulate_composite
from vivarium.core.engine import pf

from vivarium_biosimulators.composites.ode_fba import ODE_FBA

SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'


def test_tellurium_cobrapy(
        tellurium_model=SBML_MODEL_PATH,
        cobra_model=BIGG_MODEL_PATH,
        total_time=2.,
):
    import warnings;
    warnings.filterwarnings('ignore')

    config = {
        'ode_config': {
            'biosimulator_api': 'biosimulators_tellurium',
            'model_source': tellurium_model,
            'simulation': 'uniform_time_course',
            'model_language': ModelLanguage.SBML.value,
        },
        'fba_config': {
            'biosimulator_api': 'biosimulators_cobrapy',
            'model_source': cobra_model,
            'simulation': 'steady_state',
            'model_language': ModelLanguage.SBML.value,
            'default_output_value': np.array(0.)
        },
        'flux_map': {}
    }
    ode_fba_composite = ODE_FBA(config).generate()

    # initial state
    initial_state = {}

    # run the simulation
    sim_settings = {
        'total_time': total_time,
        'initial_state': initial_state,
        'display_info': False}
    output = simulate_composite(ode_fba_composite, sim_settings)

    print(pf(output))
    # import ipdb; ipdb.set_trace()


# run with python vivarium_biosimulators/experiments/tellurium_cobra.py
if __name__ == '__main__':
    test_tellurium_cobrapy()
    