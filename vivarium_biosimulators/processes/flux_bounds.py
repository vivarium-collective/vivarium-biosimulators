"""
=====================
Flux Bounds Converter
=====================
"""
from vivarium.core.process import Process
from vivarium.library.units import units


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
        flux_bounds = {
            self.flux_to_bound_map[flux_id]: (
                flux_value / dt * (self.flux_unit / units.s)
            ).to(self.bounds_unit).magnitude
            for flux_id, flux_value in fluxes.items()
        }
        return flux_bounds

    def next_update(self, interval, states):
        """
        Get the ODE process's update, convert the flux values to bounds,
        add them to the bounds port, and return the full update.
        """
        update = self.ode_process.next_update(interval, states)
        bounds = self.convert_fluxes(update['fluxes'], interval)
        update['bounds'] = {
            flux_id: {
                '_value': bound,
                '_updater': 'set',
            } for flux_id, bound in bounds.items()
        }
        return update
