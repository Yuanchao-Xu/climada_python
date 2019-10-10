"""
This file is part of CLIMADA.

Copyright (C) 2017 ETH Zurich, CLIMADA contributors listed in AUTHORS.

CLIMADA is free software: you can redistribute it and/or modify it under the
terms of the GNU Lesser General Public License as published by the Free
Software Foundation, version 3.

CLIMADA is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with CLIMADA. If not, see <https://www.gnu.org/licenses/>.

---

Define CostBenefit class.
"""

__all__ = ['CostBenefit', 'risk_aai_agg', 'risk_rp_100', 'risk_rp_250']

import copy
import logging
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
from tabulate import tabulate

from climada.engine.impact import Impact

LOGGER = logging.getLogger(__name__)

DEF_PRESENT_YEAR = 2016
""" Default present reference year """

DEF_FUTURE_YEAR = 2030
""" Default future reference year """

def risk_aai_agg(impact):
    """Risk measurement as average annual impact aggregated.

    Parameters:
        impact (Impact): an Impact instance

    Returns:
        float
    """
    return impact.aai_agg

def risk_rp_100(impact):
    """Risk measurement as exceedance impact at 100 years return period.

    Parameters:
        impact (Impact): an Impact instance

    Returns:
        float
    """
    efc = impact.calc_freq_curve([100])
    return efc.impact[0]

def risk_rp_250(impact):
    """Risk measurement as exceedance impact at 250 years return period.

    Parameters:
        impact (Impact): an Impact instance

    Returns:
        float
    """
    efc = impact.calc_freq_curve([250])
    return efc.impact[0]

