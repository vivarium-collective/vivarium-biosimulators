import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composition import simulate_composite
from vivarium.core.engine import pf

from vivarium_biosimulators.composites.ode_fba import SBML_MODEL_PATH, BIGG_MODEL_PATH, ODE_FBA


def test_tellurium_cobrapy(
        total_time=10.,
):
    config = {
        'ode_config': {
            'biosimulators_api': 'biosimulators_tellurium',
            'model_source': SBML_MODEL_PATH,
            'simulation': 'uniform_time_course',
            'model_language': ModelLanguage.SBML.value,
        },
        'fba_config': {
            'biosimulators_api': 'biosimulators_cobrapy',
            'model_source': BIGG_MODEL_PATH,
            'simulation': 'steady_state',
            'model_language': ModelLanguage.SBML.value,
            'default_output_value': np.array(0.)
        },
        'flux_map': {}
    }
    ode_fba = ODE_FBA(config).generate()

    # initial state
    initial_state = {}

    # run the simulation
    sim_settings = {
        'total_time': total_time,
        'initial_state': initial_state,
        'display_info': False}
    output = simulate_composite(ode_fba, sim_settings)

    print(pf(output))


if __name__ == '__main__':
    test_tellurium_cobrapy()