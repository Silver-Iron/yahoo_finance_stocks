import pandas as pd 
import numpy as np 
import datetime as dt
import pandas.io.data as web
from decimal import Decimal
from td_sequence import TDSequence

from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor as rfr
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.grid_search import GridSearchCV
from sklearn.cross_validation import train_test_split
from sklearn.metrics import make_scorer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.externals import joblib

'''
Sample data from 2016-07-25, name may changes as date changes
Using AAPL as test
'''
symbol = 'AAPL'
start = dt.datetime(2012, 1, 1)
end = dt.date.today()
df1 = pd.read_csv('data/companylist.csv')
df2 = pd.read_csv('data/companylist1.csv')
df3 = pd.read_csv('data/companylist2.csv')
symbols = np.append(df1.Symbol.values, df2.Symbol.values)
symbols = np.append(symbols, df3.Symbol.values)

'''DF details from before'''
er_date = '2016-08-16'
c = web.DataReader(symbol, 'yahoo', start, end)
df_stock_detail = pd.read_pickle('data/2016-07-25_all_stocks_info')
df_stock_cash_flow_quarter = pd.read_pickle('data/2016-08-19_cash_flow_quarter.pkl')
df_stock_balance_sheet_quarter = pd.read_pickle('data/2016-08-19_balance_sheet_quarter.pkl')
df_stock_balance_sheet_annual = pd.read_pickle('data/2016-08-19_balance_sheet_annual.pkl')
df_stock_income_statement_quarter = pd.read_pickle('data/2016-08-19_income_statement_quarter.pkl')
df_stock_income_statement_annual = pd.read_pickle('data/2016-08-19_income_statement_quarter.pkl')

df_er = pd.read_pickle('data/rev_full_history_er_date.pkl')

new_col_names = []
for i in df_stock_detail.columns.values:
    new_col_names.append(i.strip())
df_stock_detail.columns = new_col_names

df = pd.DataFrame(columns = ['current_price','price_to_book_value_q','price_to_free_cash_flow_q','price_to_earnings_q', 'price_to_sales_q', 'dividends', 'long_term_debt_quarter', \
                        'capital_spending_diff', 'market_cap', 'return_on_total_capital', 'return_on_shareholders_equity', 'extra_shares_outstanding', 'td_sequence' ])
j = 0
y =[]
for symbol in symbols:
    try:
#         print 'current running', symbol
        '''sample data detail: AAPL'''
        c = web.DataReader(symbol, 'yahoo', start, end)
        earning_report = df_er[df_er['symbol'] == symbol][:10]
        earning_report['er_date'] = pd.to_datetime(earning_report['er_date'])
        
        adj_dates = []
        for ix, time in enumerate(earning_report['time']):
            if 'After' in time or 'pm' in time:
                adj_dates.append(earning_report['er_date'].iloc[ix])
            else:
                adj_day = 1
                new_date = earning_report['er_date'].iloc[ix] - dt.timedelta(days=adj_day)
                for i in xrange(100):
                    if new_date not in c.index:
                        adj_day +=1
                        new_date = earning_report['er_date'].iloc[ix] - dt.timedelta(days=adj_day)
                        if i == 99:
                            print 'cannot find the er date', symbol
                            continue
                    else:
                        break
                    
                adj_dates.append(new_date)
        earning_report['adj_er_date'] = adj_dates
        earning_report.reset_index(drop = True, inplace = True)
