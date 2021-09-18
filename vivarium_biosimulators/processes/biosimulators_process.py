"""
Execute by running: ``python vivarium_biosimulators/processes/biosimulators_process.py``
"""
import re
import importlib

from vivarium.core.process import Process
from vivarium.core.composition import simulate_process
from vivarium.core.control import run_library_cli

from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Model, ModelAttributeChange, 
    UniformTimeCourseSimulation, SteadyStateSimulation, ModelLanguage
)
from biosimulators_utils.sedml.model_utils import get_parameters_variables_outputs_for_simulation


def get_delta(before, after):
    return after - before


class BiosimulatorsProcess(Process):
    
    defaults = {
        'biosimulator_api': '',
        'model_source': '',
        'model_language': '',
        'simulation': 'uniform_time_course',  # uniform_time_course, steady_state, one_step, analysis
        'time_step': 1.,
        'ports': {},  # TODO -- use this to configure custom ports
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        # import biosimulator module
        biosimulator = importlib.import_module(self.parameters['biosimulator_api'])
        self.exec_sed_task = getattr(biosimulator, 'exec_sed_task')
        self.preprocess_sed_task = getattr(biosimulator, 'preprocess_sed_task')

        # get the model
        model = Model(
            id='model',
            source=self.parameters['model_source'],
            language=self.parameters['model_language'],
        )

        # get the simulation
        simulation = None
        if self.parameters['simulation'] == 'uniform_time_course':
            simulation = UniformTimeCourseSimulation(
                id='simulation',
                initial_time=0.,
                output_start_time=0.,
                number_of_points=1,
                output_end_time=self.parameters['time_step'],
                algorithm=Algorithm(kisao_id='KISAO_0000019'),
            )
        elif self.parameters['simulation'] == 'steady_state':
            simulation = SteadyStateSimulation()  # TODO -- set this up

        # make the task
        self.task = Task(
            id='task',
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        model_attributes, _, all_variables, _ = get_parameters_variables_outputs_for_simulation(
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

        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.variables['__all__'],
            config=self.config,
        )

       # extract initial state
        self.initial_model_state = {
            'species concentrations/amounts': {}
        }
        for parameter in model_attributes:
            if parameter.target and parameter.target.endswith('@initialConcentration'):
                # TODO -- there must be a better way to get the name
                name = re.search('"(.*)"', parameter.name).group(1)
                # TODO -- why is 'dynamic_species_` added to the start of the variables in the ports schema?
                self.initial_model_state['species concentrations/amounts']['dynamics_species_' + name] = float(parameter.new_value)

    def initial_state(self, config=None):
        return self.initial_model_state

    def is_deriver(self):
        if self.parameters['simulation'] == 'one_step':
            return True
        else:
            return False

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

        # TODO (Eran) -- set the timestep in self.task

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



def test_biosimulators_process(
        biosimulator_api='biosimulators_tellurium',
        model_source='vivarium_biosimulators/models/BIOMD0000000297_url.xml',
        model_language=ModelLanguage.SBML.value,
        simulation='uniform_time_course',
):
    config = {
        'biosimulator_api': biosimulator_api,
        'model_source': model_source,
        'model_language':  model_language,
        'simulation': simulation,
    }
    process = BiosimulatorsProcess(config)

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': process.initial_state(),
        'display_info': False}
    output = simulate_process(process, sim_settings)

    # print(pf(output))
    return output


test_library = {
    '0': test_biosimulators_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/processes/biosimulators_process.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
