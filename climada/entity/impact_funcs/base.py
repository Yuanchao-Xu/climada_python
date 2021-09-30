"""
This file is part of CLIMADA.

Copyright (C) 2017 ETH Zurich, CLIMADA contributors listed in AUTHORS.

CLIMADA is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free
Software Foundation, version 3.

CLIMADA is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with CLIMADA. If not, see <https://www.gnu.org/licenses/>.

---

Define ImpactFunc class.
"""

__all__ = ['ImpactFunc']

import logging
import numpy as np
import matplotlib.pyplot as plt

import climada.util.checker as u_check

LOGGER = logging.getLogger(__name__)

class ImpactFunc():
    """Contains the definition of one impact function.

    Attributes:
        haz_type (str): hazard type acronym (e.g. 'TC')
        id (int or str): id of the impact function. Exposures of the same type
            will refer to the same impact function id
        name (str): name of the ImpactFunc
        intensity_unit (str): unit of the intensity
        intensity (np.array): intensity values
        mdd (np.array): mean damage (impact) degree for each intensity (numbers
            in [0,1])
        paa (np.array): percentage of affected assets (exposures) for each
            intensity (numbers in [0,1])
    """
    def __init__(self):
        """Empty initialization."""
        self.id = ''
        self.name = ''
        self.intensity_unit = ''
        self.haz_type = ''
        # Followng values defined for each intensity value
        self.intensity = np.array([])
        self.mdd = np.array([])
        self.paa = np.array([])

    def calc_mdr(self, inten):
        """Interpolate impact function to a given intensity.

        Parameters:
            inten (float or np.array): intensity, the x-coordinate of the
                interpolated values.

        Returns:
            np.array
        """
#        return np.interp(inten, self.intensity, self.mdd * self.paa)
        return np.interp(inten, self.intensity, self.paa) * \
            np.interp(inten, self.intensity, self.mdd)

    def plot(self, axis=None, **kwargs):
        """Plot the impact functions MDD, MDR and PAA in one graph, where
        MDR = PAA * MDD.

        Parameters:
            axis (matplotlib.axes._subplots.AxesSubplot, optional): axis to use
            kwargs (optional): arguments for plot matplotlib function, e.g. marker='x'

        Returns:
            matplotlib.axes._subplots.AxesSubplot
        """
        if not axis:
            _, axis = plt.subplots(1, 1)

        title = '%s %s' % (self.haz_type, str(self.id))
        if self.name != str(self.id):
            title += ': %s' % self.name
        axis.set_xlabel('Intensity (' + self.intensity_unit + ')')
        axis.set_ylabel('Impact (%)')
        axis.set_title(title)
        axis.plot(self.intensity, self.mdd * 100, 'b', label='MDD', **kwargs)
        axis.plot(self.intensity, self.paa * 100, 'r', label='PAA', **kwargs)
        axis.plot(self.intensity, self.mdd * self.paa * 100, 'k--', label='MDR', **kwargs)

        axis.set_xlim((self.intensity.min(), self.intensity.max()))
        axis.legend()
        return axis
    
    def check(self):
        """Check consistent instance data.

        Raises:
            ValueError
        """
        num_exp = len(self.intensity)
        u_check.size(num_exp, self.mdd, 'ImpactFunc.mdd')
        u_check.size(num_exp, self.paa, 'ImpactFunc.paa')

        if num_exp == 0:
            LOGGER.warning("%s impact function with name '%s' (id=%s) has empty"
                           " intensity.", self.haz_type, self.name, self.id)
            return

        # Warning for non-vanishing impact at intensity 0. If positive
        # and negative intensity warning for interpolation at intensity 0.
        zero_idx = np.where(self.intensity == 0)[0]
        if zero_idx.size != 0:
            if self.mdd[zero_idx[0]] != 0 or self.paa[zero_idx[0]] != 0:
                LOGGER.warning('For intensity = 0, mdd != 0 or paa != 0. '
                               'Consider shifting the origin of the intensity '
                               'scale. In impact.calc the impact is always '
                               'null at intensity = 0.')
        elif self.intensity[0] < 0 and self.intensity[-1] > 0:
            LOGGER.warning('Impact function might be interpolated to non-zero'
                           ' value at intensity = 0. Consider shifting the '
                           'origin of the intensity scale. In impact.calc '
                           'the impact is always null at intensity = 0.')

    def set_step_impf(self, intensity, mdd=(0, 1), paa=(1, 1), impf_id=1):

        """ Step function type impact function. 
        
        By default, everything is destroyed above the step.
        Useful for high resolution modelling.
        
        This method modifies self (climada.entity.impact_funcs instance)
        by assigning an id, intensity, mdd and paa to the impact function.
        
        Parameters
        ----------
        intensity: tuple(float, float, float)
            tuple of 3-intensity numbers: (minimum, threshold, maximum)
        mdd: tuple(float, float)
            (min, max) mdd values. The default is (0, 1)
        paa: tuple(float, float)
            (min, max) paa values. The default is (1, 1)
        impf_id : int, optional, default=1
            impact function id

        """

        self.id = impf_id
        inten_min, threshold, inten_max = intensity
        self.intensity = np.array([inten_min, threshold, threshold, inten_max])
        paa_min, paa_max = paa
        self.paa = np.array([paa_min, paa_min, paa_max, paa_max])
        mdd_min, mdd_max = mdd
        self.mdd = np.array([mdd_min, mdd_min, mdd_max, mdd_max])

    def set_sigmoid_impf(self, sig_mid, sig_shape, sig_max,
                    inten_min, inten_max, inten_step=5, if_id=1):

        """ Sigmoid type impact function hinging on three parameter. This type
        of impact function is very flexible for any sort of study/resolution.
        Parameters can be thought of as intercept (sig_mid), slope (sig_shape)
        and top (sig_max) of a sigmoid. More precisely, sig_mid refers to the
        intensity value where MDD equals 50% of sig_max.

        For more information: https://en.wikipedia.org/wiki/Logistic_function

        This method modifies self (climada.entity.impact_funcs instance)
        by assining an id, intensity, mdd and paa to the impact function.

        Parameters
        ----------
            sig_mid : float
                "intercept" of sigmoid
            sig_shape : float
                "slope" of sigmoid
            sig_max : float
                "top" of sigmoid
            inten_min : float
                minimum value of intensity range
            inten_min : float
                maximum value of intensity range
            inten_step : float, optional, default=5
                Spacing between intensity values
            if_id : int, optional, default=1
                impact function id

        """
        self.id = if_id
        self.intensity = np.arange(inten_min, inten_max, inten_step)
        self.paa = np.ones(len(self.intensity))
        self.mdd = sig_max / (1 + np.exp(-sig_shape * (self.intensity - sig_mid)))
