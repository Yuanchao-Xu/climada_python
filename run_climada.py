import numpy as np
import warnings
#import matplotlib


#matplotlib.use('MacOSX')  # 或者 'MacOSX'
#import matplotlib.pyplot as plt
#plt.interactive(False)

"""
below is to load data, the data has already been saved locally, to save time, comment this block

warnings.filterwarnings('ignore')


from climada.hazard import TCTracks
tracks = TCTracks.from_ibtracs_netcdf(provider='hko', basin = 'WP')
tracks_2022 = TCTracks.from_ibtracs_netcdf(provider='hko',basin = 'WP', year_range = (2018,2018))
#tracks_2022.plot()
#plt.show(block=True)

tracks.equal_timestep(time_step_h=0.5)
"""

"""
import pickle

# 保存到文件
with open('tracks_2022.pkl', 'wb') as f:
    pickle.dump(tracks_2022, f)
    
    
# 反序列化多个数据
with open('data.pkl', 'rb') as f:
    data1, data2 = pickle.load(f)
"""
# because the data is already loaded locally, read from local
import pickle
with open('/Users/yuanchaoxu/PycharmProjects/pythonProject/tracks_2022.pkl', 'rb') as f:
    tracks_2022 = pickle.load(f)


from climada.hazard import Centroids
# this is not the perfect one, this is using bond to get centroids, shd use coordinates directly
# e.g., centrs = Centroids.from_lat_lon(lat, lon)
min_lat,max_lat,min_lon,max_lon = 22.13,22.58,113.81,114.51
cent = Centroids.from_pnt_bounds((min_lon,min_lat,max_lon,max_lat),res=0.01)
#cent.plot()

from climada.hazard import TropCyclone

#downscale tracks to centroid
haz = TropCyclone.from_tracks(tracks_2022, centroids=cent)
"""
through a FUNCTION calculate_scale_factor(ref_year, rcp_scenario) to calculate a factor
then apply the factor into the orginal intensity to get new intensity
"""
haz_85 = haz.apply_climate_scenario_knu(ref_year=2050,rcp_scenario=85)
#print(haz_85.intensity)

from climada.entity import Exposures, Entity
# If shows no module named "osgeo" and cannot install "osgeo", install "gdal", if in stalled by can't find
# that's because the name cannot be found, in "site-packages" folder, find gdal package, usually shows as "GDAL 3.6.2 ****"
# simply change the package name  to "gdal", then it can read


ent = Entity()

exp_pnt = Exposures(crs='epsg:4326') #set coordinate system
#exp_pnt.gdf['latitude'] = np.array([22.40,22.32,22.24,22.24,22.34,22.48,22.34,22.49,22.50,22.32,22.37,22.37])
#exp_pnt.gdf['longitude'] = np.array([113.97,114.27,114.15,114.16,114.19,114.14,114.15,114.14,114.13,114.26,113.97,114.19])
#exp_pnt.gdf['value'] = np.array([2.525e9,1.289e9,1.408e9,2.459e9,8.770e8,2.042e9,1.243e7,2.021e7,3.064e6,2.550e7,1.279e7,2.636e7])
exp_pnt.gdf['latitude'] = np.array([22.40])
exp_pnt.gdf['longitude'] = np.array([113.97])
exp_pnt.gdf['value'] = np.array([2.525e9])

exp_pnt.check()
#exp_pnt.plot_scatter(buffer=0.05)

ent.exposures = exp_pnt

from climada.entity.impact_funcs.trop_cyclone import ImpfSetTropCyclone

imp_fun_set_TC = ImpfSetTropCyclone.from_calibrated_regional_ImpfSet()
impf_tc_1 = imp_fun_set_TC.get_func('TC',9)
#impf_tc_1.plot()

# this step is to pick impact function
ent.impact_funcs = imp_fun_set_TC
ent.exposures.gdf['impf_TC'] = 9


from climada.engine import ImpactCalc
"""
#the code below identifies hazard by centroids
        if assign_centroids:
            self.exposures.assign_centroids(self.hazard, overwrite=True)

then FUNCTION u_coord.match_centroids is used to match the centroids with closest hazard and gives back the index of hazard coordinates
can use check function name in copilot
"""
impactcal = ImpactCalc(ent.exposures,ent.impact_funcs,haz_85)
imp = impactcal.impact(save_mat=True)


print('Total Asset Value:{:.3e} HKD'.format(imp.tot_value))
print('Expected Annual Impact:{:.3e} HKD'.format(imp.aai_agg))

imp.plot_basemap_eai_exposure(buffer=0.1)

"""
For issues "certificate verify failed: unable to get local issuer certificate"

first generate certificate, then run below code 

import ssl
import certifi

ssl._create_default_https_context = ssl._create_unverified_context
"""
