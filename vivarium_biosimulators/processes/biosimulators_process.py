"""
Execute by running: ``python vivarium_biosimulators/processes/biosimulators_process.py``

KISAO: https://bioportal.bioontology.org/ontologies/KISAO
"""
import importlib
import copy

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
        'input_ports': None,
        'output_ports': None,
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

        # make an map of input ids to targets
        self.input_id_target_map = {}
        for variable in self.inputs:
            self.input_id_target_map[variable.id] = variable.target

        # assign outputs to task
        for variable in self.outputs:
            variable.task = self.task

        self.config = Config(LOG=False)

        # preprocess
        self.preprocessed_task = self.preprocess_sed_task(
            self.task,
            self.outputs,
            config=self.config,
        )

        # port assignments
        all_inputs = [input_state.id for input_state in self.inputs]
        all_outputs = [output_state.id for output_state in self.outputs]
        remaining_inputs = copy.deepcopy(all_inputs)
        remaining_outputs = copy.deepcopy(all_outputs)
        self.port_assignments = {}
        if self.parameters['input_ports']:
            for port_id, variables in self.parameters['input_ports'].items():
                for variable_id in variables:
                    assert variable_id in all_inputs, \
                        f"port assigments: {variable_id} is not in the inputs {all_inputs} "
                    remaining_inputs.remove(variable_id)
                self.port_assignments[port_id] = variables
            for port_id, variables in self.parameters['output_ports'].items():
                for variable_id in variables:
                    assert variable_id in all_outputs, \
                        f"port assigments: {variable_id} is not in the outputs {all_outputs} "
                    remaining_outputs.remove(variable_id)
                self.port_assignments[port_id] = variables


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
        input_variables = states['input']

        # update model based on input state
        self.task.changes = []
        for variable_id, variable_value in input_variables.items():
            self.task.changes.append(ModelAttributeChange(
                target=self.input_id_target_map[variable_id],
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
        biosimulator_api='',
        model_source='',
        model_language=ModelLanguage.SBML.value,
        simulation='uniform_time_course',
        initial_state=None,
        input_output_map=None,
        total_time=10.,
):
    import warnings; warnings.filterwarnings('ignore')

    config = {
        'biosimulator_api': biosimulator_api,
        'model_source': model_source,
        'model_language':  model_language,
        'simulation': simulation,
    }
    process = BiosimulatorsProcess(config)

    # make a topology
    topology = {
        'global_time': ('global_time',),
        'input': ('state',) if not input_output_map else {
            **{'_path': ('state',)},
            **input_output_map,
        },
        'output': ('state',)
    }

    # get initial_state
    initial_state = initial_state or {}
    initial_model_state = {'state': initial_state} or process.initial_state()

    # run the simulation
    sim_settings = {
        'topology': topology,
        'total_time': total_time,
        'initial_state': initial_model_state,
        'display_info': False}
    output = simulate_process(process, sim_settings)

    return output


test_library = {
    '0': test_biosimulators_process,
}

# run methods in test_library from the command line with:
# python vivarium_biosimulators/processes/biosimulators_process.py -n [experiment id]
if __name__ == '__main__':
    run_library_cli(test_library)
