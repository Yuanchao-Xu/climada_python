"""
This file is part of CLIMADA.

Copyright (C) 2017 CLIMADA contributors listed in AUTHORS.

CLIMADA is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free
Software Foundation, version 3.

CLIMADA is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along 
with CLIMADA. If not, see <https://www.gnu.org/licenses/>.

---

Define constants.
"""

__all__ = ['SOURCE_DIR',
           'DATA_DIR',
           'SYSTEM_DIR',
           'HAZ_DEMO_MAT',
           'ENT_TEMPLATE_XLS',
           'ENT_DEMO_MAT',
           'ONE_LAT_KM',
           'EARTH_RADIUS_KM',
           'GLB_CENTROIDS_MAT',
           'ENT_FL_MAT',
           'TC_ANDREW_FL']

import os

SOURCE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                          os.pardir))
""" climada directory """

DATA_DIR = os.path.abspath(os.path.join(SOURCE_DIR, os.pardir, 'data'))
""" Folder containing the data """

SYSTEM_DIR = os.path.abspath(os.path.join(DATA_DIR, 'system'))
""" Folder containing the data used internally """




GLB_CENTROIDS_MAT = os.path.join(SYSTEM_DIR, 'GLB_NatID_grid_0360as_adv_2.mat')
""" Global centroids."""

ENT_TEMPLATE_XLS = os.path.join(SYSTEM_DIR, 'entity_template.xlsx')
""" Entity template in xls format."""




HAZ_DEMO_MAT = os.path.join(DATA_DIR, 'demo', 'atl_prob.mat')
""" Hazard demo in mat format."""

ENT_DEMO_MAT = os.path.join(DATA_DIR, 'demo', 'demo_today.mat')
""" Entity demo in mat format."""

ENT_FL_MAT = os.path.join(DATA_DIR, 'demo',
                          'USA_UnitedStates_Florida_entity.mat')
""" Entity for Florida """

TC_ANDREW_FL = os.path.join(DATA_DIR, 'demo',
                            'ibtracs_global_intp-None_1992230N11325.csv')
""" Tropical cyclone Andrew in Florida """




ONE_LAT_KM = 111.12
""" Mean one latitude (in degrees) to km """

EARTH_RADIUS_KM = 6371
""" Earth radius in km """
