#!/usr/bin/env python3
"""Calculate holiday days still to take in Belgium before year end."""

import argparse
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_FLOOR

import holidays


HOLIDAY_HOURS = Decimal("7.6")
DAILY_ACCRUAL = Decimal("0.4")
WORKED_HOURS = Decimal("8")


@dataclass(frozen=True)
class CalendarSummary:
    start: date
    end: date
    weekdays: int
    public_holidays: tuple[tuple[date, str], ...]
    booked_days: Decimal
    working_days: Decimal


@dataclass(frozen=True)
class HolidayCalculation:
    total_hours: Decimal
    days: Decimal
    accrued_hours: Decimal


def count_working_days(start: date, booked_days: Decimal) -> CalendarSummary:
    """Count the inclusive period, subtracting only weekday public holidays."""
    end = date(start.year, 12, 31)
    weekdays = sum(
        (start + timedelta(days=offset)).weekday() < 5
        for offset in range((end - start).days + 1)
    )
    public_holidays = tuple(sorted(
        (day, name)
        for day, name in holidays.Belgium(years=start.year).items()
        if start <= day <= end
    ))
    weekday_holidays = sum(day.weekday() < 5 for day, _ in public_holidays)
    working_days = max(
        Decimal("0"), Decimal(weekdays - weekday_holidays) - booked_days
    )
    return CalendarSummary(
        start, end, weekdays, public_holidays, booked_days, working_days
    )


def calculate_holiday(
    legal_hours: Decimal,
    recup_days: Decimal,
    meeruren: Decimal,
    working_days: Decimal,
) -> HolidayCalculation:
    """Solve H + 0.4 * (W - D) = 7.6 * D without holiday-day accrual."""
    total_hours = legal_hours + recup_days * HOLIDAY_HOURS + meeruren
    days = (total_hours + DAILY_ACCRUAL * working_days) / WORKED_HOURS
    accrued_hours = DAILY_ACCRUAL * (working_days - days)
    return HolidayCalculation(total_hours, days, accrued_hours)


def parse_date(value: str) -> date:
    try:
        parsed = datetime.strptime(value, "%d-%m-%Y")
        if parsed.strftime("%d-%m-%Y") != value:
            raise ValueError
        return parsed.date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            "enter a valid date in DD-MM-YYYY format"
        ) from None


def nonnegative_number(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(
            "enter a finite, non-negative number"
        ) from None
    if not number.is_finite() or number < 0:
        raise argparse.ArgumentTypeError("enter a finite, non-negative number")
    return number


def prompt_value(label, converter, default=None):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        value = input(f"{label}{suffix}: ").strip()
        if not value and default is not None:
            return converter(default)
        try:
            return converter(value)
        except argparse.ArgumentTypeError as error:
            print(f"Invalid input: {error}")


def print_breakdown(calendar, result, legal_hours, recup_days, meeruren):
    print("HOLIDAY CALCULATOR")
    print("==================")
    print()
    print("Period & availability")
    print("---------------------")
    print(f"Period: {calendar.start} to {calendar.end} (inclusive)")
    print(f"Weekdays (Monday-Friday): {calendar.weekdays}")
    weekday_holidays = sum(
        day.weekday() < 5 for day, _ in calendar.public_holidays
    )
    print(
        f"Public holidays: {len(calendar.public_holidays)} total; "
        f"{weekday_holidays} weekday(s) deducted"
    )
    for day, name in calendar.public_holidays:
        note = " (weekend; not subtracted)" if day.weekday() >= 5 else ""
        print(f"  - {day}: {name}{note}")
    print(
        f"Booked days: {calendar.booked_days:.2f} "
        "(already deducted from balances)"
    )
    print(f"Remaining working days (W): {calendar.working_days}")
    print()
    print("Holiday balances")
    print("----------------")
    print(f"Legal holiday (wettelijk verlof): {legal_hours:.2f} hours")
    print(
        f"Recup: {recup_days:.2f} days "
        f"({recup_days * HOLIDAY_HOURS:.2f} hours)"
    )
    print(f"Current meeruren: {meeruren:.2f} hours")
    print(f"Current total (H): {result.total_hours:.2f} hours")
    print()
    print("Result")
    print("------")
    print(f"Holiday to take (D): {result.days:.2f} days")
    print(
        "Meeruren still to accrue on working days: "
        f"{result.accrued_hours:.2f} hours"
    )
    whole_days = result.days.to_integral_value(rounding=ROUND_FLOOR)
    half_day_units = (result.days * 2).to_integral_value(rounding=ROUND_FLOOR)
    half_days = half_day_units / Decimal("2")
    whole_day_label = "day" if whole_days == 1 else "days"
    print(f"Rounded down to whole days: {whole_days} {whole_day_label}")
    print(
        "Rounded down to half-day increments: "
        f"{half_days} days ({half_day_units} half-day units)"
    )
    print("These rounded figures are alternatives, not additive.")
    if result.days > calendar.working_days:
        print(
            "WARNING: Remaining working days are not enough to use up all "
            "the holiday. D is shown uncapped; negative projected accrual "
            "reflects this infeasible schedule."
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--date", type=parse_date, help="current date DD-MM-YYYY (default: today)"
    )
    fields = (
        ("legal_hours", "Remaining legal holiday (wettelijk verlof), HOURS"),
        ("recup_days", "Remaining recuperable days (recup), DAYS"),
        ("booked_days", "Already booked days, DAYS (balances already deducted)"),
        ("meeruren", "Current overtime balance (meeruren), HOURS"),
    )
    for name, label in fields:
        parser.add_argument(
            "--" + name.replace("_", "-"), type=nonnegative_number, help=label
        )
    args = parser.parse_args(argv)
    try:
        if args.date is None:
            args.date = prompt_value(
                "Current date (DD-MM-YYYY)",
                parse_date,
                date.today().strftime("%d-%m-%Y"),
            )
        for name, label in fields:
            if getattr(args, name) is None:
                setattr(args, name, prompt_value(label, nonnegative_number))
    except (EOFError, KeyboardInterrupt):
        parser.error("input cancelled; supply all arguments for non-interactive use")
    calendar = count_working_days(args.date, args.booked_days)
    result = calculate_holiday(
        args.legal_hours, args.recup_days, args.meeruren, calendar.working_days
    )
    print_breakdown(
        calendar, result, args.legal_hours, args.recup_days, args.meeruren
    )


if __name__ == "__main__":
    main()
