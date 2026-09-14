from rest_framework import serializers

from ..models import StudentProfile


class StudentProfileSerializer(serializers.ModelSerializer):
    """Read/response shape - includes first/last name from CustomUser even
    though they live outside StudentProfile, since a profile view is
    naturally where a frontend wants them alongside student-specific
    fields."""

    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = StudentProfile
        fields = [
            'student_id',
            'first_name',
            'last_name',
            'major',
            'uni',
            'location',
            'readiness_score',
            'graduated',
            'updated_at',
        ]


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    """Creates the caller's own profile - student_id is set once here and is
    not editable afterwards (see StudentProfileUpdateSerializer)."""

    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)

    class Meta:
        model = StudentProfile
        fields = [
            'student_id',
            'first_name',
            'last_name',
            'major',
            'uni',
            'location',
            'graduated',
        ]

    def create(self, validated_data):
        user_data = validated_data.pop('user', {})
        user = self.context['request'].user
        if user_data:
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save(update_fields=list(user_data.keys()))
        return StudentProfile.objects.create(user=user, **validated_data)


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """Partial update of the caller's own profile. No student_id field -
    school-issued, not something a student can change themselves. No
    readiness_score - computed, not self-reported."""

    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)

    class Meta:
        model = StudentProfile
        fields = ['first_name', 'last_name', 'major', 'uni', 'location', 'graduated']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save(update_fields=list(user_data.keys()))
        return super().update(instance, validated_data)
