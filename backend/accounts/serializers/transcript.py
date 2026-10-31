from rest_framework import serializers

from .academic_records import TakenClassSerializer

MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024


class TranscriptUploadSerializer(serializers.Serializer):
    """The multipart upload. The file is only checked to be a PDF here.
    accounts/transcript.py decides whether it's a readable transcript."""

    file = serializers.FileField()
    # Parse and report what would be imported, without saving anything. This lets
    # the frontend show a review step before the real upload.
    dry_run = serializers.BooleanField(default=False)

    def validate_file(self, value):
        if value.size > MAX_TRANSCRIPT_BYTES:
            raise serializers.ValidationError('Transcript must be 5 MB or smaller.')
        header = value.read(5)
        value.seek(0)
        if not value.name.lower().endswith('.pdf') or header != b'%PDF-':
            raise serializers.ValidationError('Upload your transcript as a PDF.')
        return value


# Response-only serializers, for drf-spectacular. See TranscriptUploadView.


class SkippedCourseSerializer(serializers.Serializer):
    course_code = serializers.CharField()
    course_name = serializers.CharField()
    # Null for transfer/AP credit, which has no term.
    semester = serializers.CharField(allow_null=True)
    year = serializers.IntegerField(allow_null=True)
    reason = serializers.CharField()


class TranscriptResultSerializer(serializers.Serializer):
    # The saved classes. Or on a dry run, the ones that would be saved (no
    # id/created_at/updated_at yet).
    courses = TakenClassSerializer(many=True)
    skipped = SkippedCourseSerializer(many=True)
    # Lines that looked like a course but couldn't be read, as-is.
    unparsed = serializers.ListField(child=serializers.CharField())
