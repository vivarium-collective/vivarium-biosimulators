from vivarium.core.composition import simulate_process
from vivarium_biosimulators.processes.generic_process import GenericSimulatorProcess, SimulatorConfig


def execute():

    tellurium_process_config = SimulatorConfig(
        api='tellurium',
        input_ports=None,
        output_ports=None,
        default_input_port_name='input',
        default_output_port_name='output',
        emit_ports=['output'],
        algorithm={
            'kisao_id': 'KISAO_0000019',
        },
        _parallel=True
    )

    tellurium_process = GenericSimulatorProcess(
        parameters=None,
        simulator_config=tellurium_process_config
    )

    # make a topology
    topology = {
        'global_time': ('global_time',),
    }

    total_time = 100

    def get_initial_model_state(process, initial_state=None):
        initial_state = initial_state or {}
        return process.initial_state() if not initial_state else {'state': initial_state}

    # get initial_state
    initial_model_state = get_initial_model_state(process=tellurium_process, initial_state=None)
    # run the simulation
    sim_settings = {
        'topology': topology,
        'total_time': total_time,
        'initial_state': initial_model_state,
        'display_info': False}
    output = simulate_process(tellurium_process, sim_settings)
    return output


if __name__ == '__main__':
    execute()
