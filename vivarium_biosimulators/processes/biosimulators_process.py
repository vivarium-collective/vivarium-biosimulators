'''
Execute by running: ``python vivarium_biosimulators/processes/biosimulators_process.py``
'''
import re

from vivarium.core.process import Process
from vivarium.core.composition import simulate_process

from biosimulators_tellurium.core import exec_sed_task, preprocess_sed_task
from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, UniformTimeCourseSimulation, ModelLanguage)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_for_simulation


class BiosimulatorsProcess(Process):
    defaults = {
        'sbml_path': '',
        'time_step': 1.,
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        model = Model(
            id='model',
            source=self.parameters['sbml_path'],
            language=ModelLanguage.SBML.value,
        )
        simulation = UniformTimeCourseSimulation(
            id='simulation',
            initial_time=0.,
            output_start_time=0.,
            number_of_points=1,
            output_end_time=self.parameters['time_step'],
            algorithm=Algorithm(kisao_id='KISAO_0000019'),
        )
        self.task = Task(
            id='task',
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        (parameters, _, all_variables) = get_parameters_variables_for_simulation(
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
            variables = list(filter(lambda var: var.target and var.target.startswith(variable_type['xpath_prefix']), all_variables))
            self.variables[variable_type['id']] = variables
            self.variables['__all__'] += self.variables[variable_type['id']]

        self.variable_id_target_map = {}
        for variable in self.variables['__all__']:
            variable.task = self.task
            self.variable_id_target_map[variable.id] = variable.target

        self.config = Config(LOG=False)

        self.preprocessed_task = preprocess_sed_task(self.task, self.variables['__all__'], config=self.config)

        # extract initial state
        self.initial_model_state = {
            'species concentrations/amounts': {}
        }
        for parameter in parameters:
            if parameter.target and parameter.target.endswith('@initialConcentration'):
                # TODO -- there must be a better way to get the name
                name = re.search('"(.*)"', parameter.name).group(1)
                # TODO -- why is 'dynamic_species_` added to the start of the variables in the ports schema?
                self.initial_model_state['species concentrations/amounts']['dynamics_species_' + name] = float(parameter.new_value)

    def initial_state(self, config):
        return self.initial_model_state

    def ports_schema(self):
        schema = {}
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

    def next_update(self, timestep, states):
        # set up model changes based on current state
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

        # execute step
        raw_results, log = exec_sed_task(
            self.task,
            self.variables['__all__'],
            preprocessed_task=self.preprocessed_task,
            config=self.config,
        )

        # transform results
        results = {}
        for variable_type in self.variable_types:
            variables = self.variables[variable_type['id']]
            if variables:
                results[variable_type['id']] = {
                    variable.id: raw_results[variable.id][-1]
                    for variable in variables
                }
        return results


def test_biosimulators_process():
    parameters = {
        'sbml_path': 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
    }
    process = BiosimulatorsProcess(parameters)

    # get the initial state
    initial_state = process.initial_state()

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': initial_state}
    output = simulate_process(process, sim_settings)

    return output


if __name__ == '__main__':
    test_biosimulators_process()
