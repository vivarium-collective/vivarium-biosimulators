from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess


def tellurium_mapping(model_source):
    """
    get mapping of names between input and output ports
    from a configured tellurium process
    """
    config = {
        'biosimulator_api': 'biosimulators_tellurium',
        'model_source': model_source,
        'model_language': ModelLanguage.SBML.value,
        'simulation': 'uniform_time_course',
    }
    process = BiosimulatorProcess(config)
    input_output_map = {}
    for variable in process.inputs:
        if variable.target and variable.target.endswith('@initialConcentration'):
            input_name = variable.id
            output_name = input_name.replace('init_conc_species_', 'dynamics_species_')
            input_output_map[input_name] = output_name
    return input_output_map