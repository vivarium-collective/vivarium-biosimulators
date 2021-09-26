"""
Execute by running: ``python vivarium_biosimulators/processes/cobra_process.py``
"""
import re
import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulators_process import BiosimulatorsProcess
from vivarium.core.composition import simulate_process
from vivarium.core.control import run_library_cli
from vivarium.core.engine import pf


BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'


def test_cobra_process(
        model_source=BIGG_MODEL_PATH,
):
    import warnings;
    warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.)
    }

    # make the process
    process = BiosimulatorsProcess(config)

    # get initial state
    process_initial_state = process.initial_state()

    # test a process update
    update = process.next_update(1, process_initial_state)
    assert sum(update['outputs'].values()) > 0

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': process_initial_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

    print(pf(output))


test_library = {
    '0': test_cobra_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/experiments/cobra_process.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
