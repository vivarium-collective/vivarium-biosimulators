"""
Execute by running: ``python vivarium_biosimulators/processes/tellurium_process.py``
"""
import re
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulators_process import BiosimulatorsProcess
from vivarium.core.composition import simulate_process
from vivarium.core.engine import pf

SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'


def tellurium_mapping(model_source):
    # get initial_state and topology mapping from a configured process
    config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    }
    process = BiosimulatorsProcess(config)
    initial_state = {}
    input_output_map = {}
    for input_variable in process.inputs:
        if input_variable.target and input_variable.target.endswith('@initialConcentration'):
            input_name = input_variable.id
            output_name = 'dynamics_species_' + re.search('"(.*)"', input_variable.name).group(1)
            initial_state[output_name] = float(input_variable.new_value)
            input_output_map[input_name] = (output_name,)
    return initial_state, input_output_map



def test_tellurium_process(
        model_source=SBML_MODEL_PATH,
):
    import warnings; warnings.filterwarnings('ignore')

    # update ports based on input_output_map
    initial_state, input_output_map = tellurium_mapping(model_source)
    input_variable_names = list(input_output_map.keys())
    config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
        'input_ports': {
            'concentrations': input_variable_names,
            'size': 'init_size_compartment_compartment',
        },
        'output_ports': {
            'time': 'time'
        }
    }
    
    # make the process
    process = BiosimulatorsProcess(config)

    # assert that port_assignment works
    process_initial_state = process.initial_state()
    assert list(process_initial_state['concentrations'].keys()) == input_variable_names

    # test a process update
    update = process.next_update(1, process_initial_state)
    # TODO(ERAN) -- add an assert

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': process_initial_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

    print(pf(output))


if __name__ == '__main__':
    test_tellurium_process()
