from vivarium.core.composition import simulate_process
from vivarium.core.control import Control
from vivarium_biosimulators.processes.biosimulator_process import Biosimulator


class ProcessController:
    def __init__(self, process_id: str = None):
        self.process_id = process_id

    def run_biosimulator_process(
            self,
            initial_state=None,
            input_output_map=None,
            total_time=1.,
            **config,
    ):
        """Test Biosimulator with an API and model

        Load Biosimulator with a single Biosimulator API and model, and run it
        """
        import warnings
        warnings.filterwarnings('ignore')

        # initialize the biosimulator process
        process = Biosimulator(config)

        # make a topology
        topology = {
            'global_time': ('global_time',),
            'input': ('state',) if not input_output_map else {
                **{'_path': ('state',)},
                **input_output_map,
            },
            'output': ('state',)
        }

        # get initial_state
        initial_model_state = self.get_initial_model_state(process=process, initial_state=initial_state)

        # run the simulation
        sim_settings = {
            'topology': topology,
            'total_time': total_time,
            'initial_state': initial_model_state,
            'display_info': False}
        output = simulate_process(process, sim_settings)

        return output

    def get_initial_model_state(self, process: Biosimulator, initial_state=None):
        initial_state = initial_state or {}
        return process.initial_state() if not initial_state else {'state': initial_state}
