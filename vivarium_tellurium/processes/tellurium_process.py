'''
Execute by running: ``python vivarium_tellurium/process/tellurium_process.py``
'''
from vivarium.core.process import Process
from vivarium.core.composition import simulate_process

from biosimulators_tellurium.core import exec_sed_task
from biosimulators_utils.config import Config
from biosimulators_utils.sedml.data_model import (
    Task, Algorithm, Variable, Model, UniformTimeCourseSimulation, ModelLanguage)
from biosimulators_utils.model_lang.sbml.utils import get_parameters_variables_for_simulation


class TelluriumProcess(Process):
    defaults = {
        'sbml_path': '',
        'time_step': 1,
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)

        model = Model(
            source=self.parameters['sbml_path'],
            language=ModelLanguage.SBML.value,
        )
        simulation = UniformTimeCourseSimulation(
            initial_time=0,
            output_start_time=0,
            number_of_points=1,
            output_end_time=self.parameters['time_step'],
            algorithm=Algorithm(kisao_id='KISAO_0000019'),
        )
        self.task = Task(
            model=model,
            simulation=simulation,
        )

        # extract variables from the model
        (parameters, _, self.variables) = get_parameters_variables_for_simulation(
            model_filename=model.source,
            model_language=model.language,
            simulation_type=simulation.__class__
        )

        for variable in self.variables:
            variable.task = self.task                    

        self.config = Config(
            VALIDATE_SEDML=False,
            VALIDATE_SEDML_MODELS=False,
            LOG=False,
        )

    def ports_schema(self):
        return {
            'species concentrations': {
                variable.id: {
                    '_default': 0.0,
                    '_updater': 'accumulate',
                    '_emit': True,
                } for variable in self.variables
                if variable.target and variable.target.startswith('/sbml:sbml/sbml:model/sbml:listOfSpecies')
            },
            'parameter values': {
                variable: {
                    '_default': 0.0,
                    '_updater': 'accumulate',
                    '_emit': True,
                } for variable in self.variables
                if variable.target and variable.target.startswith('/sbml:sbml/sbml:model/sbml:listOfParameters')
            },
            # 'reaction fluxes': {
            #     reaction: {
            #         '_default': 0.0,
            #         '_updater': 'accumulate',
            #         '_emit': True,
            #     } for reaction in self.parameters['reactions']
            # },
            # 'compartment sizes': {
            #     compartment: {
            #         '_default': 0.0,
            #         '_updater': 'accumulate',
            #         '_emit': True,
            #     } for compartment in self.parameters['compartment sizes']
            # },
        }

    def next_update(self, timestep, states):
        values = states['species concentrations']
        parameters = states['parameter values']

        # TODO -- implement model changes based on current state
        # TODO -- use config to turn off logging
        results, log = exec_sed_task(
            self.task,
            self.variables,
            config=self.config,
        )

        # TODO -- filter variables from results

        return {
            'species concentrations': results,
        }


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
