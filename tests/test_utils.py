from datetime import datetime, timedelta, timezone

from app.utils import time_ago, derive_name_from_email


def ago(**kwargs):
    return datetime.now(timezone.utc) - timedelta(**kwargs)


class TestTimeAgo:
    def test_none_returns_empty_string(self):
        assert time_ago(None) == ""

    def test_naive_datetime_assumed_utc(self):
        naive_now = datetime.now(timezone.utc).replace(tzinfo=None)
        assert time_ago(naive_now) == "Just now"

    def test_just_now(self):
        assert time_ago(ago(seconds=10)) == "Just now"

    def test_one_minute_ago_singular(self):
        assert time_ago(ago(minutes=1, seconds=5)) == "1 minute ago"

    def test_multiple_minutes_ago_plural(self):
        assert time_ago(ago(minutes=5)) == "5 minutes ago"

    def test_one_hour_ago_singular(self):
        assert time_ago(ago(hours=1, minutes=5)) == "1 hour ago"

    def test_multiple_hours_ago_plural(self):
        assert time_ago(ago(hours=5)) == "5 hours ago"

    def test_exactly_one_day_is_yesterday(self):
        assert time_ago(ago(days=1, hours=2)) == "Yesterday"

    def test_a_few_days_ago(self):
        assert time_ago(ago(days=3)) == "3 days ago"

    def test_one_week_ago_singular(self):
        assert time_ago(ago(weeks=1, days=1)) == "1 week ago"

    def test_multiple_weeks_ago_plural(self):
        assert time_ago(ago(weeks=3)) == "3 weeks ago"

    def test_one_month_ago_singular(self):
        assert time_ago(ago(days=35)) == "1 month ago"

    def test_multiple_months_ago_plural(self):
        assert time_ago(ago(days=100)) == "3 months ago"

    def test_one_year_ago_singular(self):
        assert time_ago(ago(days=370)) == "1 year ago"

    def test_multiple_years_ago_plural(self):
        assert time_ago(ago(days=800)) == "2 years ago"

    def test_future_datetime_does_not_go_negative(self):
        future = datetime.now(timezone.utc) + timedelta(minutes=5)
        assert time_ago(future) == "Just now"


class TestDeriveNameFromEmail:
    def test_dot_separated(self):
        assert derive_name_from_email("jane.doe@example.com") == "Jane Doe"

    def test_underscore_separated(self):
        assert derive_name_from_email("john_smith@example.com") == "John Smith"

    def test_hyphen_separated(self):
        assert derive_name_from_email("bob-jones@example.com") == "Bob Jones"

    def test_plus_separated(self):
        assert derive_name_from_email("alex+work@example.com") == "Alex Work"

    def test_mixed_separators(self):
        assert derive_name_from_email("mary_jane.watson@example.com") == "Mary Jane Watson"

    def test_single_word_local_part(self):
        assert derive_name_from_email("contact@example.com") == "Contact"

    def test_already_uppercase(self):
        assert derive_name_from_email("JOHN.DOE@example.com") == "John Doe"

    def test_numbers_stay_attached_to_word(self):
        assert derive_name_from_email("johndoe123@example.com") == "Johndoe123"

    def test_local_part_of_only_separators_falls_back_to_email(self):
        assert derive_name_from_email("...@example.com") == "...@example.com"
