import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composition import simulate_composite
from vivarium.core.engine import pf

from vivarium_biosimulators.composites.ode_fba import ODE_FBA
from vivarium_biosimulators.library.mappings import tellurium_mapping

SBML_MODEL_PATH = 'vivarium_biosimulators/models/LacOperon_deterministic.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'
# SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000244_url.xml'


def test_tellurium_cobrapy(
        tellurium_model=SBML_MODEL_PATH,
        cobra_model=BIGG_MODEL_PATH,
        total_time=2.,
):
    import warnings;
    warnings.filterwarnings('ignore')

    # get mapping between inputs (initial variables ids) and output variables in tellurium
    tellurium_input_output_map = tellurium_mapping(tellurium_model)

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
            'default_output_value': np.array(0.),
            'algorithm': {
                'kisao_id': 'KISAO_0000437',
            }
        },
        'ode_input_to_output_map': tellurium_input_output_map,
        'flux_to_bound_map': {
            'dynamics_species_Glucose_internal': 'value_parameter_R_EX_glc__D_e_lower_bound',
            # 'dynamics_species_Glucose_internal': 'value_parameter_R_EX_glc__D_e_upper_bound',
            # 'dynamics_species_Lactose_consumed': 'value_parameter_R_EX_lac__D_e_lower_bound',
            # 'dynamics_species_Lactose_consumed': 'value_parameter_R_EX_lac__D_e_upper_bound',
            # TODO upper/lower bounds? these need to connect to flux_to_bounds converter
        }
    }
    ode_fba_composer = ODE_FBA(config)

    # get initial state from composer
    initial_state = ode_fba_composer.initial_state()

    print('INITIAL STATES:\n==============')
    for var_id, val in initial_state['state'].items():
        if 'dynamics_species_' in var_id:
            print(f"{var_id}: {val}")
    print('INITIAL FLUXES:\n==============')
    for var_id, val in initial_state['fluxes'].items():
        if 'dynamics_species_' in var_id:
            print(f"{var_id}: {val}")

    # generate the composite
    ode_fba_composite = ode_fba_composer.generate()

    print('ODE_FBA TOPOLOGY:\n================')
    print(pf(ode_fba_composite['topology']))
    # print the ode outputs and fba inputs to see what is available
    ode_outputs = [var.id for var in ode_fba_composite['processes']['ode'].outputs]
    fba_inputs = [var.id for var in ode_fba_composite['processes']['fba'].inputs]
    print('ODE OUTPUTS:\n===========')
    print(pf(ode_outputs))
    print('FBA INPUTS:\n==========')
    print(pf(fba_inputs))

    # run the simulation
    sim_settings = {
        'total_time': total_time,
        'initial_state': initial_state,
        'display_info': False}
    output = simulate_composite(ode_fba_composite, sim_settings)

    print(pf(output))


# run with python vivarium_biosimulators/experiments/tellurium_cobra.py
if __name__ == '__main__':
    test_tellurium_cobrapy()
