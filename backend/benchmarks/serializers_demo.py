"""Response shapes for the demo endpoints (GP-82) - demo version of
serializers.py. Used for the /api/docs/ schema; the views return the dicts
built by scoring_demo.py and views_demo.py."""

from rest_framework import serializers

from .serializers import BenchmarkResultSerializer, RoleSerializer


class ToolSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Exact O*NET name - save this on the Skill row')
    label = serializers.CharField(help_text='Display name, e.g. "SQL"')


class LevelOptionSerializer(serializers.Serializer):
    value = serializers.CharField(help_text="Save as proficiency_level, e.g. 'expert'")
    label = serializers.CharField(help_text="Show in the UI, e.g. 'Project ready'")
    credit = serializers.FloatField(help_text="Share of a group's points earned, 0-1")


class SkillGroupOptionSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    points = serializers.FloatField(help_text='Points the group is worth, out of 50')
    tools = ToolSerializer(many=True)


class CourseOptionSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="Save as course_code, e.g. 'CS 361'")
    name = serializers.CharField(help_text='Save as course_name')


class DemoOptionsSerializer(serializers.Serializer):
    """Everything the demo input page's pickers offer."""

    role = RoleSerializer()
    school = serializers.CharField()
    location = serializers.CharField()
    levels = LevelOptionSerializer(many=True)
    skill_groups = SkillGroupOptionSerializer(many=True)
    courses = CourseOptionSerializer(many=True)
    certificates = serializers.ListField(
        child=serializers.CharField(), help_text='Save as the Certificate name'
    )


class SkillGroupResultSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    points = serializers.FloatField(help_text='Points earned')
    out_of = serializers.FloatField(help_text='Points the group is worth')
    best_tool = serializers.CharField(
        allow_null=True, help_text='Label of the tool that earned the points; null = none'
    )
    level = serializers.CharField(
        allow_null=True, help_text="'Learning', 'Practicing', 'Project ready' or null"
    )
    options = ToolSerializer(many=True)


class SkillsResultSerializer(serializers.Serializer):
    points = serializers.FloatField()
    out_of = serializers.IntegerField()
    groups = SkillGroupResultSerializer(many=True)


class CourseResultSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    taken = serializers.BooleanField()
    points = serializers.FloatField(help_text='Points the course is worth')


class CoursesResultSerializer(serializers.Serializer):
    points = serializers.FloatField()
    out_of = serializers.IntegerField()
    list = CourseResultSerializer(many=True)


class CertificatesResultSerializer(serializers.Serializer):
    bonus = serializers.IntegerField()
    max_bonus = serializers.IntegerField()
    counted = serializers.ListField(
        child=serializers.CharField(), help_text='Certificates that earned the bonus'
    )
    options = serializers.ListField(
        child=serializers.CharField(), help_text='Certificates that would count'
    )


class NextStepSerializer(serializers.Serializer):
    kind = serializers.CharField(help_text="'skill' or 'course'")
    name = serializers.CharField()
    points_available = serializers.FloatField()
    options = serializers.ListField(
        child=serializers.CharField(), help_text="For a skill group, the tools that'd count"
    )


class DemoBenchmarkInfoSerializer(serializers.Serializer):
    school = serializers.CharField()
    location = serializers.CharField()
    postings_used = serializers.IntegerField(
        help_text='How many postings the benchmark is built from'
    )
    seniorities_used = serializers.CharField(help_text="'intern/entry' or 'all'")


class StudentBenchmarkDemoSerializer(BenchmarkResultSerializer):
    """BenchmarkResultSerializer (overall score + GP-40 gap breakdown for
    skills and courses) plus everything the demo dashboard shows."""

    role = RoleSerializer()
    benchmark = DemoBenchmarkInfoSerializer()
    skills = SkillsResultSerializer()
    courses = CoursesResultSerializer()
    certificates = CertificatesResultSerializer()
    next_steps = NextStepSerializer(many=True)