#         print earning_report['er_date'][0].year
        if len(earning_report) == 0:
            continue
        if int(min(earning_report['er_date']).year) < 2012:
            continue
        symbol_cash_flow_q = df_stock_cash_flow_quarter[df_stock_cash_flow_quarter['symbol'] == symbol]
        symbol_balance_sheet_q = df_stock_balance_sheet_quarter[df_stock_balance_sheet_quarter['symbol'] == symbol]
        symbol_income_statement_q = df_stock_income_statement_quarter[df_stock_income_statement_quarter['symbol'] == symbol]
        if len(earning_report['adj_er_date']) <= 2:
            print 'too new stock', symbol
            continue
        statements = min(len(earning_report['er_date']),len(symbol_cash_flow_q), len(symbol_balance_sheet_q), len(symbol_income_statement_q))
        for i in xrange(statements-2):
            if earning_report['adj_er_date'][i+1] not in c.index or earning_report['adj_er_date'][i] not in c.index:
                continue
            price = Decimal(c.loc[earning_report['adj_er_date'][i+1]]['Close'])
            current_price = Decimal(c.loc[earning_report['adj_er_date'][i]]['Close'])
            adj_day = 1
            new_date = earning_report['adj_er_date'].iloc[i] + dt.timedelta(days=adj_day)
            while new_date not in c.index:
                adj_day +=1
                new_date = earning_report['er_date'].iloc[i] + dt.timedelta(days=adj_day)
            next_close_price = c.loc[new_date]['Close']

            symbol_cash_flow_prevQ1 = symbol_cash_flow_q.iloc[i+1]
            symbol_cash_flow_prevQ1 = symbol_cash_flow_prevQ1.fillna(0)
            symbol_cash_flow_prevQ2 = symbol_cash_flow_q.iloc[i+2]
            symbol_cash_flow_prevQ2 = symbol_cash_flow_prevQ2.fillna(0)
            symbol_balance_sheet_prevQ1 = symbol_balance_sheet_q.iloc[i+1]
            symbol_balance_sheet_prevQ1 = symbol_balance_sheet_prevQ1.fillna(0)
            symbol_balance_sheet_prevQ2 = symbol_balance_sheet_q.iloc[i+2]
            symbol_balance_sheet_prevQ2 = symbol_balance_sheet_prevQ2.fillna(0)
            symbol_income_statement_prevQ1 = symbol_income_statement_q.iloc[i+1]
            symbol_income_statement_prevQ1 = symbol_income_statement_prevQ1.fillna(0)
            '''fundamental details'''
            if symbol_cash_flow_prevQ1['Capital Expenditures'] == None:
                cap_expense_q1 = 0
            else:
                cap_expense_q1 = symbol_cash_flow_prevQ1['Capital Expenditures']
            if symbol_cash_flow_prevQ2['Capital Expenditures'] == None:
                cap_expense_q2 = 0
            else:
                cap_expense_q2 = symbol_cash_flow_prevQ2['Capital Expenditures']  
            preferred_stock = Decimal(0 if symbol_balance_sheet_prevQ1['Redeemable Preferred Stock, Total'] == None else symbol_balance_sheet_prevQ1['Redeemable Preferred Stock, Total']) \
                                + Decimal(0 if symbol_balance_sheet_prevQ1['Preferred Stock - Non Redeemable, Net'] == None else symbol_balance_sheet_prevQ1['Preferred Stock - Non Redeemable, Net']) 
            free_cash_flow = (symbol_cash_flow_prevQ1['Cash from Operating Activities'] + cap_expense_q1)
            if symbol_income_statement_prevQ1['Total Revenue'] == None:
                total_revenue = 0
            else:
                total_revenue = symbol_income_statement_prevQ1['Total Revenue'] 
            net_income = symbol_income_statement_prevQ1['Net Income']
            debt = symbol_balance_sheet_prevQ1['Total Long Term Debt']
            if debt == None:
                debt = 0
            if symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] == 0:
                symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] = 1
            if symbol_balance_sheet_prevQ1['Total Equity'] == None:
                symbol_balance_sheet_prevQ1['Total Equity'] = 0
            equity = symbol_balance_sheet_prevQ1['Total Equity']
            book_value = (symbol_balance_sheet_prevQ1['Total Equity'] - preferred_stock ) / symbol_balance_sheet_prevQ1['Total Common Shares Outstanding']


            '''value investing'''
            price_to_book_value_q = price/book_value
            if free_cash_flow ==0:
                price_to_free_cash_flow_q = 99999
            else:
                price_to_free_cash_flow_q = price/free_cash_flow
            if symbol_income_statement_prevQ1['Diluted Normalized EPS'] == None or symbol_income_statement_prevQ1['Diluted Normalized EPS'] == 0:
                price_to_earnings_q = 99999
            else:
                price_to_earnings_q = price / symbol_income_statement_prevQ1['Diluted Normalized EPS']
            price_to_sales_q = total_revenue / symbol_balance_sheet_prevQ1['Total Common Shares Outstanding']
            if symbol_income_statement_prevQ1['Dividends per Share - Common Stock Primary Issue'] == None:
                dividends = 0
            else:
                dividends = symbol_income_statement_prevQ1['Dividends per Share - Common Stock Primary Issue']
            if symbol_balance_sheet_prevQ1['Long Term Debt'] == None:
                long_term_debt_quarter  = 0
            else:
                long_term_debt_quarter = symbol_balance_sheet_prevQ1['Long Term Debt']

            if max(symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'],symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']) / min(symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'], symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']) >= 2:
                capital_spending_diff = cap_expense_q1/symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] - cap_expense_q2/symbol_balance_sheet_prevQ1['Total Common Shares Outstanding']
            else:
                capital_spending_diff = cap_expense_q1/symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] - cap_expense_q2/symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']
            market_cap = symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] * price
            return_on_total_capital =  (net_income - dividends * symbol_balance_sheet_prevQ1['Total Common Shares Outstanding']) / (debt + equity)
            return_on_shareholders_equity = net_income/equity 
            extra_shares_outstanding = symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] - symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']

            '''td_sequential'''
            end_date = earning_report['adj_er_date'][i]
            data = web.DataReader(symbol, 'yahoo', start, end_date)
            td = TDSequence(data)
            td_sequence = td.sequence()

            '''candle_stick'''

            '''sample df'''
            df.loc[j] = [current_price, price_to_book_value_q,price_to_free_cash_flow_q,price_to_earnings_q,price_to_sales_q,\
                        dividends, long_term_debt_quarter, capital_spending_diff, market_cap, return_on_total_capital, return_on_shareholders_equity,\
                        extra_shares_outstanding, td_sequence]
            j += 1
            y.append(next_close_price)
    except IOError:
        print symbol
