'''
Execute by running: ``python vivarium_tellurium/process/tellurium_process.py``
'''
from vivarium.core.process import Process
from vivarium.core.composition import simulate_process

from biosimulators_tellurium.core import exec_sed_task, preprocess_sed_task
from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Variable, Model, UniformTimeCourseSimulation, ModelLanguage)
from biosimulators_utils.model_lang.sbml.utils import get_parameters_variables_for_simulation


class TelluriumProcess(Process):
    defaults = {
        'sbml_path': '',
        'time_step': 1.,
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        model = Model(
            source=self.parameters['sbml_path'],
            language=ModelLanguage.SBML.value,
        )
        simulation = UniformTimeCourseSimulation(
            initial_time=0.,
            output_start_time=0.,
            number_of_points=1,
            output_end_time=self.parameters['time_step'],
            algorithm=Algorithm(kisao_id='KISAO_0000019'),
        )
        self.task = Task(
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        (parameters, _, all_variables) = get_parameters_variables_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__
        )

        self.variable_types = [
            {
                'id': 'species concentrations/amounts'
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfSpecies',
                'in': True,
                'out': True,
            },
            {
                'id': 'parameter values'
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfParameters',
                'in': True,
                'out': True,
            },
            {
                'id': 'reaction fluxes'
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfReactions',
                'in': False,
                'out': True,
            },
            {
                'id': 'compartment sizes'
                'xpath_prefix': '/sbml:sbml/sbml:model/sbml:listOfCompartments',
                'in': True,
                'out': True,
            },
        ]

        self.variables = {'__all__': []}
        for variable_type in self.variable_types:
            self.variables[variable_type['id']] = list(
                filter(lambda var: var.target.startswith(variable_type['xpath_prefix']), all_variables))
            self.variables['__all__'] += self.variables[variable_type['id']]

        self.variable_id_target_map = {variable.id: variable.target for variable in self.variables['__all__']}

        self.config = Config(LOG=False)

        self.preprocessed_task = preprocess_sed_task(self.task, self.variables['__all__'], config=self.config)

    def ports_schema(self):
        schema = {}
        for variable_type in self.variable_types:
            variables = self.variables[variable_type['id']]
            schema[variable_type['id']] = {
                variable.id: {
                    '_default': 0.0,
                    '_updater': 'accumulate' if variable_type['in'] else None,
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
                for variable_id, variable_value in variable_states.items():
                    self.task.changes.append(ModelAttributeChange(
                        target=self.variable_id_target_map[variable_id],
                        new_value=variable_value,
                    ))

        # execute step
        raw_results, log = exec_sed_task(
            self.task,
            self.all_variables,
            preprocessed_task=self.preprocessed_task,
            config=self.config,
        )

        # transform results
        results = {}
        for variable_type in self.variable_types:
            variables = self.variables[variable_type['id']]
            results[variable_type['id']] = {
                variable.id: raw_results[variable.id][-1]
                for variable in variables
            }

        return results


def test_tellurium_process():
    parameters = {
        'sbml_path': 'vivarium_tellurium/models/BIOMD0000000297_url.xml'
    }
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
    test_tellurium_process()
