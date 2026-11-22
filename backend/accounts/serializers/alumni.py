"""Alumni conversion (spec 3.1.1.6.1) - a student becoming an alum."""

from django.utils import timezone
from rest_framework import serializers

EARLIEST_GRADUATION_YEAR = 1900


class AlumniConversionSerializer(serializers.Serializer):
    """The one thing a student enters to convert is when they graduated."""

    graduation_date = serializers.DateField()

    def validate_graduation_date(self, value):
        # localdate(): "today" in TIME_ZONE (America/New_York), not UTC.
        # So graduating today works all day, including the evening.
        if value > timezone.localdate():
            raise serializers.ValidationError('Graduation date cannot be in the future.')
        if value.year < EARLIEST_GRADUATION_YEAR:
            raise serializers.ValidationError(
                f'Graduation date must be in {EARLIEST_GRADUATION_YEAR} or later.'
            )
        return value


class AlumniConversionResultSerializer(serializers.Serializer):
    """Response shape after converting."""

    role = serializers.CharField(read_only=True)
    graduation_date = serializers.DateField(read_only=True)