X = df.values
'''
Simple train_test_split
'''
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=67)

'''
First crappy model: random forest
'''
clf = rfr()
clf.fit(X_train, y_train)
print clf.score(X_test,y_test)
print clf.predict(X_test),y_test
# Below are for futrue test data...not useful for training with lack of data
# symbol_detail = df_stock_detail[df_stock_detail['Symbol'] == symbol]
# symbol_quarter_idx = symbol+'_prev_1Q'
# temp = symbol+'_' + str(dt.date.today().year)
# temp2 = symbol+'_' + str(dt.date.today().year-1)
# if temp in df_stock_balance_sheet_annual.index:
#   symbol_annual_idx = temp
# elif temp2 in df_stock_balance_sheet_annual.index:
#     symbol_annual_idx = temp2
# else:
#     symbol_annual_idx = symbol+'_' + str(dt.date.today().year-2)

# symbol_cash_flow_prevQ1 = df_stock_cash_flow_quarter.ix[symbol_quarter_idx]
# symbol_balance_sheet_annual = df_stock_balance_sheet_annual.ix[symbol_annual_idx]
# symbol_balance_sheet_prevQ1 = df_stock_balance_sheet_quarter.ix[symbol_quarter_idx]
# symbol_balance_sheet_prevQ2 = df_stock_balance_sheet_quarter.ix[symbol+'_prev_2Q']
# symbol_cash_flow_prevQ1 = df_stock_cash_flow_quarter.ix[symbol_quarter_idx]
# symbol_cash_flow_prevQ2 = df_stock_cash_flow_quarter.ix[symbol+'_prev_2Q']

# '''value investing'''
# price_to_book_value = symbol_detail['Price/Book']
# price_to_free_cash_flow_prevQ1 = c['Adj Close'][er_date]/(symbol_cash_flow_prevQ1['Cash from Operating Activities'] + symbol_cash_flow_prevQ1['Capital Expenditures'])
# price_to_earnings = symbol_detail['P/E Ratio']
# price_to_sales = symbol_detail['Price/Sales']
# dividends = symbol_detail['Dividend/Share']
# long_term_debt_quarter = symbol_balance_sheet_prevQ1['Long Term Debt']
# long_term_debt_annual = symbol_balance_sheet_annual['Long Term Debt']

# if max(symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'],symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']) / min(symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'], symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']) >= 2:
#     capital_spending_diff = symbol_cash_flow_prevQ1['Capital Expenditures']/symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] - symbol_cash_flow_prevQ2['Capital Expenditures']/symbol_balance_sheet_prevQ1['Total Common Shares Outstanding']
# else:
#     capital_spending_diff = symbol_cash_flow_prevQ1['Capital Expenditures']/symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] - symbol_cash_flow_prevQ2['Capital Expenditures']/symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']

# market_cap = symbol_detail['Market Capitalization']
# shares_outstanding = symbol_balance_sheet_prevQ1['Total Common Shares Outstanding'] - symbol_balance_sheet_prevQ2['Total Common Shares Outstanding']

