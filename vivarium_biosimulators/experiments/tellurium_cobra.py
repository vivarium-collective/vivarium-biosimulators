import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composition import simulate_composite
from vivarium.core.engine import pf

from vivarium_biosimulators.composites.ode_fba import ODE_FBA
from vivarium_biosimulators.library.mappings import tellurium_mapping

SBML_MODEL_PATH = 'vivarium_biosimulators/models/LacOperon_deterministic.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'


def test_tellurium_cobrapy(
        tellurium_model=SBML_MODEL_PATH,
        cobra_model=BIGG_MODEL_PATH,
        total_time=10.,
):
    import warnings;
    warnings.filterwarnings('ignore')

    # update ports based on input_output_map
    tellurium_input_output_map = tellurium_mapping(tellurium_model)
    tellurium_input_variable_names = list(tellurium_input_output_map.keys())

    # TODO -- declare mapping between ode and fba models

    # ode_fba configuration
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
        'ode_input_ports': {
            'concentrations': tellurium_input_variable_names,
        },
        'ode_output_ports': {
            'time': 'time'
        },
        'flux_map': {}
    }
    ode_fba_composite = ODE_FBA(config).generate()

    # initial state
    ode_inputs = ode_fba_composite['processes']['ode'].inputs
    ode_outputs = ode_fba_composite['processes']['ode'].outputs
    fba_inputs = ode_fba_composite['processes']['fba'].inputs
    fba_outputs = ode_fba_composite['processes']['fba'].outputs

    initial_state = ode_fba_composite.initial_state()

    # TODO -- make the initial state


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
