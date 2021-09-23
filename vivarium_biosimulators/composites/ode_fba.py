
from biosimulators_utils.sedml.data_model import ModelLanguage
from vivarium.core.composer import Composer, Composite
from vivarium.core.engine import pf
from vivarium.core.composition import simulate_composite

from vivarium_biosimulators.processes.biosimulators_process import BiosimulatorsProcess

SBML_MODEL_PATH = 'vivarium_biosimulators/models/BIOMD0000000297_url.xml'
BIGG_MODEL_PATH = 'vivarium_biosimulators/models/iAF1260b.xml'


class ODE_FBA(Composer):
    defaults = {
        'ode_config': {},
        'fba_config': {},
        'flux_map': {}  # {'ode_rxn_name': 'fba_bounds_name'}
    }

    def generate_processes(self, config):
        return {
            'ode_process': BiosimulatorsProcess(config['ode_config']),
            'fba_process': BiosimulatorsProcess(config['fba_config']),
        }

    def generate_topology(self, config):
        # TODO the flux output needs to be connected to fba's bounds input using flux_map
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



def test_ode_fba(
        total_time=10.,
):
    config = {
        'ode_config': {
            'biosimulators_api': 'biosimulators_tellurium',
            'model_source': SBML_MODEL_PATH,
            'simulation': 'uniform_time_course',
            'model_language': ModelLanguage.SBML.value,
        },
        'fba_config': {
            'biosimulators_api': 'biosimulators_cobrapy',
            'model_source': BIGG_MODEL_PATH,
            'simulation': 'steady_state',
            'model_language': ModelLanguage.SBML.value,
        },
        'flux_map': {}
    }
    ode_fba = ODE_FBA(config).generate()

    # initial state
    initial_state = {}

    # run the simulation
    sim_settings = {
        'total_time': total_time,
        'initial_state': initial_state,
        'display_info': False}
    output = simulate_composite(ode_fba, sim_settings)

    print(pf(output))


if __name__ == '__main__':
    test_ode_fba()
