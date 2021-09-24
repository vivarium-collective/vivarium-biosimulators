import re

from vivarium.core.control import run_library_cli
from vivarium.core.engine import pf
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium_biosimulators.processes.biosimulators_process import (
    BiosimulatorsProcess, test_biosimulators_process)


def tellurium_mapping(config):
    # get initial_state and topology mapping from a configured process
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




def test_tellurium_process():
    import warnings; warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': 'vivarium_biosimulators/models/BIOMD0000000297_url.xml',
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    }

    # get initial_state and topology mapping from a configured process
    initial_state, input_output_map = tellurium_mapping(config)

    # run the biosimulators process
    output = test_biosimulators_process(
        input_output_map=input_output_map,
        initial_state=initial_state,
        **config
    )
    print(pf(output))


test_library = {
    '0': test_tellurium_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/states/mappings.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
