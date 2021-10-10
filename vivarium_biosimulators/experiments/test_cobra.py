"""
Test BiosimulatorProcess's COBRApy API
======================================

Execute by running: ``python vivarium_biosimulators/processes/test_cobra.py``
"""
import os

from vivarium.processes.clock import Clock
from vivarium.core.engine import Engine, pf
from vivarium.core.composer import Composite
from vivarium.plots.simulation_output import plot_simulation_output
from vivarium.core.control import run_library_cli

from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium_biosimulators.library.mappings import remove_multi_update
from vivarium_biosimulators.models.model_paths import BIGG_iAF1260b_PATH, BIGG_ECOLI_CORE_PATH


def test_cobra_process(
    total_time=2.,
    model_source=BIGG_iAF1260b_PATH,
):
    import warnings;
    warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    }

    # make the processes
    # clock makes it save in intervals
    process = BiosimulatorProcess(config)
    clock = Clock()

    # make a composite
    composite = Composite({
        'processes': {
            'cobrapy': process,
            'clock': clock
        },
        'topology': {
            'cobrapy': {
                'outputs': ('state',),
                'inputs': ('state',),
            },
            'clock': {
                'global_time': ('global_time',)
            }
        }
    })

    # get initial state from composite
    initial_state = composite.initial_state()
    initial_state = remove_multi_update(initial_state)

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


def main(model_source=BIGG_iAF1260b_PATH):
    output = test_cobra_process(
        model_source=model_source)
    settings = {'max_rows': 25}
    basename = os.path.basename(model_source)
    model_name = basename.replace('.xml', '')
    plot_simulation_output(
        output,
        settings,
        out_dir='out/cobrapy',
        filename=f'cobrapy_{model_name}'
    )


def run_ecoli_core():
    main(model_source=BIGG_ECOLI_CORE_PATH)


exp_library = {
    '0': main,
    '1': run_ecoli_core,
}


# run with python vivarium_biosimulators/experiments/test_cobra.py -n [exp_library_id]
if __name__ == '__main__':
    run_library_cli(exp_library)
