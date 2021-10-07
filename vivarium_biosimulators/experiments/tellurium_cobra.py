"""
Test ODE_FBA by loading biosimulators_tellurium and biosimulators_cobrapy
"""

from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composition import simulate_composite
from vivarium.core.engine import pf
from vivarium.plots.simulation_output import plot_simulation_output, plot_variables
from vivarium_biosimulators.composites.ode_fba import ODE_FBA
from vivarium_biosimulators.library.mappings import tellurium_mapping
from vivarium_biosimulators.models.model_paths import MILLARD2016_PATH, BIGG_iAF1260b_PATH


BIGG_MODEL_PATH = BIGG_iAF1260b_PATH
SBML_MODEL_PATH = MILLARD2016_PATH

FLUX_TO_BOUNDS_MAP = {
    # 'dynamics_species_GLCp': 'value_parameter_R_EX_glc__D_e_upper_bound',  # use flux of target?
    'dynamics_species_GLCp': 'value_parameter_R_EX_glc__D_e_lower_bound',  # use flux of target?
    # 'dynamics_species_GLCx': 'value_parameter_R_EX_glc__D_e_lower_bound',  # use flux of source?
}


def run_tellurium_cobrapy(
        total_time=2.,
        verbose=False,
):
    import warnings;
    warnings.filterwarnings('ignore')

    # get mapping between inputs (initial variables ids) and output variables in tellurium
    tellurium_input_output_map = tellurium_mapping(SBML_MODEL_PATH)

    # ode_fba configuration
    config = {
        'ode_config': {
            'biosimulator_api': 'biosimulators_tellurium',
            'model_source': SBML_MODEL_PATH,
            'simulation': 'uniform_time_course',
            'model_language': ModelLanguage.SBML.value,
            'algorithm': {
                'kisao_id': 'KISAO_0000019',
            }
        },
        'fba_config': {
            'biosimulator_api': 'biosimulators_cobrapy',
            'model_source': BIGG_MODEL_PATH,
            'simulation': 'steady_state',
            'model_language': ModelLanguage.SBML.value,
            'algorithm': {
                'kisao_id': 'KISAO_0000437',
            }
        },
        'ode_input_to_output_map': tellurium_input_output_map,
        'flux_to_bound_map': FLUX_TO_BOUNDS_MAP,
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/L/s',
        'default_store_name': 'state',
    }
    ode_fba_composer = ODE_FBA(config)

    # get initial state from composer
    initial_state = ode_fba_composer.initial_state()
    initial_state['bounds']['value_parameter_R_EX_glc__D_e_lower_bound'] = -2.0

    # generate the composite
    ode_fba_composite = ode_fba_composer.generate()

    if verbose:
        print('\nINITIAL STATES:')
        for var_id, val in initial_state['state'].items():
            if 'flux_reaction_' not in var_id:
                print(f"{var_id}: {val}")
        print('\nINITIAL FLUXES:')
        for var_id, val in initial_state['fluxes'].items():
            # if 'flux_reaction_' not in var_id:
            print(f"{var_id}: {val}")
        print('\nODE_FBA TOPOLOGY:')
        print(pf(ode_fba_composite['topology']))
        # print the ode outputs and fba inputs to see what is available
        ode_outputs = [var.id for var in ode_fba_composite['processes']['ode'].outputs]
        fba_inputs = [var.id for var in ode_fba_composite['processes']['fba'].inputs]
        print('\nODE OUTPUTS:')
        print(pf(ode_outputs))
        print('\nFBA INPUTS:')
        print(pf(fba_inputs))

    # run the simulation
    sim_settings = {
        'total_time': total_time,
        'initial_state': initial_state,
        'display_info': False,
    }
    output = simulate_composite(ode_fba_composite, sim_settings)
    return output


def main():
    output = run_tellurium_cobrapy(
        total_time=20.,
        verbose=True,
    )

    # plot non-static output
    plot_simulation_output(
        output,
        {
            'max_rows': 25,
            'remove_flat': True,
        },
        out_dir='out/tellurium_cobrapy',
        filename='tellurium_cobrapy',
    )

    # plot specific output variables
    plot_variables(
        output,
        variables=[
            ('fluxes', 'dynamics_species_GLCp'),
            ('bounds', 'value_parameter_R_EX_glc__D_e_lower_bound'),
            ('state', 'flux_reaction_R_EX_glc__D_e'),
            ('state', 'dynamics_species_GLCx'),
        ],
        out_dir='out/tellurium_cobrapy',
        filename='tellurium_cobrapy_vars',
    )


# run with python vivarium_biosimulators/experiments/tellurium_cobra.py
if __name__ == '__main__':
    main()
