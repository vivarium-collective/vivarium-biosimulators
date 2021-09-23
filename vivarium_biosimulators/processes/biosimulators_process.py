"""
Execute by running: ``python vivarium_biosimulators/processes/biosimulators_process.py``

KISAO: https://bioportal.bioontology.org/ontologies/KISAO
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
            simulation = SteadyStateSimulation(
                id='simulation',
                algorithm=Algorithm(kisao_id='KISAO_0000437'),
            )

        # make the task
        self.task = Task(
            id='task',
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        self.inputs, _, self.outputs, _ = get_parameters_variables_outputs_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__,
            algorithm_kisao_id=simulation.algorithm.kisao_id,
        )

        self.variable_id_target_map = {}
        for variable in self.outputs:
            variable.task = self.task
            self.variable_id_target_map[variable.id] = variable.target

        self.config = Config(LOG=False)

        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.outputs,
            config=self.config,
        )

    def initial_state(self, config=None):
        # extract initial state
        # TODO -- output states are 0 by default, need to extract them from self.outputs
        initial_model_state = {
            'input': {
                input_state.id: input_state.new_value
                for input_state in self.inputs
            },
            'output': {
                output_state.id: 0
                for output_state in self.outputs
            }
        }
        return initial_model_state

    def is_deriver(self):
        if self.parameters['simulation'] == 'one_step':
            return True
        return False

    def ports_schema(self):
        schema = {
            'global_time': {'_default': 0.},
            'input': {
                input_state.id: {
                    '_default': 0.,
                    '_updater': 'accumulate'
                } for input_state in self.inputs
            },
            'output': {
                input_state.id: {
                    '_default': 0.,
                    '_updater': 'accumulate',
                    '_emit': True,
                } for input_state in self.outputs
            },
        }
        return schema

    def next_update(self, interval, states):

        global_time = states['global_time']
        input_variables = states['input']  # TODO -- set model inputs
        output_variables = states['output']

        # update model based on current state
        self.task.changes = []
        for variable_id, variable_value in output_variables.items():
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
            self.outputs,
            preprocessed_task=self.preprocessed_task,
            config=self.config,
        )

        # transform results
        outputs = {
            variable.id: get_delta(
                states['output'][variable.id],
                raw_results[variable.id][-1])
            for variable in self.outputs
        }
        return {
            'output': outputs}



def test_biosimulators_process(
        biosimulator_api='biosimulators_tellurium',
        model_source='vivarium_biosimulators/models/BIOMD0000000297_url.xml',
        model_language=ModelLanguage.SBML.value,
        simulation='uniform_time_course',
):
    import warnings; warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': biosimulator_api,
        'model_source': model_source,
        'model_language':  model_language,
        'simulation': simulation,
    }
    process = BiosimulatorsProcess(config)

    # get initial_state
    initial_state = process.initial_state()

    # run the simulation
    sim_settings = {
        'total_time': 10.,
        'initial_state': initial_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

    print(pf(output))
    return output


test_library = {
    '0': test_biosimulators_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/processes/biosimulators_process.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
