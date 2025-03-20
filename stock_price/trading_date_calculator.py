from dataclasses import dataclass
from datetime import datetime, timezone, timedelta

import exchange_calendars as xcals
import pytz


@dataclass
class TradingHourStatus:
    next_trading_open: datetime
    is_in_trading_hour: bool
    is_same_day_before_trading_hour: bool
    is_same_day_after_trading_hour: bool
    is_in_weekend: bool
    is_in_holiday: bool
    hours_before_open: float

    def get_publication_comment(self, publication_timestamp: str) -> str:
        # TODO: More information digestion and market movement can be considered and generated based on this information.
        # TODO: Change all timezone to New York time

        """Generate a comment based on the publication timestamp and trading hour status."""
        if self.is_in_trading_hour:
            return f"The article is published at {publication_timestamp}, during active market trading hours."
        elif self.is_same_day_before_trading_hour:
            return (f"The article is published at {publication_timestamp}, before market trading hours on the same day. "
                    f"Market participants have approximately {self.hours_before_open:.2f} hours to analyze and incorporate this information "
                    f"before the next market open at {self.next_trading_open}.")
        elif self.is_same_day_after_trading_hour:
            return (f"The article is published at {publication_timestamp}, after market trading hours on the same day. "
                    f"Market participants have approximately {self.hours_before_open:.2f} hours to process this information "
                    f"before the next market open at {self.next_trading_open}.")
        else:
            period = "weekend" if self.is_in_weekend else "holiday"
            return (f"The article is published at {publication_timestamp}, during a {period}. "
                    f"Market participants have approximately {self.hours_before_open:.2f} hours to consider its implications "
                    f"before markets reopen at {self.next_trading_open}.")


class TradingDateCalculator:
    _default_exchange = "NYSE"

    @classmethod
    def set_default_exchange(cls, exchange: str):
        """
        Set the default exchange for the TradingDateCalculator.
        :param exchange: The exchange code (e.g., 'NYSE', 'NASDAQ', 'CME').
        """
        cls._default_exchange = exchange

    @classmethod
    def get_trading_hour(cls, timestamp: str | datetime, exchange: str = None) -> TradingHourStatus:
        """
        Get the trading status for a given exchange and timestamp.
        :param timestamp: The timestamp string in 'YYYY-MM-DDTHH:MM:SSZ' format.
        :param exchange: The exchange code. If None, uses the default exchange.
        :return: TradingHourStatus model with next trading open and trading hour details.
        """
        if exchange is None:
            exchange = cls._default_exchange

        calendar = xcals.get_calendar(exchange)
        # if isinstance(timestamp, str):
        #     dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        # else:
        #     dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        if isinstance(timestamp, str):
            dt = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ").astimezone(pytz.timezone('US/Eastern'))
        else:
            dt = timestamp.astimezone(pytz.timezone('US/Eastern')) if timestamp.tzinfo else timestamp.replace(tzinfo=pytz.timezone('US/Eastern'))

        date = dt.date()

        if calendar.is_session(date):
            market_open = calendar.session_open(date).tz_convert("US/Eastern")
            market_close = calendar.session_close(date).tz_convert("US/Eastern")

            is_in_trading_hour = market_open <= dt <= market_close
            is_same_day_before_trading_hour = dt < market_open
            is_same_day_after_trading_hour = dt > market_close
            hours_before_open = max((market_open - dt).total_seconds() / 3600, 0) if is_same_day_before_trading_hour else 0

            if is_in_trading_hour:
                return TradingHourStatus(
                    next_trading_open=dt,
                    is_in_trading_hour=True,
                    is_same_day_before_trading_hour=False,
                    is_same_day_after_trading_hour=False,
                    is_in_weekend=False,
                    is_in_holiday=False,
                    hours_before_open=0
                )
            elif is_same_day_before_trading_hour:
                return TradingHourStatus(
                    next_trading_open=market_open,
                    is_in_trading_hour=False,
                    is_same_day_before_trading_hour=True,
                    is_same_day_after_trading_hour=False,
                    is_in_weekend=False,
                    is_in_holiday=False,
                    hours_before_open=hours_before_open
                )
            else:
                next_open = calendar.next_open(date + timedelta(days=1)).tz_convert("US/Eastern")
                hours_before_open = max((next_open - dt).total_seconds() / 3600, 0)
                return TradingHourStatus(
                    next_trading_open=next_open,
                    is_in_trading_hour=False,
                    is_same_day_before_trading_hour=False,
                    is_same_day_after_trading_hour=True,
                    is_in_weekend=False,
                    is_in_holiday=False,
                    hours_before_open=hours_before_open
                )

        previous_open = calendar.previous_open(date).tz_convert("US/Eastern")
        next_open = calendar.next_open(date).tz_convert("US/Eastern")
        hours_between = (next_open - previous_open).total_seconds() / 3600

        is_holiday = hours_between > 72  # open to open is 3 days = 72 hours, if close to open is 65.5
        is_weekend = not is_holiday

        hours_before_open = max((next_open - dt).total_seconds() / 3600, 0)
        return TradingHourStatus(
            next_trading_open=next_open,
            is_in_trading_hour=False,
            is_same_day_before_trading_hour=False,
            is_same_day_after_trading_hour=True,
            is_in_weekend=is_weekend,
            is_in_holiday=is_holiday,
            hours_before_open=hours_before_open
        )


# Example usage:
if __name__ == "__main__":
    test_cases = [
        ("2025-02-25T14:30:00Z", "NYSE"),  # In trading hours
        ("2025-02-25T08:00:00Z", "NYSE"),  # Before trading hours
        ("2025-02-25T23:00:00Z", "NYSE"),  # After trading hours
        ("2025-12-25T12:00:00Z", "NYSE"),  # Holiday (Christmas)
        ("2025-07-04T15:00:00Z", "NYSE"),  # Holiday (Independence Day)
        ("2025-02-22T12:00:00Z", "NYSE"),  # Weekend (Saturday)

    ]

    for timestamp_l, exchange_l in test_cases:
        eastern_timestamp = (datetime.strptime(timestamp_l, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                             .astimezone(pytz.timezone('US/Eastern')))

        status = TradingDateCalculator.get_trading_hour(timestamp_l, exchange_l)
        print(f"Timestamp: {eastern_timestamp}, Exchange: {exchange_l}")
        print(f"  Next Trading Open: {status.next_trading_open}")
        print(f"  In Trading Hour: {status.is_in_trading_hour}")
        print(f"  Before Trading Hour: {status.is_same_day_before_trading_hour}")
        print(f"  After Trading Hour: {status.is_same_day_after_trading_hour}")
        print(f"  Is Holiday: {status.is_in_holiday}")
        print(f"  Is Weekend: {status.is_in_weekend}")

        print(f"  Hours Before Open: {status.hours_before_open:.2f} hours")
        print()
