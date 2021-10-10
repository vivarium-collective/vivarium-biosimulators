"""
=====================
Flux Bounds Converter
=====================
"""
from vivarium.core.process import Process
from vivarium.library.units import units


def get_flux_and_bound_ids(flux_to_bound_map):
    """
    Args: flux_to_bound_map: dictionary with {flux: bounds}
    Returns: flux_ids, bounds_ids
    """
    flux_ids = []
    bounds_ids = []
    for flux_id, bounds_id in flux_to_bound_map.items():
        flux_ids.append(flux_id)
        if isinstance(bounds_id, dict):
            pass
        else:
            bounds_ids.append(bounds_id)
    return flux_ids, bounds_ids


class FluxBoundsConverter(Process):
    """A wrapper for an ODE process

    Converts the ODE process's output fluxes to flux bounds inputs for an fba process.

    TODO (ERAN) -- adjust both upper and lower bounds?
    """
    defaults = {
        'flux_to_bound_map': {},
        'ode_process': None,
        'flux_unit': 'mol/L',
        'bounds_unit': 'mmol/L/s',
        'time_unit': 's',
    }

    def __init__(self, parameters=None):
        super().__init__(parameters)
        self.flux_to_bound_map = self.parameters['flux_to_bound_map']
        self.ode_process = self.parameters['ode_process']
        self.inputs = self.ode_process.inputs
        self.outputs = self.ode_process.outputs
        self.input_ports = self.ode_process.input_ports
        self.output_ports = self.ode_process.output_ports

        # unit conversion
        self.flux_unit = units(self.parameters['flux_unit'])
        self.bounds_unit = units(self.parameters['bounds_unit'])
        self.time_unit = units(self.parameters['time_unit'])

    def initial_state(self, config=None):
        state = self.ode_process.initial_state(config)
        state['bounds'] = {}
        return state

    def calculate_timestep(self, states):
        """
        Use the ODE process's timestep
        """
        return self.ode_process.calculate_timestep(states)

    def ports_schema(self):
        """
        Use the ODE process's ports, with an added 'bounds' port for flux bounds output.
        """
        ports = self.ode_process.get_schema()
        ports['bounds'] = {
            self.flux_to_bound_map[rxn_id]: {}
            for rxn_id in ports['fluxes'].keys()
        }
        return ports

    def convert_fluxes(self, fluxes, dt):
        """
        Divide by the time step to get flux bounds, and convert to bounds unit
        """
        flux_bounds = {}
        for flux_id, flux_value in fluxes.items():
            bounds_id = self.flux_to_bound_map[flux_id]
            if isinstance(bounds_id, dict):
                Exception('no upper/lower bounds dict yet')
            else:
                flux_bounds[bounds_id] = (
                        flux_value / dt * (self.flux_unit / self.time_unit)
                ).to(self.bounds_unit).magnitude
        return flux_bounds

    def next_update(self, interval, states):
        """
        Get the ODE process's update, convert the flux values to bounds,
        add them to the bounds port, and return the full update.
        """
        update = self.ode_process.next_update(interval, states)
        if update.get('fluxes'):
            bounds = self.convert_fluxes(update['fluxes'], interval)
            update['bounds'] = {
                flux_id: {
                    '_value': bound,
                    '_updater': 'set',
                } for flux_id, bound in bounds.items()
            }
        return update
