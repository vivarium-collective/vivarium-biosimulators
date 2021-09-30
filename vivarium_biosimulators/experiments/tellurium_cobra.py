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
        'flux_to_bound_map': {
            'dynamics_species_Glucose_internal': 'value_parameter_R_EX_glc__D_e_lower_bound',
            # 'dynamics_species_Lactose_consumed': 'EX_lac__D_e', # TODO -- need to register EX_lac__D_e as an FBA parameter...
        }
    }
    ode_fba_composite = ODE_FBA(config).generate()

    # print the ode outputs and fba inputs to see what is available
    ode_outputs = [var.id for var in ode_fba_composite['processes']['ode'].outputs]
    fba_inputs = [var.id for var in ode_fba_composite['processes']['fba'].inputs]
    print('ODE OUTPUTS')
    print(pf(ode_outputs))
    print('FBA INPUTS')
    print(pf(fba_inputs))

    # get initial state from composite
    initial_state = ode_fba_composite.initial_state()

    # print initial state
    print('INITIAL STATES')
    for var_id, val in initial_state['state'].items():
        if 'dynamics_species_' in var_id:
            print(f"{var_id}: {val}")
    print('INITIAL FLUXES')
    for var_id, val in initial_state['fluxes'].items():
        if 'dynamics_species_' in var_id:
            print(f"{var_id}: {val}")

    # TODO -- initial states are not extracted from ODE model... all zeros
    # import ipdb; ipdb.set_trace()

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