class CostBenefit():
    """Impact definition. Compute from an entity (exposures and impact
    functions) and hazard.

    Attributes:
        present_year (int): present reference year
        future_year (int): future year

        tot_climate_risk (float): total climate risk without measures
        unit (str): unit used for impact

        color_rgb (dict): color code RGB for each measure.
            Key: measure name ('no measure' used for case without measure),
            Value: np.array

        benefit (dict): benefit of each measure. Key: measure name, Value:
            float benefit
        cost_ben_ratio (dict): cost benefit ratio of each measure. Key: measure
            name, Value: float cost benefit ratio

        imp_meas_future (dict): impact of each measure at future or default.
            Key: measure name ('no measure' used for case without measure),
            Value: dict with:
                             'cost' (float): cost measure,
                             'risk' (float): risk measurement,
                             'risk_transf' (float): annual expected risk transfer,
                             'efc'  (ImpactFreqCurve): impact exceedance freq
                (optional)   'impact' (Impact): impact instance
        imp_meas_present (dict): impact of each measure at present.
            Key: measure name ('no measure' used for case without measure),
            Value: dict with:
                             'cost' (float): cost measure,
                             'risk' (float): risk measurement,
                             'risk_transf' (float): annual expected risk transfer,
                             'efc'  (ImpactFreqCurve): impact exceedance freq
                (optional)   'impact' (Impact): impact instance
    """

    def __init__(self):
        """ Initilization """
        self.present_year = DEF_PRESENT_YEAR
        self.future_year = DEF_FUTURE_YEAR

        self.tot_climate_risk = 0.0
        self.unit = 'USD'

        # dictionaries with key: measure name
        # value: measure color_rgb
        self.color_rgb = dict()
        # value: measure benefit
        self.benefit = dict()
        # value: measure cost benefit
        self.cost_ben_ratio = dict()
        # 'no measure' key for impact without measures
        # values: dictionary with 'cost': cost measure,
        #                         'risk': risk measurement,
        #                         'efc': ImpactFreqCurve
        #          (optionally)   'impact': Impact
        self.imp_meas_future = dict()
        self.imp_meas_present = dict()

    def calc(self, hazard, entity, haz_future=None, ent_future=None, \
        future_year=None, risk_func=risk_aai_agg, imp_time_depen=None, save_imp=False):
        """ Compute cost-benefit ratio for every measure provided current
        and, optionally, future conditions. Present and future measures need
        to have the same name. The measures costs need to be discounted by the user.
        If future entity provided, only the costs of the measures
        of the future and the discount rates of the present will be used.

        Parameters:
            hazard (Hazard): hazard
            entity (Entity): entity
            haz_future (Hazard, optional): hazard in the future (future year provided at
                ent_future)
            ent_future (Entity, optional): entity in the future
            future_year (int, optional): future year to consider if no ent_future
                provided. The benefits are added from the entity.exposures.ref_year until
                ent_future.exposures.ref_year, or until future_year if no ent_future given.
                Default: entity.exposures.ref_year+1
            risk_func (func, optional): function describing risk measure to use
                to compute the annual benefit from the Impact. Default: average
                annual impact (aggregated).
            imp_time_depen (float, optional): parameter which represents time
                evolution of impact (super- or sublinear). If None: all years
                count the same when there is no future hazard nor entity and 1
                (linear annual change) when there is future hazard or entity.
                Default: None.
            save_imp (bool, optional): True if Impact of each measure is saved.
                Default: False.
        """
        # Present year given in entity. Future year in ent_future if provided.
        self.present_year = entity.exposures.ref_year
        self.unit = entity.exposures.value_unit

        # save measure colors
        for meas in entity.measures.get_measure(hazard.tag.haz_type):
            self.color_rgb[meas.name] = meas.color_rgb

        if future_year is None:
            future_year = entity.exposures.ref_year + 1

        if not haz_future and not ent_future:
            self.future_year = future_year
            self._calc_impact_measures(hazard, entity.exposures, \
                entity.measures, entity.impact_funcs, 'future', \
                risk_func, save_imp)
        else:
            if imp_time_depen is None:
                imp_time_depen = 1
            self._calc_impact_measures(hazard, entity.exposures, \
                entity.measures, entity.impact_funcs, 'present', \
                risk_func, save_imp)
            if haz_future and ent_future:
                self.future_year = ent_future.exposures.ref_year
                self._calc_impact_measures(haz_future, ent_future.exposures, \
                    ent_future.measures, ent_future.impact_funcs, 'future', \
                    risk_func, save_imp)
            elif haz_future:
                self.future_year = future_year
                self._calc_impact_measures(haz_future, entity.exposures, \
                    entity.measures, entity.impact_funcs, 'future', risk_func,\
                    save_imp)
            else:
                self.future_year = ent_future.exposures.ref_year
                self._calc_impact_measures(hazard, ent_future.exposures, \
                    ent_future.measures, ent_future.impact_funcs, 'future', \
                    risk_func, save_imp)

        self._calc_cost_benefit(entity.disc_rates, imp_time_depen)
        self._print_results()

    def combine_measures(self, in_meas_names, new_name, new_color, disc_rates,
                         risk_transf=(0, 0), imp_time_depen=None, risk_func=risk_aai_agg):
        """ Compute cost-benefit of the combination of (independent) measures
        previously computed by calc with save_imp=True. Appended to dictionaries of
        measures. The benefits of the measures per event are added and risk transfer
        can be additionally implemented.

        Parameters:
            in_meas_names (list(str)): list with names of measures to combine
            new_name (str): name to give to the new resulting measure
            new_color (np.array): color code RGB for new measure, e.g.
                np.array([0.1, 0.1, 0.1])
            disc_rates (DiscRates): discount rates instance
            risk_transf (tuple): Risk transfer values (attachment, cover) to use
                to resulting combined impact.
            imp_time_depen (float, optional): parameter which represents time
                evolution of impact (super- or sublinear). If None: all years
                count the same when there is no future hazard nor entity and 1
                (linear annual change) when there is future hazard or entity.
                Default: None.
            risk_func (func, optional): function describing risk measure given
                an Impact. Default: average annual impact (aggregated).
        """
        self.color_rgb[new_name] = new_color

        # compute impacts for imp_meas_future and imp_meas_present
        self._combine_imp_meas(in_meas_names, new_name, risk_transf, risk_func,
                               when='future')
        if self.imp_meas_present:
            if imp_time_depen is None:
                imp_time_depen = 1
            self._combine_imp_meas(in_meas_names, new_name, risk_transf, risk_func,
                                   when='present')

        # cost-benefit computation: fill measure's benefit and cost_ben_ratio
        time_dep = self._time_dependency_array(imp_time_depen)
        self._cost_ben_one(new_name, self.imp_meas_future[new_name], disc_rates, time_dep)

    def plot_cost_benefit(self, cb_list=None, axis=None, **kwargs):
        """ Plot cost-benefit graph. Call after calc().

        Parameters:
            cb_list (list(CostBenefit), optional): if other CostBenefit
                provided, overlay them all. Used for uncertainty visualization.
            axis (matplotlib.axes._subplots.AxesSubplot, optional): axis to use
            kwargs (optional): arguments for Rectangle matplotlib, e.g. alpha=0.5
                (color is set by measures color attribute)

        Returns:
            matplotlib.axes._subplots.AxesSubplot
        """
        if cb_list:
            if 'alpha' not in kwargs:
                kwargs['alpha'] = 0.5
            cb_uncer = [self]
            cb_uncer.extend(cb_list)
            axis = self._plot_list_cost_ben(cb_uncer, axis, **kwargs)
            return axis

        if 'alpha' not in kwargs:
            kwargs['alpha'] = 1.0
        axis = self._plot_list_cost_ben([self], axis, **kwargs)
        norm_fact, norm_name = _norm_values(self.tot_climate_risk+0.01)
        axis.scatter(self.tot_climate_risk/norm_fact, 0, c='r', zorder=200, clip_on=False)
        axis.text(self.tot_climate_risk/norm_fact, 0, '  Tot risk', horizontalalignment='center',
                  verticalalignment='bottom', rotation=90, fontsize=12, color='r')

        text_pos = self.imp_meas_future['no measure']['risk']/norm_fact
        axis.scatter(text_pos, 0, c='r', zorder=200, clip_on=False)
        axis.text(text_pos, 0, '  AAI', horizontalalignment='center',
                  verticalalignment='bottom', rotation=90, fontsize=12, color='r')

        axis.set_xlim(0, max(int(self.tot_climate_risk/norm_fact),
                             np.array(list(self.benefit.values())).sum()/norm_fact))
        axis.set_ylim(0, int(1/np.array(list(self.cost_ben_ratio.values())).min()) + 1)
        x_label = 'NPV averted damage over ' + str(self.future_year - \
            self.present_year + 1) + ' years (' + self.unit + ' ' + norm_name + ')'
        axis.set_xlabel(x_label)
        axis.set_ylabel('Benefit/Cost ratio')
        return axis

    def plot_event_view(self, return_per=(10, 25, 100), axis=None, **kwargs):
        """ Plot averted damages for return periods. Call after calc().

        Parameters:
            return_per (list, optional): years to visualize. Default 10, 25, 100
            axis (matplotlib.axes._subplots.AxesSubplot, optional): axis to use
            kwargs (optional): arguments for bar matplotlib function, e.g. alpha=0.5
                (color is set by measures color attribute)

        Returns:
            matplotlib.axes._subplots.AxesSubplot
        """
        if not self.imp_meas_future:
            LOGGER.error('Compute CostBenefit.calc() first')
            raise ValueError
        if not axis:
            _, axis = plt.subplots(1, 1)
        avert_rp = dict()
        ref_imp = np.interp(return_per,
                            self.imp_meas_future['no measure']['efc'].return_per,
                            self.imp_meas_future['no measure']['efc'].impact)
        for meas_name, meas_val in self.imp_meas_future.items():
            if meas_name == 'no measure':
                continue
            interp_imp = np.interp(return_per, meas_val['efc'].return_per,
                                   meas_val['efc'].impact)
            avert_rp[meas_name] = ref_imp - interp_imp

        m_names = list(self.cost_ben_ratio.keys())
        sort_cb = np.argsort(np.array([self.cost_ben_ratio[name] for name in m_names]))
        names_sort = [m_names[i] for i in sort_cb]
        color_sort = [self.color_rgb[name] for name in names_sort]
        for rp_i, _ in enumerate(return_per):
            val_i = [avert_rp[name][rp_i] for name in names_sort]
            cum_effect = np.cumsum(np.array([0] + val_i))
            for (eff, color) in zip(cum_effect[::-1][:-1], color_sort[::-1]):
                axis.bar(rp_i+1, eff, color=color, **kwargs)
            axis.bar(rp_i+1, ref_imp[rp_i], edgecolor='k', fc=(1, 0, 0, 0))
        axis.set_xlabel('Return Period (%s)' % str(self.future_year))
        axis.set_ylabel('Impact ('+ self.unit + ')')
        axis.set_xticks(np.arange(len(return_per))+1)
        axis.set_xticklabels([str(per) for per in return_per])
        return axis

    @staticmethod
    def plot_waterfall(hazard, entity, haz_future, ent_future,
                       risk_func=risk_aai_agg, axis=None, **kwargs):
        """ Plot waterfall graph with given risk metric. Can be called before
        and after calc().

        Parameters:
            hazard (Hazard): hazard
            entity (Entity): entity
            haz_future (Hazard): hazard in the future (future year provided at
                ent_future)
            ent_future (Entity): entity in the future
            risk_func (func, optional): function describing risk measure given
                an Impact. Default: average annual impact (aggregated).
            axis (matplotlib.axes._subplots.AxesSubplot, optional): axis to use
            kwargs (optional): arguments for bar matplotlib function, e.g. alpha=0.5

        Returns:
            matplotlib.axes._subplots.AxesSubplot
        """
        if ent_future.exposures.ref_year == entity.exposures.ref_year:
            LOGGER.error('Same reference years for future and present entities.')
            raise ValueError
        present_year = entity.exposures.ref_year
        future_year = ent_future.exposures.ref_year

        imp = Impact()
        imp.calc(entity.exposures, entity.impact_funcs, hazard)
        curr_risk = risk_func(imp)

        imp = Impact()
        imp.calc(ent_future.exposures, ent_future.impact_funcs, haz_future)
        fut_risk = risk_func(imp)

        if not axis:
            _, axis = plt.subplots(1, 1)
        norm_fact, norm_name = _norm_values(curr_risk)

        # current situation
        LOGGER.info('Risk at {:d}: {:.3e}'.format(present_year, curr_risk))

        # changing future
        # socio-economic dev
        imp = Impact()
        imp.calc(ent_future.exposures, ent_future.impact_funcs, hazard)
        risk_dev = risk_func(imp)
        LOGGER.info('Risk with development at {:d}: {:.3e}'.format(future_year,
                                                                   risk_dev))

        # socioecon + cc
        LOGGER.info('Risk with development and climate change at {:d}: {:.3e}'.\
                    format(future_year, fut_risk))

        axis.bar(1, curr_risk/norm_fact, **kwargs)
        axis.text(1, curr_risk/norm_fact, str(int(round(curr_risk/norm_fact))), \
            horizontalalignment='center', verticalalignment='bottom', \
            fontsize=12, color='k')
        axis.bar(2, height=(risk_dev-curr_risk)/norm_fact, bottom=curr_risk/norm_fact, **kwargs)
        axis.text(2, curr_risk/norm_fact + (risk_dev-curr_risk)/norm_fact/2, \
            str(int(round((risk_dev-curr_risk)/norm_fact))), \
            horizontalalignment='center', verticalalignment='center', fontsize=12, color='k')
        axis.bar(3, height=(fut_risk-risk_dev)/norm_fact, bottom=risk_dev/norm_fact, **kwargs)
        axis.text(3, risk_dev/norm_fact + (fut_risk-risk_dev)/norm_fact/2, \
            str(int(round((fut_risk-risk_dev)/norm_fact))), \
            horizontalalignment='center', verticalalignment='center', fontsize=12, color='k')
        axis.bar(4, height=fut_risk/norm_fact, **kwargs)
        axis.text(4, fut_risk/norm_fact, str(int(round(fut_risk/norm_fact))), \
                  horizontalalignment='center', verticalalignment='bottom', \
                  fontsize=12, color='k')
        axis.set_xticks(np.arange(4)+1)
        axis.set_xticklabels(['Risk ' + str(present_year), \
            'Economic \ndevelopment', 'Climate \nchange', 'Risk ' + str(future_year)])
        axis.set_ylabel('Impact (' + imp.unit + ' ' + norm_name + ')')
        axis.set_title('Risk at {:d} and {:d}'.format(present_year, future_year))
        return axis

    def plot_waterfall_accumulated(self, hazard, entity, ent_future,
                                   risk_func=risk_aai_agg, imp_time_depen=1,
                                   plot_arrow=True, axis=None, **kwargs):
        """ Plot waterfall graph with accumulated values from present to future
        year. Call after calc(). Provide same inputs as in calc.

        Parameters:
            hazard (Hazard): hazard
            entity (Entity): entity
            ent_future (Entity): entity in the future
            risk_func (func, optional): function describing risk measure given
                an Impact. Default: average annual impact (aggregated).
            imp_time_depen (float, optional): parameter which represent time
                evolution of impact. Default: 1 (linear).
            plot_arrow (bool, optional): plot adaptation arrow
            axis (matplotlib.axes._subplots.AxesSubplot, optional): axis to use
            kwargs (optional): arguments for bar matplotlib function, e.g. alpha=0.5

        Returns:
            matplotlib.axes._subplots.AxesSubplot
        """
        if not self.imp_meas_future or not self.imp_meas_present:
            LOGGER.error('Compute CostBenefit.calc() first')
            raise ValueError
        if ent_future.exposures.ref_year == entity.exposures.ref_year:
            LOGGER.error('Same reference years for future and present entities.')
            raise ValueError

        self.present_year = entity.exposures.ref_year
        self.future_year = ent_future.exposures.ref_year

        # current situation
        curr_risk = self.imp_meas_present['no measure']['risk']
        time_dep = self._time_dependency_array()
        risk_curr = self._npv_unaverted_impact(curr_risk, entity.disc_rates,
                                               time_dep)
        LOGGER.info('Current total risk at {:d}: {:.3e}'.format(self.future_year,
                                                                risk_curr))

        # changing future
        time_dep = self._time_dependency_array(imp_time_depen)
        # socio-economic dev
        imp = Impact()
        imp.calc(ent_future.exposures, ent_future.impact_funcs, hazard)
        risk_dev = self._npv_unaverted_impact(risk_func(imp), entity.disc_rates,
                                              time_dep, curr_risk)
        LOGGER.info('Total risk with development at {:d}: {:.3e}'.format( \
            self.future_year, risk_dev))

        # socioecon + cc
        risk_tot = self._npv_unaverted_impact(self.imp_meas_future['no measure']['risk'], \
            entity.disc_rates, time_dep, curr_risk)
        LOGGER.info('Total risk with development and climate change at {:d}: {:.3e}'.\
            format(self.future_year, risk_tot))

        # plot
        if not axis:
            _, axis = plt.subplots(1, 1)
        norm_fact, norm_name = _norm_values(curr_risk)
        axis.bar(1, risk_curr/norm_fact, **kwargs)
        axis.text(1, risk_curr/norm_fact, str(int(round(risk_curr/norm_fact))), \
            horizontalalignment='center', verticalalignment='bottom', \
            fontsize=12, color='k')
        axis.bar(2, height=(risk_dev-risk_curr)/norm_fact, bottom=risk_curr/norm_fact, **kwargs)
        axis.text(2, risk_curr/norm_fact + (risk_dev-risk_curr)/norm_fact/2, \
            str(int(round((risk_dev-risk_curr)/norm_fact))), \
            horizontalalignment='center', verticalalignment='center', fontsize=12, color='k')
        axis.bar(3, height=(risk_tot-risk_dev)/norm_fact, bottom=risk_dev/norm_fact, **kwargs)
        axis.text(3, risk_dev/norm_fact + (risk_tot-risk_dev)/norm_fact/2, \
            str(int(round((risk_tot-risk_dev)/norm_fact))), \
            horizontalalignment='center', verticalalignment='center', fontsize=12, color='k')
        bar_4 = axis.bar(4, height=risk_tot/norm_fact, **kwargs)
        axis.text(4, risk_tot/norm_fact, str(int(round(risk_tot/norm_fact))), \
                  horizontalalignment='center', verticalalignment='bottom', \
                  fontsize=12, color='k')

        if plot_arrow:
            bar_bottom, bar_top = bar_4[0].get_bbox().get_points()
            axis.text(bar_top[0] - (bar_top[0]-bar_bottom[0])/2, bar_top[1],
                      "Averted", ha="center", va="top", rotation=270, size=15)
            arrow_len = min(np.array(list(self.benefit.values())).sum()/norm_fact,
                            risk_tot/norm_fact)
            axis.add_patch(FancyArrowPatch((bar_top[0] - (bar_top[0]-bar_bottom[0])/2, \
                bar_top[1]), (bar_top[0]- (bar_top[0]-bar_bottom[0])/2, \
                risk_tot/norm_fact-arrow_len), mutation_scale=100, color='k', \
                alpha=0.4))

        axis.xticks(np.arange(4)+1)
        axis.set_xticklabels(['Risk ' + str(self.present_year), \
            'Economic \ndevelopment', 'Climate \nchange', 'Risk ' + str(self.future_year)])
        axis.set_ylabel('Impact (' + self.unit + ' ' + norm_name + ')')
        axis.set_title('Total accumulated impact from {:d} to {:d}'.format( \
                       self.present_year, self.future_year))
        return axis

    def _calc_impact_measures(self, hazard, exposures, meas_set, imp_fun_set, \
        when='future', risk_func=risk_aai_agg, save_imp=False):
        """Compute impact of each measure and transform it to input risk
        measurement. Set reference year from exposures value.

        Parameters:
            hazard (Hazard): hazard.
            exposures (Exposures): exposures.
            meas_set (MeasureSet): set of measures.
            imp_fun_set (ImpactFuncSet): set of impact functions.
            when (str, optional): 'present' or 'future'. The conditions that
                are being considered.
            risk_func (function, optional): function used to transform impact
                to a risk measurement.
            save_imp (bool, optional): activate if Impact of each measure is
                saved. Default: False.
        """
        impact_meas = dict()

        # compute impact without measures
        LOGGER.debug('%s impact with no measure.', when)
        imp_tmp = Impact()
        imp_tmp.calc(exposures, imp_fun_set, hazard)
        impact_meas['no measure'] = dict()
        impact_meas['no measure']['cost'] = 0.0
        impact_meas['no measure']['risk'] = risk_func(imp_tmp)
        impact_meas['no measure']['risk_transf'] = 0.0
        impact_meas['no measure']['efc'] = imp_tmp.calc_freq_curve()
        if save_imp:
            impact_meas['no measure']['impact'] = imp_tmp

        # compute impact for each measure
        for measure in meas_set.get_measure(hazard.tag.haz_type):
            LOGGER.debug('%s impact of measure %s.', when, measure.name)
            imp_tmp, risk_transf = measure.calc_impact(exposures, imp_fun_set, hazard)
            impact_meas[measure.name] = dict()
            impact_meas[measure.name]['cost'] = measure.cost
            impact_meas[measure.name]['risk'] = risk_func(imp_tmp)
            impact_meas[measure.name]['risk_transf'] = risk_transf
            impact_meas[measure.name]['efc'] = imp_tmp.calc_freq_curve()
            if save_imp:
                impact_meas[measure.name]['impact'] = imp_tmp

        # if present reference provided save it
        if when == 'future':
            self.imp_meas_future = impact_meas
        else:
            self.imp_meas_present = impact_meas

    def _calc_cost_benefit(self, disc_rates, imp_time_depen=None):
        """Compute discounted impact from present year to future year

        Parameters:
            disc_rates (DiscRates): discount rates instance
            imp_time_depen (float, optional): parameter which represent time
                evolution of impact
        """
        LOGGER.info('Computing cost benefit from years %s to %s.',
                    str(self.present_year), str(self.future_year))

        if self.future_year - self.present_year + 1 <= 0:
            LOGGER.error('Wrong year range: %s - %s.', str(self.present_year),
                         str(self.future_year))
            raise ValueError

        if not self.imp_meas_future:
            LOGGER.error('Compute first _calc_impact_measures')
            raise ValueError

        time_dep = self._time_dependency_array(imp_time_depen)

        # discounted cost benefit for each measure and total climate risk
        for meas_name, meas_val in self.imp_meas_future.items():
            if meas_name == 'no measure':
                # npv of the full unaverted damages
                if self.imp_meas_present:
                    self.tot_climate_risk = self._npv_unaverted_impact(
                        self.imp_meas_future['no measure']['risk'], \
                        disc_rates, time_dep, self.imp_meas_present['no measure']['risk'])
                else:
                    self.tot_climate_risk = self._npv_unaverted_impact(
                        self.imp_meas_future['no measure']['risk'], \
                        disc_rates, time_dep)
                continue

            self._cost_ben_one(meas_name, meas_val, disc_rates, time_dep)

    def _cost_ben_one(self, meas_name, meas_val, disc_rates, time_dep):
        """ Compute cost and benefit for given measure with time dependency

        Parameters:
            meas_name (str): name of measure
            meas_val (dict): contains measure's cost, risk, efc, risk_trans and
                optionally impact at future
            disc_rates (DiscRates): discount rates instance
            time_dep (np.array): time dependency array
        """
        fut_benefit = self.imp_meas_future['no measure']['risk'] - meas_val['risk']
        fut_risk_tr = meas_val['risk_transf']
        if self.imp_meas_present:
            pres_benefit = self.imp_meas_present['no measure']['risk'] - \
                self.imp_meas_present[meas_name]['risk']
            meas_ben = pres_benefit + (fut_benefit-pres_benefit) * time_dep

            pres_risk_tr = self.imp_meas_present[meas_name]['risk_transf']
            risk_tr = pres_risk_tr + (fut_risk_tr-pres_risk_tr) * time_dep
        else:
            meas_ben = time_dep*fut_benefit
            risk_tr = time_dep*fut_risk_tr

        # discount
        meas_ben = disc_rates.net_present_value(self.present_year,
                                                self.future_year, meas_ben)
        risk_tr = disc_rates.net_present_value(self.present_year,
                                               self.future_year, risk_tr)
        self.benefit[meas_name] = meas_ben
        self.cost_ben_ratio[meas_name] = (meas_val['cost']+risk_tr)/meas_ben

    def _time_dependency_array(self, imp_time_depen=None):
        """ Construct time dependency array. Each year contains a value in [0,1]
        representing the rate of damage difference achieved that year, according
        to the growth represented by parameter imp_time_depen.

        Parameters:
            imp_time_depen (float, optional): parameter which represent time
                evolution of impact. Time array is all ones if not provided

        Returns:
            np.array
        """
        n_years = self.future_year - self.present_year + 1
        if imp_time_depen:
            time_dep = np.arange(n_years)**imp_time_depen / \
                (n_years-1)**imp_time_depen
        else:
            time_dep = np.ones(n_years)
        return time_dep

    def _npv_unaverted_impact(self, risk_future, disc_rates, time_dep,
                              risk_present=None):
        """ Net present value of total unaverted damages

        Parameters:
            risk_future (float): risk under future situation
            disc_rates (DiscRates): discount rates object
            time_dep (np.array): values in 0-1 indicating impact growth at each
                year
            risk_present (float): risk under current situation

        Returns:
            float
        """
        if risk_present:
            tot_climate_risk = risk_present + (risk_future-risk_present) * time_dep
            tot_climate_risk = disc_rates.net_present_value(self.present_year, \
                self.future_year, tot_climate_risk)
        else:
            tot_climate_risk = disc_rates.net_present_value(self.present_year, \
                self.future_year, time_dep * risk_future)
        return tot_climate_risk

    def _combine_imp_meas(self, in_meas_names, new_name, risk_transf, risk_func,
                          when='future'):
        """ Compute impacts combined measures assuming they are independent, i.e.
        their benefit can be added. Costs are also added. For the new measure
        the dictionary imp_meas_future if when='future' and imp_meas_present
        if when='present'.

        Parameters:


        """
        if when == 'future':
            imp_dict = self.imp_meas_future
        else:
            imp_dict = self.imp_meas_present

        sum_ben = np.sum([imp_dict['no measure']['impact'].at_event - \
            imp_dict[name]['impact'].at_event for name in in_meas_names], axis=0)
        new_imp = copy.deepcopy(imp_dict[in_meas_names[0]]['impact'])
        new_imp.at_event = np.maximum(imp_dict['no measure']['impact'].at_event
                                      - sum_ben, 0)
        risk_transfer = 0
        if risk_transf != (0, 0):
            imp_layer = np.minimum(np.maximum(new_imp.at_event - risk_transf[0], 0),
                                   risk_transf[1])
            risk_transfer = np.sum(imp_layer * new_imp.frequency)
            new_imp.at_event = np.maximum(new_imp.at_event - imp_layer, 0)
        new_imp.eai_exp = np.array([])
        new_imp.aai_agg = sum(new_imp.at_event * new_imp.frequency)

        imp_dict[new_name] = dict()
        imp_dict[new_name]['impact'] = new_imp
        imp_dict[new_name]['efc'] = new_imp.calc_freq_curve()
        imp_dict[new_name]['risk'] = risk_func(new_imp)
        imp_dict[new_name]['cost'] = np.array([imp_dict[name]['cost'] \
                                               for name in in_meas_names]).sum()
        imp_dict[new_name]['risk_transf'] = risk_transfer

    def _print_results(self):
        """ Print table with main results """
        norm_fact, norm_name = _norm_values(np.array(list(self.benefit.values())).max())
        norm_name = '(' + self.unit + ' ' + norm_name + ')'

        table = []
        headers = ['Measure', 'Cost ' + norm_name, 'Benefit ' + norm_name, 'Benefit/Cost']
        for meas_name in self.benefit:
            table.append([meas_name, \
            self.cost_ben_ratio[meas_name]*self.benefit[meas_name]/norm_fact, \
            self.benefit[meas_name]/norm_fact, 1/self.cost_ben_ratio[meas_name]])
        print()
        print(tabulate(table, headers, tablefmt="simple"))

        table = []
        table.append(['Total climate risk:',
                      self.tot_climate_risk/norm_fact, norm_name])
        table.append(['Average annual risk:',
                      self.imp_meas_future['no measure']['risk']/norm_fact, norm_name])
        table.append(['Residual damage:',
                      (self.tot_climate_risk -
                       np.array(list(self.benefit.values())).sum())/norm_fact, norm_name])
        print()
        print(tabulate(table, tablefmt="simple"))

    @staticmethod
    def _plot_list_cost_ben(cb_list, axis=None, **kwargs):
        """ Overlay cost-benefit bars for every measure

        Parameters:
            cb_list (list): list of CostBenefit instances with filled values
            axis (matplotlib.axes._subplots.AxesSubplot, optional): axis to use
            kwargs (optional): arguments for Rectangle matplotlib, e.g. alpha=0.5
                (color is set by measures color attribute)

        Returns:
            matplotlib.axes._subplots.AxesSubplot
        """
        if 'alpha' not in kwargs:
            kwargs['alpha'] = 0.5
        norm_fact = [_norm_values(cb_res.tot_climate_risk)[0] for cb_res in cb_list]
        norm_fact = np.array(norm_fact).mean()
        _, norm_name = _norm_values(norm_fact+0.01)

        if not axis:
            _, axis = plt.subplots(1, 1)
        m_names = list(cb_list[0].cost_ben_ratio.keys())
        sort_cb = np.argsort(np.array([cb_list[0].cost_ben_ratio[name] for name in m_names]))
        xy_lim = [0, 0]
        for i_cb, cb_res in enumerate(cb_list):
            xmin = 0
            for meas_id in sort_cb:
                meas_n = m_names[meas_id]
                axis.add_patch(Rectangle((xmin, 0), cb_res.benefit[meas_n]/norm_fact, \
                    1/cb_res.cost_ben_ratio[meas_n], color=cb_res.color_rgb[meas_n],\
                    **kwargs))

                if i_cb == 0:
                    axis.text(xmin + (cb_res.benefit[meas_n]/norm_fact)/2,
                              0.5, meas_n, horizontalalignment='center',
                              verticalalignment='bottom', rotation=90, fontsize=12)
                xmin += cb_res.benefit[meas_n]/norm_fact

            xy_lim[0] = max(xy_lim[0], max(int(cb_res.tot_climate_risk/norm_fact), \
                np.array(list(cb_res.benefit.values())).sum()/norm_fact))
            xy_lim[1] = max(xy_lim[1], int(1/cb_res.cost_ben_ratio[m_names[sort_cb[0]]]) + 1)

        axis.set_xlim(0, xy_lim[0])
        axis.set_ylim(0, xy_lim[1])
        axis.set_xlabel('NPV averted damage over ' + \
                        str(cb_list[0].future_year - cb_list[0].present_year + 1) + \
                        ' years (' + cb_list[0].unit + ' ' + norm_name + ')')
        axis.set_ylabel('Benefit/Cost ratio')
        return axis

def _norm_values(value):
    """ Compute normalization value and name

    Parameters:
        value (float): value to normalize

    Returns:
        norm_fact, norm_name
    """
    norm_fact = 1.
    norm_name = ''
    if value/1.0e9 > 1:
        norm_fact = 1.0e9
        norm_name = 'bn'
    elif value/1.0e6 > 1:
        norm_fact = 1.0e6
        norm_name = 'm'
    elif value/1.0e3 > 1:
        norm_fact = 1.0e3
        norm_name = 'k'
    return norm_fact, norm_name
