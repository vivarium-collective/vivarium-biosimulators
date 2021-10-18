"""
Test Biosimulator's Tellurium API
========================================

Execute by running: ``python vivarium_biosimulators/processes/test_tellurium.py``
"""

from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium.core.engine import Engine, pf
from vivarium.core.composer import Composite
from vivarium.core.control import run_library_cli
from vivarium.plots.simulation_output import plot_simulation_output
from vivarium_biosimulators.processes.biosimulator_process import Biosimulator
from vivarium_biosimulators.library.mappings import remove_multi_update
from vivarium_biosimulators.models.model_paths import MILLARD2016_PATH


SBML_MODEL_PATH = MILLARD2016_PATH


def test_tellurium_process(
        total_time=10.,
        time_step=1.,
):
    import warnings; warnings.filterwarnings('ignore')

    # config
    config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': SBML_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
        'emit_ports': ['outputs'],
        'time_step': time_step,
    }

    # make the process
    process = Biosimulator(config)

    # make a composite with a topology, which connects the inputs and outputs
    composite = Composite({
        'processes': {
            'tellurium': process,
        },
        'topology': {
            'tellurium': {
                'outputs': ('state',),
                'inputs': ('state',),
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


def run_once(
    dt=1.,
    total_time=30.,
):
    plot_settings = {'max_rows': 10}
    output = test_tellurium_process(
        total_time=total_time,
        time_step=dt)
    dt_str = str(dt).replace('.', '')
    plot_simulation_output(
        output,
        plot_settings,
        out_dir='out/tellurium',
        filename=f'tellurium_dt={dt_str}_ttotal={total_time}.png',
    )


def scan_dt():
    total_time = 30
    for dt in [1e-1, 1e0, 2e0]:
        run_once(
            dt=dt,
            total_time=total_time,
        )

exp_library = {
    '0': run_once,
    '1': scan_dt,
}

# run with python vivarium_biosimulators/experiments/test_tellurium.py -n [exp_library_id]
if __name__ == '__main__':
    run_library_cli(exp_library)