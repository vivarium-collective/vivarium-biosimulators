from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess


def tellurium_mapping(
        model_source,
):
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
        if variable.target and (
                variable.target.endswith('@initialConcentration') or
                variable.target.endswith('@initialAmount')
        ):
            input_name = variable.id
            if 'init_conc_' in input_name:
                output_name = input_name.replace('init_conc_', 'dynamics_')
            elif 'init_amount_' in input_name:
                output_name = input_name.replace('init_amount_', 'dynamics_')
            input_output_map[input_name] = output_name

    return input_output_map


def remove_multi_update(d):
    new = {}
    for k, v in d.items():
        if isinstance(v, dict):
            if '_multi_update' in v:
                new[k] = v['_multi_update'][0]
            else:
                new[k] = remove_multi_update(v)
        else:
            new[k] = v
    return new
