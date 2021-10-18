"""
Test Biosimulator's COBRApy API
======================================

Execute by running: ``python vivarium_biosimulators/processes/test_cobra.py``

TODO:
 - test parsimonious fba: KISAO_0000528
 - test geometric fba: KISAO_0000527
 - test linear moma fba: KISAO_0000579  (not yet mapped to methods in cobrapy)
 - test quadratic moma fba: KISAO_0000593  (not yet mapped to methods in cobrapy)
"""
import os

from vivarium.processes.timeline import TimelineProcess
from vivarium.core.engine import Engine, pf
from vivarium.core.composer import Composite
from vivarium.library.dict_utils import deep_merge
from vivarium.plots.simulation_output import plot_simulation_output
from vivarium.core.control import run_library_cli

from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulator_process import Biosimulator
from vivarium_biosimulators.library.mappings import remove_multi_update
from vivarium_biosimulators.models.model_paths import BIGG_iAF1260b_PATH, BIGG_ECOLI_CORE_PATH


def test_cobra_process(
    total_time=2.,
    model_source=BIGG_iAF1260b_PATH,
    kisao_id='KISAO_0000437',
    change_initial_state=None,
    timeline=None,
):
    import warnings;
    warnings.filterwarnings('ignore')
    change_initial_state = change_initial_state or {}
    timeline = timeline or [(total_time, {('state',): None})]
    total_time = timeline[-1][0]  # use the last element of the timeline

    config = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'algorithm': {
            'kisao_id': kisao_id,
        }
    }

    # make the processes
    # timeline adds perturbations to inputs
    process = Biosimulator(config)
    timeline_process = TimelineProcess({'timeline': timeline})

    # make a composite
    composite = Composite({
        'processes': {
            'timeline': timeline_process,
            'cobrapy': process,
        },
        'topology': {
            'timeline': {
                'global': ('global',),
                'state': ('state',)
            },
            'cobrapy': {
                'outputs': ('state',),
                'inputs': ('state',),
            },
        }
    })

    # get initial state from composite
    initial_state = composite.initial_state()
    initial_state = remove_multi_update(initial_state)
    initial_state = deep_merge(initial_state, change_initial_state)

    # make an experiment
    experiment = Engine(
        processes=composite.processes,
        topology=composite.topology,
        initial_state=initial_state,
    )
    # run the simulation
    experiment.update(total_time)

    # get the data
    output = experiment.emitter.get_timeseries()
    return output


def main(model_source=BIGG_iAF1260b_PATH, **kwargs):
    output = test_cobra_process(
        model_source=model_source,
        **kwargs,
    )
    settings = {'max_rows': 25}
    basename = os.path.basename(model_source)
    model_name = basename.replace('.xml', '')
    plot_simulation_output(
        output,
        settings,
        out_dir='out/cobrapy',
        filename=f'cobrapy_{model_name}'
    )

def run_iAF1260b():
    main(
        model_source=BIGG_iAF1260b_PATH,
        change_initial_state={
            'state': {
                'upper_bound_reaction_R_EX_glc__D_e': 55,
                'lower_bound_reaction_R_EX_glc__D_e': -7.5,
            }
        },
    )

def run_ecoli_core():
    timeline = [
        (0, {
            ('state', 'lower_bound_reaction_R_EX_glc__D_e'): -10,
        }),
        (1, {
            ('state', 'lower_bound_reaction_R_EX_glc__D_e'): -8,
        }),
        (2, {
            ('state', 'lower_bound_reaction_R_EX_glc__D_e'): -6,
        }),
        (3, {
            ('state', 'lower_bound_reaction_R_EX_glc__D_e'): -4,
        }),
        (4, {})
    ]
    main(
        model_source=BIGG_ECOLI_CORE_PATH,
        timeline=timeline,
    )


exp_library = {
    '0': run_ecoli_core,
    '1': run_iAF1260b,
}


# run with python vivarium_biosimulators/experiments/test_cobra.py -n [exp_library_id]
if __name__ == '__main__':
    run_library_cli(exp_library)
