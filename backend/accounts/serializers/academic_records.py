from django.http import Http404
from rest_framework import serializers

from ..models import Certificate, Skill, StudentProfile, TakenClass


class CurrentStudentProfileDefault:
    """Resolves to the caller's own StudentProfile. Lets `student`
    participate in Skill's (student, name) uniqueness validation without
    ever accepting it from client input. 404s (not 500s) if the caller
    hasn't created a profile yet. Same as the other profile-scoped views."""

    requires_context = True

    def __call__(self, serializer_field):
        try:
            return serializer_field.context['request'].user.student_profile
        except StudentProfile.DoesNotExist:
            raise Http404 from None

    def __repr__(self):
        return f'{self.__class__.__name__}()'


class TakenClassSerializer(serializers.ModelSerializer):
    """`student` is set by the view from the caller's own profile, never
    accepted from the request body."""

    class Meta:
        model = TakenClass
        fields = [
            'id',
            'course_code',
            'course_name',
            'semester',
            'year',
            'grade',
            'credits',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CertificateSerializer(serializers.ModelSerializer):
    """`student` is set by the view from the caller's own profile, never
    accepted from the request body."""

    class Meta:
        model = Certificate
        fields = [
            'id',
            'name',
            'issuing_organization',
            'date_earned',
            'credential_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillSerializer(serializers.ModelSerializer):
    """`student` is a HiddenField (always resolved from the caller, never
    from the request body). So ModelSerializer can still build the
    (student, name) UniqueTogetherValidator automatically."""

    student = serializers.HiddenField(default=CurrentStudentProfileDefault())

    class Meta:
        model = Skill
        fields = ['id', 'student', 'name', 'proficiency_level', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
