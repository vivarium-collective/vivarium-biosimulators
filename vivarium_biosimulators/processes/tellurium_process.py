"""
Execute by running: ``python vivarium_biosimulators/processes/tellurium_process.py``
"""
import re
import importlib

from vivarium.core.process import Process
from vivarium.core.composition import simulate_process
from vivarium.core.control import run_library_cli
from vivarium.core.engine import pf

from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, 
    UniformTimeCourseSimulation, ModelLanguage
)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_outputs_for_simulation


def get_delta(before, after):
    return after - before


class TelluriumProcess(Process):
    
    defaults = {
        'model_source': '',
        'time_step': 1.,
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        # import biosimulator module
        biosimulator = importlib.import_module('biosimulators_tellurium')
        self.exec_sed_task = getattr(biosimulator, 'exec_sed_task')
        self.preprocess_sed_task = getattr(biosimulator, 'preprocess_sed_task')

        # get the model
        model = Model(
            id='model',
            source=self.parameters['model_source'],
            language=ModelLanguage.SBML.value,
        )

        # get the simulation
        simulation = UniformTimeCourseSimulation(
            id='simulation',
            initial_time=0.,
            output_start_time=0.,
            number_of_points=1,
            output_end_time=self.parameters['time_step'],
            algorithm=Algorithm(kisao_id='KISAO_0000019'),
        )

        # make the task
        self.task = Task(
            id='task',
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        inputs, _, outputs, _ = get_parameters_variables_outputs_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__,
            algorithm_kisao_id=simulation.algorithm.kisao_id,
        )

        self.variable_types = [
            {
                'id': 'species concentrations/amounts',
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfSpecies',
                'in': True,
                'out': True,
            },
            {
                'id': 'parameter values',
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfParameters',
                'in': True,
                'out': True,
            },
            {
                'id': 'reaction fluxes',
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfReactions',
                'in': False,
                'out': True,
            },
            {
                'id': 'compartment sizes',
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfCompartments',
                'in': True,
                'out': True,
            },
        ]

        self.variables = {'__all__': []}
        for variable_type in self.variable_types:
            variables = list(filter(
                lambda var: var.target and var.target.startswith(variable_type['xpath_prefix']), outputs))
            self.variables[variable_type['id']] = variables
            self.variables['__all__'] += self.variables[variable_type['id']]

        self.variable_id_target_map = {}
        for variable in self.variables['__all__']:
            variable.task = self.task
            self.variable_id_target_map[variable.id] = variable.target

        self.config = Config(LOG=False)

        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.variables['__all__'],
            config=self.config,
        )

        # extract initial state
        self.initial_model_state = {
            'species concentrations/amounts': {}
        }
        for parameter in inputs:
            if parameter.target and parameter.target.endswith('@initialConcentration'):
                name = re.search('"(.*)"', parameter.name).group(1)
                self.initial_model_state[
                    'species concentrations/amounts']['dynamics_species_' + name] = float(parameter.new_value)

    def initial_state(self, config=None):
        return self.initial_model_state

    def ports_schema(self):
        schema = {
            'global_time': {'_default': 0.}
        }
        for variable_type in self.variable_types:
            variables = self.variables[variable_type['id']]
            schema[variable_type['id']] = {
                variable.id: {
                    '_default': 0.0,
                    '_updater': 'accumulate' if variable_type['in'] else 'null',
                    '_emit': True,
                } for variable in variables
            }
        return schema

    def next_update(self, interval, states):

        global_time = states['global_time']

        # update model based on current state
        self.task.changes = []
        for variable_type in self.variable_types:
            if variable_type['in']:
                variable_states = states[variable_type['id']]
                if variable_states:
                    for variable_id, variable_value in variable_states.items():
                        self.task.changes.append(ModelAttributeChange(
                            target=self.variable_id_target_map[variable_id],
                            new_value=variable_value,
                        ))
        # set the simulation time
        self.task.simulation.initial_time = global_time
        self.task.simulation.output_start_time = global_time
        self.task.simulation.output_end_time = global_time + interval

        # execute step
        raw_results, log = self.exec_sed_task(
            self.task,
            self.variables['__all__'],
            preprocessed_task=self.preprocessed_task,
            config=self.config,
        )

        # transform results
        results = {}
        for variable_type in self.variable_types:
            variable_type_id = variable_type['id']
            variables = self.variables[variable_type_id]
            if variables:
                results[variable_type_id] = {
                    variable.id: get_delta(
                        states[variable_type_id][variable.id],
                        raw_results[variable.id][-1])
                    for variable in variables
                }
        return results



def test_tellurium_process(
        model_source='vivarium_biosimulators/models/BIOMD0000000297_url.xml',
):
    import warnings; warnings.filterwarnings('ignore')
    
    config = {
        'model_source': model_source,
    }
    process = TelluriumProcess(config)

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': process.initial_state(),
        'display_info': False}
    output = simulate_process(process, sim_settings)

    print(pf(output))
    return output


test_library = {
    '0': test_tellurium_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/processes/tellurium_process.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
