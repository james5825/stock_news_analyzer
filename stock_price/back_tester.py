import datetime
import math

import backtrader as bt
import pandas as pd

from config import Config
from stock_price.trading_date_calculator import TradingHourStatus

BROKER_STARTING_CASH = Config.BROKER_STARTING_CASH


class BacktestResult:
    def __init__(self, total_pnl, total_pnl_ratio):
        self.total_pnl = total_pnl
        self.total_pnl_ratio = total_pnl_ratio


class NewsImpactStrategy(bt.Strategy):
    def __init__(self, impact_weight, maximum_impact_days, minimum_impact_days, position_movement,
                 start_trading_date, trading_hour_status: TradingHourStatus):
        self.impact_weight = impact_weight
        self.maximum_impact_days = maximum_impact_days
        self.minimum_impact_days = minimum_impact_days
        self.position_movement = position_movement
        self.start_trading_date = start_trading_date  # start trading date
        self.trading_hour_status = trading_hour_status  # trading hour status

        self.holding_days = math.floor((self.minimum_impact_days + self.maximum_impact_days) / 2)
        self.size = self.impact_weight * 10  # weight position size
        self.entry_price = None
        self.entry_date = None
        self.total_pnl = 0  # total profit and loss
        self.total_pnl_ratio = 0
        self.trade_completed = False  # flag to indicate if trade is completed

        # Keep a reference to the "close" line in the data[0] dataseries
        self.dataclose = self.datas[0].close

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"BUY EXECUTED: Price {order.executed.price}, Size {order.executed.size}, Date {self.datas[0].datetime.date(0)}")
            elif order.issell():
                print(f"SELL EXECUTED: Price {order.executed.price}, Size {order.executed.size}, Date {self.datas[0].datetime.date(0)}")

    def notify_trade(self, trade):
        if trade.isclosed:
            pnl = trade.pnl
            self.total_pnl += pnl
            print(f"TRADE CLOSED: Gross PnL {pnl}, Net PnL {trade.pnlcomm}")

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        # print(f"Checking conditions on {current_date}:")
        # print(f" - Start Impact Date: {self.start_impact_date}")
        # print(f" - Holding Days: {self.holding_days}")
        # print(f" - Current Position: {'Open' if self.position else 'None'}")
        # print(f" - Trade Completed: {self.trade_completed}")

        if not self.trade_completed:
            if current_date == self.start_trading_date:
                print(" -> Condition met: Entering position")
                if self.position_movement == 'long':
                    if self.trading_hour_status.is_in_trading_hour:
                        self.buy(price=self.data.high[0], size=self.size)
                        self.entry_price = self.data.high[0]
                    else:
                        self.buy(price=self.data.open[0], size=self.size)
                        self.entry_price = self.data.open[0]
                else:
                    if self.trading_hour_status.is_in_trading_hour:
                        self.sell(price=self.data.low[0], size=self.size)
                        self.entry_price = self.data.low[0]
                    else:
                        self.sell(price=self.data.open[0], size=self.size)
                        self.entry_price = self.data.open[0]

                self.entry_price = self.data.close[0]
                self.entry_date = current_date

            if self.position and (current_date - self.entry_date).days >= self.holding_days:
                print(" -> Condition met: Closing position")
                self.close()
                self.trade_completed = True  # Trade completed, no entry anymore

    def stop(self):
        print(f"FINAL TOTAL PnL: {self.total_pnl}")
        self.total_pnl_ratio = self.total_pnl / (self.entry_price * self.size)
        print(f"FINAL TOTAL PnL%: {self.total_pnl_ratio}")
        if self.total_pnl > 0:
            print("RESULT: GAIN ✅")
        elif self.total_pnl < 0:
            print("RESULT: LOSS ❌")
        else:
            print("RESULT: BREAKEVEN ⚖️")


class BacktestRunner:
    def __init__(self, data_frame):
        self.data_frame = data_frame

    def run(self,
            impact_weight, maximum_impact_days, minimum_impact_days,
            position_movement, start_trading_date: datetime, trading_hour_status=None):
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(BROKER_STARTING_CASH)
        cerebro.addstrategy(NewsImpactStrategy,
                            impact_weight=impact_weight,
                            maximum_impact_days=maximum_impact_days,
                            minimum_impact_days=minimum_impact_days,
                            position_movement=position_movement,
                            start_trading_date=start_trading_date,
                            trading_hour_status=trading_hour_status
                            )

        cerebro.adddata(bt.feeds.PandasData(dataname=self.data_frame))
        st = cerebro.run()

        # cerebro.plot()

        return BacktestResult(st[0].total_pnl, st[0].total_pnl_ratio)


if __name__ == "__main__":
    impact_weight_l = 6
    maximum_impact_days_l = 4
    minimum_impact_days_l = 2
    position_movement_l = "short"
    start_impact_date_l = datetime.date(2025, 2, 18)

    data_file_l = "data_stock_price/AAPL.csv"

    df_l = pd.read_csv(data_file_l, index_col='Date', parse_dates=True)
    df_l = df_l.loc['2025-2-18':'2025-2-28']

    runner = BacktestRunner(df_l)
    runner.run(impact_weight=impact_weight_l,
               maximum_impact_days=maximum_impact_days_l,
               minimum_impact_days=minimum_impact_days_l,
               position_movement=position_movement_l,
               start_trading_date=start_impact_date_l,
               trading_hour_status=TradingHourStatus(
                   next_trading_open=datetime.datetime(2025, 2, 19, 9, 30),
                   is_in_trading_hour=False,
                   is_same_day_before_trading_hour=False,
                   is_same_day_after_trading_hour=False,
                   is_in_weekend=False,
                   is_in_holiday=False,
                   hours_before_open=24
               ))
