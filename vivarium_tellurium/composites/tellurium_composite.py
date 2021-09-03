"""
Execute by running: ``python vivarium_tellurium/composites/tellurium_composite.py``
"""
from vivarium.core.composer import Composer
from vivarium.core.composition import simulate_composite
from vivarium_tellurium.processes.tellurium_process import TelluriumProcess

class TelluriumComposer(Composer):
    defaults = {
        'models': {}
    }

    def __init__(self, config):
        super().__init__(config)
        self.topology = {}

    def generate_processes(self, config):
        processes = {}
        for model_name, sbml_path in config['models'].items():
            parameters = {'sbml_path': sbml_path}
            process = TelluriumProcess(parameters)
            processes[model_name] = process
            self.topology[model_name] = {
                port: (port,)
                for port in process.get_schema().keys()}
        return processes

    def generate_topology(self, config):
        return self.topology


def test_tellurium_composite():
    config = {
        'models': {
            'morphogenesis': 'vivarium_tellurium/models/BIOMD0000000297_url.xml',
        }
    }
    composer = TelluriumComposer(config)
    composite = composer.generate()

    # get the initial state
    initial_state = composite.initial_state()

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': initial_state}
    output = simulate_composite(composite, sim_settings)

    return output

if __name__ == '__main__':
    test_tellurium_composite()
