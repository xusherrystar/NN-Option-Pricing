# -*- coding: utf-8 -*-
"""
Created on Fri Mar 23 21:42:13 2018

@author: user
"""

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

import pricing_class
import option_class
import process_class
import engine_class
import importlib

importlib.reload(pricing_class)
importlib.reload(option_class)
importlib.reload(process_class)
importlib.reload(engine_class)

class Option_Fitter:
    '''calibrate theta, v, sigma,'''
    def __init__(self, train):
        self.train = train
       
    def residuals(self, params):
        all_market_price = np.array((None,),dtype=float)
        all_model_price = np.array((None,),dtype=float)
        for unique_date in self.train['exdate'].unique():
            maturity_date = unique_date
            df = self.train.groupby(['exdate']).get_group(unique_date)[['exdate','cp_flag','strike_price','last','volume']].sort_values('strike_price')
            vanilla_option = option_class.BasicOption()
            (vanilla_option.set_underlying_close_price(underlying_price)
            .set_dividend(dividend_rate)
            .set_maturity_date(maturity_date)
            .set_evaluation_date(evaluation_date)
            .set_zero_rate(risk_free_rate))
        
            strike_arr = np.array(df['strike_price'])
            put_call = np.array(df['cp_flag'])
            all_market_price = np.append(all_market_price, np.array(df['last']))

        
            ft_pricer = pricing_class.FourierPricer(vanilla_option)
            #initialize parameters
            ft_pricer.set_log_st_process(process_class.VarianceGamma(
                    theta=params[0],
                    v=params[1],
                    sigma=params[2]))

            ft_pricer.set_pricing_engine(engine_class.FFTEngine(N=2**15, d_u=0.01, alpha=1, spline_order=2))

            fft_price = ft_pricer.calc_price(strike_arr,put_call)
            all_model_price = np.append(all_model_price, fft_price)
        
        all_market_price = all_market_price[1:]
        all_model_price = all_model_price[1:]
        return all_market_price - all_model_price
         
    def fit(self, initial, solver='lm'):
        return least_squares(self.residuals, initial, method = solver)
    
    
option_input_name = '../../data/option.pkl'
option_output_name = '../../data/option.pkl'
#read date
option = pd.read_pickle(option_input_name)
option = option[option['volume'] > 1]
option['cp_flag'] = option['cp_flag'].replace('P','put')
option['cp_flag'] = option['cp_flag'].replace('C','call')
option = option.dropna()
option = option[(option['best_bid'] > 1) & (option['best_offer'] > 1)]
#calibrate

result = pd.DataFrame(index = range(len(option.index.unique()) - 1),columns = ['date','percentage_square_error','percentage_square_error','MSSE'])
VG_price = pd.DataFrame()
params_initial = [-0.14,0.2,0.3]
for i in range(len(option.index.unique()) - 1)[:-3600]:
#for i in range(30):
    evaluation_date = option.index.unique()[i]
    train = option[option.index == evaluation_date]
    test = option[option.index == option.index.unique()[i+1]]
    underlying_price = train['index'][0]
    risk_free_rate = train['rf'][0]
    dividend_rate = train['dividend_rate'][0]
    
    option_fit = Option_Fitter(train)
    res = option_fit.fit(params_initial)
    [theta,v,sigma] = res.x
    params_initial = [theta,v,sigma] 
    #test
    test_evaluation_date = option.index.unique()[i+1]
    underlying_price = test['index'][0]
    risk_free_rate = test['rf'][0]
    dividend_rate = test['dividend_rate'][0]
    
    test_all_market_price = np.array((None,),dtype=float)
    test_all_model_price = np.array((None,),dtype=float)
    for unique_date in test['exdate'].unique():
            maturity_date = unique_date
            df = test.groupby(['exdate']).get_group(unique_date)[['exdate','cp_flag','strike_price','last','BS_realized_vol_price','volume']].sort_values('strike_price')
            vanilla_option = option_class.BasicOption()
            (vanilla_option.set_underlying_close_price(underlying_price)
            .set_dividend(dividend_rate)
            .set_maturity_date(maturity_date)
            .set_evaluation_date(test_evaluation_date)
            .set_zero_rate(risk_free_rate))
        
            strike_arr = np.array(df['strike_price'])
            put_call = np.array(df['cp_flag'])
            test_all_market_price = np.append(test_all_market_price, np.array(df['last']))
        
            ft_pricer = pricing_class.FourierPricer(vanilla_option)
            ft_pricer.set_log_st_process(process_class.VarianceGamma( theta,v,sigma))
            ft_pricer.set_pricing_engine(engine_class.FFTEngine(N=2**15, d_u=0.01, alpha=1, spline_order=2))
            fft_price = ft_pricer.calc_price(strike_arr,put_call)
            test_all_model_price = np.append(test_all_model_price, fft_price)
            df['VG_price'] = fft_price
            VG_price = VG_price.append(df)
            
    test_all_market_price = test_all_market_price[1:]
    test_all_model_price = test_all_model_price[1:]           
    square_error = np.sum(((test_all_market_price - test_all_model_price) / test_all_market_price)**2)
    result.iloc[i,:] = [test_evaluation_date,square_error,len(test),square_error /len(test) ]
    print(result.iloc[i,:])
    
#merge VG with option_price      
VG_price.to_pickle('VG_data/VG_price_xx_xx.pkl')

import os
VG_price = pd.DataFrame()
for filename in os.listdir('VG_data'):
    VG_price = VG_price.append(pd.read_pickle('VG_data/' + filename)  )
VG_price.to_pickle('VG_data/VG_price_all.pkl')
VG_price['BS_realized_vol_square_error'] = ((VG_price['BS_realized_vol_price']  - VG_price['last']) / VG_price['last'])**2 
VG_price['VG_square_error'] = ((VG_price['VG_price']  - VG_price['last']) / VG_price['last'])**2 

heston_price['heston_square_error'].nlargest(100)
 
print("mean square error for BS",VG_price['BS_realized_vol_square_error'].mean() )
print("mean square error for BS call option",VG_price.loc[VG_price['cp_flag'] == 'call','BS_realized_vol_square_error'].mean())
print("mean square error for BS put option",VG_price.loc[VG_price['cp_flag'] == 'put','BS_realized_vol_square_error'].mean())

print("mean square error for VG",VG_price['VG_square_error'].mean() )
print("mean square error for VG call option",VG_price.loc[VG_price['cp_flag'] == 'call','VG_square_error'].mean())
print("mean square error for VG put option",VG_price.loc[VG_price['cp_flag'] == 'put','VG_square_error'].mean())


option = option.reset_index().merge(VG_price[['exdate','cp_flag','strike_price','volume','VG_price']].reset_index(), how = 'left',on = ['date','exdate','cp_flag','strike_price','volume']).set_index('date')
option.to_pickle(option_output_name)