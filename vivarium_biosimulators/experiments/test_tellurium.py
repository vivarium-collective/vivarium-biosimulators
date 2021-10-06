"""
Test BiosimulatorProcess's Tellurium API
========================================

Execute by running: ``python vivarium_biosimulators/processes/test_tellurium.py``
"""

from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium_biosimulators.library.mappings import tellurium_mapping
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium.core.composition import simulate_process
from vivarium.core.engine import pf

# SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
SBML_MODEL_PATH = 'vivarium_biosimulators/models/LacOperon_deterministic.xml'


def test_tellurium_process(
        model_source=SBML_MODEL_PATH,
):
    import warnings; warnings.filterwarnings('ignore')

    # update ports based on input_output_map
    input_output_map = tellurium_mapping(model_source)
    input_variable_names = list(input_output_map.keys())
    config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
        'input_ports': {
            'concentrations': input_variable_names,
        },
        'output_ports': {
            'time': 'time'
        }
    }
    
    # make the process
    process = BiosimulatorProcess(config)

    # declare the topology
    # connect initial concentrations to outputs
    rename_concs = {
        input: (output,)
        for input, output in input_output_map.items()
    }
    topology = {
        'concentrations': {
            '_path': ('concentrations',),
            **rename_concs
        },
        'outputs': ('concentrations',),
    }

    # assert that port_assignment works
    process_initial_state = process.initial_state()
    assert list(process_initial_state['concentrations'].keys()) == input_variable_names

    # test a process update
    update = process.next_update(1, process_initial_state)
    # assert values remain positive after update added
    assert sum([process_initial_state['outputs'][name]+value
                for name, value in update['outputs'].items()]) > 0

    # rename initial concentrations variables according to input_output_map
    init_concentrations = process_initial_state['concentrations']
    process_initial_state['concentrations'] = {
        input_output_map[input_name]: value
        for input_name, value in init_concentrations.items()
    }
    del process_initial_state['outputs']  # outputs port maps to concentration

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'topology': topology,
        'initial_state': process_initial_state,
        'display_info': False,
    }
    output = simulate_process(process, sim_settings)

    print(pf(output))

# run with python vivarium_biosimulators/experiments/test_tellurium.py
if __name__ == '__main__':
    test_tellurium_process()
