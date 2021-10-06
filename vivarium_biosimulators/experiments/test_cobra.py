"""
Test BiosimulatorProcess's COBRApy API
======================================

Execute by running: ``python vivarium_biosimulators/processes/test_cobra.py``
"""
from vivarium.processes.clock import Clock
from vivarium.core.engine import Engine, pf
from vivarium.core.composer import Composite
from vivarium.plots.simulation_output import plot_simulation_output

from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium_biosimulators.library.mappings import remove_multi_update



BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'


def test_cobra_process(
        model_source=BIGG_MODEL_PATH,
        total_time=2.,
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


def main():
    output = test_cobra_process()
    settings = {'max_rows': 25}
    plot_simulation_output(output, settings, out_dir='out', filename='cobrapy')


# run with python vivarium_biosimulators/experiments/test_cobra.py
if __name__ == '__main__':
    main()
