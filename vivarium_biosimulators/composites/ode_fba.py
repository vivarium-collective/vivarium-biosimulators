
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composer import Composer, Composite
from vivarium.core.composition import simulate_composite

from vivarium_biosimulators.processes.biosimulators_process import BiosimulatorsProcess

class ODE_FBA(Composer):
    defaults = {
        'ode_simulator': {
            'biosimulators_api': 'biosimulators_tellurium',
            'model_source': '',
            'simulation': 'uniform_time_course',
            'model_language': ModelLanguage.SBML.value,
        },
        'fba_simulator': {
            'biosimulators_api': 'biosimulators_cobrapy',
            'model_source': '',
            'simulation': 'steady_state',
            'model_language': ModelLanguage.SBML.value,
        },
        'flux_mapping': {
            'ode_rxn_name': 'fba_bounds_name'
        }
    }

    def generate_processes(self, config):
        ode_process = BiosimulatorsProcess(config['ode_simulator'])
        fba_process = BiosimulatorsProcess(config['fba_simulator'])
        return {
            'ode_process': ode_process,
            'fba_process': fba_process
        }

    def generate_topology(self, config):
        # TODO the flux output needs to be connected to fba's bounds input using flux_mapping
        return {
            'ode_process': {
                'input': ('state',),
                'output': ('state',),
            },
            'fba_process': {
                'input': ('state',),
                'output': ('state',),
            },
        }



def main():
    config = {
        'ode_simulator': {
            'biosimulators_api': 'biosimulators_tellurium',
            'model_source': ''  # Barton dFBA paper, iFBA paper's ode portion, glc/lcts SBML,
        },
        'fba_simulator': {
            'biosimulators_api': 'biosimulators_cobrapy',
            'model_source': ''  # load in a BiGG model, e_coli_core, iAF1260b
        },
        'flux_mapping': {}
    }
    ode_fba = ODE_FBA(config).generate()

    sim_settings = {}
    output = simulate_composite(ode_fba, sim_settings)


if __name__ == '__main__':
    main()
