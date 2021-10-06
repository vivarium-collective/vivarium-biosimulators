"""
Test BiosimulatorProcess's Tellurium API
========================================

Execute by running: ``python vivarium_biosimulators/processes/test_tellurium.py``
"""

from biosimulators_utils.sedml.data_model import ModelLanguage

from vivarium.core.engine import Engine, pf
from vivarium.core.composer import Composite
from vivarium.plots.simulation_output import plot_simulation_output
from vivarium_biosimulators.library.mappings import tellurium_mapping
from vivarium_biosimulators.processes.biosimulator_process import BiosimulatorProcess
from vivarium_biosimulators.library.mappings import remove_multi_update



SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000244_url.xml'
# SBML_MODEL_PATH = 'vivarium_biosimulators/models/LacOperon_deterministic.xml'


def test_tellurium_process(
        model_source=SBML_MODEL_PATH,
        total_time=5.,
        time_step=1.,
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
        'emit_ports': ['concentrations', 'outputs'],
        'time_step': time_step,
    }

    # make the process
    process = BiosimulatorProcess(config)

    # make a composite with a topology
    # connects initial concentrations to outputs
    rename_concs = {
        input: (output,)
        for input, output in input_output_map.items()
    }
    composite = Composite({
        'processes': {
            'tellurium': process
        },
        'topology': {
            'tellurium': {
                'concentrations': {
                    '_path': ('concentrations',),
                    **rename_concs
                },
                'outputs': ('concentrations',),
                'inputs': ('state',),
                'global': ('global',),
            }
        }
    })

    # get initial state from composite
    initial_state = composite.initial_state()
    initial_state = remove_multi_update(initial_state)

    # make an experiment
    experiment = Engine(
        processes=composite.processes,
        topology=composite.topology,
        initial_state=initial_state,
    )
    # run the simulation
    experiment.update(total_time)

    # get the data
    output = experiment.emitter.get_timeseries()
    # print(pf(output['concentrations']))
    return output


def main():
    output = test_tellurium_process(total_time=1, time_step=0.1)
    settings = {'max_rows': 10}
    plot_simulation_output(output, settings, out_dir='out', filename='tellurium')


# run with python vivarium_biosimulators/experiments/test_tellurium.py
if __name__ == '__main__':
    main()
