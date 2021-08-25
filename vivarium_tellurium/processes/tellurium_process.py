'''
Execute by running: ``python vivarium_tellurium/process/tellurium_process.py``
'''
from vivarium.core.process import Process
from vivarium.core.composition import simulate_process

from biosimulators_tellurium.core import exec_sed_doc_with_tellurium



class TelluriumProcess(Process):
    defaults = {}

    def __init__(self, parameters=None):
        super().__init__(parameters)

    def ports_schema(self):
        return {}

    def next_update(self, timestep, states):
        return {}


def run_tellurium_process():
    parameters = {}
    process = TelluriumProcess(parameters)

    # declare the initial state, mirroring the ports structure
    initial_state = {}

    # run the simulation
    sim_settings = {
        'total_time': 10,
        'initial_state': initial_state}
    output = simulate_process(process, sim_settings)

    return output


if __name__ == '__main__':
    run_tellurium_process()
