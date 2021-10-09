"""
Test BiosimulatorProcess's COBRApy API
======================================

Execute by running: ``python vivarium_biosimulators/processes/test_cobra.py``
"""
import numpy as np
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium_biosimulators.library.mappings import remove_multi_update
from vivarium_biosimulators.models.model_paths import BIGG_iAF1260b_PATH
from vivarium.core.composition import simulate_process
from vivarium.core.engine import pf


BIGG_MODEL_PATH = BIGG_iAF1260b_PATH


def test_cobra_process(
        total_time=2.,
        model_source=BIGG_MODEL_PATH,
):
    import warnings;
    warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': 'biosimulators_cobrapy',
        'model_source': BIGG_MODEL_PATH,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'steady_state',
        'default_output_value': np.array(0.),
        'algorithm': {
            'kisao_id': 'KISAO_0000437',
        }
    }

    # make the process
    process = BiosimulatorProcess(config)

    # get initial state
    process_initial_state = process.initial_state()

    # test a process update
    update = process.next_update(1, process_initial_state)
    # assert that fluxes did not change (delta is 0)
    assert sum(update['outputs'].values()) == 0

    # run the simulation
    sim_settings = {
        'total_time': 2.,
        'initial_state': process_initial_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

def main():
    output = test_cobra_process()
    settings = {'max_rows': 25}
    # plot_simulation_output(
    #     output,
    #     settings,
    #     out_dir='out/cobrapy',
    #     filename='cobrapy'
    # )
    print(pf(output))


# run with python vivarium_biosimulators/experiments/test_cobra.py
if __name__ == '__main__':
    test_cobra_process()
