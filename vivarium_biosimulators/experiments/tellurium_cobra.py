"""
Test ODE_FBA by loading biosimulators_tellurium and biosimulators_cobrapy
"""

from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composition import simulate_composite
from vivarium.core.engine import pf
from vivarium.plots.simulation_output import plot_simulation_output, plot_variables
from vivarium_biosimulators.processes.flux_bounds import get_flux_and_bound_ids
from vivarium_biosimulators.composites.ode_fba import ODE_FBA
from vivarium_biosimulators.models.model_paths import MILLARD2016_PATH, BIGG_ECOLI_CORE_PATH
from biosimulators_cobrapy.data_model import KISAO_ALGORITHMS_PARAMETERS_MAP

# Turn off errors when solution not optimal
KISAO_ALGORITHMS_PARAMETERS_MAP['KISAO_0000437']['check_status'] = False


BIGG_MODEL_PATH = BIGG_ECOLI_CORE_PATH
SBML_MODEL_PATH = MILLARD2016_PATH


FLUX_TO_BOUNDS_MAP = {
    # 'GLCp': 'lower_bound_reaction_R_EX_glc__D_e',
    'GLCp': {
        'upper_bound': 'upper_bound_reaction_R_EX_glc__D_e',
        'lower_bound': 'lower_bound_reaction_R_EX_glc__D_e',
        'range': (0.9, 1.1),
    },
    'ACEp': {
        'upper_bound': 'upper_bound_reaction_R_EX_ac_e',
        'lower_bound': 'lower_bound_reaction_R_EX_ac_e',
        'range': (0.9, 1.1),
    },
}


def test_tellurium_cobrapy(
        total_time=10.,
        time_step=1.,
        verbose=False,
):
    import warnings;
    warnings.filterwarnings('ignore')

    # ode_fba configuration
    config = {
        'ode_config': {
            'biosimulator_api': 'biosimulators_tellurium',
            'model_source': SBML_MODEL_PATH,
            'simulation': 'uniform_time_course',
            'model_language': ModelLanguage.SBML.value,
            'algorithm': {
                'kisao_id': 'KISAO_0000019',
            },
            'time_step': time_step,
        },
        'fba_config': {
            'biosimulator_api': 'biosimulators_cobrapy',
            'model_source': BIGG_MODEL_PATH,
            'simulation': 'steady_state',
            'model_language': ModelLanguage.SBML.value,
            'algorithm': {
                'kisao_id': 'KISAO_0000437',
            },
        },
        'flux_to_bound_map': FLUX_TO_BOUNDS_MAP,
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/g/hr',
        'default_store_name': 'state',
    }
    ode_fba_composer = ODE_FBA(config)

    # get initial state from composer
    initial_state = ode_fba_composer.initial_state()
    initial_state['bounds']['upper_bound_reaction_R_EX_glc__D_e'] = 10.
    initial_state['bounds']['lower_bound_reaction_R_EX_glc__D_e'] = -10.
    initial_state['bounds']['upper_bound_reaction_R_EX_ac_e'] = 10.
    initial_state['bounds']['lower_bound_reaction_R_EX_ac_e'] = -10.

    # generate the composite
    ode_fba_composite = ode_fba_composer.generate()

    if verbose:
        print('\nINITIAL STATES:')
        for var_id, val in initial_state['state'].items():
            print(f"{var_id}: {val}")
        print('\nINITIAL FLUXES:')
        for var_id, val in initial_state['fluxes'].items():
            print(f"{var_id}: {val}")
        print('\nODE_FBA TOPOLOGY:')
        print(pf(ode_fba_composite['topology']))
        # print the ode outputs and fba inputs to see what is available
        ode_outputs = [var.id for var in ode_fba_composite['processes']['ode'].outputs]
        fba_inputs = [var for var in ode_fba_composite['processes']['fba'].input_target_map.keys()]
        print('\nODE OUTPUTS:')
        print(ode_outputs)
        print('\nFBA INPUTS:')
        print(fba_inputs)

    # run the simulation
    sim_settings = {
        'total_time': total_time,
        'initial_state': initial_state,
        'display_info': False,
    }
    output = simulate_composite(ode_fba_composite, sim_settings)
    return output


def main():
    output = test_tellurium_cobrapy(
        total_time=3.,
        time_step=1.,
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
    flux_ids, bound_ids = get_flux_and_bound_ids(FLUX_TO_BOUNDS_MAP)
    fluxes = [('fluxes', flux) for flux in flux_ids]
    bounds = [('bounds', bound) for bound in bound_ids]
    plot_variables(
        output,
        variables=[
            ('state', 'R_EX_glc__D_e'),
            ('state', 'GLCx'),
        ] + fluxes + bounds,
        out_dir='out/tellurium_cobrapy',
        filename='tellurium_cobrapy_vars',
    )


# run with python vivarium_biosimulators/experiments/tellurium_cobra.py
if __name__ == '__main__':
    main()
